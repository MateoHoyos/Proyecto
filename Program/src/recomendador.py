import pandas as pd
from sqlalchemy import create_engine, text
import math

# ... (ESTADO_PDB_HARDCODED y CONSTANTES se mantienen igual, déjalos arriba) ...
ESTADO_PDB_HARDCODED = {
    "PDB1": {"A": {"actual": 115.0, "limite": 160.0}, "B": {"actual": 149.0, "limite": 160.0}},
    "PDB2": {"A": {"actual": 4.5, "limite": 250.0}, "B": {"actual": 1.3, "limite": 250.0}}
}
CONSTANTES = {
    "VOLTAJE_DC": 54.0, "VOLTAJE_AC": 220.0, "EFICIENCIA_RECT": 0.94,
    "FP_EQUIPO": 0.98, "CAPACIDAD_TR_KVA": 75.0, "LIMITE_SEGURIDAD": 0.90
}

# ... (Funciones auxiliares _calcular... _buscar... y _validar_capacidad... se mantienen IGUALES) ...
def _calcular_corriente_ac_trifasica(potencia_dc_w):
    potencia_ac_w = potencia_dc_w / CONSTANTES["EFICIENCIA_RECT"]
    return potencia_ac_w / (math.sqrt(3) * CONSTANTES["VOLTAJE_AC"] * CONSTANTES["FP_EQUIPO"])

def _buscar_espacio_pdb(engine, fuentes_requeridas):
    # (Copia la versión que te funcionaba bien de la respuesta anterior)
    sql = """SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb WHERE UPPER(estado) IN ('DISPONIBLE', 'LIBRE') ORDER BY pdb_nombre ASC, posicion ASC"""
    df_libres = pd.read_sql(sql, engine)
    df_libres['fuente'] = df_libres['fuente'].str.strip().str.upper()
    df_libres['pdb_nombre'] = df_libres['pdb_nombre'].str.strip().str.upper()
    necesarias_a = math.ceil(fuentes_requeridas / 2)
    necesarias_b = fuentes_requeridas // 2
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
    else: return False, "❌ INSUFICIENTE ESPACIO FÍSICO en PDBs.", None
    opciones_a = df_candidatos[df_candidatos['fuente'].str.contains('A')].iloc[:necesarias_a]
    opciones_b = df_candidatos[df_candidatos['fuente'].str.contains('B')].iloc[:necesarias_b]
    seleccionados = []
    for _, r in opciones_a.iterrows(): seleccionados.append(f"• Fuente A: {r['pdb_nombre']} - Pos {r['posicion']}")
    for _, r in opciones_b.iterrows(): seleccionados.append(f"• Fuente B: {r['pdb_nombre']} - Pos {r['posicion']}")
    return True, "\n".join(seleccionados), pdb_elegido

def _validar_capacidad_electrica_pdb(pdb_nombre, fuentes_requeridas, amps_nuevos_totales):
    # (Igual a la versión anterior)
    if pdb_nombre not in ESTADO_PDB_HARDCODED: return False, ["Datos no encontrados"]
    datos_pdb = ESTADO_PDB_HARDCODED[pdb_nombre]
    checks = []; aprobado = True
    amps_por_fuente = amps_nuevos_totales 
    info_a = datos_pdb.get("A")
    futuro_a = info_a['actual'] + amps_por_fuente
    if futuro_a > info_a['limite']:
        checks.append(f"❌ SOBRECARGA {pdb_nombre}-A: {info_a['actual']} + {amps_por_fuente:.1f} = {futuro_a:.1f}A > {info_a['limite']}A")
        aprobado = False
    else:
        checks.append(f"✅ {pdb_nombre}-A OK: {futuro_a:.1f}A (Límite {info_a['limite']}A)")
    if fuentes_requeridas >= 2:
        info_b = datos_pdb.get("B")
        futuro_b = info_b['actual'] + amps_por_fuente
        if futuro_b > info_b['limite']:
            checks.append(f"❌ SOBRECARGA {pdb_nombre}-B: {info_b['actual']} + {amps_por_fuente:.1f} = {futuro_b:.1f}A > {info_b['limite']}A")
            aprobado = False
        else:
            checks.append(f"✅ {pdb_nombre}-B OK: {futuro_b:.1f}A (Límite {info_b['limite']}A)")
    return aprobado, checks

