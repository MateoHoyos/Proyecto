"""
alarmas.py — Módulo de Alarmas y Monitoreo en Tiempo Real
──────────────────────────────────────────────────────────────────────────────
Este módulo es el encargado de vigilar continuamente el estado eléctrico
y térmico del nodo. Implementa dos capas de detección independientes que
se ejecutan juntas en cada evaluación:

    Capa 1 — Umbrales Fijos:
        Reglas técnicas explícitas que comparan cada variable contra límites
        definidos según las especificaciones del fabricante y los estándares
        del nodo. Genera alarmas inmediatas y claras cuando un valor supera
        un límite conocido.

    Capa 2 — Isolation Forest:
        Modelo de inteligencia artificial entrenado con el histórico 2025
        del nodo. Detecta situaciones anómalas multivariables que no
        necesariamente violan un umbral fijo pero son inusuales para el
        comportamiento típico del sistema. Complementa la Capa 1.

Flujo de uso (desde panel_alarmas.py):
    from src.alarmas import evaluar_alarmas_completo
    resultado = evaluar_alarmas_completo(engine)
    # resultado contiene el nivel de severidad, lista de alarmas e IF score
──────────────────────────────────────────────────────────────────────────────
"""

import os
import pickle
import math
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────
#  CAPA 1 — CONFIGURACIÓN DE UMBRALES FIJOS
#
#  Cada variable tiene un umbral definido según su tipo:
#
#  Tipo warn/crit (solo límite superior):
#    warn: primer nivel de alerta (ej: 80% de la capacidad)
#    crit: nivel crítico que requiere acción inmediata (ej: 90%)
#
#  Tipo min/max (rango bilateral):
#    min: límite inferior permitido
#    max: límite superior permitido
#    Si el valor sale del rango [min, max], genera alarma CRÍTICO
#
#  Fuentes de los límites:
#    - Corriente AC: límite del fusible del nodo = 160A → warn al 80%, crit al 90%
#    - Potencia TR:  transformador 75kVA → límite operativo 90% = 67.5 kVA
#    - Voltaje AC:   nominal 220V ±10% → rango válido [198V, 242V]
#    - Temperatura:  estándar ASHRAE A2 → máximo 27°C, advertencia desde 25°C
#    - % Carga RECT: warn al 80%, crit al 90%
#    - Voltaje DC:   nominal 54V ±5% → rango válido [51.3V, 56.7V]
# ─────────────────────────────────────────────────────────────
UMBRALES = {
    # ── Corriente AC — Transformador (TR) ────────────────────
    "tr_corriente_ac_l1": {"warn": 128.0, "crit": 144.0, "unidad": "A",  "label": "Corriente AC L1 (TR)"},
    "tr_corriente_ac_l2": {"warn": 128.0, "crit": 144.0, "unidad": "A",  "label": "Corriente AC L2 (TR)"},
    "tr_corriente_ac_l3": {"warn": 128.0, "crit": 144.0, "unidad": "A",  "label": "Corriente AC L3 (TR)"},

    # ── Potencia aparente — Transformador (TR) ───────────────
    "tr_potencia_aparente_kva": {"warn": 60.0, "crit": 67.5, "unidad": "kVA", "label": "Potencia Aparente (TR)"},

    # ── Voltaje AC — Transformador (TR) ──────────────────────
    "tr_voltaje_ac_l1_l2": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje L1-L2 (TR)"},
    "tr_voltaje_ac_l2_l3": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje L2-L3 (TR)"},
    "tr_voltaje_ac_l3_l1": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje L3-L1 (TR)"},

    # ── Voltaje AC — Tablero Principal (ML) ──────────────────
    "ml_voltaje_ac_rs": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje AC R-S (ML)"},
    "ml_voltaje_ac_st": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje AC S-T (ML)"},
    "ml_voltaje_ac_tr": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje AC T-R (ML)"},

    # ── Corriente AC — Tablero Principal (ML) ────────────────
    "ml_corriente_ac_r": {"warn": 128.0, "crit": 144.0, "unidad": "A", "label": "Corriente AC R (ML)"},
    "ml_corriente_ac_s": {"warn": 128.0, "crit": 144.0, "unidad": "A", "label": "Corriente AC S (ML)"},
    "ml_corriente_ac_t": {"warn": 128.0, "crit": 144.0, "unidad": "A", "label": "Corriente AC T (ML)"},

    # ── Temperatura de la sala ────────────────────────────────
    # Estándar ASHRAE A2: temperatura máxima de entrada al equipo = 27°C
    "ml_temp_sala_s01": {"warn": 25.0, "crit": 27.0, "unidad": "°C", "label": "Temperatura Sala S01"},
    "ml_temp_sala_s02": {"warn": 25.0, "crit": 27.0, "unidad": "°C", "label": "Temperatura Sala S02"},

    # ── Rectificadores (se evalúan R1 y R2 por separado) ─────
    # El prefijo "rect_" indica que se aplica a ambos rectificadores
    "rect_porcentaje_carga":  {"warn": 80.0, "crit": 90.0,  "unidad": "%", "label": "% Carga Rectificador"},
    "rect_voltaje_dc_salida": {"min": 51.3,  "max": 56.7,   "unidad": "V", "label": "Voltaje DC Salida (RECT)"},
}


