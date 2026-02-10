import pandas as pd
from sqlalchemy import create_engine, text
import math
import reportlab

# ==========================================
# 1. DATOS MANUALES 
# ==========================================

# Estado actual de carga y límites de los PDBs (Totalizadores)
ESTADO_PDB_HARDCODED = {
    "PDB1": {
        "A": {"actual": 115.0, "limite": 160.0}, # Ojo: Limite del totalizador, no del cable
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
    "LIMITE_SEGURIDAD": 0.90
}



def _obtener_carga_actual_historica(engine):

    kva_actual=22.37203496 # promedio kVA 
    r1_amps= 119.9588015 # promedio 11 - CORRIENTE DC DE LA CARGA
    r2_amps= 155.55375 # promedio 11 - CORRIENTE DC DE LA CARGA

    return kva_actual, r1_amps, r2_amps

    """Obtiene la última lectura de TR y Rectificadores desde MySQL
    with engine.connect() as conn:
        try:
            sql_tr = "SELECT potencia_aparente_kva FROM tr_historico ORDER BY timestamp DESC LIMIT 1"
            kva_actual = conn.execute(text(sql_tr)).scalar() or 0.0
            
            sql_r1 = "SELECT corriente_total_dc FROM rect1_historico ORDER BY timestamp DESC LIMIT 1"
            r1_amps = conn.execute(text(sql_r1)).scalar() or 0.0
            
            sql_r2 = "SELECT corriente_total_dc FROM rect2_historico ORDER BY timestamp DESC LIMIT 1"
            r2_amps = conn.execute(text(sql_r2)).scalar() or 0.0
            
            return kva_actual, r1_amps, r2_amps
        except Exception as e:
            print(f"⚠️ Error leyendo históricos: {e}. Asumiendo carga 0.")
            return 0.0, 0.0, 0.0 """
    

def _verificar_espacio_fisico_en_un_pdb(df_libres, pdb_objetivo, fuentes_requeridas):
    """
    Verifica si UN PDB específico tiene espacio para TODAS las fuentes.
    Retorna: (True/False, Mensaje_Detalle)
    """
    # Filtrar solo el PDB que nos interesa
    df_pdb = df_libres[df_libres['pdb_nombre'] == pdb_objetivo]
    
    # Calcular pares necesarios (A y B)
    necesarias_a = math.ceil(fuentes_requeridas / 2)
    necesarias_b = fuentes_requeridas // 2

    # Separar disponibles en A y B
    opciones_a = df_pdb[df_pdb['fuente'].str.contains('A')].copy().reset_index(drop=True)
    opciones_b = df_pdb[df_pdb['fuente'].str.contains('B')].copy().reset_index(drop=True)

    if len(opciones_a) < necesarias_a or len(opciones_b) < necesarias_b:
        return False, f"Espacio insuficiente en {pdb_objetivo} (Req: {necesarias_a}A/{necesarias_b}B - Disp: {len(opciones_a)}A/{len(opciones_b)}B)"

    # Asignación (Simulación)
    seleccionados = []
    idx_a, idx_b = 0, 0
    fuentes_asignadas = 0

    while fuentes_asignadas < fuentes_requeridas:
        if (fuentes_asignadas % 2 == 0 and idx_a < len(opciones_a)) or (idx_b >= len(opciones_b) and idx_a < len(opciones_a)):
            breaker = opciones_a.iloc[idx_a]
            seleccionados.append(f"• Fuente A: {breaker['pdb_nombre']} - Pos {breaker['posicion']}")
            idx_a += 1
        else:
            breaker = opciones_b.iloc[idx_b]
            seleccionados.append(f"• Fuente B: {breaker['pdb_nombre']} - Pos {breaker['posicion']}")
            idx_b += 1
        fuentes_asignadas += 1

    return True, "\n".join(seleccionados)

def _validar_capacidad_electrica_pdb(pdb_nombre, amps_nuevos_totales):
    """
    Valida si el totalizador del PDB aguanta la carga asumiendo peor escenario.
    """
    if pdb_nombre not in ESTADO_PDB_HARDCODED:
        return False, [f"❌ Datos no encontrados para {pdb_nombre}"]

    datos_pdb = ESTADO_PDB_HARDCODED[pdb_nombre]
    checks = []
    aprobado = True

    # Escenario N+N: Si falla la fuente B, la A asume el 100% de la carga
    amps_carga_peor_caso = amps_nuevos_totales

    for fuente in ["A", "B"]:
        info = datos_pdb.get(fuente)
        if info:
            futuro = info['actual'] + amps_carga_peor_caso
            if futuro > info['limite']:
                checks.append(f"❌ SOBRECARGA {pdb_nombre}-{fuente}: Actual {info['actual']}A + Nuevo {amps_carga_peor_caso:.1f}A = {futuro:.1f}A (Límite {info['limite']}A).")
                aprobado = False
            else:
                checks.append(f"✅ {pdb_nombre}-{fuente} OK: {futuro:.1f}A (Límite {info['limite']}A).")

    return aprobado, checks

# ==========================================
# 3. FUNCIÓN PRINCIPAL (LÓGICA DE INTENTOS)
# ==========================================

def evaluar_solicitud(engine, datos_entrada):
    informe = {
        "Equipo": datos_entrada.get("Equipment"),
        "Checks": [],
        "Recomendacion_Instalacion": "N/A",
        "PRE-Factibilidad Infraestructura (Si / No)": "NO"
    }
    
    print(f"🔄 Evaluando solicitud para: {datos_entrada.get('Equipment')}...")

    # 1. Cálculos de Potencia
    potencia_w = datos_entrada.get("Máx. Power DC (W)", 0)
    cantidad = datos_entrada.get("Quantity Equipment DC", 1)
    potencia_total = potencia_w * cantidad
    amps_nuevos = potencia_total / CONSTANTES["VOLTAJE_DC"]
    fuentes = int(datos_entrada.get("Power sources", 1))

    # 2. Obtener inventario libre global
    sql = "SELECT pdb_nombre, fuente, posicion FROM inventario_dc_pdb WHERE UPPER(estado) IN ('DISPONIBLE', 'LIBRE') ORDER BY pdb_nombre ASC, posicion ASC"
    df_libres = pd.read_sql(sql, engine)
    df_libres['fuente'] = df_libres['fuente'].str.strip().str.upper()
    df_libres['pdb_nombre'] = df_libres['pdb_nombre'].str.strip().str.upper()

    # ---------------------------------------------------------
    # ESTRATEGIA DE FAILOVER (INTENTOS EN ORDEN)
    # ---------------------------------------------------------
    pdbs_a_evaluar = ["PDB1", "PDB2"] # Orden de preferencia
    pdb_ganador = None
    
    for pdb_candidato in pdbs_a_evaluar:
        print(f"   🔎 Evaluando candidato: {pdb_candidato}...")
        
        # A. Chequeo Físico
        fisico_ok, msg_fisico = _verificar_espacio_fisico_en_un_pdb(df_libres, pdb_candidato, fuentes)
        
        if not fisico_ok:
            informe["Checks"].append(f"⚠️ {pdb_candidato} descartado por espacio físico.")
            continue # Salta al siguiente PDB
            
        # B. Chequeo Eléctrico
        electrico_ok, msgs_electrico = _validar_capacidad_electrica_pdb(pdb_candidato, amps_nuevos)
        
        if not electrico_ok:
            informe["Checks"].append(f"⚠️ {pdb_candidato} descartado por capacidad eléctrica:")
            informe["Checks"].extend(msgs_electrico)
            continue # Salta al siguiente PDB
            
        # ¡SI LLEGAMOS AQUÍ, ES EL GANADOR!
        pdb_ganador = pdb_candidato
        informe["Recomendacion_Instalacion"] = f"Instalación asignada en {pdb_ganador} ({fuentes} fuentes):\n{msg_fisico}"
        informe["Checks"].extend(msgs_electrico) # Agregamos los checks exitosos
        break # Dejamos de buscar

    # ---------------------------------------------------------
    # RESULTADO DE LA BÚSQUEDA
    # ---------------------------------------------------------
    if not pdb_ganador:
        informe["Checks"].append("❌ RECHAZADO FINAL: Ningún PDB cumple con requisitos físicos Y eléctricos.")
        return informe

    # 4. VALIDACIÓN AGUAS ARRIBA (Solo si pasó los PDBs)
    kva_actual, r1_amps, r2_amps = _obtener_carga_actual_historica(engine)
    potencia_ac = potencia_total / CONSTANTES["EFICIENCIA_RECT"]
    kva_nuevo = (potencia_ac / 1000) / CONSTANTES["FP_EQUIPO"]
    kva_futuro = kva_actual + kva_nuevo
    
    if kva_futuro > (CONSTANTES["CAPACIDAD_TR_KVA"] * CONSTANTES["LIMITE_SEGURIDAD"]):
        informe["Checks"].append(f"❌ RECHAZADO: Sobrecarga en potencia ({kva_futuro:.1f} kVA).")
        informe["PRE-Factibilidad Infraestructura (Si / No)"] = "NO"
    else:
        informe["Checks"].append(f"✅ Potencia actual (kva) OK: {kva_actual:.1f} -> Potencia futuro (kva) {kva_futuro:.1f} kVA.")
        informe["PRE-Factibilidad Infraestructura (Si / No)"] = "SI"

    return informe




#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def _calcular_corriente_ac_trifasica(potencia_dc_total_w):
    """
    Convierte la carga DC (Watts) a Corriente AC por fase (Amperios).
    Fórmula: I_ac = (Watts_DC / Eficiencia) / (sqrt(3) * Voltaje_AC * FP)
    """
    # 1. Watts reales que toma de la red (considerando pérdidas de calor)
    potencia_ac_w = potencia_dc_total_w / CONSTANTES["EFICIENCIA_RECT"]
    
    # 2. Corriente por fase (Trifásica)
    # I = P / (√3 * V * PF)
    amps_ac = potencia_ac_w / (math.sqrt(3) * CONSTANTES["VOLTAJE_AC"] * CONSTANTES["FP_EQUIPO"])
    
    return amps_ac







def _validar_protecciones_aguas_arriba(self, engine, pdb_seleccionado, potencia_total_w, amps_nuevos_dc):
        """
        Valida Fusibles, Breakers AC, ML y TR usando PROMEDIOS FIJOS para la carga actual.
        """
        checks = []
        aprobado = True
        
        # --- 1. DATOS DE CARGA ACTUAL (Promedios Manuales) ---
        # Corriente AC (Amperios por fase)
        corriente_ac_l1_tr = 61.01
        corriente_ac_l2_tr = 60.23
        corriente_ac_l3_tr = 61.06
        
        corriente_ac_r_ml = 61.49
        corriente_ac_s_ml = 62.59  
        corriente_ac_t_ml = 67.77

        # Promedios trifásicos actuales
        carga_actual_tr_ac = (corriente_ac_l1_tr + corriente_ac_l2_tr + corriente_ac_l3_tr) / 3
        carga_actual_ml_ac = (corriente_ac_r_ml + corriente_ac_s_ml + corriente_ac_t_ml) / 3
        
        # Corriente DC Actual (Amperios Totales)
        carga_actual_r1_dc = 118.67 
        carga_actual_r2_dc = 155.96 

        # --- 2. CÁLCULOS DE LA NUEVA CARGA ---
        # Calculamos cuánto representa la nueva carga en AC (para sumar al TR y ML)
        # Asegúrate de tener self.CONSTANTES disponible o pásalas
        amps_nuevos_ac = (potencia_total_w / self.CONSTANTES["EFICIENCIA_RECT"]) / (math.sqrt(3) * self.CONSTANTES["VOLTAJE_AC"] * self.CONSTANTES["FP_EQUIPO"])
        
        # --- 3. SELECCIÓN DE RUTA CRÍTICA (¿R1 o R2?) ---
        if "PDB1" in pdb_seleccionado:
            rect_asociado = "Rect1"
            nombre_fusible = "Fusible PDB1%"
            nombre_breaker_rect = "Breaker Rect 1"
            # ¡ESTO FALTABA!: Asignar la carga base correcta según el PDB
            carga_dc_base = carga_actual_r1_dc 
        else:
            rect_asociado = "Rect2"
            nombre_fusible = "Fusible PDB2%"
            nombre_breaker_rect = "Breaker Rect 2"
            # ¡ESTO FALTABA!:
            carga_dc_base = carga_actual_r2_dc

        with engine.connect() as conn:
            
            # =========================================================
            # NIVEL 1: FUSIBLES DC (Salida del Rectificador -> PDB)
            # =========================================================
            sql_fus = text("""
                SELECT capacidad_amps FROM inventario_protecciones 
                WHERE ubicacion = :rect AND componente LIKE :fus AND tipo = 'DC'
            """)
            limite_fusible = conn.execute(sql_fus, {"rect": rect_asociado, "fus": nombre_fusible}).scalar()
            
            if limite_fusible:
                futuro_dc = carga_dc_base + amps_nuevos_dc
                if futuro_dc > limite_fusible:
                    checks.append(f"❌ SOBRECARGA FUSIBLE DC ({rect_asociado}): Actual {carga_dc_base}A + Nuevo {amps_nuevos_dc:.1f}A = {futuro_dc:.1f}A > {limite_fusible}A")
                    aprobado = False
                else:
                    checks.append(f"✅ Fusible DC {rect_asociado} OK: {futuro_dc:.1f}A (Límite {limite_fusible}A)")
            else:
                checks.append(f"⚠️ No se encontró info del fusible para {rect_asociado} en BD.")

            # =========================================================
            # NIVEL 2: BREAKER AC DEL RECTIFICADOR (Entrada)
            # =========================================================
            sql_brk = text("""
                SELECT capacidad_amps FROM inventario_protecciones 
                WHERE ubicacion = 'ML' AND componente = :comp AND tipo = 'AC'
            """)
            limite_breaker_rect = conn.execute(sql_brk, {"comp": nombre_breaker_rect}).scalar()
            
            # Estimamos cuánto consume el rectificador actual en AC basándonos en su carga DC actual
            # Fórmula inversa: (AmperiosDC * VoltajeDC) / Eficiencia ... convertido a AC
            potencia_actual_rect_watts = carga_dc_base * self.CONSTANTES["VOLTAJE_DC"]
            potencia_actual_rect_ac_watts = potencia_actual_rect_watts / self.CONSTANTES["EFICIENCIA_RECT"]
            carga_actual_rect_ac = potencia_actual_rect_ac_watts / (math.sqrt(3) * self.CONSTANTES["VOLTAJE_AC"] * self.CONSTANTES["FP_EQUIPO"])
            
            if limite_breaker_rect:
                futuro_rect_ac = carga_actual_rect_ac + amps_nuevos_ac
                if futuro_rect_ac > limite_breaker_rect:
                    checks.append(f"❌ SOBRECARGA BREAKER AC ({nombre_breaker_rect}): {futuro_rect_ac:.1f}A > {limite_breaker_rect}A")
                    aprobado = False
                else:
                    checks.append(f"✅ Breaker AC {rect_asociado} OK: {futuro_rect_ac:.1f}A (Límite {limite_breaker_rect}A)")
            else:
                checks.append(f"⚠️ No se encontró el breaker AC '{nombre_breaker_rect}' en el ML.")

            # =========================================================
            # NIVEL 3: TOTALIZADORES GENERALES (ML y TR)
            # =========================================================
            
            # A. Totalizador ML
            sql_ml_limit = text("SELECT capacidad_amps FROM inventario_protecciones WHERE componente = 'Totalizador ML' AND tipo = 'AC'")
            limite_ml = conn.execute(sql_ml_limit).scalar()
            
            if limite_ml:
                futuro_ml = carga_actual_ml_ac + amps_nuevos_ac
                if futuro_ml > limite_ml:
                    checks.append(f"❌ SOBRECARGA TOTALIZADOR ML: {futuro_ml:.1f}A > {limite_ml}A")
                    aprobado = False
                else:
                    checks.append(f"✅ Totalizador ML OK: {futuro_ml:.1f}A / {limite_ml}A")

            # B. Totalizador TR
            sql_tr_limit = text("SELECT capacidad_amps FROM inventario_protecciones WHERE componente = 'Totalizador Red' AND tipo = 'AC'")
            limite_tr = conn.execute(sql_tr_limit).scalar()
            
            if limite_tr:
                futuro_tr = carga_actual_tr_ac + amps_nuevos_ac
                if futuro_tr > limite_tr:
                    checks.append(f"❌ SOBRECARGA TOTALIZADOR TR: {futuro_tr:.1f}A > {limite_tr}A")
                    aprobado = False
                else:
                    checks.append(f"✅ Totalizador TR OK: {futuro_tr:.1f}A / {limite_tr}A")

        return aprobado, checks