"""
entrenar_if.py
──────────────────────────────────────────────────────────────────────────────
Entrena el Isolation Forest con el histórico consolidado (10 min) desde MySQL.

PRE-REQUISITO: Haber cargado el histórico primero:
    python src/etl_historico.py
    (o desde Streamlit: Gestión de Datos → ETL Histórico)

Luego ejecutar:
    python src/modelo_if/entrenar_if.py
    (o desde Streamlit: Monitor de Alarmas → Entrenar Modelo)

Genera en src/modelo_if/:
    modelo_if.pkl  → pipeline (scaler + modelo) listo para inferencia
    meta_if.pkl    → estadísticas para normalizar scores y detectar features
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
# ─────────────────────────────────────────────────────────────
CONTAMINATION = 0.05   # ~5% de lecturas anómalas esperadas en el histórico
N_ESTIMATORS  = 200
RANDOM_STATE  = 42

# Features del modelo — deben coincidir con alarmas.py → FEATURES_IF
FEATURES_IF = [
    # TR
    "tr_corriente_ac_l1", "tr_corriente_ac_l2", "tr_corriente_ac_l3",
    "tr_potencia_activa_kw", "tr_potencia_reactiva_kvar", "tr_potencia_aparente_kva",
    "tr_factor_potencia",
    "tr_voltaje_ac_l1_l2", "tr_voltaje_ac_l2_l3", "tr_voltaje_ac_l3_l1",
    # ML
    "ml_corriente_ac_r", "ml_corriente_ac_s", "ml_corriente_ac_t",
    "ml_voltaje_ac_rs", "ml_voltaje_ac_st", "ml_voltaje_ac_tr",
    "ml_temp_sala_s01", "ml_temp_sala_s02",
    # Rectificadores — solo columnas disponibles en rect1/2_historico
    "rect_avg_corriente_dc", "rect_avg_voltaje_dc", "rect_avg_corriente_carga",
]

DIR_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_SALIDA = os.path.join(DIR_BASE, "Model")


# ─────────────────────────────────────────────────────────────
#  CARGA DESDE TABLAS HISTÓRICAS
#  Nombres de columna según DDL real en etl_historico.py:
#
#  tr_historico    → corriente_ac_l1/l2/l3, potencia_activa_kw,
#                    potencia_reactiva_kvar, potencia_aparente_kva,
#                    factor_potencia, voltaje_ac_l1_l2/l2_l3/l3_l1
#
#  ml_historico    → corriente_ac_r/s/t, voltaje_ac_rs/st/tr,
#                    temp_sala_s01/s02
#
#  rect1_historico → voltaje_ac_vs, voltaje_dc_vs,
#                    corriente_dc_cs, corriente_dc_carga
#
#  rect2_historico → (mismas columnas que rect1)
# ─────────────────────────────────────────────────────────────

def cargar_historico(engine) -> pd.DataFrame:

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
        FROM tr_historico
        ORDER BY timestamp
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
        FROM ml_historico
        ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    print("  Cargando rect1_historico...")
    df_r1 = pd.read_sql("""
        SELECT
            timestamp,
            corriente_dc_cs    AS r1_corriente_dc,
            voltaje_dc_vs      AS r1_voltaje_dc,
            corriente_dc_carga AS r1_corriente_carga
        FROM rect1_historico
        ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    print("  Cargando rect2_historico...")
    df_r2 = pd.read_sql("""
        SELECT
            timestamp,
            corriente_dc_cs    AS r2_corriente_dc,
            voltaje_dc_vs      AS r2_voltaje_dc,
            corriente_dc_carga AS r2_corriente_carga
        FROM rect2_historico
        ORDER BY timestamp
    """, engine, parse_dates=["timestamp"])

    # ── JOIN por timestamp exacto ─────────────────────────────
    # Los 4 históricos ya están alineados a los mismos intervalos
    # de 10 min gracias al resample en etl_historico.py
    print("  Uniendo tablas por timestamp...")
    df = df_tr.merge(df_ml, on="timestamp", how="inner")
    df = df.merge(df_r1,   on="timestamp", how="inner")
    df = df.merge(df_r2,   on="timestamp", how="inner")

    # ── Promedios R1 + R2 ────────────────────────────────────
    df["rect_avg_corriente_dc"]   = (df["r1_corriente_dc"]   + df["r2_corriente_dc"])   / 2
    df["rect_avg_voltaje_dc"]     = (df["r1_voltaje_dc"]     + df["r2_voltaje_dc"])     / 2
    df["rect_avg_corriente_carga"]= (df["r1_corriente_carga"]+ df["r2_corriente_carga"])/ 2

    # Eliminar columnas intermedias
    df = df.drop(columns=[
        "r1_corriente_dc", "r1_voltaje_dc", "r1_corriente_carga",
        "r2_corriente_dc", "r2_voltaje_dc", "r2_corriente_carga",
        "timestamp"
    ])

    print(f"  Registros tras JOIN: {len(df):,}")

    # Advertir si el JOIN redujo mucho los datos
    min_tabla  = min(len(df_tr), len(df_ml), len(df_r1), len(df_r2))
    retencion  = len(df) / min_tabla * 100 if min_tabla > 0 else 0
    if retencion < 70:
        print(f"  ⚠️  Retención del JOIN: {retencion:.0f}% — revise alineación de timestamps.")
    else:
        print(f"  ✅ Retención del JOIN: {retencion:.0f}%")

    return df


