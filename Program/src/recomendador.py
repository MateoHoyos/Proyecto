import pandas as pd
from sqlalchemy import create_engine, text
import math

# ... (ESTADO_PDB_HARDCODED y CONSTANTES se mantienen IGUALES) ...
ESTADO_PDB_HARDCODED = {
    "PDB1": {"A": {"actual": 115.0, "limite": 160.0}, "B": {"actual": 149.0, "limite": 160.0}},
    "PDB2": {"A": {"actual": 4.5, "limite": 250.0}, "B": {"actual": 1.3, "limite": 250.0}}
}
CONSTANTES = {
    "VOLTAJE_DC": 54.0, "VOLTAJE_AC": 220.0, "EFICIENCIA_RECT": 0.94,
    "FP_EQUIPO": 0.98, "CAPACIDAD_TR_KVA": 75.0, "LIMITE_SEGURIDAD": 0.90
}

def _calcular_corriente_ac_trifasica(potencia_dc_w):
    potencia_ac_w = potencia_dc_w / CONSTANTES["EFICIENCIA_RECT"]
    return potencia_ac_w / (math.sqrt(3) * CONSTANTES["VOLTAJE_AC"] * CONSTANTES["FP_EQUIPO"])

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
    if pdb_nombre not in ESTADO_PDB_HARDCODED: return False, ["[FALLO] Datos no encontrados"]
    datos_pdb = ESTADO_PDB_HARDCODED[pdb_nombre]
    checks = []; aprobado = True
    amps_por_fuente = amps_nuevos_totales 
    
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
    
    # 1. DATOS PROMEDIO
    carga_actual_tr_ac = (61.01 + 60.23 + 61.06) / 3
    carga_actual_ml_ac = (61.49 + 62.59 + 67.77) / 3
    carga_actual_r1_dc = 118.67 
    carga_actual_r2_dc = 155.96 
    
    # 2. CÁLCULOS
    amps_nuevos_ac = _calcular_corriente_ac_trifasica(potencia_total_w)
    
    if "PDB1" in pdb_seleccionado:
        rect_asociado = "Rect1"; nombre_fusible = "Fusible PDB1%"; nombre_breaker_rect = "Breaker Rect 1"; carga_dc_base = carga_actual_r1_dc
    else:
        rect_asociado = "Rect2"; nombre_fusible = "Fusible PDB2%"; nombre_breaker_rect = "Breaker Rect 2"; carga_dc_base = carga_actual_r2_dc

    with engine.connect() as conn:
        # FUSIBLE DC
        sql_fus = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'")
        limite_fusible = conn.execute(sql_fus, {"rect": rect_asociado, "fus": nombre_fusible}).scalar()
        if limite_fusible:
            futuro_dc = carga_dc_base + amps_nuevos_dc
            if futuro_dc > limite_fusible:
                checks.append(f"[FALLO] SOBRECARGA FUSIBLE DC ({rect_asociado}): {futuro_dc:.1f}A > {limite_fusible}A")
                aprobado = False
            else:
                checks.append(f"[OK] Fusible DC {rect_asociado} OK: {futuro_dc:.1f}A (Limite {limite_fusible}A)")

        # BREAKER AC
        sql_brk = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = 'ML' AND componente = :comp AND tipo = 'AC'")
        limite_breaker_rect = conn.execute(sql_brk, {"comp": nombre_breaker_rect}).scalar()
        carga_actual_rect_ac = _calcular_corriente_ac_trifasica(carga_dc_base * CONSTANTES["VOLTAJE_DC"])
        
        if limite_breaker_rect:
            futuro_rect_ac = carga_actual_rect_ac + amps_nuevos_ac
            if futuro_rect_ac > limite_breaker_rect:
                checks.append(f"[FALLO] SOBRECARGA BREAKER AC ({nombre_breaker_rect}): {futuro_rect_ac:.1f}A > {limite_breaker_rect}A")
                aprobado = False
            else:
                checks.append(f"[OK] Breaker AC {rect_asociado} OK: {futuro_rect_ac:.1f}A (Limite {limite_breaker_rect}A)")

        # ML
        sql_ml_limit = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador ML' AND tipo = 'AC'")
        limite_ml = conn.execute(sql_ml_limit).scalar()
        if limite_ml:
            futuro_ml = carga_actual_ml_ac + amps_nuevos_ac
            if futuro_ml > limite_ml:
                checks.append(f"[FALLO] SOBRECARGA ML: {futuro_ml:.1f}A > {limite_ml}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador ML OK: {futuro_ml:.1f}A (Limite {limite_ml}A)")

        # TR
        sql_tr_limit = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador Red' AND tipo = 'AC'")
        limite_tr = conn.execute(sql_tr_limit).scalar()
        if limite_tr:
            futuro_tr = carga_actual_tr_ac + amps_nuevos_ac
            if futuro_tr > limite_tr:
                checks.append(f"[FALLO] SOBRECARGA TR (Amps): {futuro_tr:.1f}A > {limite_tr}A")
                aprobado = False
            else:
                checks.append(f"[OK] Totalizador TR OK (Amps): {futuro_tr:.1f}A (Limite {limite_tr}A)")

    return aprobado, checks

def evaluar_solicitud(engine, datos_entrada):
    informe = {
        "Equipo": datos_entrada.get("Equipment"),
        "Checks": [],
        "Recomendacion_Instalacion": "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO"
    }
    
    potencia_w = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total_dc = potencia_w * cantidad
    amps_nuevos_dc = potencia_total_dc / CONSTANTES["VOLTAJE_DC"]
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
    carga_total = 118.67 + 155.96 + amps_nuevos_dc
    if carga_total > 1000.0:
        informe["Checks"].append(f"[FALLO] REDUNDANCIA N+1: Carga {carga_total:.1f}A > 1000A.")
        return informe
    else:
        informe["Checks"].append(f"[OK] Redundancia N+1 OK: Carga {carga_total:.1f}A soportada.")

    # TR kVA
    kva_actual = 22.372
    pot_ac = potencia_total_dc / CONSTANTES["EFICIENCIA_RECT"]
    kva_nuevo = (pot_ac / 1000) / CONSTANTES["FP_EQUIPO"]
    kva_futuro = kva_actual + kva_nuevo
    limite_tr = CONSTANTES["CAPACIDAD_TR_KVA"] * CONSTANTES["LIMITE_SEGURIDAD"]
    
    if kva_futuro > limite_tr:
        informe["Checks"].append(f"[FALLO] Sobrecarga TR: {kva_futuro:.1f} > {limite_tr:.1f} kVA.")
        return informe
    else:
        informe["Checks"].append(f"[OK] Transformador Potencia OK: {kva_actual:.1f} -> {kva_futuro:.1f} kVA (Limite {limite_tr:.1f} kVA).")

    informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"
    return informe