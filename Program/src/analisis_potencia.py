"""
analisis_potencia.py — Módulo de Lógica y Evaluación Técnica
──────────────────────────────────────────────────────────────────────────────
Este módulo es el núcleo técnico del sistema. Determina si un nuevo equipo
puede instalarse en el nodo evaluando una cadena de validaciones eléctricas
en cascada.

La evaluación sigue la topología real del sistema eléctrico del nodo:

    Red / Planta Diesel
          ↓
    Transformador (TR) — 75 kVA
          ↓
    Tablero Principal (ML)
          ↓
    Rectificador 1 / Rectificador 2  (CC 48V)
          ↓
    PDB1 / PDB2  (Tableros de Distribución DC)
          ↓
    Racks con equipos

El proceso de evaluación intenta primero con PDB1. Si falla alguna validación,
intenta automáticamente con PDB2 antes de emitir un rechazo definitivo.
──────────────────────────────────────────────────────────────────────────────
"""

import math
import pandas as pd
from sqlalchemy import text

# ─────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE LOS PDB
#  Carga actual medida en campo (con pinza amperimétrica) por fuente.
#  Como los PDB no tienen sensores en tiempo real en el sistema de monitoreo,
#  estos valores se ingresan manualmente tras cada medición en sitio.
# ─────────────────────────────────────────────────────────────
ESTADO_PDB_CONFIG = {
    "PDB1": {"A": {"actual": 115.0, "limite": 160.0},
             "B": {"actual": 149.0, "limite": 160.0}},

    "PDB2": {"A": {"actual": 4.5,   "limite": 250.0},
             "B": {"actual": 1.3,   "limite": 250.0}}
}

# ─────────────────────────────────────────────────────────────
#  CONSTANTES FÍSICAS DEL NODO
#  Valores fijos de la infraestructura eléctrica del nodo IDEO Cali.
#  LIMITE_SEGURIDAD: se opera al 90% de la capacidad nominal del transformador
#  para mantener margen de seguridad ante picos de carga.
# ─────────────────────────────────────────────────────────────
CONSTANTES_FISICAS = {
    "VOLTAJE_DC":        54.0,    # Voltaje nominal DC de salida del rectificador (V)
    "VOLTAJE_AC":        220.0,   # Voltaje nominal AC de la red (V)
    "EFICIENCIA_RECT":   0.94,    # Eficiencia del rectificador (94%)
    "FP_EQUIPO":         0.98,    # Factor de potencia de los equipos DC
    "CAPACIDAD_TR_KVA":  75.0,    # Capacidad nominal del transformador (kVA)
    "LIMITE_SEGURIDAD":  0.90     # Límite operativo: 90% de la capacidad nominal
}

# ─────────────────────────────────────────────────────────────
#  CAPACIDAD DE CABLES
#  Corriente máxima admisible según el calibre del cable (A).
#  Los calibres son los reales del nodo, obtenidos en el levantamiento físico.
# ─────────────────────────────────────────────────────────────
CAPACIDAD_CABLES = {
    "1/0":    200.0,
    "4/0":    250.0,
    "Barraje": 250.0,
    "0":        0.0,
    "None":     0.0
}


def obtener_configuracion_actual():
    """
    Retorna las constantes y configuración del nodo para visualización en la interfaz.
    Permite al usuario ver los parámetros con los que trabaja el evaluador.
    """
    return {
        "Constantes Físicas": CONSTANTES_FISICAS,
        "Configuración PDBs": ESTADO_PDB_CONFIG
    }