# ─────────────────────────────────────────────────────────────
#  RUTA DEL MODELO ISOLATION FOREST
#  El modelo se guarda en la carpeta Model/ en la raíz del proyecto.
#  Si el modelo no existe, la Capa 2 retorna "no disponible"
#  y el sistema funciona únicamente con umbrales fijos.
# ─────────────────────────────────────────────────────────────
_DIR_SRC    = os.path.dirname(os.path.abspath(__file__))
_DIR_BASE   = os.path.dirname(_DIR_SRC)
RUTA_MODELO = os.path.join(_DIR_BASE, "Model", "modelo_if.pkl")
RUTA_META   = os.path.join(_DIR_BASE, "Model", "meta_if.pkl")


# ═════════════════════════════════════════════════════════════
# CAPA 1 — UMBRALES FIJOS
# ═════════════════════════════════════════════════════════════

def _evaluar_umbral(clave, valor, config):
    """
    Evalúa una variable contra su umbral y retorna una alarma si hay problema.

    Para umbrales de rango (min/max):
        Si el valor está fuera del rango [min, max], genera alarma CRÍTICO.
        Ejemplo: voltaje AC fuera del ±10% del nominal.

    Para umbrales de límite superior (warn/crit):
        Si supera el umbral crítico → CRÍTICO.
        Si supera solo el de advertencia → ADVERTENCIA.
        Si está por debajo del warn → sin alarma (retorna None).

    Retorna None si el valor está dentro de los parámetros normales,
    o un diccionario de alarma con variable, valor, umbral y severidad.
    """
    # Ignorar valores nulos o NaN (sensor sin datos)
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None

    label  = config.get("label", clave)
    unidad = config.get("unidad", "")

    # Umbral de rango bilateral (voltajes AC y DC)
    if "min" in config and "max" in config:
        if valor < config["min"]:
            return {
                "variable": label, "valor": valor,
                "umbral": config["min"], "unidad": unidad,
                "tipo": "BAJO", "severidad": "CRITICO",
                "mensaje": f"{label}: {valor:.1f}{unidad} por debajo del mínimo ({config['min']}{unidad})"
            }
        if valor > config["max"]:
            return {
                "variable": label, "valor": valor,
                "umbral": config["max"], "unidad": unidad,
                "tipo": "ALTO", "severidad": "CRITICO",
                "mensaje": f"{label}: {valor:.1f}{unidad} por encima del máximo ({config['max']}{unidad})"
            }
        return None

    # Umbral de límite superior (corriente, potencia, temperatura)
    if "crit" in config and valor >= config["crit"]:
        return {
            "variable": label, "valor": valor,
            "umbral": config["crit"], "unidad": unidad,
            "tipo": "SOBRECARGA", "severidad": "CRITICO",
            "mensaje": f"{label}: {valor:.1f}{unidad} ≥ límite crítico ({config['crit']}{unidad})"
        }
    if "warn" in config and valor >= config["warn"]:
        return {
            "variable": label, "valor": valor,
            "umbral": config["warn"], "unidad": unidad,
            "tipo": "ADVERTENCIA", "severidad": "ADVERTENCIA",
            "mensaje": f"{label}: {valor:.1f}{unidad} ≥ umbral de advertencia ({config['warn']}{unidad})"
        }
    return None


