import math
import pandas as pd
from sqlalchemy import text

ESTADO_PDB_CONFIG = {
    "PDB1": {"A": {"actual": 115.0, "limite": 160.0}, 
             "B": {"actual": 149.0, "limite": 160.0}},

    "PDB2": {"A": {"actual": 4.5, "limite": 250.0}, 
             "B": {"actual": 1.3, "limite": 250.0}}
}

CONSTANTES_FISICAS = {
    "VOLTAJE_DC": 54.0,
    "VOLTAJE_AC": 220.0,
    "EFICIENCIA_RECT": 0.94,
    "FP_EQUIPO": 0.98,
    "CAPACIDAD_TR_KVA": 75.0, 
    "LIMITE_SEGURIDAD": 0.90
}

CAPACIDAD_CABLES = {
    "1/0": 200.0,
    "4/0": 250.0,
    "Barraje": 250.0, 
    "0": 0.0,
    "None": 0.0
}

def obtener_configuracion_actual():
    """
    Retorna las constantes para ser visualizadas en la interfaz 
    """
    return {
        "Constantes Físicas": CONSTANTES_FISICAS,
        "Configuración PDBs": ESTADO_PDB_CONFIG
    }

def _obtener_estado_actual_db(engine):
    """
    Consulta la base de datos (tablas _dce) para obtener la ÚLTIMA lectura real.
    Retorna un diccionario con los valores operativos actuales.
    """
    estado = {
        "tr_amps_ac": 0.0,
        "tr_kva": 0.0,
        "ml_amps_ac": 0.0,
        "r1_amps_dc": 0.0,
        "r2_amps_dc": 0.0
    }
    
    with engine.connect() as conn:
        try:
            # 1. TR (transferencia)
            # Promediamos las 3 fases de corriente y traemos la potencia aparente
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
                estado["tr_kva"] = float(res_tr[1] or 0)

            # 2. ML (Tablero Principal)
            sql_ml = text("""
                SELECT (corriente_ac_r + corriente_ac_s + corriente_ac_t) / 3 as prom_amps
                FROM ml_dce 
                ORDER BY fecha DESC LIMIT 1
            """)
            res_ml = conn.execute(sql_ml).fetchone()
            if res_ml:
                estado["ml_amps_ac"] = float(res_ml[0] or 0)

            # 3. Rectificadores (Tabla unificada rect_dce)
            # Rectificador 1
            sql_r1 = text("SELECT corriente_dc_total FROM rect_dce WHERE rectificador_id = 1 ORDER BY fecha DESC LIMIT 1")
            res_r1 = conn.execute(sql_r1).fetchone()
            if res_r1: estado["r1_amps_dc"] = float(res_r1[0] or 0)

            # Rectificador 2
            sql_r2 = text("SELECT corriente_dc_total FROM rect_dce WHERE rectificador_id = 2 ORDER BY fecha DESC LIMIT 1")
            res_r2 = conn.execute(sql_r2).fetchone()
            if res_r2: estado["r2_amps_dc"] = float(res_r2[0] or 0)

        except Exception as e:
            print(f"⚠️ Error consultando estado actual en BD: {e}")
            # En caso de error, el sistema usará 0.0 (modo seguro) o podrías poner los promedios fijos aquí como fallback.
            
    return estado

def _calcular_corriente_ac_trifasica(potencia_dc_w):
    potencia_ac_w = potencia_dc_w / CONSTANTES_FISICAS["EFICIENCIA_RECT"]
    return potencia_ac_w / (math.sqrt(3) * CONSTANTES_FISICAS["VOLTAJE_AC"] * CONSTANTES_FISICAS["FP_EQUIPO"])

