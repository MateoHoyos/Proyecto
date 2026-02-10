import pandas as pd
from sqlalchemy import create_engine, text
import math

# ==========================================
# 1. DATOS MANUALES Y CONSTANTES
# ==========================================

ESTADO_PDB_HARDCODED = {
    "PDB1": {
        "A": {"actual": 115.0, "limite": 160.0},
        "B": {"actual": 149.0, "limite": 160.0}
    },
    "PDB2": {
        "A": {"actual": 4.5, "limite": 250.0},
        "B": {"actual": 1.3, "limite": 250.0}
    }
}

CONSTANTES = {
    "VOLTAJE_DC": 54.0,
    "VOLTAJE_AC": 220.0,
    "EFICIENCIA_RECT": 0.94,
    "FP_EQUIPO": 0.98,
    "CAPACIDAD_TR_KVA": 75.0, 
    "LIMITE_SEGURIDAD": 0.90 # El 90% de 75kVA es 67.5 kVA
}

# ==========================================
# 2. FUNCIONES AUXILIARES
# ==========================================

def _calcular_corriente_ac_trifasica(potencia_dc_w):
    """
    Convierte Watts DC a Amperios AC por fase.
    """
    potencia_ac_w = potencia_dc_w / CONSTANTES["EFICIENCIA_RECT"]
    amps_ac = potencia_ac_w / (math.sqrt(3) * CONSTANTES["VOLTAJE_AC"] * CONSTANTES["FP_EQUIPO"])
    return amps_ac

def _buscar_espacio_pdb(engine, fuentes_requeridas):
    """
    Busca espacio físico y retorna: (Tiene_Espacio, Mensaje, NOMBRE_PDB_ELEGIDO)
    """
    sql = """
    SELECT pdb_nombre, fuente, posicion 
    FROM inventario_dc_pdb 
    WHERE UPPER(estado) IN ('DISPONIBLE', 'LIBRE')
    ORDER BY pdb_nombre ASC, posicion ASC
    """
    df_libres = pd.read_sql(sql, engine)
    df_libres['fuente'] = df_libres['fuente'].str.strip().str.upper()
    df_libres['pdb_nombre'] = df_libres['pdb_nombre'].str.strip().str.upper()

    necesarias_a = math.ceil(fuentes_requeridas / 2)
    necesarias_b = fuentes_requeridas // 2

    # Filtros por PDB
    df_pdb1 = df_libres[df_libres['pdb_nombre'] == 'PDB1']
    df_pdb2 = df_libres[df_libres['pdb_nombre'] == 'PDB2']

    disp_pdb1_a = len(df_pdb1[df_pdb1['fuente'].str.contains('A')])
    disp_pdb1_b = len(df_pdb1[df_pdb1['fuente'].str.contains('B')])
    disp_pdb2_a = len(df_pdb2[df_pdb2['fuente'].str.contains('A')])
    disp_pdb2_b = len(df_pdb2[df_pdb2['fuente'].str.contains('B')])

    pdb_elegido = None

    if disp_pdb1_a >= necesarias_a and disp_pdb1_b >= necesarias_b:
        pdb_elegido = "PDB1"
    elif disp_pdb2_a >= necesarias_a and disp_pdb2_b >= necesarias_b:
        pdb_elegido = "PDB2"
    else:
        if len(df_libres) >= fuentes_requeridas:
            pdb_elegido = "MIXTO"
        else:
            return False, "❌ INSUFICIENTE ESPACIO FÍSICO en PDBs.", None

    return True, f"Espacio asignado en {pdb_elegido}", pdb_elegido