def evaluar_umbrales_fijos(lectura: dict) -> list:
    """
    Evalúa todas las variables de la lectura actual contra los umbrales definidos.

    Recibe un diccionario plano con todas las lecturas del nodo, donde las
    claves siguen el formato: equipo_variable (ej: tr_corriente_ac_l1).

    Para las variables de rectificador (prefijo 'rect_'), evalúa R1 y R2
    por separado, generando una alarma independiente para cada uno si aplica.

    Retorna la lista de alarmas detectadas (puede estar vacía si todo está normal).
    """
    alarmas = []

    for clave_cfg, config in UMBRALES.items():

        # Variables de rectificador: evaluar R1 y R2 de forma independiente
        if clave_cfg.startswith("rect_"):
            sufijo = clave_cfg[5:]   # Ej: "porcentaje_carga"
            for rid in [1, 2]:
                clave_real = f"r{rid}_{sufijo}"
                valor      = lectura.get(clave_real)
                if valor is not None:
                    alarma = _evaluar_umbral(clave_real, float(valor), config)
                    if alarma:
                        # Personalizar el label con el número del rectificador
                        alarma["variable"] = f"{config['label']} (Rect {rid})"
                        alarmas.append(alarma)
        else:
            # Variables del TR y ML: evaluación directa
            valor = lectura.get(clave_cfg)
            if valor is not None:
                alarma = _evaluar_umbral(clave_cfg, float(valor), config)
                if alarma:
                    alarmas.append(alarma)

    return alarmas


# ═════════════════════════════════════════════════════════════
# CAPA 2 — ISOLATION FOREST
# ═════════════════════════════════════════════════════════════

# Features del modelo — deben coincidir exactamente con entrenar_if.py
# Son las 21 variables que el modelo aprendió durante el entrenamiento
FEATURES_IF = [
    # Transformador
    "tr_corriente_ac_l1", "tr_corriente_ac_l2", "tr_corriente_ac_l3",
    "tr_potencia_activa_kw", "tr_potencia_reactiva_kvar", "tr_potencia_aparente_kva",
    "tr_factor_potencia",
    "tr_voltaje_ac_l1_l2", "tr_voltaje_ac_l2_l3", "tr_voltaje_ac_l3_l1",
    # Tablero ML
    "ml_corriente_ac_r", "ml_corriente_ac_s", "ml_corriente_ac_t",
    "ml_voltaje_ac_rs", "ml_voltaje_ac_st", "ml_voltaje_ac_tr",
    "ml_temp_sala_s01", "ml_temp_sala_s02",
    # Rectificadores (promedio R1 + R2)
    "rect_avg_corriente_dc", "rect_avg_voltaje_dc", "rect_avg_corriente_carga",
]


