"""
config_dce.py — IDs y Mapas de Sensores de Data Center Expert
──────────────────────────────────────────────────────────────────────────────
Archivo de configuración específico para la integración con la plataforma
EcoStruxure IT Data Center Expert del nodo IDEO Cali.

Contiene dos tipos de información:

    1. DCE_IDS: Identificadores únicos (GUID) de cada equipo registrado
       en la plataforma DCE. Estos IDs se obtienen una sola vez consultando
       el endpoint GET /v1/devices de la API y no cambian a menos que
       el equipo sea dado de baja y reregistrado en la plataforma.

    2. MAPAS DE SENSORES (MAPA_TR, MAPA_ML, MAPA_RECT):
       Diccionarios que relacionan el label de cada sensor en la API del DCE
       con el nombre de columna que tendrá en la base de datos MySQL.
       Permiten que etl_dce.py construya las filas de datos sin necesidad
       de conocer los nombres internos de la plataforma.

Este archivo es importado únicamente por etl_dce.py.
──────────────────────────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────────────────────
#  IDs DE EQUIPOS EN DATA CENTER EXPERT
#  Cada equipo registrado en la plataforma DCE tiene un GUID único.
#  Estos valores se obtienen del endpoint GET /v1/devices y se registran
#  aquí una sola vez para no tener que consultarlos en cada ejecución.
#
#  TR    : Transferencia automática (COMAP IL-NT-AMF25) — protocolo Modbus
#  ML    : Tablero principal (EATON SC200) — protocolo SNMP
#  RECT1 : Rectificador 1 (ELTEK SmartPack 2) — protocolo SNMP
#  RECT2 : Rectificador 2 (ELTEK SmartPack 2) — protocolo SNMP
# ─────────────────────────────────────────────────────────────
DCE_IDS = {
    "TR":    "B7e755e_nbModbusEnc4B4D008D",
    "ML":    "B7e755e_nbSNMPEnc60BA612C",
    "RECT1": "B7e755e_nbSNMPEncD1F128BD",
    "RECT2": "B7e755e_nbSNMPEnc7D425FC9"
}

# ─────────────────────────────────────────────────────────────
#  MAPA DE SENSORES — TRANSFERENCIA AUTOMÁTICA (TR)
#  El TR tiene 24 sensores registrados en el DCE.
#  Este mapa incluye los 17 sensores eléctricos relevantes:
#  voltajes y corrientes AC de la red y del generador,
#  potencias y factor de potencia de la carga total del nodo.
#
#  Clave : label del sensor tal como aparece en la API del DCE
#  Valor : nombre de columna en la tabla tr_dce de MySQL
# ─────────────────────────────────────────────────────────────
MAPA_TR = {
    "01 - VOLTAJE AC DEL SISTEMA L1-L2":   "voltaje_ac_l1_l2",
    "02 - VOLTAJE AC DEL SISTEMA L2-L3":   "voltaje_ac_l2_l3",
    "03 - VOLTAJE AC DEL SISTEMA L3-L1":   "voltaje_ac_l3_l1",
    "04 - FRECUENCIA DEL SISTEMA":         "frecuencia_sistema",
    "05 - VOLTAJE DE LA BATERIA":          "voltaje_bateria",
    "06 - VOLTAJE AC DEL GENERADOR L1-L2": "voltaje_gen_l1_l2",
    "07 - VOLTAJE AC DEL GENERADOR L2-L3": "voltaje_gen_l2_l3",
    "08 - VOLTAJE AC DEL GENERADOR L3-L1": "voltaje_gen_l3_l1",
    "09 - FRENCUENCIA DEL GENERADOR":      "frecuencia_gen",
    "10 - RPM DEL GENERADOR":              "rpm_gen",
    "11 - CORRIENTE AC DE LA CARGA L1":    "corriente_ac_l1",
    "12 - CORRIENTE AC DE LA CARGA L2":    "corriente_ac_l2",
    "13 - CORRIENTE AC DE LA CARGA L3":    "corriente_ac_l3",
    "14 - POTENCIA ACTIVA DE LA CARGA":    "potencia_activa_kw",
    "15 - POTENCIA REACTIVA DE LA CARGA":  "potencia_reactiva_kvar",
    "16 - POTENCIA APARENTE DE LA CARGA":  "potencia_aparente_kva",
    "17 - FACTOR DE POTENCIA DE LA CARGA": "factor_potencia",
}

# ─────────────────────────────────────────────────────────────
#  MAPA DE SENSORES — TABLERO PRINCIPAL (ML)
#  El ML tiene 12 sensores registrados en el DCE.
#  Este mapa incluye las corrientes y voltajes AC de las 3 fases
#  y los dos sensores de temperatura de la sala (S01 y S02).
#
#  Clave : label del sensor tal como aparece en la API del DCE
#  Valor : nombre de columna en la tabla ml_dce de MySQL
# ─────────────────────────────────────────────────────────────
MAPA_ML = {
    "ANALOG INPUT - ML CURRENT AC R":   "corriente_ac_r",
    "ANALOG INPUT - ML CURRENT AC S":   "corriente_ac_s",
    "ANALOG INPUT - ML CURRENT AC T":   "corriente_ac_t",
    "ANALOG INPUT - ML VOLTAGE AC R-S": "voltaje_ac_rs",
    "ANALOG INPUT - ML VOLTAGE AC S-T": "voltaje_ac_st",
    "ANALOG INPUT - ML VOLTAGE AC T-R": "voltaje_ac_tr",
    "ANALOG INPUT - °C SALA S01":       "temp_sala_s01",
    "ANALOG INPUT - °C SALA S02":       "temp_sala_s02",
}

# ─────────────────────────────────────────────────────────────
#  MAPA DE SENSORES — RECTIFICADORES (RECT1 y RECT2)
#  Ambos rectificadores tienen los mismos 21 sensores en el DCE.
#  Este mapa incluye los sensores eléctricos más relevantes:
#  voltaje AC de entrada, voltaje DC de salida, corrientes DC
#  del sistema y de la carga, porcentaje de carga y estados.
#
#  Se usa el mismo mapa para ambos rectificadores. Se diferencian
#  en la base de datos por la columna rectificador_id (1 o 2),
#  que se agrega como extra_data en etl_dce.py.
#
#  Clave : label del sensor tal como aparece en la API del DCE
#  Valor : nombre de columna en la tabla rect_dce de MySQL
# ─────────────────────────────────────────────────────────────
MAPA_RECT = {
    "01 - VOLTAJE AC DEL SISTEMA":          "voltaje_ac_entrada",
    "02 - VOLTAJE DC DEL SISTEMA":          "voltaje_dc_salida",
    "03 - CORRIENTE DC DEL SISTEMA":        "corriente_dc_total",
    "04 - PORCENTAJE DE CARGA DEL SISTEMA": "porcentaje_carga",
    "05 - MODO DEL SISTEMA":                "modo_sistema",
    "06 - NUMERO DE FASES":                 "num_fases",
    "07 - RECTIFICADORES INSTALADOS":       "modulos_instalados",
    "08 - RECTIFICADORES FALLADOS":         "modulos_fallados",
    "09 - CORRIENTE DC DE LAS BATERIAS":    "corriente_baterias",
    "10 - TEMPERATURA DE LAS BATERIAS":     "temp_baterias",
    "11 - CORRIENTE DC DE LA CARGA":        "corriente_carga",
}