def _obtener_estado_actual_db(engine):
    """
    Consulta MySQL para obtener la ÚLTIMA lectura real de cada equipo.

    Esta función es la que conecta la evaluación con los datos en tiempo real.
    En lugar de usar valores fijos, trae la corriente y potencia actuales
    del transformador, tablero ML y rectificadores directamente de la BD,
    lo que hace que cada evaluación refleje el estado real del nodo
    en el momento en que se ejecuta.

    Retorna un diccionario con:
        tr_amps_ac : corriente promedio de las 3 fases del TR (A)
        tr_kva     : potencia aparente actual del TR (kVA)
        ml_amps_ac : corriente promedio de las 3 fases del ML (A)
        r1_amps_dc : corriente DC total del Rectificador 1 (A)
        r2_amps_dc : corriente DC total del Rectificador 2 (A)
    """
    estado = {
        "tr_amps_ac": 0.0,
        "tr_kva":     0.0,
        "ml_amps_ac": 0.0,
        "r1_amps_dc": 0.0,
        "r2_amps_dc": 0.0
    }

    with engine.connect() as conn:
        try:
            # TR: promedio de corriente en las 3 fases + potencia aparente
            # Se usa LIMIT 1 con ORDER BY fecha DESC para obtener la lectura más reciente
            sql_tr = text("""
                SELECT
                    (corriente_ac_l1 + corriente_ac_l2 + corriente_ac_l3) / 3 as prom_amps,
                    potencia_aparente_kva
                FROM tr_dce
                ORDER BY fecha DESC LIMIT 1
            """)
            res_tr = conn.execute(sql_tr).fetchone()
            if res_tr:
                estado["tr_amps_ac"] = float(res_tr[0] or 0)
                estado["tr_kva"]     = float(res_tr[1] or 0)

            # ML: promedio de corriente en las 3 fases (R, S, T)
            sql_ml = text("""
                SELECT (corriente_ac_r + corriente_ac_s + corriente_ac_t) / 3 as prom_amps
                FROM ml_dce
                ORDER BY fecha DESC LIMIT 1
            """)
            res_ml = conn.execute(sql_ml).fetchone()
            if res_ml:
                estado["ml_amps_ac"] = float(res_ml[0] or 0)

            # Rectificador 1: corriente DC total de salida
            sql_r1 = text("""
                SELECT corriente_dc_total FROM rect_dce
                WHERE rectificador_id = 1 ORDER BY fecha DESC LIMIT 1
            """)
            res_r1 = conn.execute(sql_r1).fetchone()
            if res_r1:
                estado["r1_amps_dc"] = float(res_r1[0] or 0)

            # Rectificador 2: corriente DC total de salida
            sql_r2 = text("""
                SELECT corriente_dc_total FROM rect_dce
                WHERE rectificador_id = 2 ORDER BY fecha DESC LIMIT 1
            """)
            res_r2 = conn.execute(sql_r2).fetchone()
            if res_r2:
                estado["r2_amps_dc"] = float(res_r2[0] or 0)

        except Exception as e:
            # En caso de error de BD, se devuelven valores 0 (modo seguro)
            print(f"⚠️ Error consultando estado actual en BD: {e}")

    return estado


def _calcular_corriente_ac_trifasica(potencia_dc_w):
    """
    Convierte la potencia DC del nuevo equipo a corriente AC equivalente.

    Esta conversión es necesaria para validar las protecciones del lado AC
    (breakers del rectificador, totalizador ML, transformador).

    Fórmula aplicada:
        1. Potencia AC = Potencia DC / Eficiencia del rectificador
        2. Corriente AC = Potencia AC / (√3 × Voltaje AC × Factor de Potencia)

    La división por √3 × V corresponde a la fórmula de potencia trifásica,
    ya que el sistema AC del nodo es trifásico a 220V.
    """
    potencia_ac_w = potencia_dc_w / CONSTANTES_FISICAS["EFICIENCIA_RECT"]
    return potencia_ac_w / (math.sqrt(3) * CONSTANTES_FISICAS["VOLTAJE_AC"] * CONSTANTES_FISICAS["FP_EQUIPO"])