def _preparar_vector_if(lectura: dict) -> np.ndarray:
    """
    Construye el vector de features para el modelo a partir de la lectura actual.

    Los rectificadores se representan como promedios de R1 y R2, igual que
    durante el entrenamiento en entrenar_if.py. Esto es necesario para que
    el vector de entrada sea compatible con el modelo entrenado.

    Mapeo de columnas de rect_dce a features del modelo:
        r1/r2_corriente_dc_total → rect_avg_corriente_dc   (promedio R1+R2)
        r1/r2_voltaje_dc_salida  → rect_avg_voltaje_dc
        r1/r2_corriente_carga    → rect_avg_corriente_carga

    Si algún valor falta en la lectura, se usa 0.0 como fallback para no
    interrumpir la evaluación del modelo.
    """
    lectura_ext = dict(lectura)

    def avg(campo_r1, campo_r2):
        """Calcula el promedio de dos campos, usando 0 si alguno es None."""
        v1 = lectura_ext.get(campo_r1) or 0
        v2 = lectura_ext.get(campo_r2) or 0
        return (v1 + v2) / 2

    # Calcular los promedios de los rectificadores
    lectura_ext["rect_avg_corriente_dc"]    = avg("r1_corriente_dc_total", "r2_corriente_dc_total")
    lectura_ext["rect_avg_voltaje_dc"]      = avg("r1_voltaje_dc_salida",  "r2_voltaje_dc_salida")
    lectura_ext["rect_avg_corriente_carga"] = avg("r1_corriente_carga",    "r2_corriente_carga")

    # Construir el vector en el mismo orden que se usó en el entrenamiento
    vector = []
    for feat in FEATURES_IF:
        val = lectura_ext.get(feat, 0)
        vector.append(float(val) if val is not None else 0.0)

    return np.array(vector).reshape(1, -1)


def evaluar_isolation_forest(lectura: dict) -> dict:
    """
    Evalúa la lectura actual con el modelo Isolation Forest entrenado.

    El modelo calcula un score de anomalía para la lectura:
        - score_samples() retorna un valor negativo: más negativo = más anómalo
        - El score se normaliza a escala 0-100 usando el rango observado
          durante el entrenamiento (guardado en meta_if.pkl)
        - score_pct cercano a 100 = muy anómalo / cercano a 0 = muy normal

    También identifica las 3 variables que más se desvían de su media
    histórica (en unidades de desviación estándar), ayudando al técnico
    a identificar qué está causando la anomalía detectada.

    Retorna un diccionario con:
        disponible          : bool — si el modelo existe y pudo cargarse
        es_anomalia         : bool — True si el modelo clasificó como anómalo
        score               : float — score raw del modelo
        score_pct           : float — score normalizado 0-100
        features_influyentes: list  — top 3 variables más desviadas
        todas_las_desviaciones: list — todas las variables ordenadas por desviación
        mensaje             : str   — resumen legible del resultado
    """
    resultado = {
        "disponible":           False,
        "es_anomalia":          False,
        "score":                None,
        "score_pct":            None,
        "features_influyentes": [],
        "mensaje":              "Modelo no entrenado. Ejecute 'Entrenar Modelo' primero."
    }

    # Si el modelo no existe, retornar sin evaluación de IA
    if not os.path.exists(RUTA_MODELO):
        return resultado

    try:
        # Cargar el modelo y sus metadatos desde los archivos pickle
        with open(RUTA_MODELO, "rb") as f:
            paquete = pickle.load(f)
        with open(RUTA_META, "rb") as f:
            meta    = pickle.load(f)

        resultado["disponible"] = True

        # Preparar el vector de entrada y aplicar el scaler del modelo
        vector_raw    = _preparar_vector_if(lectura)
        scaler        = paquete.get("scaler")
        modelo        = paquete.get("modelo")
        vector_scaled = scaler.transform(vector_raw)

        # Obtener el score de anomalía y la predicción del modelo
        score_raw  = modelo.score_samples(vector_scaled)[0]
        prediccion = modelo.predict(vector_scaled)[0]   # -1 = anómalo, 1 = normal

        # Normalizar el score a escala 0-100
        # score_min y score_max son los valores extremos del histórico de entrenamiento
        score_min  = meta.get("score_min", -0.5)
        score_max  = meta.get("score_max",  0.0)
        score_norm = (score_raw - score_min) / (score_max - score_min + 1e-9)
        score_pct  = round((1 - np.clip(score_norm, 0, 1)) * 100, 1)

        resultado["score"]       = round(score_raw, 4)
        resultado["score_pct"]   = score_pct
        resultado["es_anomalia"] = (prediccion == -1)

        # Identificar las variables más desviadas de su media histórica
        # Se calcula la desviación en sigmas: (valor_actual - media) / std
        medias  = meta.get("feature_means", {})
        stds    = meta.get("feature_stds", {})
        desvios = []
        for i, feat in enumerate(FEATURES_IF):
            mu  = medias.get(feat, 0)
            sig = stds.get(feat, 1) or 1
            dev = abs((vector_raw[0][i] - mu) / sig)
            desvios.append((feat, dev, vector_raw[0][i]))

        # Ordenar de mayor a menor desviación
        desvios.sort(key=lambda x: x[1], reverse=True)

        # Top 3 para el mensaje rápido en la interfaz
        resultado["features_influyentes"] = [
            {"feature": f, "desviacion_sigma": round(d, 2), "valor_actual": round(v, 2)}
            for f, d, v in desvios[:3]
        ]

        # Todas las desviaciones para la vista detallada en el panel de alarmas
        resultado["todas_las_desviaciones"] = [
            {
                "feature":          f,
                "desviacion_sigma": round(d, 2),
                "valor_actual":     round(v, 2),
                "media_historica":  round(medias.get(f, 0), 2),
                "std_historica":    round(stds.get(f, 1) or 1, 2),
            }
            for f, d, v in desvios
        ]

        # Construir el mensaje resumen
        if resultado["es_anomalia"]:
            resultado["mensaje"] = (
                f"⚠️ ANOMALÍA DETECTADA — Score anómalo: {score_pct:.0f}/100. "
                f"Variables más desviadas: "
                f"{', '.join(x['feature'] for x in resultado['features_influyentes'])}"
            )
        else:
            resultado["mensaje"] = f"✅ Operación normal — Score anómalo: {score_pct:.0f}/100"

    except Exception as e:
        resultado["mensaje"] = f"Error evaluando modelo IF: {e}"

    return resultado


