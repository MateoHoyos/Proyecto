"""
entrenar_if.py — Entrenamiento del Modelo Isolation Forest
──────────────────────────────────────────────────────────────────────────────
Este módulo entrena el modelo de inteligencia artificial que usa el sistema
para detectar anomalías en el comportamiento eléctrico y térmico del nodo.

El algoritmo utilizado es Isolation Forest, un método de detección de
anomalías no supervisado que no requiere datos etiquetados. Aprende el
comportamiento normal del nodo a partir del histórico 2025 (158.376 lecturas)
y genera un modelo capaz de identificar lecturas que se alejan de ese patrón.

PRE-REQUISITO: Las tablas históricas deben estar cargadas en MySQL.
    Ejecutar primero: etl_historico.py (o desde la interfaz → ETL Histórico)

Archivos generados en la carpeta Model/:
    modelo_if.pkl → pipeline completo (StandardScaler + IsolationForest)
    meta_if.pkl   → metadatos del modelo (rango de scores, medias, desviaciones)
                    usados por alarmas.py para normalizar el score y detectar
                    las variables más anómalas en cada evaluación

Flujo completo:
    MySQL (tablas históricas) → cargar_historico() → limpiar_datos()
    → entrenar_y_guardar() → modelo_if.pkl + meta_if.pkl
──────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from src.db import get_engine

# ─────────────────────────────────────────────────────────────
#  PARÁMETROS DEL MODELO
#  contamination: fracción estimada de lecturas anómalas en el histórico.
#    0.05 = se espera que el 5% de las lecturas del histórico sean anómalas.
#    Este valor determina el umbral de decisión del modelo.
#  n_estimators: número de árboles de aislamiento. Más árboles = más
#    estabilidad en las predicciones, a costa de mayor tiempo de entrenamiento.
#  random_state: semilla aleatoria para reproducibilidad de resultados.
# ─────────────────────────────────────────────────────────────
CONTAMINATION = 0.05   # 5% de lecturas anómalas esperadas en el histórico
N_ESTIMATORS  = 200    # Número de árboles de aislamiento
RANDOM_STATE  = 42     # Semilla para reproducibilidad

# ─────────────────────────────────────────────────────────────
#  FEATURES DEL MODELO — 21 variables de entrada
#  Representan el estado eléctrico y térmico completo del nodo.
#  IMPORTANTE: Estas features deben coincidir exactamente con las
#  definidas en alarmas.py → FEATURES_IF para que el modelo pueda
#  evaluar las lecturas en tiempo real correctamente.
# ─────────────────────────────────────────────────────────────
FEATURES_IF = [
    # Transformador (TR): corrientes, potencias y voltajes AC
    "tr_corriente_ac_l1", "tr_corriente_ac_l2", "tr_corriente_ac_l3",
    "tr_potencia_activa_kw", "tr_potencia_reactiva_kvar", "tr_potencia_aparente_kva",
    "tr_factor_potencia",
    "tr_voltaje_ac_l1_l2", "tr_voltaje_ac_l2_l3", "tr_voltaje_ac_l3_l1",
    # Tablero ML: corrientes, voltajes AC y temperatura de sala
    "ml_corriente_ac_r", "ml_corriente_ac_s", "ml_corriente_ac_t",
    "ml_voltaje_ac_rs", "ml_voltaje_ac_st", "ml_voltaje_ac_tr",
    "ml_temp_sala_s01", "ml_temp_sala_s02",
    # Rectificadores: promedios de R1 y R2 (corriente DC y voltaje DC)
    "rect_avg_corriente_dc", "rect_avg_voltaje_dc", "rect_avg_corriente_carga",
]

# Carpeta donde se guardan los archivos del modelo entrenado
DIR_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_SALIDA = os.path.join(DIR_BASE, "Model")


def cargar_historico(engine) -> pd.DataFrame:
    """
    Carga y une las 4 tablas históricas de MySQL en un solo DataFrame.

    Las 4 tablas (tr_historico, ml_historico, rect1_historico, rect2_historico)
    fueron generadas por etl_historico.py con resample a 10 minutos, lo que
    garantiza que todos los timestamps están alineados y el JOIN por timestamp
    produce el mínimo de pérdida de datos posible.

    Para los rectificadores, se calcula el promedio de R1 y R2 en lugar de
    usar los valores individuales, ya que el modelo aprende el comportamiento
    conjunto del sistema de rectificación del nodo.

    Si la retención del JOIN es menor al 70%, se muestra una advertencia
    porque podría indicar desalineación de timestamps entre tablas.
    """
    print("  Cargando tr_historico...")
    df_tr = pd.read_sql("""
        SELECT
            timestamp,
            corriente_ac_l1        AS tr_corriente_ac_l1,
            corriente_ac_l2        AS tr_corriente_ac_l2,
            corriente_ac_l3        AS tr_corriente_ac_l3,
            potencia_activa_kw     AS tr_potencia_activa_kw,
            potencia_reactiva_kvar AS tr_potencia_reactiva_kvar,
            potencia_aparente_kva  AS tr_potencia_aparente_kva,
            factor_potencia        AS tr_factor_potencia,
            voltaje_ac_l1_l2       AS tr_voltaje_ac_l1_l2,
            voltaje_ac_l2_l3       AS tr_voltaje_ac_l2_l3,
            voltaje_ac_l3_l1       AS tr_voltaje_ac_l3_l1
        FROM tr_historico ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    print("  Cargando ml_historico...")
    df_ml = pd.read_sql("""
        SELECT
            timestamp,
            corriente_ac_r AS ml_corriente_ac_r,
            corriente_ac_s AS ml_corriente_ac_s,
            corriente_ac_t AS ml_corriente_ac_t,
            voltaje_ac_rs  AS ml_voltaje_ac_rs,
            voltaje_ac_st  AS ml_voltaje_ac_st,
            voltaje_ac_tr  AS ml_voltaje_ac_tr,
            temp_sala_s01  AS ml_temp_sala_s01,
            temp_sala_s02  AS ml_temp_sala_s02
        FROM ml_historico ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    print("  Cargando rect1_historico...")
    df_r1 = pd.read_sql("""
        SELECT timestamp,
            corriente_dc_cs    AS r1_corriente_dc,
            voltaje_dc_vs      AS r1_voltaje_dc,
            corriente_dc_carga AS r1_corriente_carga
        FROM rect1_historico ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    print("  Cargando rect2_historico...")
    df_r2 = pd.read_sql("""
        SELECT timestamp,
            corriente_dc_cs    AS r2_corriente_dc,
            voltaje_dc_vs      AS r2_voltaje_dc,
            corriente_dc_carga AS r2_corriente_carga
        FROM rect2_historico ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    # JOIN por timestamp exacto: une las 4 tablas en un solo DataFrame
    # Las 4 tablas están alineadas a intervalos de 10 min por el resample de etl_historico.py
    print("  Uniendo tablas por timestamp...")
    df = df_tr.merge(df_ml, on="timestamp", how="inner")
    df = df.merge(df_r1,   on="timestamp", how="inner")
    df = df.merge(df_r2,   on="timestamp", how="inner")

    # Calcular promedios de R1 y R2 como features del modelo
    df["rect_avg_corriente_dc"]    = (df["r1_corriente_dc"]    + df["r2_corriente_dc"])    / 2
    df["rect_avg_voltaje_dc"]      = (df["r1_voltaje_dc"]      + df["r2_voltaje_dc"])      / 2
    df["rect_avg_corriente_carga"] = (df["r1_corriente_carga"] + df["r2_corriente_carga"]) / 2

    # Eliminar columnas intermedias que no son features del modelo
    df = df.drop(columns=[
        "r1_corriente_dc", "r1_voltaje_dc", "r1_corriente_carga",
        "r2_corriente_dc", "r2_voltaje_dc", "r2_corriente_carga",
        "timestamp"
    ])

    print(f"  Registros tras JOIN: {len(df):,}")

    # Verificar retención del JOIN
    min_tabla  = min(len(df_tr), len(df_ml), len(df_r1), len(df_r2))
    retencion  = len(df) / min_tabla * 100 if min_tabla > 0 else 0
    if retencion < 70:
        print(f"  ⚠️  Retención del JOIN: {retencion:.0f}% — revise alineación de timestamps.")
    else:
        print(f"  ✅ Retención del JOIN: {retencion:.0f}%")

    return df


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el DataFrame histórico antes de entrenar el modelo.

    Aplica tres pasos de limpieza:

        1. Imputación de NaN con la mediana de cada columna:
           Los valores faltantes (períodos sin datos del sensor) se rellenan
           con la mediana para no distorsionar el entrenamiento.

        2. Eliminación de filas con voltaje = 0:
           Un voltaje de 0 indica que el sensor estaba offline o hubo un
           corte de energía. Estas lecturas no representan el comportamiento
           normal del nodo y se eliminan para no contaminar el modelo.

        3. Eliminación de outliers extremos (> 5 sigma):
           Lecturas que se alejan más de 5 desviaciones estándar de la media
           son casi con certeza errores de medición y se eliminan antes
           de entrenar para que no sesguen los árboles de aislamiento.
    """
    cols_validas   = [c for c in FEATURES_IF if c in df.columns]
    cols_faltantes = [c for c in FEATURES_IF if c not in df.columns]
    if cols_faltantes:
        print(f"  ⚠️  Features no encontradas: {cols_faltantes}")

    df = df[cols_validas].copy()

    # PASO 1: Imputar NaN con la mediana de cada columna
    for col in df.columns:
        if df[col].isna().any():
            mediana  = df[col].median()
            df[col]  = df[col].fillna(mediana)

    # PASO 2: Eliminar filas con voltaje = 0 (sensor offline o corte de energía)
    for col in [c for c in cols_validas if "voltaje" in c]:
        antes  = len(df)
        df     = df[df[col] > 0]
        if len(df) < antes:
            print(f"      Eliminadas {antes - len(df)} filas con {col}=0")

    # PASO 3: Eliminar outliers extremos > 5 sigma (errores de medición)
    for col in df.columns:
        mu, sig = df[col].mean(), df[col].std()
        if sig > 0:
            antes = len(df)
            df    = df[(df[col] >= mu - 5*sig) & (df[col] <= mu + 5*sig)]
            if len(df) < antes:
                print(f"      Eliminados {antes - len(df)} outliers en '{col}'")

    print(f"  Registros limpios: {len(df):,}")
    return df


def entrenar_y_guardar(df: pd.DataFrame):
    """
    Entrena el modelo Isolation Forest y guarda los archivos resultantes.

    Proceso de entrenamiento:
        1. Estandarización: StandardScaler normaliza cada feature a media=0
           y desviación=1, necesario para que el Isolation Forest no sea
           afectado por diferencias de escala entre variables (ej: voltaje
           en V vs temperatura en °C).
        2. Entrenamiento: IsolationForest construye 200 árboles de aislamiento.
           Cada árbol intenta aislar puntos al azar; los puntos que se aíslan
           más rápido (con menos particiones) son los más anómalos.
        3. Cálculo de scores: score_samples() retorna un valor negativo por
           cada muestra. Más negativo = más anómalo.

    Archivos guardados:
        modelo_if.pkl : diccionario con el scaler y el modelo entrenados,
                        listos para aplicar a nuevas lecturas en tiempo real.
        meta_if.pkl   : metadatos para normalizar el score a escala 0-100
                        y para identificar las variables más desviadas.
    """
    X        = df[FEATURES_IF].values
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)   # Normalizar a media=0, std=1

    print(f"\n  Entrenando Isolation Forest...")
    print(f"    contamination = {CONTAMINATION}")
    print(f"    n_estimators  = {N_ESTIMATORS}")
    print(f"    n_features    = {len(FEATURES_IF)}")
    print(f"    n_samples     = {len(X):,}")

    modelo = IsolationForest(
        n_estimators  = N_ESTIMATORS,
        contamination = CONTAMINATION,
        random_state  = RANDOM_STATE,
        n_jobs        = -1   # Usar todos los núcleos disponibles
    )
    modelo.fit(X_scaled)

    # Calcular scores sobre los datos de entrenamiento para los metadatos
    scores       = modelo.score_samples(X_scaled)
    pct_anomalas = (modelo.predict(X_scaled) == -1).mean() * 100

    print(f"\n  Resultados:")
    print(f"    Score mín (más anómalo): {scores.min():.4f}")
    print(f"    Score máx (más normal):  {scores.max():.4f}")
    print(f"    % anomalías detectadas:  {pct_anomalas:.1f}%")

    # Metadatos para alarmas.py:
    # score_min/max permiten normalizar el score raw a escala 0-100
    # feature_means/stds permiten identificar qué variables están más desviadas
    meta = {
        "features":                   FEATURES_IF,
        "score_min":                  float(scores.min()),
        "score_max":                  float(scores.max()),
        "feature_means":              {f: float(df[f].mean()) for f in FEATURES_IF if f in df},
        "feature_stds":               {f: float(df[f].std())  for f in FEATURES_IF if f in df},
        "n_muestras_entrenamiento":   len(X),
        "fecha_entrenamiento":        pd.Timestamp.now().isoformat(),
        "contamination":              CONTAMINATION,
    }

    # Guardar modelo y metadatos como archivos pickle
    os.makedirs(DIR_SALIDA, exist_ok=True)
    ruta_modelo = os.path.join(DIR_SALIDA, "modelo_if.pkl")
    ruta_meta   = os.path.join(DIR_SALIDA, "meta_if.pkl")

    with open(ruta_modelo, "wb") as f:
        pickle.dump({"scaler": scaler, "modelo": modelo}, f)
    with open(ruta_meta, "wb") as f:
        pickle.dump(meta, f)

    print(f"\n  Modelo guardado:     {ruta_modelo}")
    print(f"  Metadatos guardados: {ruta_meta}")
    return ruta_modelo


def main():
    """
    Función principal: ejecuta el entrenamiento completo en 3 etapas.

    Etapa 1: Cargar el histórico desde las 4 tablas MySQL y unirlas por timestamp.
    Etapa 2: Limpiar los datos (imputar NaN, eliminar voltajes en 0, quitar outliers).
    Etapa 3: Entrenar el Isolation Forest y guardar el modelo en Model/.

    Verifica antes de comenzar que las tablas históricas existen en MySQL.
    Si no existen, indica al usuario que debe ejecutar etl_historico.py primero.
    """
    print("\n" + "="*60)
    print("  ENTRENAMIENTO ISOLATION FOREST — NODO IDEO")
    print("  (tablas: tr_historico, ml_historico, rect1/2_historico)")
    print("="*60)

    engine = get_engine()

    # Verificar que las 4 tablas históricas existen y tienen datos
    try:
        from sqlalchemy import inspect as sql_inspect
        tablas_existentes = sql_inspect(engine).get_table_names()
        tablas_requeridas = ["tr_historico", "ml_historico",
                             "rect1_historico", "rect2_historico"]
        faltantes = [t for t in tablas_requeridas if t not in tablas_existentes]
        if faltantes:
            print(f"\n  ❌ Tablas no encontradas: {faltantes}")
            print("  Ejecute primero: python src/etl_historico.py")
            return
    except Exception as e:
        print(f"  Error verificando tablas: {e}")
        return

    print("\n[1/3] Cargando histórico desde MySQL...")
    df_raw = cargar_historico(engine)

    if len(df_raw) < 100:
        print(f"\n  ❌ Solo {len(df_raw)} registros tras el JOIN.")
        print("  Verifique que etl_historico.py haya cargado los 4 dispositivos.")
        return

    print("\n[2/3] Limpiando datos...")
    df_clean = limpiar_datos(df_raw)

    if len(df_clean) < 100:
        print(f"\n  ❌ Solo {len(df_clean)} registros después de limpieza.")
        return

    print("\n[3/3] Entrenando y guardando...")
    entrenar_y_guardar(df_clean)

    print("\n" + "="*60)
    print("  ✅ ENTRENAMIENTO COMPLETADO")
    print("="*60)
    print("  El modelo está listo. Use el Monitor de Alarmas en Streamlit.\n")


if __name__ == "__main__":
    main()