# ==========================================
# FUNCIÓN CORREGIDA Y MEJORADA
# ==========================================
def _validar_protecciones_aguas_arriba(engine, pdb_seleccionado, potencia_total_w, amps_nuevos_dc):
    """
    Valida Rectificadores (Ambos), ML y TR usando la tabla 'protecciones'.
    """
    checks = []
    aprobado = True
    
    # 1. DATOS PROMEDIO ACTUALES
    carga_actual_tr_ac = (61.01 + 60.23 + 61.06) / 3
    carga_actual_ml_ac = (61.49 + 62.59 + 67.77) / 3
    
    # Mapa de cargas DC actuales
    cargas_rect_dc = {
        "Rect1": 118.67,
        "Rect2": 155.96
    }

    # 2. CÁLCULOS
    amps_nuevos_ac = _calcular_corriente_ac_trifasica(potencia_total_w)
    
    # Definimos qué PDB se alimenta de qué Rectificador
    # Si seleccionamos PDB1, la carga va a Rect1. Si es PDB2, va a Rect2.
    rect_objetivo = "Rect1" if "PDB1" in pdb_seleccionado else "Rect2"

    with engine.connect() as conn:
        
        # --- A. VALIDACIÓN DE AMBOS RECTIFICADORES (1 y 2) ---
        # Recorremos ambos para asegurar salud completa del sistema
        rectificadores = [
            {"nombre": "Rect1", "pdb_asoc": "PDB1"},
            {"nombre": "Rect2", "pdb_asoc": "PDB2"}
        ]

        for r in rectificadores:
            nombre_rect = r['nombre']
            es_el_seleccionado = (nombre_rect == rect_objetivo)
            
            # Si es el seleccionado, le sumamos la carga. Si no, solo validamos su estado actual.
            carga_base = cargas_rect_dc[nombre_rect]
            carga_dc_evaluada = carga_base + amps_nuevos_dc if es_el_seleccionado else carga_base
            
            # -- Fusible DC --
            nombre_fusible = f"Fusible {r['pdb_asoc']}%"
            # CAMBIO: Tabla 'protecciones'
            sql_fus = text("SELECT capacidad_amps FROM protecciones WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'")
            limite_fusible = conn.execute(sql_fus, {"rect": nombre_rect, "fus": nombre_fusible}).scalar()
            
            if limite_fusible:
                if carga_dc_evaluada > limite_fusible:
                    checks.append(f"❌ SOBRECARGA FUSIBLE DC ({nombre_rect}): {carga_dc_evaluada:.1f}A > {limite_fusible}A")
                    if es_el_seleccionado: aprobado = False
                else:
                    checks.append(f"✅ Fusible DC {nombre_rect} OK: {carga_dc_evaluada:.1f}A / {limite_fusible}A")

            # -- Breaker AC --
            nombre_breaker = f"Breaker {nombre_rect}"
            # CAMBIO: Tabla 'protecciones', ubicacion ML (o RectX según tu CSV final, ajusta aquí si es necesario)
            # Según tu CSV último: "Rect1;Breaker Rect 1...". Si está en ML pon 'ML', si en tu CSV dice Rect1 pon 'Rect1'.
            # Voy a asumir que en tu base de datos quedó como en tu CSV: Ubicación 'Rect1' o 'ML'. 
            # Usaré una búsqueda flexible OR para encontralo donde sea.
            sql_brk = text("""
                SELECT capacidad_amps FROM protecciones 
                WHERE componente = :comp AND tipo = 'AC'
            """)
            limite_brk = conn.execute(sql_brk, {"comp": nombre_breaker}).scalar()
            
            # Conversión inversa para estimar AC actual de ese rectificador
            watts_rect = carga_dc_evaluada * CONSTANTES["VOLTAJE_DC"]
            amps_ac_rect = _calcular_corriente_ac_trifasica(watts_rect) # Reutilizamos la fórmula con los watts totales de ese rect

            if limite_brk:
                if amps_ac_rect > limite_brk:
                    checks.append(f"❌ SOBRECARGA BREAKER AC ({nombre_rect}): {amps_ac_rect:.1f}A > {limite_brk}A")
                    if es_el_seleccionado: aprobado = False
                else:
                    checks.append(f"✅ Breaker AC {nombre_rect} OK: {amps_ac_rect:.1f}A / {limite_brk}A")

        # --- B. TOTALIZADORES GENERALES (ML y TR) ---
        
        # ML (Carga base + Nueva carga AC)
        futuro_ml = carga_actual_ml_ac + amps_nuevos_ac
        sql_ml = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador ML' AND tipo = 'AC'")
        limite_ml = conn.execute(sql_ml).scalar()
        if limite_ml:
            if futuro_ml > limite_ml:
                checks.append(f"❌ SOBRECARGA ML: {futuro_ml:.1f}A > {limite_ml}A")
                aprobado = False
            else:
                checks.append(f"✅ Totalizador ML OK: {futuro_ml:.1f}A / {limite_ml}A")

        # TR
        futuro_tr = carga_actual_tr_ac + amps_nuevos_ac
        sql_tr = text("SELECT capacidad_amps FROM protecciones WHERE componente = 'Totalizador Red' AND tipo = 'AC'")
        limite_tr = conn.execute(sql_tr).scalar()
        if limite_tr:
            if futuro_tr > limite_tr:
                checks.append(f"❌ SOBRECARGA TR (Amps): {futuro_tr:.1f}A > {limite_tr}A")
                aprobado = False
            else:
                checks.append(f"✅ Totalizador TR OK: {futuro_tr:.1f}A / {limite_tr}A")

    return aprobado, checks