# ═════════════════════════════════════════════════════════════
# LECTOR DE ÚLTIMA LECTURA DESDE MySQL
# ═════════════════════════════════════════════════════════════

def obtener_ultima_lectura_db(engine) -> dict:
    """
    Lee la última fila de cada tabla operativa del DCE y construye
    el diccionario plano que usan las funciones de evaluación.

    Siempre consulta con ORDER BY fecha DESC LIMIT 1 para obtener
    la lectura más reciente disponible en la base de datos.

    Las claves del diccionario siguen el formato equipo_variable:
        tr_voltaje_ac_l1_l2, ml_temp_sala_s01, r1_corriente_dc_total...

    Si una tabla falla (por error de conexión u otro motivo), se registra
    el error en el diccionario y se continúa con las demás tablas para
    no interrumpir el monitoreo completo del nodo.
    """
    lectura = {}

    with engine.connect() as conn:

        # ── Transferencia Automática (TR) ─────────────────────────────────
        try:
            row = conn.execute(text("""
                SELECT voltaje_ac_l1_l2, voltaje_ac_l2_l3, voltaje_ac_l3_l1,
                       corriente_ac_l1, corriente_ac_l2, corriente_ac_l3,
                       potencia_activa_kw, potencia_reactiva_kvar,
                       potencia_aparente_kva, factor_potencia, fecha
                FROM tr_dce ORDER BY fecha DESC LIMIT 1
            """)).mappings().fetchone()
            if row:
                lectura["tr_voltaje_ac_l1_l2"]      = row["voltaje_ac_l1_l2"]
                lectura["tr_voltaje_ac_l2_l3"]      = row["voltaje_ac_l2_l3"]
                lectura["tr_voltaje_ac_l3_l1"]      = row["voltaje_ac_l3_l1"]
                lectura["tr_corriente_ac_l1"]        = row["corriente_ac_l1"]
                lectura["tr_corriente_ac_l2"]        = row["corriente_ac_l2"]
                lectura["tr_corriente_ac_l3"]        = row["corriente_ac_l3"]
                lectura["tr_potencia_activa_kw"]     = row["potencia_activa_kw"]
                lectura["tr_potencia_reactiva_kvar"] = row["potencia_reactiva_kvar"]
                lectura["tr_potencia_aparente_kva"]  = row["potencia_aparente_kva"]
                lectura["tr_factor_potencia"]        = row["factor_potencia"]
                lectura["_fecha_tr"]                 = str(row["fecha"])
        except Exception as e:
            lectura["_error_tr"] = str(e)

        # ── Tablero Principal (ML) ────────────────────────────────────────
        try:
            row = conn.execute(text("""
                SELECT corriente_ac_r, corriente_ac_s, corriente_ac_t,
                       voltaje_ac_rs, voltaje_ac_st, voltaje_ac_tr,
                       temp_sala_s01, temp_sala_s02, fecha
                FROM ml_dce ORDER BY fecha DESC LIMIT 1
            """)).mappings().fetchone()
            if row:
                lectura["ml_corriente_ac_r"] = row["corriente_ac_r"]
                lectura["ml_corriente_ac_s"] = row["corriente_ac_s"]
                lectura["ml_corriente_ac_t"] = row["corriente_ac_t"]
                lectura["ml_voltaje_ac_rs"]  = row["voltaje_ac_rs"]
                lectura["ml_voltaje_ac_st"]  = row["voltaje_ac_st"]
                lectura["ml_voltaje_ac_tr"]  = row["voltaje_ac_tr"]
                lectura["ml_temp_sala_s01"]  = row["temp_sala_s01"]
                lectura["ml_temp_sala_s02"]  = row["temp_sala_s02"]
                lectura["_fecha_ml"]         = str(row["fecha"])
        except Exception as e:
            lectura["_error_ml"] = str(e)

        # ── Rectificadores 1 y 2 ─────────────────────────────────────────
        # Se consultan en el mismo loop para no duplicar código
        for rid in [1, 2]:
            try:
                row = conn.execute(text(f"""
                    SELECT voltaje_dc_salida, corriente_dc_total,
                           porcentaje_carga, corriente_carga, fecha
                    FROM rect_dce
                    WHERE rectificador_id = {rid}
                    ORDER BY fecha DESC LIMIT 1
                """)).mappings().fetchone()
                if row:
                    lectura[f"r{rid}_voltaje_dc_salida"]  = row["voltaje_dc_salida"]
                    lectura[f"r{rid}_corriente_dc_total"] = row["corriente_dc_total"]
                    lectura[f"r{rid}_porcentaje_carga"]   = row["porcentaje_carga"]
                    lectura[f"r{rid}_corriente_carga"]    = row["corriente_carga"]
                    lectura[f"_fecha_r{rid}"]             = str(row["fecha"])
            except Exception as e:
                lectura[f"_error_r{rid}"] = str(e)

    return lectura


