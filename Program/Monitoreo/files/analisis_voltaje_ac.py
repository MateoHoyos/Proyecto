"""
=============================================================================
ANÁLISIS HISTÓRICO DE VOLTAJE AC - TR IDEO CALI 2025
=============================================================================
Descripción : Análisis completo de 175,072 registros de voltaje AC (L1-L2)
              con estadísticas por hora, semana, mes y año, detección de
              anomalías y generación de reporte en texto.
Norma ref.  : CREG 024/2005 - Voltaje nominal 220V, tolerancia ±10%
              Rango aceptable: 198V – 242V
Autor       : Script generado con Claude (Anthropic)
Fecha       : 2026
=============================================================================
Dependencias:
    pip install pandas numpy matplotlib seaborn scipy scikit-learn openpyxl
=============================================================================
"""

import os
import sys
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # modo sin pantalla (headless)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
from scipy import stats
from sklearn.ensemble import IsolationForest
from datetime import datetime

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

CSV_PATH = "TR_-_IDEO_CALI__Wed_Feb_18_2026_13_36_36_GMT-0500__hora_estándar_de_Colombia_.csv"

# Voltaje nominal sistema L1-L2 (Colombia, red trifásica 220V L-L)
VOLTAJE_NOMINAL   = 220.0      # V
TOLERANCIA_PCT    = 10.0       # %
LIMITE_INFERIOR   = VOLTAJE_NOMINAL * (1 - TOLERANCIA_PCT / 100)   # 198 V
LIMITE_SUPERIOR   = VOLTAJE_NOMINAL * (1 + TOLERANCIA_PCT / 100)   # 242 V
UMBRAL_CRITICO_BAJO = 190.0    # V — subtensión crítica
UMBRAL_CRITICO_ALT  = 240.0   # V — sobrevoltaje de atención

OUTPUT_DIR = "reporte_voltaje_2025"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

DIAS_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. CARGA Y LIMPIEZA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────

def cargar_datos(path: str) -> tuple[pd.DataFrame, dict]:
    """Carga el CSV, limpia valores inválidos y retorna df + resumen de calidad."""
    print(f"\n{'='*60}")
    print("  CARGANDO Y LIMPIANDO DATOS")
    print(f"{'='*60}")

    df_raw = pd.read_csv(path)
    total_raw = len(df_raw)
    print(f"  Registros totales leídos : {total_raw:,}")

    # Conteo de valores problemáticos
    n_unplugged = (df_raw["Value"] == "Unplugged").sum()
    df_raw["Value_num"] = pd.to_numeric(df_raw["Value"], errors="coerce")
    n_cero = (df_raw["Value_num"] == 0).sum()
    n_nan  = df_raw["Value_num"].isna().sum() - n_unplugged  # NaN que no son Unplugged

    # Filtrar: quitar Unplugged, cero y NaN
    df = df_raw.copy()
    df = df[df["Value"] != "Unplugged"]
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df[df["Value"] > 0].copy()
    df = df.dropna(subset=["Value"])

    # Parseo de fechas con formato español (a. m. / p. m.) incluyendo espacio no-separable \xa0
    df["Time"] = (df["Time"]
                  .str.replace("\xa0", " ", regex=False)
                  .str.replace("a. m.", "AM", regex=False)
                  .str.replace("p. m.", "PM", regex=False))
    df["Time"] = pd.to_datetime(df["Time"], format="%d/%m/%Y, %I:%M:%S %p", errors="coerce")
    n_fecha_invalida = df["Time"].isna().sum()
    df = df.dropna(subset=["Time"])
    df = df.sort_values("Time").reset_index(drop=True)
    df = df.set_index("Time")

    # Columnas derivadas útiles
    df["hora"]    = df.index.hour
    df["dia"]     = df.index.day
    df["semana"]  = df.index.isocalendar().week.astype(int)
    df["mes"]     = df.index.month
    df["dia_sem"] = df.index.dayofweek   # 0=lunes
    df["anio"]    = df.index.year

    # Clasificación de calidad de voltaje
    df["estado"] = "Normal"
    df.loc[df["Value"] < LIMITE_INFERIOR,    "estado"] = "Subtensión"
    df.loc[df["Value"] > LIMITE_SUPERIOR,    "estado"] = "Sobretensión"
    df.loc[df["Value"] < UMBRAL_CRITICO_BAJO, "estado"] = "Subtensión Crítica"
    df.loc[df["Value"] > UMBRAL_CRITICO_ALT,  "estado"] = "Sobretensión Crítica"

    calidad = {
        "total_raw":       total_raw,
        "n_unplugged":     int(n_unplugged),
        "n_cero":          int(n_cero),
        "n_nan":           int(n_nan),
        "n_fecha_invalida":int(n_fecha_invalida),
        "n_validos":       len(df),
        "inicio":          df.index.min(),
        "fin":             df.index.max(),
    }

    print(f"  Valores 'Unplugged'      : {n_unplugged:,}")
    print(f"  Valores en cero (0.0)   : {n_cero:,}")
    print(f"  Valores NaN/inválidos   : {n_nan:,}")
    print(f"  Fechas inválidas        : {n_fecha_invalida:,}")
    print(f"  Registros válidos        : {len(df):,}")
    print(f"  Período                  : {df.index.min().date()} → {df.index.max().date()}")
    return df, calidad