def _validar_capacidad_electrica_pdb(pdb_nombre, fuentes_requeridas, amps_nuevos_totales):
    """
    Valida contra los DATOS FIJOS (Hardcoded) si el PDB aguanta la carga.
    """
    if pdb_nombre == "MIXTO":
        return False, ["⚠️ Instalación fragmentada. Validar manualmente."]
    
    if pdb_nombre not in ESTADO_PDB_HARDCODED:
        return False, [f"❌ Datos no encontrados para {pdb_nombre}."]

    datos_pdb = ESTADO_PDB_HARDCODED[pdb_nombre]
    checks = []
    aprobado = True
    
    amps_por_fuente = amps_nuevos_totales 

    # Validar Fuente A
    info_a = datos_pdb.get("A")
    futuro_a = info_a['actual'] + amps_por_fuente
    if futuro_a > info_a['limite']:
        checks.append(f"❌ SOBRECARGA {pdb_nombre}-A: {info_a['actual']} + {amps_por_fuente:.1f} = {futuro_a:.1f}A > {info_a['limite']}A")
        aprobado = False
    else:
        checks.append(f"✅ {pdb_nombre}-A OK: {futuro_a:.1f}A (Límite {info_a['limite']}A)")

    # Validar Fuente B
    if fuentes_requeridas >= 2:
        info_b = datos_pdb.get("B")
        futuro_b = info_b['actual'] + amps_por_fuente
        if futuro_b > info_b['limite']:
            checks.append(f"❌ SOBRECARGA {pdb_nombre}-B: {info_b['actual']} + {amps_por_fuente:.1f} = {futuro_b:.1f}A > {info_b['limite']}A")
            aprobado = False
        else:
            checks.append(f"✅ {pdb_nombre}-B OK: {futuro_b:.1f}A (Límite {info_b['limite']}A)")

    return aprobado, checks

def _validar_protecciones_aguas_arriba(engine, pdb_seleccionado, potencia_total_w, amps_nuevos_dc):
    """
    Valida Fusibles, Breakers AC, ML y TR usando PROMEDIOS FIJOS para la carga actual.
    """
    checks = []
    aprobado = True
    
    # --- 1. DATOS PROMEDIO FIJOS ---
    carga_actual_tr_ac = (61.01 + 60.23 + 61.06) / 3
    carga_actual_ml_ac = (61.49 + 62.59 + 67.77) / 3
    carga_actual_r1_dc = 118.67 
    carga_actual_r2_dc = 155.96 

    # --- 2. CÁLCULOS ---
    amps_nuevos_ac = _calcular_corriente_ac_trifasica(potencia_total_w)
    
    # Selección de ruta
    if "PDB1" in pdb_seleccionado:
        rect_asociado = "Rect1"
        nombre_fusible = "Fusible PDB1%"
        nombre_breaker_rect = "Breaker Rect 1"
        carga_dc_base = carga_actual_r1_dc
    else:
        rect_asociado = "Rect2"
        nombre_fusible = "Fusible PDB2%"
        nombre_breaker_rect = "Breaker Rect 2"
        carga_dc_base = carga_actual_r2_dc

    with engine.connect() as conn:
        # NIVEL 1: FUSIBLE DC
        sql_fus = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'")
        limite_fusible = conn.execute(sql_fus, {"rect": rect_asociado, "fus": nombre_fusible}).scalar()
        
        if limite_fusible:
            futuro_dc = carga_dc_base + amps_nuevos_dc
            if futuro_dc > limite_fusible:
                checks.append(f"❌ SOBRECARGA FUSIBLE DC ({rect_asociado}): {futuro_dc:.1f}A > {limite_fusible}A")
                aprobado = False
            else:
                checks.append(f"✅ Fusible DC {rect_asociado} OK: {futuro_dc:.1f}A / {limite_fusible}A")

        # NIVEL 2: BREAKER AC RECTIFICADOR
        sql_brk = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = 'ML' AND componente = :comp AND tipo = 'AC'")
        limite_breaker_rect = conn.execute(sql_brk, {"comp": nombre_breaker_rect}).scalar()
        
        # Estimación consumo AC actual del rectificador
        carga_actual_rect_ac = _calcular_corriente_ac_trifasica(carga_dc_base * CONSTANTES["VOLTAJE_DC"])
        
        if limite_breaker_rect:
            futuro_rect_ac = carga_actual_rect_ac + amps_nuevos_ac
            if futuro_rect_ac > limite_breaker_rect:
                checks.append(f"❌ SOBRECARGA BREAKER AC ({nombre_breaker_rect}): {futuro_rect_ac:.1f}A > {limite_breaker_rect}A")
                aprobado = False
            else:
                checks.append(f"✅ Breaker AC {rect_asociado} OK: {futuro_rect_ac:.1f}A / {limite_breaker_rect}A")

        # NIVEL 3: ML y TR (CORRIENTE)
        sql_ml_limit = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador ML' AND tipo = 'AC'")
        limite_ml = conn.execute(sql_ml_limit).scalar()
        if limite_ml:
            if (carga_actual_ml_ac + amps_nuevos_ac > limite_ml):
                checks.append(f"❌ SOBRECARGA ML: {carga_actual_ml_ac + amps_nuevos_ac:.1f}A > {limite_ml}A")
                aprobado = False
            else:
                checks.append(f"✅ Totalizador ML OK")

        sql_tr_limit = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador Red' AND tipo = 'AC'")
        limite_tr = conn.execute(sql_tr_limit).scalar()
        if limite_tr:
            if (carga_actual_tr_ac + amps_nuevos_ac > limite_tr):
                checks.append(f"❌ SOBRECARGA TR (Amps): {carga_actual_tr_ac + amps_nuevos_ac:.1f}A > {limite_tr}A")
                aprobado = False
            else:
                checks.append(f"✅ Totalizador TR OK (Amps)")

    return aprobado, checks