# ═════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL — EVALUACIÓN COMPLETA
# ═════════════════════════════════════════════════════════════

def evaluar_alarmas_completo(engine, lectura: dict = None) -> dict:
    """
    Punto de entrada principal del módulo de alarmas.

    Ejecuta las dos capas de detección y consolida los resultados
    en un único diccionario con toda la información necesaria para
    la interfaz (panel_alarmas.py) y el envío de email.

    Si no se provee una lectura, la obtiene automáticamente de MySQL.
    Esto permite también evaluar lecturas de prueba externas.

    El nivel máximo de severidad se determina así:
        - Si hay al menos una alarma CRÍTICO → nivel = "CRITICO"
        - Si hay advertencias o el IF detectó anomalía → nivel = "ADVERTENCIA"
        - Si no hay ninguna alarma activa → nivel = "OK"

    Retorna:
        timestamp        : fecha y hora de la evaluación
        lectura          : dict con los valores actuales de todos los sensores
        alarmas_umbrales : list de alarmas de la Capa 1
        resultado_if     : dict con el resultado de la Capa 2
        hay_alarmas      : bool — True si alguna capa detectó algo
        nivel_maximo     : "OK" | "ADVERTENCIA" | "CRITICO"
        resumen          : mensaje resumen con emoji de color para la UI
    """
    # Obtener la última lectura de la BD si no se proporcionó externamente
    if lectura is None:
        lectura = obtener_ultima_lectura_db(engine)

    # CAPA 1: Evaluación de umbrales fijos
    alarmas_u = evaluar_umbrales_fijos(lectura)

    # CAPA 2: Evaluación con Isolation Forest
    resultado_if = evaluar_isolation_forest(lectura)

    # Determinar el nivel máximo de severidad consolidando ambas capas
    niveles = [a["severidad"] for a in alarmas_u]
    if resultado_if.get("es_anomalia"):
        niveles.append("ADVERTENCIA")   # IF agrega nivel de advertencia si detecta anomalía

    if "CRITICO" in niveles:
        nivel = "CRITICO"
    elif "ADVERTENCIA" in niveles:
        nivel = "ADVERTENCIA"
    else:
        nivel = "OK"

    hay_alarmas = len(alarmas_u) > 0 or resultado_if.get("es_anomalia", False)

    # Construir el mensaje resumen con emoji de semáforo
    if nivel == "CRITICO":
        n_crit  = len([a for a in alarmas_u if a['severidad'] == 'CRITICO'])
        resumen = f"🔴 {n_crit} alarma(s) CRÍTICA(S) detectada(s)."
    elif nivel == "ADVERTENCIA":
        resumen = f"🟡 {len(alarmas_u)} advertencia(s). Revisar condiciones del nodo."
    else:
        resumen = "🟢 Nodo operando dentro de parámetros normales."

    return {
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lectura":          lectura,
        "alarmas_umbrales": alarmas_u,
        "resultado_if":     resultado_if,
        "hay_alarmas":      hay_alarmas,
        "nivel_maximo":     nivel,
        "resumen":          resumen,
    }