# ─────────────────────────────────────────────────────────────
#  LIMPIEZA
# ─────────────────────────────────────────────────────────────

def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:

    cols_validas   = [c for c in FEATURES_IF if c in df.columns]
    cols_faltantes = [c for c in FEATURES_IF if c not in df.columns]
    if cols_faltantes:
        print(f"  ⚠️  Features no encontradas: {cols_faltantes}")

    df = df[cols_validas].copy()

    # Imputar NaN con mediana
    for col in df.columns:
        if df[col].isna().any():
            mediana = df[col].median()
            df[col] = df[col].fillna(mediana)

    # Eliminar filas con voltajes en 0 (sensor offline)
    for col in [c for c in cols_validas if "voltaje" in c]:
        antes = len(df)
        df = df[df[col] > 0]
        if len(df) < antes:
            print(f"      Eliminadas {antes - len(df)} filas con {col}=0")

    # Eliminar outliers extremos >5 sigma
    for col in df.columns:
        mu, sig = df[col].mean(), df[col].std()
        if sig > 0:
            antes = len(df)
            df = df[(df[col] >= mu - 5*sig) & (df[col] <= mu + 5*sig)]
            if len(df) < antes:
                print(f"      Eliminados {antes - len(df)} outliers en '{col}'")

    print(f"  Registros limpios: {len(df):,}")
    return df


# ─────────────────────────────────────────────────────────────
#  ENTRENAMIENTO Y GUARDADO
# ─────────────────────────────────────────────────────────────

def entrenar_y_guardar(df: pd.DataFrame):

    X        = df[FEATURES_IF].values
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"\n  Entrenando Isolation Forest...")
    print(f"    contamination = {CONTAMINATION}")
    print(f"    n_estimators  = {N_ESTIMATORS}")
    print(f"    n_features    = {len(FEATURES_IF)}")
    print(f"    n_samples     = {len(X):,}")

    modelo = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    modelo.fit(X_scaled)

    scores       = modelo.score_samples(X_scaled)
    pct_anomalas = (modelo.predict(X_scaled) == -1).mean() * 100

    print(f"\n  Resultados:")
    print(f"    Score mín (más anómalo): {scores.min():.4f}")
    print(f"    Score máx (más normal):  {scores.max():.4f}")
    print(f"    % anomalías detectadas:  {pct_anomalas:.1f}%")

    meta = {
        "features":      FEATURES_IF,
        "score_min":     float(scores.min()),
        "score_max":     float(scores.max()),
        "feature_means": {f: float(df[f].mean()) for f in FEATURES_IF if f in df},
        "feature_stds":  {f: float(df[f].std())  for f in FEATURES_IF if f in df},
        "n_muestras_entrenamiento": len(X),
        "fecha_entrenamiento":      pd.Timestamp.now().isoformat(),
        "contamination":            CONTAMINATION,
    }

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


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  ENTRENAMIENTO ISOLATION FOREST — NODO IDEO")
    print("  (tablas: tr_historico, ml_historico, rect1/2_historico)")
    print("="*60)

    engine = get_engine()

    # Verificar que las tablas históricas existan y tengan datos
    try:
        from sqlalchemy import inspect as sql_inspect
        tablas_existentes = sql_inspect(engine).get_table_names()
        tablas_requeridas = ["tr_historico", "ml_historico", "rect1_historico", "rect2_historico"]
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