def _buscar_espacio_pdb(engine, fuentes_requeridas, pdb_nombre=None):
    """
    Busca posiciones físicas disponibles en los tableros de distribución (PDB).

    Cada equipo DC requiere una o dos fuentes de alimentación (redundancia).
    Esta función verifica si hay suficientes posiciones libres en las
    barras A y B del PDB para conectar el nuevo equipo.

    Si se especifica pdb_nombre, consulta solo ese PDB y retorna las posiciones
    disponibles. Si no se especifica, recorre PDB1 y PDB2 en orden y retorna
    el primero que tenga espacio suficiente.

    Retorna: (hay_espacio: bool, detalle_posiciones: str, pdb_candidato: str)
    """
    # Calcular cuántas posiciones se necesitan en cada barra
    # Si el equipo requiere 2 fuentes: 1 en barra A y 1 en barra B
    # Si requiere 1 fuente: solo barra A
    necesarias_a = math.ceil(fuentes_requeridas / 2)
    necesarias_b = fuentes_requeridas // 2

    if pdb_nombre:
        # Modo específico: consultar solo el PDB indicado
        sql = f"""SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb
                  WHERE UPPER(pdb_nombre) = '{pdb_nombre.upper()}'
                  AND UPPER(estado) IN ('DISPONIBLE', 'LIBRE')
                  ORDER BY posicion ASC"""
        df = pd.read_sql(sql, engine)
        df['fuente']    = df['fuente'].str.strip().str.upper()
        df['pdb_nombre'] = df['pdb_nombre'].str.strip().str.upper()

        opciones_a = df[df['fuente'].str.contains('A')].iloc[:necesarias_a]
        opciones_b = df[df['fuente'].str.contains('B')].iloc[:necesarias_b]

        seleccionados = []
        for _, r in opciones_a.iterrows():
            seleccionados.append(f"- Fuente A: {r['pdb_nombre']} - Pos {r['posicion']}")
        for _, r in opciones_b.iterrows():
            seleccionados.append(f"- Fuente B: {r['pdb_nombre']} - Pos {r['posicion']}")

        return True, "\n".join(seleccionados), pdb_nombre

    # Modo automático: buscar en todos los PDB en orden de prioridad
    sql = """
        SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb
        WHERE UPPER(estado) IN ('DISPONIBLE', 'LIBRE')
        ORDER BY pdb_nombre ASC, posicion ASC"""

    df_libres            = pd.read_sql(sql, engine)
    df_libres['fuente']   = df_libres['fuente'].str.strip().str.upper()
    df_libres['pdb_nombre'] = df_libres['pdb_nombre'].str.strip().str.upper()

    for pdb_cand in ['PDB1', 'PDB2']:
        df_cand = df_libres[df_libres['pdb_nombre'] == pdb_cand]
        disp_a  = len(df_cand[df_cand['fuente'].str.contains('A')])
        disp_b  = len(df_cand[df_cand['fuente'].str.contains('B')])

        if disp_a >= necesarias_a and disp_b >= necesarias_b:
            opciones_a    = df_cand[df_cand['fuente'].str.contains('A')].iloc[:necesarias_a]
            opciones_b    = df_cand[df_cand['fuente'].str.contains('B')].iloc[:necesarias_b]
            seleccionados = []

            for _, r in opciones_a.iterrows():
                seleccionados.append(f"- Fuente A: {r['pdb_nombre']} - Pos {r['posicion']}")
            for _, r in opciones_b.iterrows():
                seleccionados.append(f"- Fuente B: {r['pdb_nombre']} - Pos {r['posicion']}")

            return True, "\n".join(seleccionados), pdb_cand

    return False, "[FALLO] INSUFICIENTE ESPACIO FÍSICO en PDBs.", None


def _validar_capacidad_electrica_pdb(pdb_nombre, fuentes_requeridas, amps_nuevos_totales):
    """
    Valida que el PDB tenga capacidad eléctrica suficiente para la nueva carga.

    Usa los datos de ESTADO_PDB_CONFIG (mediciones manuales con pinza amperimétrica)
    porque los PDB del nodo no tienen sensores de monitoreo en tiempo real.

    La validación compara:
        Carga actual (medida) + Carga nueva (calculada) vs Límite del fusible/barra

    Se evalúa en el escenario de peor caso: toda la carga nueva cae sobre
    una sola fuente (simulando falla de la fuente redundante).

    Retorna: (aprobado: bool, lista_de_checks: list)
    """
    if pdb_nombre not in ESTADO_PDB_CONFIG:
        return False, ["Datos no encontrados"]

    datos_pdb       = ESTADO_PDB_CONFIG[pdb_nombre]
    checks          = []
    aprobado        = True
    amps_por_fuente = amps_nuevos_totales  # Peor caso: todo en una fuente

    # Validar barra A
    info_a    = datos_pdb.get("A")
    futuro_a  = info_a['actual'] + amps_por_fuente
    if futuro_a > info_a['limite']:
        checks.append(f"[FALLO] SOBRECARGA {pdb_nombre}-A: {info_a['actual']} + "
                      f"{amps_por_fuente:.1f} = {futuro_a:.1f}A > {info_a['limite']}A")
        aprobado = False
    else:
        checks.append(f"[OK] {pdb_nombre}-A OK: {futuro_a:.1f}A (Limite {info_a['limite']}A)")

    # Validar barra B solo si el equipo requiere 2 fuentes (redundancia)
    if fuentes_requeridas >= 2:
        info_b   = datos_pdb.get("B")
        futuro_b = info_b['actual'] + amps_por_fuente
        if futuro_b > info_b['limite']:
            checks.append(f"[FALLO] SOBRECARGA {pdb_nombre}-B: {info_b['actual']} + "
                          f"{amps_por_fuente:.1f} = {futuro_b:.1f}A > {info_b['limite']}A")
            aprobado = False
        else:
            checks.append(f"[OK] {pdb_nombre}-B OK: {futuro_b:.1f}A (Limite {info_b['limite']}A)")

    return aprobado, checks