def _buscar_espacio_pdb(engine, fuentes_requeridas, pdb_nombre=None):
    """
    Si pdb_nombre se especifica, solo consulta ese PDB y retorna sus posiciones libres.
    Si no se especifica, busca en PDB1 y PDB2 en orden y retorna el primero con espacio.
    """
    necesarias_a = math.ceil(fuentes_requeridas / 2)
    necesarias_b = fuentes_requeridas // 2

    if pdb_nombre:
        # Modo: obtener posiciones de un PDB ya elegido
        sql = f"""SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb 
                  WHERE UPPER(pdb_nombre) = '{pdb_nombre.upper()}' 
                  AND UPPER(estado) IN ('DISPONIBLE', 'LIBRE') 
                  ORDER BY posicion ASC"""
        df = pd.read_sql(sql, engine)
        df['fuente'] = df['fuente'].str.strip().str.upper()
        df['pdb_nombre'] = df['pdb_nombre'].str.strip().str.upper()

        opciones_a = df[df['fuente'].str.contains('A')].iloc[:necesarias_a]
        opciones_b = df[df['fuente'].str.contains('B')].iloc[:necesarias_b]

        seleccionados = []
        for _, r in opciones_a.iterrows():
            seleccionados.append(f"- Fuente A: {r['pdb_nombre']} - Pos {r['posicion']}")
        for _, r in opciones_b.iterrows():
            seleccionados.append(f"- Fuente B: {r['pdb_nombre']} - Pos {r['posicion']}")

        return True, "\n".join(seleccionados), pdb_nombre

    # Modo legado: buscar en todos los PDBs
    sql = """
    SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb 
    WHERE UPPER(estado) IN ('DISPONIBLE', 'LIBRE') ORDER BY pdb_nombre ASC, posicion ASC"""
    
    df_libres = pd.read_sql(sql, engine)
    df_libres['fuente'] = df_libres['fuente'].str.strip().str.upper()
    df_libres['pdb_nombre'] = df_libres['pdb_nombre'].str.strip().str.upper()

    for pdb_cand in ['PDB1', 'PDB2']:

        df_cand = df_libres[df_libres['pdb_nombre'] == pdb_cand]
        disp_a = len(df_cand[df_cand['fuente'].str.contains('A')])
        disp_b = len(df_cand[df_cand['fuente'].str.contains('B')])

        if disp_a >= necesarias_a and disp_b >= necesarias_b:

            opciones_a = df_cand[df_cand['fuente'].str.contains('A')].iloc[:necesarias_a]
            opciones_b = df_cand[df_cand['fuente'].str.contains('B')].iloc[:necesarias_b]
            seleccionados = []

            for _, r in opciones_a.iterrows():
                seleccionados.append(f"- Fuente A: {r['pdb_nombre']} - Pos {r['posicion']}")

            for _, r in opciones_b.iterrows():
                seleccionados.append(f"- Fuente B: {r['pdb_nombre']} - Pos {r['posicion']}")

            return True, "\n".join(seleccionados), pdb_cand

    return False, "[FALLO] INSUFICIENTE ESPACIO FÍSICO en PDBs.", None