# ... (Función evaluar_solicitud sigue igual) ...
def evaluar_solicitud(engine, datos_entrada):
    # ... (Copia el resto de la función anterior, es idéntica) ...
    # Solo recuerda que ahora _validar_protecciones_aguas_arriba devuelve info de los DOS rectificadores
    informe = {
        "Equipment": datos_entrada.get("Equipment"),
        "Checks": [],
        "Recomendacion_Instalacion": "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO"
    }
    print(f"🔄 Evaluando solicitud para: {datos_entrada.get('Equipment')}...")

    # 1. Cálculos
    potencia_w = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total_dc = potencia_w * cantidad
    amps_nuevos_dc = potencia_total_dc / CONSTANTES["VOLTAJE_DC"]
    fuentes = int(datos_entrada.get("Power sources", 1))

    # 2. Espacio
    espacio_ok, msg_espacio, pdb_elegido = _buscar_espacio_pdb(engine, fuentes)
    informe["Recomendacion_Instalacion"] = msg_espacio
    if not espacio_ok:
        informe["Checks"].append(f"❌ {msg_espacio}")
        return informe

    # 3. Validacion Electrica PDB
    elec_pdb_ok, msgs_pdb = _validar_capacidad_electrica_pdb(pdb_elegido, fuentes, amps_nuevos_dc)
    informe["Checks"].extend(msgs_pdb)
    if not elec_pdb_ok:
        informe["Checks"].append("❌ RECHAZADO: PDB sobrecargado.")
        return informe

    # 4. Validacion Aguas Arriba
    protec_ok, msgs_protec = _validar_protecciones_aguas_arriba(engine, pdb_elegido, potencia_total_dc, amps_nuevos_dc)
    informe["Checks"].extend(msgs_protec)
    if not protec_ok:
        informe["Checks"].append("❌ RECHAZADO: Falla en protecciones aguas arriba.")
        return informe

    # 5. Redundancia N+1
    carga_total_sitio = 118.67 + 155.96 + amps_nuevos_dc
    CAPACIDAD_RECT_UNITARIA = 1000.0 
    if carga_total_sitio > CAPACIDAD_RECT_UNITARIA:
        informe["Checks"].append(f"❌ FALLO REDUNDANCIA N+1: Carga Total {carga_total_sitio:.1f}A > Capacidad {CAPACIDAD_RECT_UNITARIA}A.")
        return informe
    else:
        informe["Checks"].append(f"✅ Redundancia N+1 OK: Carga total {carga_total_sitio:.1f}A soportada.")

    # 6. Potencia TR
    kva_actual_promedio = 22.372
    potencia_ac_w = potencia_total_dc / CONSTANTES["EFICIENCIA_RECT"]
    kva_nuevo = (potencia_ac_w / 1000) / CONSTANTES["FP_EQUIPO"]
    kva_futuro = kva_actual_promedio + kva_nuevo
    capacidad_limite = CONSTANTES["CAPACIDAD_TR_KVA"] * CONSTANTES["LIMITE_SEGURIDAD"]
    if kva_futuro > capacidad_limite:
        informe["Checks"].append(f"❌ RECHAZADO: Sobrecarga TR. {kva_futuro:.2f} kVA > {capacidad_limite} kVA.")
        return informe
    else:
        informe["Checks"].append(f"✅ Transformador Potencia OK: {kva_actual_promedio:.1f} -> {kva_futuro:.1f} kVA (Límite {capacidad_limite} kVA).")

    informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"
    return informe