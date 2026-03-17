# IDs de los equipos
DCE_IDS = {
    "TR": "B7e755e_nbModbusEnc4B4D008D",
    "ML": "B7e755e_nbSNMPEnc60BA612C",
    "RECT1": "B7e755e_nbSNMPEncD1F128BD",
    "RECT2": "B7e755e_nbSNMPEnc7D425FC9"
}

MAPA_TR = {
    "01 - VOLTAJE AC DEL SISTEMA L1-L2": "voltaje_ac_l1_l2",
    "02 - VOLTAJE AC DEL SISTEMA L2-L3": "voltaje_ac_l2_l3",
    "03 - VOLTAJE AC DEL SISTEMA L3-L1": "voltaje_ac_l3_l1",
    "04 - FRECUENCIA DEL SISTEMA": "frecuencia_sistema",
    "05 - VOLTAJE DE LA BATERIA": "voltaje_bateria",
    "06 - VOLTAJE AC DEL GENERADOR L1-L2": "voltaje_gen_l1_l2",
    "07 - VOLTAJE AC DEL GENERADOR L2-L3": "voltaje_gen_l2_l3",
    "08 - VOLTAJE AC DEL GENERADOR L3-L1": "voltaje_gen_l3_l1",
    "09 - FRENCUENCIA DEL GENERADOR": "frecuencia_gen",
    "10 - RPM DEL GENERADOR": "rpm_gen",
    "11 - CORRIENTE AC DE LA CARGA L1": "corriente_ac_l1",
    "12 - CORRIENTE AC DE LA CARGA L2": "corriente_ac_l2",
    "13 - CORRIENTE AC DE LA CARGA L3": "corriente_ac_l3",
    "14 - POTENCIA ACTIVA DE LA CARGA": "potencia_activa_kw",
    "15 - POTENCIA REACTIVA DE LA CARGA": "potencia_reactiva_kvar",
    "16 - POTENCIA APARENTE DE LA CARGA": "potencia_aparente_kva",
    "17 - FACTOR DE POTENCIA DE LA CARGA": "factor_potencia",
}

MAPA_ML = {
    "ANALOG INPUT - ML CURRENT AC R": "corriente_ac_r",
    "ANALOG INPUT - ML CURRENT AC S": "corriente_ac_s",
    "ANALOG INPUT - ML CURRENT AC T": "corriente_ac_t",
    "ANALOG INPUT - ML VOLTAGE AC R-S": "voltaje_ac_rs",
    "ANALOG INPUT - ML VOLTAGE AC S-T": "voltaje_ac_st",
    "ANALOG INPUT - ML VOLTAGE AC T-R": "voltaje_ac_tr",
    "ANALOG INPUT - °C SALA S01": "temp_sala_s01",
    "ANALOG INPUT - °C SALA S02": "temp_sala_s02",
}

MAPA_RECT = {
    "01 - VOLTAJE AC DEL SISTEMA": "voltaje_ac_entrada",
    "02 - VOLTAJE DC DEL SISTEMA": "voltaje_dc_salida",
    "03 - CORRIENTE DC DEL SISTEMA": "corriente_dc_total",
    "04 - PORCENTAJE DE CARGA DEL SISTEMA": "porcentaje_carga",
    "05 - MODO DEL SISTEMA": "modo_sistema",
    "06 - NUMERO DE FASES": "num_fases",
    "07 - RECTIFICADORES INSTALADOS": "modulos_instalados",
    "08 - RECTIFICADORES FALLADOS": "modulos_fallados",
    "09 - CORRIENTE DC DE LAS BATERIAS": "corriente_baterias",
    "10 - TEMPERATURA DE LAS BATERIAS": "temp_baterias",
    "11 - CORRIENTE DC DE LA CARGA": "corriente_carga",
}