# ==========================================
# 3. FUNCIÓN PRINCIPAL (ORQUESTADOR)
# ==========================================

def evaluar_solicitud(engine, datos_entrada):
    informe = {
        "Equipment": datos_entrada.get("Equipment"),
        "Checks": [],
        "Recomendacion_Instalacion": "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO"
    }
    
    print(f"🔄 Evaluando solicitud para: {datos_entrada.get('Equipment')}...")

    # 1. Cálculos de Potencia y Corriente DC
    potencia_w = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total_dc = potencia_w * cantidad
    amps_nuevos_dc = potencia_total_dc / CONSTANTES["VOLTAJE_DC"]
    fuentes = int(datos_entrada.get("Power sources", 1))

    # 2. VALIDACIÓN DE ESPACIO FÍSICO PDB
    espacio_ok, msg_espacio, pdb_elegido = _buscar_espacio_pdb(engine, fuentes)
    informe["Recomendacion_Instalacion"] = msg_espacio
    
    if not espacio_ok:
        informe["Checks"].append(f"❌ {msg_espacio}")
        return informe

    # 3. VALIDACIÓN ELÉCTRICA PDB (Interna - Hardcoded)
    elec_pdb_ok, msgs_pdb = _validar_capacidad_electrica_pdb(pdb_elegido, fuentes, amps_nuevos_dc)
    informe["Checks"].extend(msgs_pdb)

    if not elec_pdb_ok:
        informe["Checks"].append("❌ RECHAZADO: PDB sobrecargado.")
        return informe

    # 4. VALIDACIÓN PROTECCIONES AGUAS ARRIBA (Corriente Amps)
    protec_ok, msgs_protec = _validar_protecciones_aguas_arriba(engine, pdb_elegido, potencia_total_dc, amps_nuevos_dc)
    informe["Checks"].extend(msgs_protec)

    if not protec_ok:
        informe["Checks"].append("❌ RECHAZADO: Falla en protecciones aguas arriba.")
        return informe

    # -------------------------------------------------------------
    # 5. VALIDACIÓN DE POTENCIA TOTAL (kVA) - EL PASO NUEVO
    # -------------------------------------------------------------
    
    # Dato promedio manual que tienes
    kva_actual_promedio = 22.37203496 
    
    # Calcular kVA que aporta el nuevo equipo
    # Watts DC -> Watts AC (Eficiencia) -> kVA (Factor Potencia)
    potencia_ac_w = potencia_total_dc / CONSTANTES["EFICIENCIA_RECT"]
    kva_nuevo = (potencia_ac_w / 1000) / CONSTANTES["FP_EQUIPO"]
    
    kva_futuro = kva_actual_promedio + kva_nuevo
    
    # Límite: 75 kVA * 90% seguridad = 67.5 kVA
    capacidad_limite = CONSTANTES["CAPACIDAD_TR_KVA"] * CONSTANTES["LIMITE_SEGURIDAD"]
    
    if kva_futuro > capacidad_limite:
        informe["Checks"].append(f"❌ RECHAZADO: Sobrecarga de Potencia TR. {kva_futuro:.2f} kVA > {capacidad_limite} kVA.")
        return informe
    else:
        informe["Checks"].append(f"✅ Transformador Potencia OK: {kva_actual_promedio:.1f} kVA -> {kva_futuro:.1f} kVA (Límite {capacidad_limite} kVA).")

    # 6. RESULTADO FINAL
    informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"
    return informe