def _validar_protecciones_aguas_arriba(engine, pdb_seleccionado, potencia_total_w, amps_nuevos_dc):
    """
    Valida todas las protecciones eléctricas entre el PDB y la red eléctrica.

    'Aguas arriba' significa recorrer el sistema eléctrico en sentido inverso:
    desde el punto de conexión del equipo hasta el transformador, verificando
    que cada protección en el camino soporte la carga adicional.

    Validaciones realizadas para cada rectificador (R1 y R2):
        A. Fusible DC y su cable (entre el PDB y el rectificador)
        B. Breaker AC y su cable (entrada del rectificador)

    Validaciones generales del sistema:
        C. Totalizador del Tablero ML (corriente AC total)
        D. Totalizador de la Red / Transformador (corriente AC total)

    Todos los límites se consultan desde la tabla 'protecciones' en MySQL,
    que fue cargada con los datos reales del levantamiento físico del nodo.

    Retorna: (aprobado: bool, lista_de_checks: list)
    """
    checks   = []
    aprobado = True

    # Obtener la carga base actual desde la BD (lecturas en tiempo real)
    estado_real      = _obtener_estado_actual_db(engine)
    carga_actual_tr_ac = estado_real["tr_amps_ac"]
    carga_actual_ml_ac = estado_real["ml_amps_ac"]
    cargas_rect_dc     = {
        "Rect1": estado_real["r1_amps_dc"],
        "Rect2": estado_real["r2_amps_dc"]
    }

    # Corriente AC equivalente que genera el nuevo equipo
    amps_nuevos_ac_total = _calcular_corriente_ac_trifasica(potencia_total_w)

    with engine.connect() as conn:

        # ── A y B: Validar protecciones de cada rectificador ──────────────
        # Topología del nodo: Fuente A del PDB → Rectificador 1
        #                     Fuente B del PDB → Rectificador 2
        rectificadores = [
            {"nombre": "Rect1", "fuente_asoc": "A"},
            {"nombre": "Rect2", "fuente_asoc": "B"}
        ]

        for r in rectificadores:
            nombre_rect  = r['nombre']
            fuente_letra = r['fuente_asoc']
            carga_base   = cargas_rect_dc[nombre_rect]

            # Carga proyectada: actual + nueva (se asume que ambos rectificadores
            # reciben la nueva carga por diseño redundante N+1)
            carga_dc_evaluada = carga_base + amps_nuevos_dc

            # A. FUSIBLE DC: protege el cable entre el rectificador y el PDB
            nombre_fusible = f"Fusible {pdb_seleccionado} {fuente_letra}"
            sql_fus = text("""
                SELECT capacidad_amps, calibre_cable_salida
                FROM protecciones
                WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'
            """)
            res_fus = conn.execute(sql_fus, {"rect": nombre_rect,
                                             "fus": nombre_fusible}).fetchone()

            if res_fus:
                limite_fusible = res_fus[0]
                calibre_dc     = str(res_fus[1])

                if carga_dc_evaluada > limite_fusible:
                    checks.append(f"[FALLO] SOBRECARGA FUSIBLE DC ({nombre_rect} -> "
                                  f"{pdb_seleccionado}): {carga_dc_evaluada:.1f}A > {limite_fusible}A")
                    aprobado = False
                else:
                    checks.append(f"[OK] Fusible DC {nombre_rect} ({fuente_letra}) OK: "
                                  f"{carga_dc_evaluada:.1f}A (Límite {limite_fusible}A)")

                # Verificar capacidad del cable DC
                limite_cable_dc = CAPACIDAD_CABLES.get(calibre_dc, 0.0)
                if limite_cable_dc > 0:
                    if carga_dc_evaluada > limite_cable_dc:
                        checks.append(f"[FALLO] CABLE DC INSUFICIENTE ({nombre_rect}): "
                                      f"Tipo {calibre_dc} soporta {limite_cable_dc}A, "
                                      f"carga {carga_dc_evaluada:.1f}A")
                        aprobado = False
                    else:
                        checks.append(f"[OK] Cable DC {nombre_rect} ({calibre_dc}) OK")
            else:
                checks.append(f"[ADVERTENCIA] No se encontró en BD: {nombre_fusible} en {nombre_rect}")

            # B. BREAKER AC: protege la entrada de corriente alterna del rectificador
            nombre_breaker = f"Breaker {nombre_rect}"
            sql_brk = text("""
                SELECT capacidad_amps, calibre_cable_salida
                FROM protecciones
                WHERE componente = :comp AND tipo = 'AC'
            """)
            res_brk = conn.execute(sql_brk, {"comp": nombre_breaker}).fetchone()

            # Convertir la carga DC evaluada a AC para comparar con el breaker
            watts_rect  = carga_dc_evaluada * CONSTANTES_FISICAS["VOLTAJE_DC"]
            amps_ac_rect = _calcular_corriente_ac_trifasica(watts_rect)

            if res_brk:
                limite_brk = res_brk[0]
                calibre_ac = str(res_brk[1])

                if amps_ac_rect > limite_brk:
                    checks.append(f"[FALLO] SOBRECARGA BREAKER AC ({nombre_rect}): "
                                  f"{amps_ac_rect:.1f}A > {limite_brk}A")
                    aprobado = False
                else:
                    checks.append(f"[OK] Breaker AC {nombre_rect} OK: "
                                  f"{amps_ac_rect:.1f}A (Límite {limite_brk}A)")

                # Verificar capacidad del cable AC
                limite_cable_ac = CAPACIDAD_CABLES.get(calibre_ac, 0.0)
                if limite_cable_ac > 0 and amps_ac_rect > limite_cable_ac:
                    checks.append(f"[FALLO] CABLE AC RECT INSUFICIENTE: "
                                  f"{calibre_ac} soporta {limite_cable_ac}A, "
                                  f"carga {amps_ac_rect:.1f}A")
                    aprobado = False
                elif limite_cable_ac > 0:
                    checks.append(f"[OK] Cable AC {nombre_rect} ({calibre_ac}) OK")

        # ── C: Totalizador ML ─────────────────────────────────────────────
        # Verifica que el tablero principal soporte la nueva corriente total
        futuro_ml = carga_actual_ml_ac + amps_nuevos_ac_total
        sql_ml    = text("""
            SELECT capacidad_amps, calibre_cable_salida FROM protecciones
            WHERE componente = 'Totalizador ML' AND tipo = 'AC'
        """)
        res_ml = conn.execute(sql_ml).fetchone()

        if res_ml:
            limite_ml  = res_ml[0]
            calibre_ml = str(res_ml[1])
            if futuro_ml > limite_ml:
                checks.append(f"[FALLO] SOBRECARGA ML: {futuro_ml:.1f}A > {limite_ml}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador ML OK: {futuro_ml:.1f}A (Límite {limite_ml}A)")

            limite_c_ml = CAPACIDAD_CABLES.get(calibre_ml, 0.0)
            if limite_c_ml > 0 and futuro_ml > limite_c_ml:
                checks.append(f"[FALLO] CABLE ML EXCEDIDO: {futuro_ml:.1f}A > {limite_c_ml}A")
                aprobado = False

        # ── D: Transformador (TR) ─────────────────────────────────────────
        # Verifica que el transformador soporte la nueva corriente total
        futuro_tr = carga_actual_tr_ac + amps_nuevos_ac_total
        sql_tr    = text("""
            SELECT capacidad_amps, calibre_cable_salida FROM protecciones
            WHERE componente = 'Totalizador Red' AND tipo = 'AC'
        """)
        res_tr = conn.execute(sql_tr).fetchone()

        if res_tr:
            limite_tr  = res_tr[0]
            calibre_tr = str(res_tr[1])
            if futuro_tr > limite_tr:
                checks.append(f"[FALLO] SOBRECARGA TR (Amps): {futuro_tr:.1f}A > {limite_tr}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador TR OK: {futuro_tr:.1f}A (Límite {limite_tr}A)")

            limite_c_tr = CAPACIDAD_CABLES.get(calibre_tr, 0.0)
            if limite_c_tr > 0 and futuro_tr > limite_c_tr:
                checks.append(f"[FALLO] CABLE TR EXCEDIDO: {futuro_tr:.1f}A > {limite_c_tr}A")
                aprobado = False

    return aprobado, checks