# ─────────────────────────────────────────────────────────────────────────────
# 2. ESTADÍSTICAS AGREGADAS
# ─────────────────────────────────────────────────────────────────────────────

def calcular_estadisticas(df: pd.DataFrame) -> dict:
    """Calcula estadísticas a múltiples granularidades."""
    print(f"\n{'='*60}")
    print("  CALCULANDO ESTADÍSTICAS TEMPORALES")
    print(f"{'='*60}")

    agg_funcs = {
        "Value": ["mean", "median", "min", "max", "std",
                  lambda x: x.quantile(0.05),
                  lambda x: x.quantile(0.95)]
    }

    def resample_df(freq: str) -> pd.DataFrame:
        r = df["Value"].resample(freq).agg(
            media="mean", mediana="median",
            minimo="min", maximo="max",
            std="std", p5=lambda x: x.quantile(0.05),
            p95=lambda x: x.quantile(0.95),
            n="count"
        )
        return r.round(2)

    # Anual (estadística global)
    anual = {
        "media":   round(df["Value"].mean(), 2),
        "mediana": round(df["Value"].median(), 2),
        "minimo":  round(df["Value"].min(), 2),
        "maximo":  round(df["Value"].max(), 2),
        "std":     round(df["Value"].std(), 2),
        "p5":      round(df["Value"].quantile(0.05), 2),
        "p95":     round(df["Value"].quantile(0.95), 2),
        "n":       len(df),
    }

    horario  = resample_df("h")
    diario   = resample_df("D")
    semanal  = resample_df("W")
    mensual  = resample_df("ME")

    # Perfil por hora del día (promedio de todas las horas iguales)
    perfil_hora = df.groupby("hora")["Value"].agg(
        media="mean", std="std", p5=lambda x: x.quantile(0.05),
        p95=lambda x: x.quantile(0.95)
    ).round(2)

    # Perfil por día de la semana
    perfil_dia_sem = df.groupby("dia_sem")["Value"].agg(
        media="mean", std="std"
    ).round(2)
    perfil_dia_sem.index = [DIAS_ES[i] for i in perfil_dia_sem.index]

    # Perfil mensual
    perfil_mes = df.groupby("mes")["Value"].agg(
        media="mean", std="std", minimo="min", maximo="max", n="count"
    ).round(2)
    perfil_mes.index = [MESES_ES[i] for i in perfil_mes.index]

    print("  ✓ Estadísticas horarias, diarias, semanales y mensuales calculadas")
    print(f"  Voltaje promedio anual   : {anual['media']} V")
    print(f"  Voltaje mínimo registrado: {anual['minimo']} V")
    print(f"  Voltaje máximo registrado: {anual['maximo']} V")
    print(f"  Desviación estándar      : {anual['std']} V")

    return {
        "anual":         anual,
        "horario":       horario,
        "diario":        diario,
        "semanal":       semanal,
        "mensual":       mensual,
        "perfil_hora":   perfil_hora,
        "perfil_dia_sem":perfil_dia_sem,
        "perfil_mes":    perfil_mes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. ANÁLISIS DE CALIDAD Y ANOMALÍAS
# ─────────────────────────────────────────────────────────────────────────────

def analizar_anomalias(df: pd.DataFrame) -> dict:
    """Detecta anomalías con reglas CREG + Isolation Forest."""
    print(f"\n{'='*60}")
    print("  DETECCIÓN DE ANOMALÍAS")
    print(f"{'='*60}")

    # --- Reglas de negocio (CREG) ---
    fuera_rango = df[df["estado"] != "Normal"]
    n_subtension     = (df["estado"] == "Subtensión").sum()
    n_subtension_crit= (df["estado"] == "Subtensión Crítica").sum()
    n_sobretension   = (df["estado"] == "Sobretensión").sum()
    n_sobretension_cr= (df["estado"] == "Sobretensión Crítica").sum()
    n_normal         = (df["estado"] == "Normal").sum()
    total            = len(df)

    disponibilidad   = round(n_normal / total * 100, 2)

    print(f"  Normal                   : {n_normal:,} ({n_normal/total*100:.1f}%)")
    print(f"  Subtensión (<198V)       : {n_subtension:,} ({n_subtension/total*100:.2f}%)")
    print(f"  Subtensión Crítica(<190V): {n_subtension_crit:,} ({n_subtension_crit/total*100:.2f}%)")
    print(f"  Sobretensión (>242V)     : {n_sobretension:,} ({n_sobretension/total*100:.2f}%)")
    print(f"  Disponibilidad voltaje   : {disponibilidad}%")

    # --- Isolation Forest (detección estadística avanzada) ---
    # Usamos ventana deslizante de stats para enriquecer features
    serie = df["Value"].copy()
    X = pd.DataFrame({
        "valor":    serie.values,
        "rolling3": serie.rolling(3, min_periods=1).mean().values,
        "diff":     serie.diff().fillna(0).values,
    })

    iso = IsolationForest(contamination=0.005, random_state=42, n_estimators=100)
    df_copy = df.copy()
    df_copy["iso_score"] = iso.fit_predict(X)
    anomalias_iso = df_copy[df_copy["iso_score"] == -1]

    print(f"  Anomalías (Isolation Forest): {len(anomalias_iso):,}")

    # Eventos: rachas consecutivas fuera de rango
    df_copy["fuera_rango"] = (df_copy["estado"] != "Normal").astype(int)
    df_copy["grupo_evento"] = (df_copy["fuera_rango"] != df_copy["fuera_rango"].shift()).cumsum()
    eventos = df_copy[df_copy["fuera_rango"] == 1].groupby("grupo_evento").agg(
        inicio=("Value", lambda x: x.index[0]),
        fin=("Value", lambda x: x.index[-1]),
        duracion_min=("Value", "count"),
        voltaje_min=("Value", "min"),
        voltaje_max=("Value", "max"),
        estado=("estado", "first")
    ).reset_index(drop=True)
    eventos["duracion_min"] = eventos["duracion_min"] * 3  # ~3 min por lectura

    # Top 10 eventos más largos
    top_eventos = eventos.nlargest(10, "duracion_min")[
        ["inicio", "fin", "duracion_min", "voltaje_min", "voltaje_max", "estado"]
    ]

    return {
        "n_normal":           int(n_normal),
        "n_subtension":       int(n_subtension),
        "n_subtension_crit":  int(n_subtension_crit),
        "n_sobretension":     int(n_sobretension),
        "n_sobretension_cr":  int(n_sobretension_cr),
        "disponibilidad":     disponibilidad,
        "total":              total,
        "n_anomalias_iso":    len(anomalias_iso),
        "anomalias_iso":      anomalias_iso,
        "top_eventos":        top_eventos,
        "n_eventos":          len(eventos),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. VISUALIZACIONES
# ─────────────────────────────────────────────────────────────────────────────

COLORES = {
    "principal": "#2563EB",
    "normal":    "#16A34A",
    "warning":   "#F59E0B",
    "danger":    "#DC2626",
    "gris":      "#6B7280",
    "fondo":     "#F8FAFC",
}

def set_estilo():
    plt.rcParams.update({
        "figure.facecolor":  COLORES["fondo"],
        "axes.facecolor":    "#FFFFFF",
        "axes.grid":         True,
        "grid.alpha":        0.35,
        "grid.linestyle":    "--",
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "font.family":       "DejaVu Sans",
        "font.size":         10,
        "axes.titlesize":    12,
        "axes.titleweight":  "bold",
        "axes.labelsize":    10,
    })

def fig1_serie_mensual(stats: dict, output_dir: str):
    """Gráfica 1: Serie temporal mensual con banda de confianza."""
    set_estilo()
    mensual = stats["mensual"]
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.fill_between(mensual.index, mensual["p5"], mensual["p95"],
                    alpha=0.18, color=COLORES["principal"], label="P5–P95")
    ax.fill_between(mensual.index, mensual["minimo"], mensual["maximo"],
                    alpha=0.08, color=COLORES["gris"], label="Mín–Máx")
    ax.plot(mensual.index, mensual["media"], color=COLORES["principal"],
            lw=2.5, marker="o", markersize=6, label="Promedio mensual")
    ax.plot(mensual.index, mensual["mediana"], color=COLORES["gris"],
            lw=1.5, linestyle="--", label="Mediana mensual")

    ax.axhline(VOLTAJE_NOMINAL,   color=COLORES["normal"],  lw=1.5, ls="--", alpha=0.8, label=f"Nominal {VOLTAJE_NOMINAL}V")
    ax.axhline(LIMITE_INFERIOR,   color=COLORES["danger"],  lw=1.2, ls=":",  alpha=0.8, label=f"Límite inferior {LIMITE_INFERIOR:.0f}V")
    ax.axhline(LIMITE_SUPERIOR,   color=COLORES["danger"],  lw=1.2, ls=":",  alpha=0.8, label=f"Límite superior {LIMITE_SUPERIOR:.0f}V")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_title("Voltaje AC L1-L2 — Tendencia Mensual 2025")
    ax.set_ylabel("Voltaje (V)")
    ax.set_xlabel("Mes")
    ax.legend(fontsize=8, ncol=3)
    plt.tight_layout()
    path = os.path.join(output_dir, "fig1_serie_mensual.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")

def fig2_perfil_horario(stats: dict, output_dir: str):
    """Gráfica 2: Perfil promedio por hora del día."""
    set_estilo()
    ph = stats["perfil_hora"]
    fig, ax = plt.subplots(figsize=(12, 4))

    ax.fill_between(ph.index, ph["p5"], ph["p95"],
                    alpha=0.25, color=COLORES["principal"], label="P5–P95")
    ax.plot(ph.index, ph["media"], color=COLORES["principal"],
            lw=2.5, marker="o", markersize=5, label="Promedio")
    ax.fill_between(ph.index,
                    ph["media"] - ph["std"], ph["media"] + ph["std"],
                    alpha=0.15, color=COLORES["gris"], label="±1σ")

    ax.axhline(VOLTAJE_NOMINAL, color=COLORES["normal"], lw=1.5, ls="--", alpha=0.7)
    ax.axhline(LIMITE_INFERIOR, color=COLORES["danger"], lw=1, ls=":", alpha=0.7)

    ax.set_xticks(range(0, 24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, fontsize=8)
    ax.set_title("Perfil de Voltaje Promedio por Hora del Día — 2025")
    ax.set_ylabel("Voltaje (V)")
    ax.set_xlabel("Hora")
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(output_dir, "fig2_perfil_horario.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")

def fig3_distribucion(df: pd.DataFrame, output_dir: str):
    """Gráfica 3: Histograma + KDE de distribución de voltaje."""
    set_estilo()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))

    # Histograma
    ax = axes[0]
    ax.hist(df["Value"], bins=60, color=COLORES["principal"],
            alpha=0.75, edgecolor="white", linewidth=0.5)
    ax.axvline(VOLTAJE_NOMINAL,  color=COLORES["normal"], lw=2, ls="--", label=f"Nominal {VOLTAJE_NOMINAL}V")
    ax.axvline(LIMITE_INFERIOR,  color=COLORES["danger"], lw=1.5, ls=":", label=f"Límite inf. {LIMITE_INFERIOR:.0f}V")
    ax.axvline(LIMITE_SUPERIOR,  color=COLORES["danger"], lw=1.5, ls=":", label=f"Límite sup. {LIMITE_SUPERIOR:.0f}V")
    ax.axvline(df["Value"].mean(), color=COLORES["warning"], lw=1.5, ls="-", label=f"Media {df['Value'].mean():.1f}V")
    ax.set_title("Distribución de Voltaje AC 2025")
    ax.set_xlabel("Voltaje (V)")
    ax.set_ylabel("Frecuencia")
    ax.legend(fontsize=8)

    # Box plot mensual
    ax2 = axes[1]
    meses_data = [df[df["mes"] == m]["Value"].values for m in range(1, 13)]
    meses_labels = [MESES_ES[m][:3] for m in range(1, 13)]
    bp = ax2.boxplot(meses_data, labels=meses_labels, patch_artist=True,
                     medianprops=dict(color=COLORES["warning"], lw=2),
                     flierprops=dict(marker=".", markersize=2, alpha=0.3))
    for patch in bp["boxes"]:
        patch.set_facecolor(COLORES["principal"])
        patch.set_alpha(0.6)
    ax2.axhline(VOLTAJE_NOMINAL, color=COLORES["normal"], lw=1.5, ls="--", alpha=0.7)
    ax2.axhline(LIMITE_INFERIOR, color=COLORES["danger"], lw=1, ls=":", alpha=0.7)
    ax2.set_title("Box Plot Mensual de Voltaje")
    ax2.set_xlabel("Mes")
    ax2.set_ylabel("Voltaje (V)")
    ax2.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    path = os.path.join(output_dir, "fig3_distribucion.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")

def fig4_heatmap_hora_mes(df: pd.DataFrame, output_dir: str):
    """Gráfica 4: Heatmap de voltaje promedio por hora × mes."""
    set_estilo()
    pivot = df.groupby(["mes", "hora"])["Value"].mean().unstack(level="hora")
    pivot.index = [MESES_ES[m][:3] for m in pivot.index]

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(
        pivot, ax=ax,
        cmap="RdYlGn",
        vmin=196, vmax=222,
        linewidths=0.3,
        cbar_kws={"label": "Voltaje Promedio (V)"},
        annot=True, fmt=".1f", annot_kws={"size": 7}
    )
    ax.set_title("Heatmap: Voltaje Promedio por Hora × Mes — 2025")
    ax.set_xlabel("Hora del día")
    ax.set_ylabel("Mes")
    plt.tight_layout()
    path = os.path.join(output_dir, "fig4_heatmap_hora_mes.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")

def fig5_anomalias_mes(anomalias: dict, df: pd.DataFrame, output_dir: str):
    """Gráfica 5: Eventos de anomalía por mes."""
    set_estilo()
    df_a = df[df["estado"] != "Normal"].copy()

    conteo = df_a.groupby(["mes", "estado"]).size().unstack(fill_value=0)
    conteo.index = [MESES_ES[m][:3] for m in conteo.index]

    fig, ax = plt.subplots(figsize=(12, 4))
    palette = {
        "Subtensión": COLORES["warning"],
        "Subtensión Crítica": COLORES["danger"],
        "Sobretensión": "#7C3AED",
        "Sobretensión Crítica": "#1E1B4B",
    }
    conteo.plot(kind="bar", ax=ax, stacked=True,
                color=[palette.get(c, COLORES["gris"]) for c in conteo.columns],
                edgecolor="white", linewidth=0.5, width=0.75)
    ax.set_title("Lecturas Fuera de Rango CREG por Mes — 2025")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Número de lecturas")
    ax.legend(title="Estado", fontsize=8)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    path = os.path.join(output_dir, "fig5_anomalias_mes.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")

def fig6_serie_semanal(stats: dict, output_dir: str):
    """Gráfica 6: Serie temporal semanal con promedio móvil."""
    set_estilo()
    semanal = stats["semanal"]
    fig, ax = plt.subplots(figsize=(14, 4))

    ax.plot(semanal.index, semanal["media"], color=COLORES["gris"],
            lw=1, alpha=0.6, label="Promedio semanal")
    ma4 = semanal["media"].rolling(4).mean()
    ax.plot(semanal.index, ma4, color=COLORES["principal"],
            lw=2, label="Media móvil 4 semanas")
    ax.fill_between(semanal.index, semanal["p5"], semanal["p95"],
                    alpha=0.1, color=COLORES["principal"])

    ax.axhline(VOLTAJE_NOMINAL, color=COLORES["normal"], lw=1.5, ls="--", alpha=0.7, label=f"Nominal {VOLTAJE_NOMINAL}V")
    ax.axhline(LIMITE_INFERIOR, color=COLORES["danger"], lw=1, ls=":", alpha=0.7)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title("Voltaje AC — Tendencia Semanal 2025 (con media móvil 4 semanas)")
    ax.set_ylabel("Voltaje (V)")
    ax.set_xlabel("Semana")
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = os.path.join(output_dir, "fig6_serie_semanal.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")

def generar_graficas(df: pd.DataFrame, stats: dict, anomalias: dict, output_dir: str):
    print(f"\n{'='*60}")
    print("  GENERANDO GRÁFICAS")
    print(f"{'='*60}")
    fig1_serie_mensual(stats, output_dir)
    fig2_perfil_horario(stats, output_dir)
    fig3_distribucion(df, output_dir)
    fig4_heatmap_hora_mes(df, output_dir)
    fig5_anomalias_mes(anomalias, df, output_dir)
    fig6_serie_semanal(stats, output_dir)


# ─────────────────────────────────────────────────────────────────────────────
# 5. REPORTE EN TEXTO
# ─────────────────────────────────────────────────────────────────────────────

def generar_reporte_texto(calidad: dict, stats: dict, anomalias: dict, output_dir: str):
    """Genera un reporte ejecutivo en texto plano (.txt)."""
    print(f"\n{'='*60}")
    print("  GENERANDO REPORTE EJECUTIVO")
    print(f"{'='*60}")

    anual = stats["anual"]
    pct_normal = round(anomalias["n_normal"] / anomalias["total"] * 100, 2)
    pct_sub    = round((anomalias["n_subtension"] + anomalias["n_subtension_crit"]) / anomalias["total"] * 100, 2)
    pct_sobre  = round((anomalias["n_sobretension"] + anomalias["n_sobretension_cr"]) / anomalias["total"] * 100, 2)

    perfil_mes = stats["perfil_mes"]
    mes_max = perfil_mes["media"].idxmax()
    mes_min = perfil_mes["media"].idxmin()
    hora_min_v = stats["perfil_hora"]["media"].idxmin()
    hora_max_v = stats["perfil_hora"]["media"].idxmax()

    # Clasificación general
    if pct_normal >= 98:
        clasificacion = "EXCELENTE ✓"
        diagnostico = "El voltaje se mantuvo dentro del rango regulatorio CREG casi todo el año."
    elif pct_normal >= 95:
        clasificacion = "BUENO"
        diagnostico = "El voltaje presentó desviaciones menores, con algunos eventos de subtensión puntual."
    elif pct_normal >= 90:
        clasificacion = "ACEPTABLE — REQUIERE ATENCIÓN"
        diagnostico = "Se registraron eventos recurrentes fuera de rango que pueden afectar equipos sensibles."
    else:
        clasificacion = "CRÍTICO — ACCIÓN REQUERIDA"
        diagnostico = "El voltaje presentó desviaciones frecuentes que implican riesgo para equipos y operaciones."

    linea = "=" * 70

    reporte = f"""
{linea}
  REPORTE HISTÓRICO DE VOLTAJE AC — TR IDEO CALI — AÑO 2025
  Sistema: 01 - VOLTAJE AC DEL SISTEMA L1-L2
  Generado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{linea}

1. CALIDAD DE DATOS
{'-'*50}
  Registros totales en CSV    : {calidad['total_raw']:,}
  Valores 'Unplugged'         : {calidad['n_unplugged']:,}
  Valores en cero             : {calidad['n_cero']:,}
  Registros válidos analizados: {calidad['n_validos']:,}
  Período cubierto            : {calidad['inicio'].strftime('%Y-%m-%d')} → {calidad['fin'].strftime('%Y-%m-%d')}

2. ESTADÍSTICAS ANUALES
{'-'*50}
  Voltaje promedio anual  : {anual['media']:.2f} V
  Voltaje mediana anual   : {anual['mediana']:.2f} V
  Voltaje mínimo          : {anual['minimo']:.1f} V
  Voltaje máximo          : {anual['maximo']:.1f} V
  Desviación estándar     : {anual['std']:.2f} V
  Percentil 5%            : {anual['p5']:.2f} V
  Percentil 95%           : {anual['p95']:.2f} V
  Total lecturas válidas  : {anual['n']:,}

  Voltaje Nominal (referencia): {VOLTAJE_NOMINAL} V
  Rango regulatorio CREG      : {LIMITE_INFERIOR:.0f} V — {LIMITE_SUPERIOR:.0f} V

3. ESTADÍSTICAS MENSUALES
{'-'*50}
  Mes con mayor voltaje promedio : {mes_max} ({perfil_mes.loc[mes_max, 'media']:.2f} V)
  Mes con menor voltaje promedio : {mes_min} ({perfil_mes.loc[mes_min, 'media']:.2f} V)

  Resumen mensual:
  {'Mes':<15} {'Promedio':>9} {'Mín':>7} {'Máx':>7} {'Desv.Std':>9} {'Lecturas':>9}
  {'-'*62}"""

    for mes_name, row in perfil_mes.iterrows():
        reporte += f"\n  {mes_name:<15} {row['media']:>9.2f} {row['minimo']:>7.1f} {row['maximo']:>7.1f} {row['std']:>9.2f} {int(row['n']):>9,}"

    reporte += f"""

4. PERFIL POR HORA DEL DÍA
{'-'*50}
  Hora de menor voltaje promedio: {hora_min_v:02d}:00 h ({stats['perfil_hora'].loc[hora_min_v,'media']:.2f} V)
  Hora de mayor voltaje promedio: {hora_max_v:02d}:00 h ({stats['perfil_hora'].loc[hora_max_v,'media']:.2f} V)

  {'Hora':<8} {'Promedio':>9} {'P5':>7} {'P95':>7}
  {'-'*36}"""

    for hora, row in stats["perfil_hora"].iterrows():
        marker = " ← mín" if hora == hora_min_v else (" ← máx" if hora == hora_max_v else "")
        reporte += f"\n  {hora:02d}:00   {row['media']:>9.2f} {row['p5']:>7.2f} {row['p95']:>7.2f}{marker}"

    reporte += f"""

5. ANÁLISIS DE CALIDAD DE VOLTAJE (CREG 024/2005)
{'-'*50}
  Estado        Lecturas     Porcentaje
  {'-'*44}
  Normal        {anomalias['n_normal']:>10,}     {pct_normal:>6.2f}%
  Subtensión    {anomalias['n_subtension']:>10,}     {anomalias['n_subtension']/anomalias['total']*100:>6.2f}%
  Sub. Crítica  {anomalias['n_subtension_crit']:>10,}     {anomalias['n_subtension_crit']/anomalias['total']*100:>6.2f}%
  Sobretensión  {anomalias['n_sobretension']:>10,}     {anomalias['n_sobretension']/anomalias['total']*100:>6.2f}%
  {'-'*44}
  TOTAL VÁLIDO  {anomalias['total']:>10,}     100.00%

  Disponibilidad en rango regulatorio: {anomalias['disponibilidad']}%
  Anomalías detectadas (Isolation Forest): {anomalias['n_anomalias_iso']:,}
  Total de eventos fuera de rango: {anomalias['n_eventos']:,}

6. TOP 10 EVENTOS MÁS PROLONGADOS FUERA DE RANGO
{'-'*50}"""

    top = anomalias["top_eventos"]
    if len(top) > 0:
        reporte += f"\n  {'#':<4} {'Inicio':<22} {'Fin':<22} {'Duración':>10} {'V.Mín':>7} {'V.Máx':>7} {'Estado'}"
        reporte += f"\n  {'-'*88}"
        for i, (_, row) in enumerate(top.iterrows(), 1):
            inicio = row["inicio"].strftime("%Y-%m-%d %H:%M") if hasattr(row["inicio"], "strftime") else str(row["inicio"])
            fin    = row["fin"].strftime("%Y-%m-%d %H:%M")    if hasattr(row["fin"],    "strftime") else str(row["fin"])
            reporte += f"\n  {i:<4} {inicio:<22} {fin:<22} {row['duracion_min']:>8.0f} min {row['voltaje_min']:>7.1f} {row['voltaje_max']:>7.1f} {row['estado']}"
    else:
        reporte += "\n  No se registraron eventos fuera de rango."

    reporte += f"""

7. DIAGNÓSTICO Y CLASIFICACIÓN GENERAL
{'-'*50}
  Clasificación del sistema : {clasificacion}
  {diagnostico}

  Observaciones adicionales:
  - El voltaje promedio anual ({anual['media']:.2f} V) está {'POR DEBAJO' if anual['media'] < VOLTAJE_NOMINAL else 'DENTRO O SOBRE'} del nominal ({VOLTAJE_NOMINAL} V).
  - La desviación estándar de {anual['std']:.2f} V indica una {'alta' if anual['std'] > 5 else 'moderada' if anual['std'] > 2 else 'baja'} variabilidad en el suministro.
  - Se registraron {calidad['n_unplugged']:,} desconexiones del sensor durante el año.

8. RECOMENDACIONES
{'-'*50}"""

    recs = []
    if pct_sub > 2:
        recs.append("  ➤ REVISAR regulación del transformador o acometida en momentos de subtensión.")
    if pct_sub > 5:
        recs.append("  ➤ INSTALAR regulador automático de voltaje (AVR) o UPS con regulación activa.")
    if anomalias["n_subtension_crit"] > 100:
        recs.append("  ➤ ANALIZAR los eventos de subtensión crítica (<190V) con el operador de red (ESSA/EPSA).")
    if anual["std"] > 5:
        recs.append("  ➤ Considerar filtrado o acondicionamiento de red por alta variabilidad detectada.")
    if calidad["n_unplugged"] > 500:
        recs.append("  ➤ Revisar la estabilidad del sensor de medición (muchas desconexiones registradas).")
    if not recs:
        recs.append("  ✓ El sistema opera dentro de parámetros aceptables. Continuar monitoreo periódico.")
    reporte += "\n" + "\n".join(recs)

    reporte += f"""

{linea}
  Archivo de datos fuente: {os.path.basename(CSV_PATH)}
  Norma de referencia    : CREG 024/2005 — Calidad de voltaje Colombia
  Voltaje nominal L1-L2  : {VOLTAJE_NOMINAL} V | Rango: ±{TOLERANCIA_PCT}% ({LIMITE_INFERIOR:.0f}–{LIMITE_SUPERIOR:.0f} V)
{linea}
"""

    path = os.path.join(output_dir, "reporte_voltaje_2025.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(reporte)
    print(reporte)
    print(f"  ✓ Reporte guardado: {path}")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 6. EXPORTAR ESTADÍSTICAS A EXCEL
# ─────────────────────────────────────────────────────────────────────────────

def exportar_excel(stats: dict, anomalias: dict, output_dir: str):
    """Exporta todas las tablas estadísticas a un Excel multi-hoja."""
    path = os.path.join(output_dir, "estadisticas_voltaje_2025.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Mensual
        stats["mensual"].to_excel(writer, sheet_name="Mensual")
        # Semanal
        stats["semanal"].to_excel(writer, sheet_name="Semanal")
        # Horario (primeras 168 filas = 1 semana)
        stats["horario"].head(168).to_excel(writer, sheet_name="Horario_Muestra")
        # Perfil por hora
        stats["perfil_hora"].to_excel(writer, sheet_name="Perfil_Hora")
        # Perfil por mes
        stats["perfil_mes"].to_excel(writer, sheet_name="Perfil_Mes")
        # Top eventos
        anomalias["top_eventos"].to_excel(writer, sheet_name="Top_Eventos", index=False)
        # Resumen anomalías
        resumen_an = pd.DataFrame({
            "Estado": ["Normal", "Subtensión", "Subtensión Crítica", "Sobretensión", "Sobretensión Crítica"],
            "Lecturas": [anomalias["n_normal"], anomalias["n_subtension"],
                         anomalias["n_subtension_crit"], anomalias["n_sobretension"],
                         anomalias["n_sobretension_cr"]],
        })
        resumen_an["Porcentaje (%)"] = (resumen_an["Lecturas"] / anomalias["total"] * 100).round(2)
        resumen_an.to_excel(writer, sheet_name="Calidad_Voltaje", index=False)
    print(f"  ✓ Excel exportado: {path}")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "🔌 " * 20)
    print("  ANÁLISIS HISTÓRICO DE VOLTAJE AC — TR IDEO CALI 2025")
    print("🔌 " * 20)

    if not os.path.exists(CSV_PATH):
        print(f"\n  ERROR: No se encontró el archivo: {CSV_PATH}")
        print("  Asegúrate de que el CSV esté en el mismo directorio que este script.")
        sys.exit(1)

    # Pipeline completo
    df, calidad   = cargar_datos(CSV_PATH)
    stats         = calcular_estadisticas(df)
    anomalias     = analizar_anomalias(df)
    generar_graficas(df, stats, anomalias, OUTPUT_DIR)
    generar_reporte_texto(calidad, stats, anomalias, OUTPUT_DIR)
    exportar_excel(stats, anomalias, OUTPUT_DIR)

    print(f"\n{'='*60}")
    print(f"  ✅ ANÁLISIS COMPLETO")
    print(f"  Todos los archivos están en: ./{OUTPUT_DIR}/")
    print(f"  - reporte_voltaje_2025.txt")
    print(f"  - estadisticas_voltaje_2025.xlsx")
    print(f"  - fig1_serie_mensual.png")
    print(f"  - fig2_perfil_horario.png")
    print(f"  - fig3_distribucion.png")
    print(f"  - fig4_heatmap_hora_mes.png")
    print(f"  - fig5_anomalias_mes.png")
    print(f"  - fig6_serie_semanal.png")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
