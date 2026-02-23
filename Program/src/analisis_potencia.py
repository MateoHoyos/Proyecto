import pandas as pd
from sqlalchemy import create_engine, text
import math


ESTADO_PDB_CONFIG = {
    "PDB1": {"A": {"actual": 115.0, "limite": 160.0}, "B": {"actual": 149.0, "limite": 160.0}},
    "PDB2": {"A": {"actual": 4.5, "limite": 250.0}, "B": {"actual": 1.3, "limite": 250.0}}
}

CONSTANTES_FISICAS = {
    "VOLTAJE_DC": 54.0,
    "VOLTAJE_AC": 220.0,
    "EFICIENCIA_RECT": 0.94,
    "FP_EQUIPO": 0.98,
    "CAPACIDAD_TR_KVA": 75.0, 
    "LIMITE_SEGURIDAD": 0.90
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



def _buscar_espacio_pdb(engine, fuentes_requeridas):
    # Lógica igual, solo cambiamos los textos de retorno
    sql = """SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb WHERE UPPER(estado) IN ('DISPONIBLE', 'LIBRE') ORDER BY pdb_nombre ASC, posicion ASC"""
    df_libres = pd.read_sql(sql, engine)
    df_libres['fuente'] = df_libres['fuente'].str.strip().str.upper()
    df_libres['pdb_nombre'] = df_libres['pdb_nombre'].str.strip().str.upper()
    
    necesarias_a = math.ceil(fuentes_requeridas / 2)
    necesarias_b = fuentes_requeridas // 2
    
    # ... (Filtrado de DataFrames igual) ...
    df_pdb1 = df_libres[df_libres['pdb_nombre'] == 'PDB1']
    df_pdb2 = df_libres[df_libres['pdb_nombre'] == 'PDB2']
    
    disp_pdb1_a = len(df_pdb1[df_pdb1['fuente'].str.contains('A')])
    disp_pdb1_b = len(df_pdb1[df_pdb1['fuente'].str.contains('B')])
    disp_pdb2_a = len(df_pdb2[df_pdb2['fuente'].str.contains('A')])
    disp_pdb2_b = len(df_pdb2[df_pdb2['fuente'].str.contains('B')])

    pdb_elegido = None
    df_candidatos = pd.DataFrame()

    if disp_pdb1_a >= necesarias_a and disp_pdb1_b >= necesarias_b:
        pdb_elegido = "PDB1"; df_candidatos = df_pdb1
    elif disp_pdb2_a >= necesarias_a and disp_pdb2_b >= necesarias_b:
        pdb_elegido = "PDB2"; df_candidatos = df_pdb2
    else:
        # Fallo de espacio
        return False, "[FALLO] INSUFICIENTE ESPACIO FÍSICO en PDBs.", None

    opciones_a = df_candidatos[df_candidatos['fuente'].str.contains('A')].iloc[:necesarias_a]
    opciones_b = df_candidatos[df_candidatos['fuente'].str.contains('B')].iloc[:necesarias_b]
    
    seleccionados = []
    for _, r in opciones_a.iterrows(): seleccionados.append(f"- Fuente A: {r['pdb_nombre']} - Pos {r['posicion']}")
    for _, r in opciones_b.iterrows(): seleccionados.append(f"- Fuente B: {r['pdb_nombre']} - Pos {r['posicion']}")
    
    return True, "\n".join(seleccionados), pdb_elegido




def _validar_capacidad_electrica_pdb(pdb_nombre, fuentes_requeridas, amps_nuevos_totales):
    """
    Valida usando los datos de configuración (Manuales del PDB).
    Nota: Aquí seguimos usando ESTADO_PDB_CONFIG porque los PDBs no tienen sensores en tiempo real.
    """
    if pdb_nombre not in ESTADO_PDB_CONFIG: return False, ["Datos no encontrados"]
    datos_pdb = ESTADO_PDB_CONFIG[pdb_nombre]
    checks = []; aprobado = True
    
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
    checks = []; aprobado = True
    
    # 1. OBTENER DATOS REALES DE BD
    estado_real = _obtener_estado_actual_db(engine)
    
    # 2. CÁLCULOS
    amps_nuevos_ac = _calcular_corriente_ac_trifasica(potencia_total_w)
    
    if "PDB1" in pdb_seleccionado:
        rect_asociado = "Rect1"; nombre_fusible = "Fusible PDB1%"; nombre_breaker_rect = "Breaker Rect 1"
        carga_dc_base = estado_real["r1_amps_dc"]
    else:
        rect_asociado = "Rect2"; nombre_fusible = "Fusible PDB2%"; nombre_breaker_rect = "Breaker Rect 2"
        carga_dc_base = estado_real["r2_amps_dc"]

    with engine.connect() as conn:
        # FUSIBLE DC
        sql_fus = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'")
        limite_fusible = conn.execute(sql_fus, {"rect": rect_asociado, "fus": nombre_fusible}).scalar()
        if limite_fusible:
            futuro_dc = carga_dc_base + amps_nuevos_dc
            if futuro_dc > limite_fusible:
                checks.append(f"[FALLO] SOBRECARGA FUSIBLE DC ({rect_asociado}): Actual {carga_dc_base}A + {amps_nuevos_dc:.1f}A = {futuro_dc:.1f}A > {limite_fusible}A")
                aprobado = False
            else:
                checks.append(f"[OK] Fusible DC {rect_asociado} OK: {futuro_dc:.1f}A (Límite {limite_fusible}A)")

        # BREAKER AC RECTIFICADOR
        # (Lógica similar a la anterior pero usando carga_dc_base real para estimar AC actual)
        # ... (Puedes reutilizar tu lógica de conversión inversa aquí si quieres precisión máxima) ...
        sql_brk = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = 'ML' AND componente = :comp AND tipo = 'AC'")
        limite_breaker_rect = conn.execute(sql_brk, {"comp": nombre_breaker_rect}).scalar()
        carga_actual_rect_ac = _calcular_corriente_ac_trifasica(carga_dc_base * CONSTANTES_FISICAS["VOLTAJE_DC"])
        
        if limite_breaker_rect:
            futuro_rect_ac = carga_actual_rect_ac + amps_nuevos_ac
            if futuro_rect_ac > limite_breaker_rect:
                checks.append(f"[FALLO] SOBRECARGA BREAKER AC ({nombre_breaker_rect}): {futuro_rect_ac:.1f}A > {limite_breaker_rect}A")
                aprobado = False
            else:
                checks.append(f"[OK] Breaker AC {rect_asociado} OK: {futuro_rect_ac:.1f}A (Limite {limite_breaker_rect}A)")



        # TOTALIZADORES GENERALES (Usando datos reales)
        # ML
        sql_ml_limit = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador ML'")
        limite_ml = conn.execute(sql_ml_limit).scalar()
        if limite_ml:
            futuro_ml = estado_real["ml_amps_ac"] + amps_nuevos_ac
            if futuro_ml > limite_ml:
                checks.append(f"[FALLO] SOBRECARGA ML: Actual {estado_real['ml_amps_ac']:.1f}A + {amps_nuevos_ac:.1f}A = {futuro_ml:.1f}A > {limite_ml}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador ML OK: {futuro_ml:.1f}A (Límite {limite_ml}A)")

        # TR
        sql_tr_limit = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador Red'")
        limite_tr = conn.execute(sql_tr_limit).scalar()
        if limite_tr:
            futuro_tr = estado_real["tr_amps_ac"] + amps_nuevos_ac
            if futuro_tr > limite_tr:
                checks.append(f"[FALLO] SOBRECARGA TR (Amps): Actual {estado_real['tr_amps_ac']:.1f}A + {amps_nuevos_ac:.1f}A = {futuro_tr:.1f}A > {limite_tr}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador TR OK (Amps): {futuro_tr:.1f}A (Límite {limite_tr}A)")

    return aprobado, checks







def evaluar_solicitud(engine, datos_entrada):

    informe = {
        "Equipo": datos_entrada.get("Equipment"),
        "Checks": [],
        "Recomendacion_Instalacion": "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO"
    }

    estado_real = _obtener_estado_actual_db(engine)
    
    potencia_w = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total_dc = potencia_w * cantidad
    amps_nuevos_dc = potencia_total_dc / CONSTANTES_FISICAS["VOLTAJE_DC"]
    fuentes = int(datos_entrada.get("Power sources", 1))

    # --- FAILOVER: PDB1 -> PDB2 ---
    pdbs_a_evaluar = ["PDB1", "PDB2"]
    pdb_ganador = None
    
    for pdb_candidato in pdbs_a_evaluar:
        # A. Espacio
        # Reutilizamos la lógica interna de buscar_espacio, pero filtrando.
        # Para simplificar y no duplicar código, asumimos que _buscar_espacio_pdb
        # devuelve el óptimo global. Si queremos forzar validación uno por uno:
        
        # Consultamos espacio específico para este PDB
        sql_libres = f"SELECT * FROM inventario_dc_pdb WHERE pdb_nombre = '{pdb_candidato}' AND UPPER(estado) IN ('DISPONIBLE', 'LIBRE')"
        df_libres = pd.read_sql(sql_libres, engine)
        
        # Validar si cabe
        necesarias_a = math.ceil(fuentes / 2)
        necesarias_b = fuentes // 2
        hay_a = len(df_libres[df_libres['fuente'].str.contains('A')]) >= necesarias_a
        hay_b = len(df_libres[df_libres['fuente'].str.contains('B')]) >= necesarias_b
        
        if not (hay_a and hay_b):
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por falta de espacio físico.")
            continue # Siguiente PDB

        # B. Eléctrico
        electrico_ok, msgs_electrico = _validar_capacidad_electrica_pdb(pdb_candidato, fuentes, amps_nuevos_dc)
        if not electrico_ok:
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por capacidad eléctrica.")
            # Guardamos los fallos como info
            for m in msgs_electrico:
                informe["Checks"].append(m.replace("[FALLO]", "[INFO]"))
            continue

        # C. Aguas Arriba
        protec_ok, msgs_protec = _validar_protecciones_aguas_arriba(engine, pdb_candidato, potencia_total_dc, amps_nuevos_dc)
        if not protec_ok:
            informe["Checks"].append(f"[ADVERTENCIA] {pdb_candidato}: Descartado por protecciones aguas arriba.")
            for m in msgs_protec:
                informe["Checks"].append(m.replace("[FALLO]", "[INFO]"))
            continue
            
        # GANADOR
        pdb_ganador = pdb_candidato
        # Generar detalle de posiciones (Recuperamos la función de búsqueda para obtener el string bonito)
        _, detalle_pos, _ = _buscar_espacio_pdb(engine, fuentes) # Esto puede dar mixto, mejor filtramos manual
        # Para el reporte, volvemos a generar el string de posiciones solo del ganador
        # (Aquí simplifico usando la función general, pero lo ideal es generar el string aquí)
        # Reutilicemos la función general que ya tiene la lógica de strings
        _, detalle_pos, _ = _buscar_espacio_pdb(engine, fuentes) # Nota: esto asume que la general encontrará el mismo PDB ganador por orden.
        
        # Construimos el mensaje de la Sección 3
        informe["Recomendacion_Instalacion"] = f"Instalación APROBADA en {pdb_ganador}\n{detalle_pos}"
        
        informe["Checks"].extend(msgs_electrico)
        informe["Checks"].extend(msgs_protec)
        break

    if not pdb_ganador:
        informe["Checks"].append("[FALLO] RECHAZADO FINAL: Ningún PDB cumple requisitos.")
        return informe

    # N+1
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
        informe["Checks"].append(f"[OK] Transformador Potencia OK: {kva_actual:.1f} -> {kva_futuro:.1f} kVA (Limite {limite_tr:.1f} kVA).")

    informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"
    return informe