def _generar_ruta_dinamica(engine, pdb_seleccionado):
    """
    Construye la ruta de conexión eléctrica del nuevo equipo leyendo los
    calibres de cable reales desde la base de datos.

    La ruta describe el camino físico de la energía desde el PDB hasta
    el transformador, pasando por los rectificadores y el tablero ML.
    Esta información se incluye en el informe PDF de pre-factibilidad
    para guiar al técnico durante la instalación.
    """
    ruta = []

    fusible_a = f"Fusible {pdb_seleccionado} A"
    fusible_b = f"Fusible {pdb_seleccionado} B"

    with engine.connect() as conn:
        def get_calibre(comp):
            """Consulta el calibre del cable de un componente en la tabla protecciones."""
            res = conn.execute(
                text("SELECT calibre_cable_salida FROM protecciones WHERE componente = :c"),
                {"c": comp}
            ).fetchone()
            return str(res[0]) if res else "?"

        # Obtener los calibres reales de cada tramo del circuito
        cal_fus_a  = get_calibre(fusible_a)
        cal_fus_b  = get_calibre(fusible_b)
        cal_brk_r1 = get_calibre("Breaker Rect1")
        cal_brk_r2 = get_calibre("Breaker Rect2")
        cal_tr     = get_calibre("Totalizador Red")

        # Construir la descripción de la ruta de conexión
        ruta.append(f"{pdb_seleccionado} - Barraje - Totalizador Fuente A")
        ruta.append(f"{pdb_seleccionado} - Barraje - Totalizador Fuente B")
        ruta.append(f"Totalizador Fuente A - Cable {cal_fus_a} - {fusible_a} (Rect1)")
        ruta.append(f"Totalizador Fuente B - Cable {cal_fus_b} - {fusible_b} (Rect2)")
        ruta.append(f"Breaker Rect1 - Cable {cal_brk_r1} - Rect1")
        ruta.append(f"Breaker Rect2 - Cable {cal_brk_r2} - Rect2")
        ruta.append(f"Rect1 - Barraje - Totalizador ML")
        ruta.append(f"Rect2 - Barraje - Totalizador ML")
        ruta.append(f"Totalizador Red - Cable {cal_tr} - Totalizador ML")

    return ruta