# ═════════════════════════════════════════════════════════════
# EMAIL DE ALARMA
# ═════════════════════════════════════════════════════════════

def enviar_email_alarma(resultado: dict, destinatarios: list) -> tuple:
    """
    Envía un correo electrónico HTML con el resumen de las alarmas detectadas.

    El email se construye con formato HTML para mejor legibilidad, incluyendo:
        - Banner de color según la severidad (rojo, amarillo, verde)
        - Tabla de variables en alarma con valor actual vs límite
        - Resultado del Isolation Forest con el score de anomalía

    Configuración SMTP:
        Usa el servidor de Outlook corporativo (smtp.office365.com, puerto 587)
        con autenticación TLS. Las credenciales deben configurarse antes de usar.

    PENDIENTE DE CONFIGURACIÓN:
        Reemplazar SMTP_USER y SMTP_PASS con las credenciales corporativas.
        En producción, estas deberían cargarse desde variables de entorno.

    Retorna (True, mensaje) si el envío fue exitoso,
            (False, error)  si ocurrió algún problema.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # ── CONFIGURACIÓN SMTP — PENDIENTE DE COMPLETAR ────────────────────
    SMTP_HOST = "smtp.office365.com"     # Servidor Outlook corporativo
    SMTP_PORT = 587                       # Puerto TLS
    SMTP_USER = "tu_usuario@tigo.com"    # ← Reemplazar con usuario corporativo
    SMTP_PASS = "tu_contraseña"          # ← Reemplazar (usar variable de entorno)
    REMITENTE = "alertas-ideo@tigo.com"
    # ────────────────────────────────────────────────────────────────────

    nivel   = resultado["nivel_maximo"]
    alarmas = resultado["alarmas_umbrales"]
    res_if  = resultado["resultado_if"]
    ts      = resultado["timestamp"]

    # Colores del banner según severidad
    color_banner = {"CRITICO": "#C0392B", "ADVERTENCIA": "#E67E22", "OK": "#1E8449"}.get(nivel, "#888")
    icono        = {"CRITICO": "🔴",      "ADVERTENCIA": "🟡",      "OK": "🟢"}.get(nivel, "⚪")

    # Construir filas HTML de la tabla de alarmas
    filas_html = ""
    for a in alarmas:
        color_fila  = "#FADBD8" if a["severidad"] == "CRITICO" else "#FEF9E7"
        filas_html += f"""
        <tr style="background:{color_fila}">
            <td style="padding:6px 10px">{a['variable']}</td>
            <td style="padding:6px 10px;text-align:center"><b>{a['valor']:.1f} {a['unidad']}</b></td>
            <td style="padding:6px 10px;text-align:center">{a['umbral']} {a['unidad']}</td>
            <td style="padding:6px 10px;text-align:center"><b>{a['severidad']}</b></td>
        </tr>"""

    # Sección del Isolation Forest (solo si el modelo está disponible)
    if_html = ""
    if res_if.get("disponible"):
        color_if = "#FADBD8" if res_if["es_anomalia"] else "#D5F5E3"
        if_html  = f"""
        <h3 style="color:#1A5276">Análisis Isolation Forest</h3>
        <div style="background:{color_if};padding:10px;border-radius:6px">
            {res_if['mensaje']}<br>
            Score anómalo: <b>{res_if['score_pct']}/100</b>
        </div>"""

    # Construir el cuerpo HTML completo del email
    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#2C3E50">
    <div style="background:{color_banner};color:white;padding:16px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">{icono} Alerta IDEO — Nodo IDEO CALI | {nivel}</h2>
        <p style="margin:4px 0 0 0;font-size:13px">Generado: {ts}</p>
    </div>
    <div style="padding:16px;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px">
        <p>{resultado['resumen']}</p>
        {"<table border='0' cellspacing='0' width='100%' style='border-collapse:collapse'>"
         "<tr style='background:#1A5276;color:white'>"
         "<th style='padding:7px 10px;text-align:left'>Variable</th>"
         "<th style='padding:7px 10px'>Valor Actual</th>"
         "<th style='padding:7px 10px'>Límite</th>"
         "<th style='padding:7px 10px'>Severidad</th></tr>"
         + filas_html + "</table>"
         if alarmas else "<p>✅ Sin violaciones de umbrales.</p>"}
        {if_html}
        <hr style="margin:20px 0">
        <p style="font-size:11px;color:#888">
            Este es un mensaje automático del Sistema IDEO — Gerencia Infraestructura.
        </p>
    </div>
    </body></html>
    """

    try:
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = f"[IDEO] Alerta {nivel} — Nodo IDEO CALI — {ts}"
        msg["From"]    = REMITENTE
        msg["To"]      = ", ".join(destinatarios)
        msg.attach(MIMEText(html, "html"))

        # Conectar al servidor SMTP y enviar
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
            servidor.starttls()                         # Iniciar conexión TLS
            servidor.login(SMTP_USER, SMTP_PASS)        # Autenticación
            servidor.sendmail(REMITENTE, destinatarios, msg.as_string())

        return True, f"Email enviado a: {', '.join(destinatarios)}"

    except Exception as e:
        return False, f"Error enviando email: {e}"