def _validar_capacidad_electrica_pdb(pdb_nombre, fuentes_requeridas, amps_nuevos_totales):
    """
    Valida usando los datos de configuración (Manuales del PDB).
    Nota: Aquí seguimos usando ESTADO_PDB_CONFIG porque los PDBs no tienen sensores en tiempo real.
    """
    if pdb_nombre not in ESTADO_PDB_CONFIG: return False, ["Datos no encontrados"]
    datos_pdb = ESTADO_PDB_CONFIG[pdb_nombre]
    checks = []
    aprobado = True
    
    # Validamos asumiendo carga total en una fuente (Redundancia)
    amps_por_fuente = amps_nuevos_totales 
    
    '''
    for fuente in ['A', 'B']:
        if fuente == 'B' and fuentes_requeridas < 2: continue # Si solo pide 1 fuente, quizás no validamos B (depende lógica)
        
        info = datos_pdb.get(fuente)
        futuro = info['manual'] + amps_por_fuente # Usamos el dato manual (medición con pinza)
        
        if futuro > info['limite']:
            checks.append(f"[FALLO] SOBRECARGA {pdb_nombre}-{fuente}: Manual {info['manual']}A + Nuevo {amps_por_fuente:.1f}A = {futuro:.1f}A > {info['limite']}A")
            aprobado = False
        else:
            checks.append(f"[OK] {pdb_nombre}-{fuente} OK: {futuro:.1f}A (Límite {info['limite']}A)")

    '''

    info_a = datos_pdb.get("A")
    futuro_a = info_a['actual'] + amps_por_fuente
    if futuro_a > info_a['limite']:
        checks.append(f"[FALLO] SOBRECARGA {pdb_nombre}-A: {info_a['actual']} + {amps_por_fuente:.1f} = {futuro_a:.1f}A > {info_a['limite']}A")
        aprobado = False
    else:
        checks.append(f"[OK] {pdb_nombre}-A OK: {futuro_a:.1f}A (Limite {info_a['limite']}A)")

    if fuentes_requeridas >= 2:
        info_b = datos_pdb.get("B")
        futuro_b = info_b['actual'] + amps_por_fuente
        if futuro_b > info_b['limite']:
            checks.append(f"[FALLO] SOBRECARGA {pdb_nombre}-B: {info_b['actual']} + {amps_por_fuente:.1f} = {futuro_b:.1f}A > {info_b['limite']}A")
            aprobado = False
        else:
            checks.append(f"[OK] {pdb_nombre}-B OK: {futuro_b:.1f}A (Limite {info_b['limite']}A)")
            
    return aprobado, checks