def evaluar_solicitud(engine, datos_entrada):
    """
    Función principal del módulo: evalúa si una solicitud de instalación es viable.

    Recibe el diccionario de datos del equipo nuevo (potencia, fuentes, cantidad)
    y ejecuta todas las validaciones en cascada. Si PDB1 no pasa alguna validación,
    intenta automáticamente con PDB2 antes de emitir un rechazo definitivo.

    Validaciones en orden (para cada PDB candidato):
        1. Espacio físico disponible en el PDB (posiciones libres)
        2. Capacidad eléctrica del PDB (corriente por barra A y B)
        3. Protecciones aguas arriba (fusibles, breakers, ML, TR)

    Si un PDB pasa todas las validaciones (PDB ganador):
        4. Redundancia N+1: la carga total DC no debe superar 1000A
        5. Capacidad del transformador en kVA (límite operativo al 90%)

    Retorna un informe dict con:
        - Equipment           : nombre del equipo evaluado
        - Checks              : lista de resultados [OK] / [FALLO] / [ADVERTENCIA]
        - Recomendacion_Instalacion : instrucción de conexión si es aprobado
        - PRE-Factibilidad    : "SI" o "NO"
        - Ruta_Conexion       : ruta eléctrica completa del nuevo equipo
    """
    informe = {
        "Equipment":                                  datos_entrada.get("Equipment"),
        "Checks":                                     [],
        "Recomendacion_Instalacion":                  "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO",
        "Ruta_Conexion":                              []
    }

    estado_real    = _obtener_estado_actual_db(engine)

    # Calcular los amperios DC del nuevo equipo
    potencia_w      = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad        = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total_dc = potencia_w * cantidad
    amps_nuevos_dc  = potencia_total_dc / CONSTANTES_FISICAS["VOLTAJE_DC"]
    fuentes         = int(datos_entrada.get("Power sources", 1))

    # ── LOOP DE FAILOVER: intentar PDB1, luego PDB2 ───────────────────────
    # Si PDB1 falla en cualquier validación, se descarta y se intenta PDB2
    pdbs_a_evaluar = ["PDB1", "PDB2"]
    pdb_ganador    = None

    for pdb_candidato in pdbs_a_evaluar:

        # VALIDACIÓN 1: Espacio físico en el PDB
        sql_libres = (f"SELECT * FROM inventario_dc_pdb WHERE pdb_nombre = '{pdb_candidato}' "
                      f"AND UPPER(estado) IN ('DISPONIBLE', 'LIBRE')")
        df_libres  = pd.read_sql(sql_libres, engine)
        req_a = math.ceil(fuentes / 2)
        req_b = fuentes // 2
        hay_a = len(df_libres[df_libres['fuente'].str.contains('A')]) >= req_a
        hay_b = len(df_libres[df_libres['fuente'].str.contains('B')]) >= req_b

        if not (hay_a and hay_b):
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por falta de espacio físico.")
            continue

        # VALIDACIÓN 2: Capacidad eléctrica del PDB
        electrico_ok, msgs_electrico = _validar_capacidad_electrica_pdb(
            pdb_candidato, fuentes, amps_nuevos_dc)
        if not electrico_ok:
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por capacidad eléctrica.")
            for m in msgs_electrico:
                informe["Checks"].append(m.replace("[FALLO]", "[INFO]"))
            continue

        # VALIDACIÓN 3: Protecciones aguas arriba (fusibles, breakers, ML, TR)
        protec_ok, msgs_protec = _validar_protecciones_aguas_arriba(
            engine, pdb_candidato, potencia_total_dc, amps_nuevos_dc)
        if not protec_ok:
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por protecciones aguas arriba.")
            for m in msgs_protec:
                informe["Checks"].append(m.replace("[FALLO]", "[INFO]"))
            continue

        # PDB GANADOR: este PDB pasó todas las validaciones
        pdb_ganador = pdb_candidato
        _, detalle_pos, _ = _buscar_espacio_pdb(engine, fuentes, pdb_nombre=pdb_ganador)
        informe["Recomendacion_Instalacion"] = f"Instalación APROBADA en {pdb_ganador}\n{detalle_pos}"
        informe["Checks"].extend(msgs_electrico)
        informe["Checks"].extend(msgs_protec)
        informe["Ruta_Conexion"] = _generar_ruta_dinamica(engine, pdb_ganador)
        break

    # Si ningún PDB pasó las validaciones, rechazar definitivamente
    if not pdb_ganador:
        informe["Checks"].append("[FALLO] RECHAZADO FINAL: Ningún PDB cumple requisitos.")
        return informe

    # VALIDACIÓN 4: Redundancia N+1
    # La carga DC total (actual + nueva) no debe superar los 1000A,
    # que es la capacidad combinada de ambos rectificadores en el nodo
    r1_dc       = estado_real["r1_amps_dc"]
    r2_dc       = estado_real["r2_amps_dc"]
    carga_total = r1_dc + r2_dc + amps_nuevos_dc

    if carga_total > 1000.0:
        informe["Checks"].append(f"[FALLO] REDUNDANCIA N+1: Carga {carga_total:.1f}A > 1000A.")
        return informe
    else:
        informe["Checks"].append(f"[OK] Redundancia N+1 OK: Carga {carga_total:.1f}A soportada.")

    # VALIDACIÓN 5: Capacidad del transformador en kVA
    # El transformador de 75 kVA no debe superar el 90% de su capacidad (67.5 kVA)
    kva_actual = estado_real["tr_kva"]
    pot_ac     = potencia_total_dc / CONSTANTES_FISICAS["EFICIENCIA_RECT"]
    kva_nuevo  = (pot_ac / 1000) / CONSTANTES_FISICAS["FP_EQUIPO"]
    kva_futuro = kva_actual + kva_nuevo
    limite_tr  = CONSTANTES_FISICAS["CAPACIDAD_TR_KVA"] * CONSTANTES_FISICAS["LIMITE_SEGURIDAD"]

    if kva_futuro > limite_tr:
        informe["Checks"].append(f"[FALLO] Sobrecarga TR: {kva_futuro:.1f} > {limite_tr:.1f} kVA.")
        return informe
    else:
        informe["Checks"].append(f"[OK] Transformador Potencia OK: {kva_actual:.1f} -> "
                                 f"{kva_futuro:.1f} kVA (Límite {limite_tr:.1f} kVA).")

    # Todas las validaciones pasadas: PRE-FACTIBILIDAD APROBADA
    informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"
    return informe