def _validar_protecciones_aguas_arriba(engine, pdb_seleccionado, potencia_total_w, amps_nuevos_dc):
    checks = []
    aprobado = True
    
    # 1. OBTENER DATOS REALES DE BD (Carga Base)
    # Ya no usamos valores fijos, llamamos a la función que consulta MySQL
    estado_real = _obtener_estado_actual_db(engine)
    
    # print(estado_real)

    # Extraemos los valores del diccionario
    carga_actual_tr_ac = estado_real["tr_amps_ac"]
    carga_actual_ml_ac = estado_real["ml_amps_ac"]
    cargas_rect_dc = {
        "Rect1": estado_real["r1_amps_dc"],
        "Rect2": estado_real["r2_amps_dc"]
    }

    # 2. CÁLCULOS GENERALES
    amps_nuevos_ac_total = _calcular_corriente_ac_trifasica(potencia_total_w)
    
    # Definimos la asociación física (Topología Cruzada)
    # Fuente A (de cualquier PDB) -> Rectificador 1
    # Fuente B (de cualquier PDB) -> Rectificador 2
    
    # Identificamos qué rectificador recibe la CARGA NUEVA principal
    # Si es PDB1, asumimos que se carga prioritariamente en A (Rect1) y B (Rect2)
    # Pero para validación de protecciones individuales, necesitamos saber cuál fusible se afecta.
    
    # NOTA: En diseño redundante A+B, AMBOS rectificadores reciben carga.
    # Pero para pruebas de estrés, asumimos que uno puede fallar y el otro lleva todo.
    # Aquí validaremos que AMBOS caminos aguanten la carga completa (Peor caso).

    with engine.connect() as conn:
        
        # --- A. VALIDACIÓN DE AMBOS RECTIFICADORES ---
        rectificadores = [
            {"nombre": "Rect1", "fuente_asoc": "A"}, 
            {"nombre": "Rect2", "fuente_asoc": "B"}
        ]

        for r in rectificadores:
            nombre_rect = r['nombre']
            fuente_letra = r['fuente_asoc']
            
            # Carga Base actual de este rectificador
            carga_base = cargas_rect_dc[nombre_rect]
            
            # ESCENARIO DE VALIDACIÓN:
            # Asumimos que la nueva carga se conecta a este rectificador (por redundancia o balanceo)
            carga_dc_evaluada = carga_base + amps_nuevos_dc
            
            # Nombre dinámico del fusible: Ej "Fusible PDB1 A"
            nombre_fusible_dyn = f"Fusible {pdb_seleccionado} {fuente_letra}"
            
            # 1. FUSIBLE DC Y CABLE
            sql_fus = text("""
                SELECT capacidad_amps, calibre_cable_salida 
                FROM protecciones 
                WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'
            """)
            # Usamos LIKE porque a veces el nombre en BD tiene espacios extra
            res_fus = conn.execute(sql_fus, {"rect": nombre_rect, "fus": nombre_fusible_dyn}).fetchone()
            
            if res_fus:
                limite_fusible = res_fus[0]
                calibre_dc = str(res_fus[1])
                
                # Check Fusible
                if carga_dc_evaluada > limite_fusible:
                    checks.append(f"[FALLO] SOBRECARGA FUSIBLE DC ({nombre_rect} -> {pdb_seleccionado}): {carga_dc_evaluada:.1f}A > {limite_fusible}A")
                    aprobado = False
                else:
                    checks.append(f"[OK] Fusible DC {nombre_rect} ({fuente_letra}) OK: {carga_dc_evaluada:.1f}A (Límite {limite_fusible}A)")
                
                # Check Cable DC
                limite_cable_dc = CAPACIDAD_CABLES.get(calibre_dc, 0.0)
                if limite_cable_dc > 0:
                    if carga_dc_evaluada > limite_cable_dc:
                        checks.append(f"[FALLO] CABLE DC INSUFICIENTE ({nombre_rect}): Tipo {calibre_dc} soporta {limite_cable_dc}A, carga {carga_dc_evaluada:.1f}A")
                        aprobado = False
                    else:
                        checks.append(f"[OK] Cable DC {nombre_rect} ({calibre_dc}) OK")
            else:
                # Si no encuentra el fusible, es una advertencia de datos, no necesariamente un fallo técnico
                checks.append(f"[ADVERTENCIA] No se encontró en BD: {nombre_fusible_dyn} en {nombre_rect}")

            # 2. BREAKER AC Y CABLE (Entrada del Rectificador)
            nombre_breaker = f"Breaker {nombre_rect}"
            sql_brk = text("""
                SELECT capacidad_amps, calibre_cable_salida 
                FROM protecciones 
                WHERE componente = :comp AND tipo = 'AC'
            """)
            res_brk = conn.execute(sql_brk, {"comp": nombre_breaker}).fetchone()
            
            # Convertimos la carga DC total evaluada a AC
            watts_rect = carga_dc_evaluada * CONSTANTES_FISICAS["VOLTAJE_DC"]
            amps_ac_rect = _calcular_corriente_ac_trifasica(watts_rect)

            if res_brk:
                limite_brk = res_brk[0]
                calibre_ac = str(res_brk[1])

                # Check Breaker
                if amps_ac_rect > limite_brk:
                    checks.append(f"[FALLO] SOBRECARGA BREAKER AC ({nombre_rect}): {amps_ac_rect:.1f}A > {limite_brk}A")
                    aprobado = False
                else:
                    checks.append(f"[OK] Breaker AC {nombre_rect} OK: {amps_ac_rect:.1f}A (Límite {limite_brk}A)")
                
                # Check Cable AC
                limite_cable_ac = CAPACIDAD_CABLES.get(calibre_ac, 0.0)
                if limite_cable_ac > 0 and amps_ac_rect > limite_cable_ac:
                    checks.append(f"[FALLO] CABLE AC RECT INSUFICIENTE: {calibre_ac} soporta {limite_cable_ac}A, carga {amps_ac_rect:.1f}A")
                    aprobado = False
                elif limite_cable_ac > 0:
                    checks.append(f"[OK] Cable AC {nombre_rect} ({calibre_ac}) OK")

        # --- B. TOTALIZADORES GENERALES (ML y TR) ---
        
        # ML
        futuro_ml = carga_actual_ml_ac + amps_nuevos_ac_total
        sql_ml = text("SELECT capacidad_amps, calibre_cable_salida FROM protecciones WHERE componente = 'Totalizador ML' AND tipo = 'AC'")
        res_ml = conn.execute(sql_ml).fetchone()
        
        if res_ml:
            limite_ml = res_ml[0]
            calibre_ml = str(res_ml[1])
            if futuro_ml > limite_ml:
                checks.append(f"[FALLO] SOBRECARGA ML: {futuro_ml:.1f}A > {limite_ml}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador ML OK: {futuro_ml:.1f}A (Límite {limite_ml}A)")
            
            # Cable ML
            limite_c_ml = CAPACIDAD_CABLES.get(calibre_ml, 0.0)
            if limite_c_ml > 0 and futuro_ml > limite_c_ml:
                 checks.append(f"[FALLO] CABLE ML EXCEDIDO: {futuro_ml:.1f}A > {limite_c_ml}A")
                 aprobado = False

        # TR
        futuro_tr = carga_actual_tr_ac + amps_nuevos_ac_total
        sql_tr = text("SELECT capacidad_amps, calibre_cable_salida FROM protecciones WHERE componente = 'Totalizador Red' AND tipo = 'AC'")
        res_tr = conn.execute(sql_tr).fetchone()
        
        if res_tr:
            limite_tr = res_tr[0]
            calibre_tr = str(res_tr[1])
            if futuro_tr > limite_tr:
                checks.append(f"[FALLO] SOBRECARGA TR (Amps): {futuro_tr:.1f}A > {limite_tr}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador TR OK: {futuro_tr:.1f}A (Límite {limite_tr}A)")
            
            # Cable TR
            limite_c_tr = CAPACIDAD_CABLES.get(calibre_tr, 0.0)
            if limite_c_tr > 0 and futuro_tr > limite_c_tr:
                 checks.append(f"[FALLO] CABLE TR EXCEDIDO: {futuro_tr:.1f}A > {limite_c_tr}A")
                 aprobado = False

    return aprobado, checks

def _generar_ruta_dinamica(engine, pdb_seleccionado):
    """
    Construye la lista de conexiones leyendo los calibres reales de la BD.
    """
    ruta = []
    
    # 1. Definir nombres para buscar en BD
    # Nota: Fusible PDB1 A está en Rect1, Fusible PDB1 B está en Rect2
    fusible_a = f"Fusible {pdb_seleccionado} A"
    fusible_b = f"Fusible {pdb_seleccionado} B"
    
    with engine.connect() as conn:
        def get_calibre(comp):
            res = conn.execute(text("SELECT calibre_cable_salida FROM protecciones WHERE componente = :c"), {"c": comp}).fetchone()
            return str(res[0]) if res else "?"

        # Consultamos los calibres reales
        cal_fus_a = get_calibre(fusible_a)
        cal_fus_b = get_calibre(fusible_b)
        cal_brk_r1 = get_calibre("Breaker Rect1")
        cal_brk_r2 = get_calibre("Breaker Rect2")
        cal_tr = get_calibre("Totalizador Red")
        
        # Construimos la lista
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

    informe = {
        "Equipment": datos_entrada.get("Equipment"),
        "Checks": [],
        "Recomendacion_Instalacion": "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO",
        "Ruta_Conexion": [] 
    }

    estado_real = _obtener_estado_actual_db(engine)
    
    # ... (Cálculos de potencia y fuentes igual) ...
    potencia_w = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total_dc = potencia_w * cantidad
    amps_nuevos_dc = potencia_total_dc / CONSTANTES_FISICAS["VOLTAJE_DC"]
    fuentes = int(datos_entrada.get("Power sources", 1))

    # --- FAILOVER LOOP ---
    pdbs_a_evaluar = ["PDB1", "PDB2"]
    pdb_ganador = None
    
    for pdb_candidato in pdbs_a_evaluar:
        # A. Espacio (Igual)
        sql_libres = f"SELECT * FROM inventario_dc_pdb WHERE pdb_nombre = '{pdb_candidato}' AND UPPER(estado) IN ('DISPONIBLE', 'LIBRE')"
        df_libres = pd.read_sql(sql_libres, engine)
        req_a = math.ceil(fuentes/2)
        req_b = fuentes // 2
        hay_a = len(df_libres[df_libres['fuente'].str.contains('A')]) >= req_a
        hay_b = len(df_libres[df_libres['fuente'].str.contains('B')]) >= req_b
        
        if not (hay_a and hay_b):
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por falta de espacio físico.")
            continue 

        # B. Eléctrico (Igual)
        electrico_ok, msgs_electrico = _validar_capacidad_electrica_pdb(pdb_candidato, fuentes, amps_nuevos_dc)
        if not electrico_ok:
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por capacidad eléctrica.")
            for m in msgs_electrico: informe["Checks"].append(m.replace("[FALLO]", "[INFO]"))
            continue

        # C. Aguas Arriba (Igual)
        protec_ok, msgs_protec = _validar_protecciones_aguas_arriba(engine, pdb_candidato, potencia_total_dc, amps_nuevos_dc)
        if not protec_ok:
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por protecciones aguas arriba.")
            for m in msgs_protec: informe["Checks"].append(m.replace("[FALLO]", "[INFO]"))
            continue
            
        # GANADOR
        pdb_ganador = pdb_candidato
        _, detalle_pos, _ = _buscar_espacio_pdb(engine, fuentes, pdb_nombre=pdb_ganador) # Posiciones del PDB ganador
        informe["Recomendacion_Instalacion"] = f"Instalación APROBADA en {pdb_ganador}\n{detalle_pos}"
        informe["Checks"].extend(msgs_electrico)
        informe["Checks"].extend(msgs_protec)
        
        # Generar Ruta Dinámica ---
        informe["Ruta_Conexion"] = _generar_ruta_dinamica(engine, pdb_ganador)
        break

    if not pdb_ganador:
        informe["Checks"].append("[FALLO] RECHAZADO FINAL: Ningún PDB cumple requisitos.")
        return informe


    # N+1
    #carga_total = 118.67 + 155.96 + amps_nuevos_dc
    r1_corriente_dc_total = estado_real["r1_amps_dc"]
    r2_corriente_dc_total = estado_real["r2_amps_dc"]
    carga_total = r1_corriente_dc_total + r2_corriente_dc_total + amps_nuevos_dc

    if carga_total > 1000.0: 
        informe["Checks"].append(f"[FALLO] REDUNDANCIA N+1: Carga {carga_total:.1f}A > 1000A.")
        return informe
    else: 
        informe["Checks"].append(f"[OK] Redundancia N+1 OK: Carga {carga_total:.1f}A soportada.")
    

    
    # TR kVA
    #kva_actual = 22.372
    kva_actual = estado_real["tr_kva"]

    pot_ac = potencia_total_dc / CONSTANTES_FISICAS["EFICIENCIA_RECT"]
    kva_nuevo = (pot_ac / 1000) / CONSTANTES_FISICAS["FP_EQUIPO"]
    kva_futuro = kva_actual + kva_nuevo
    limite_tr = CONSTANTES_FISICAS["CAPACIDAD_TR_KVA"] * CONSTANTES_FISICAS["LIMITE_SEGURIDAD"]
    if kva_futuro > limite_tr: 
        informe["Checks"].append(f"[FALLO] Sobrecarga TR: {kva_futuro:.1f} > {limite_tr:.1f} kVA.")
        return informe
    else: 
        informe["Checks"].append(f"[OK] Transformador Potencia OK: {kva_actual:.1f} -> {kva_futuro:.1f} kVA (Límite {limite_tr:.1f} kVA).")


    informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"
    # print(informe)
    return informe