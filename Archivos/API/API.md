Read Only para API

DCE (REST + OAuth2)



[https://10.159.125.33/isxg/dce-rest-api.html](https://10.159.125.33/isxg/dce-rest-api.html)

[https://10.159.125.34/isxg/dce-rest-api.html](https://10.159.125.34/isxg/dce-rest-api.html)





TABLERO - IDEO CALI: B7e755e\_nbSNMPEnc60BA612C  B7eef4c\_nbSNMPEnc60BA612C   B7eef4c\_nbModbusEnc11703964

RECT 01 - IDEO CALI: B7e755e\_nbSNMPEncD1F128BD  B7eef4c\_nbSNMPEncD1F128BD

RECT 02: 	     B7e755e\_nbSNMPEnc7D425FC9  B7eef4c\_nbSNMPEnc7D425FC9

 





get /v1/devices:

GET /v1/devices/{guid}/sensors



&nbsp;{

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "inMaintenance": false,

&nbsp;   "isxcGuid": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "model": "COMAP - IL-NT-AMF25 - 3P",

&nbsp;   "type": "Generator",

&nbsp;   "hostname": "10.170.203.3",

&nbsp;   "ipAddress": "10.170.203.3",

&nbsp;   "privateSide": false,

&nbsp;   "label": "TR - IDEO CALI",

&nbsp;   "serialNumber": "20240D2A",

&nbsp;   "location": "V. CAUCA - CALI"

&nbsp; },



\[

&nbsp; {

&nbsp;   "label": "08 - VOLTAJE AC DEL GENERADOR L3-L1",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_08\_VOLTAJE\_AC\_DEL\_GENERADOR\_L3\_L1",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "0.0 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "0.0",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "11 - CORRIENTE AC DE LA CARGA L1",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_11\_CORRIENTE\_AC\_DE\_LA\_CARGA\_L1",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "58.0 A",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "AMP\_DETECTOR",

&nbsp;   "rawValue": "58.0",

&nbsp;   "units": "A"

&nbsp; },

&nbsp; {

&nbsp;   "label": "19 - AC FAIL",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_19\_AC\_FAIL",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "INACTIVO",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "STATE"

&nbsp; },

&nbsp; {

&nbsp;   "label": "18 - MODO DEL CONTROL",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_18\_MODO\_DEL\_CONTROL",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "AUTOMATICO",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "STATE"

&nbsp; },

&nbsp; {

&nbsp;   "label": "05 - VOLTAJE DE LA BATERIA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_05\_VOLTAJE\_DE\_LA\_BATERIA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "27.5 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "27.5",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "15 - POTENCIA REACTIVA DE LA CARGA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_15\_POTENCIA\_REACTIVA\_DE\_LA\_CARGA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "-4.0 kVAR",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "K\_REACT\_POWER",

&nbsp;   "rawValue": "-4.0",

&nbsp;   "units": "kVAR"

&nbsp; },

&nbsp; {

&nbsp;   "label": "09 - FRENCUENCIA DEL GENERADOR",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_09\_FRENCUENCIA\_DEL\_GENERADOR",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "0.0 Hz",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "NUMBER",

&nbsp;   "rawValue": "0.0",

&nbsp;   "units": "Hz"

&nbsp; },

&nbsp; {

&nbsp;   "label": "22 - CONTACTOR DEL GENERADOR",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_22\_CONTACTOR\_DEL\_GENERADOR",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "INACTIVO",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "STATE"

&nbsp; },

&nbsp; {

&nbsp;   "label": "20 - CONTACTOR DE RED",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_20\_CONTACTOR\_DE\_RED",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "ACTIVO",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "STATE"

&nbsp; },

&nbsp; {

&nbsp;   "label": "21 - GENERADOR ENCENDIDO",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_21\_GENERADOR\_ENCENDIDO",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "INACTIVO",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "STATE"

&nbsp; },

&nbsp; {

&nbsp;   "label": "03 - VOLTAJE AC DEL SISTEMA L3-L1",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_03\_VOLTAJE\_AC\_DEL\_SISTEMA\_L3\_L1",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "215.0 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "215.0",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "07 - VOLTAJE AC DEL GENERADOR L2-L3",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_07\_VOLTAJE\_AC\_DEL\_GENERADOR\_L2\_L3",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "0.0 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "0.0",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "14 - POTENCIA ACTIVA DE LA CARGA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_14\_POTENCIA\_ACTIVA\_DE\_LA\_CARGA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "21.0 kW",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "POWER\_KWATTS",

&nbsp;   "rawValue": "21.0",

&nbsp;   "units": "kW"

&nbsp; },

&nbsp; {

&nbsp;   "label": "17 - FACTOR DE POTENCIA DE LA CARGA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_17\_FACTOR\_DE\_POTENCIA\_DE\_LA\_CARGA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "0.98",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "NUMBER",

&nbsp;   "rawValue": "0.98",

&nbsp;   "units": ""

&nbsp; },

&nbsp; {

&nbsp;   "label": "13 - CORRIENTE AC DE LA CARGA L3",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_13\_CORRIENTE\_AC\_DE\_LA\_CARGA\_L3",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "59.0 A",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "AMP\_DETECTOR",

&nbsp;   "rawValue": "59.0",

&nbsp;   "units": "A"

&nbsp; },

&nbsp; {

&nbsp;   "label": "23 - ALARMA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_23\_ALARMA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "INACTIVO",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "STATE"

&nbsp; },

&nbsp; {

&nbsp;   "label": "16 - POTENCIA APARENTE DE LA CARGA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_16\_POTENCIA\_APARENTE\_DE\_LA\_CARGA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "21.0 kVA",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "POWER\_KVA",

&nbsp;   "rawValue": "21.0",

&nbsp;   "units": "kVA"

&nbsp; },

&nbsp; {

&nbsp;   "label": "04 - FRECUENCIA DEL SISTEMA",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_04\_FRECUENCIA\_DEL\_SISTEMA",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "60.0 Hz",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "NUMBER",

&nbsp;   "rawValue": "60.0",

&nbsp;   "units": "Hz"

&nbsp; },

&nbsp; {

&nbsp;   "label": "Link Status",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_STATUS",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "Online",

&nbsp;   "sensorType": "STATE",

&nbsp;   "kind": "COMMUNICATION\_SENSOR"

&nbsp; },

&nbsp; {

&nbsp;   "label": "01 - VOLTAJE AC DEL SISTEMA L1-L2",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_01\_VOLTAJE\_AC\_DEL\_SISTEMA\_L1\_L2",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "214.0 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "214.0",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "10 - RPM DEL GENERADOR",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_10\_RPM\_DEL\_GENERADOR",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "0.0",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "NUMBER",

&nbsp;   "rawValue": "0.0",

&nbsp;   "units": ""

&nbsp; },

&nbsp; {

&nbsp;   "label": "02 - VOLTAJE AC DEL SISTEMA L2-L3",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_02\_VOLTAJE\_AC\_DEL\_SISTEMA\_L2\_L3",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "214.0 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "214.0",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "06 - VOLTAJE AC DEL GENERADOR L1-L2",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_06\_VOLTAJE\_AC\_DEL\_GENERADOR\_L1\_L2",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "0.0 V",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "VOLTAGE",

&nbsp;   "rawValue": "0.0",

&nbsp;   "units": "V"

&nbsp; },

&nbsp; {

&nbsp;   "label": "12 - CORRIENTE AC DE LA CARGA L2",

&nbsp;   "guid": "B7e755e\_nbModbusEnc4B4D008D\_12\_CORRIENTE\_AC\_DE\_LA\_CARGA\_L2",

&nbsp;   "podId": "B7e755e\_nbModbusEnc4B4D008D",

&nbsp;   "severity": 0,

&nbsp;   "severityText": "None",

&nbsp;   "value": "58.0 A",

&nbsp;   "sensorType": "NUMBER",

&nbsp;   "kind": "AMP\_DETECTOR",

&nbsp;   "rawValue": "58.0",

&nbsp;   "units": "A"

&nbsp; }

]













\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*+

{

    "severity": 0,

    "severityText": "None",

    "inMaintenance": false,

    "isxcGuid": "B7e755e\_nbSNMPEnc60BA612C",

    "model": "EATON - SC200",

    "type": "Sensor Pod",

    "hostname": "10.170.203.2",

    "ipAddress": "10.170.203.2",

    "privateSide": false,

    "label": "TABLERO - IDEO CALI - (10.170.203.2)",

    "serialNumber": "244448746",

    "location": "V. CAUCA - CALI"

  },







\[

  {

    "label": "ANALOG INPUT - ML CURRENT AC S",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_5",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "59.46 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "59.46",

    "units": "A"

  },

  {

    "label": "ANALOG INPUT - ML CURRENT AC T",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_6",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "66.25 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "66.25",

    "units": "A"

  },

  {

    "label": "ANALOG INPUT - °C SALA S01",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_8",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "23.00 ° C",

    "sensorType": "NUMBER",

    "kind": "TEMPERATURE",

    "rawValue": "23.00",

    "units": "° C"

  },

  {

    "label": "ANALOG INPUT - ML VOLTAGE AC R-S",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_1",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "214.93 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "214.93",

    "units": "V"

  },

  {

    "label": "ANALOG INPUT - ML VOLTAGE AC S-T",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_2",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "214.35 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "214.35",

    "units": "V"

  },

  {

    "label": "08 - CORRIENTE DC DE LAS BATERIAS",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_08\_\_\_CORRIENTE\_DC\_DE\_LAS\_BATERIAS",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "0.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "0.00",

    "units": "A"

  },

  {

    "label": "Link Status",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_STATUS",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "Online",

    "sensorType": "STATE",

    "kind": "COMMUNICATION\_SENSOR"

  },

  {

    "label": "ANALOG INPUT - ML VOLTAGE AC T-R",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_3",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "219.85 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "219.85",

    "units": "V"

  },

  {

    "label": "ANALOG INPUT - ML CURRENT AC R",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_4",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "58.46 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "58.46",

    "units": "A"

  },

  {

    "label": "DIGITAL OUTPUT - ML AC FAIL",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_DIGITAL\_OUTPUT\_0",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "INACTIVO",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "ANALOG INPUT - °C SALA S02",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_ANALOG\_INPUT\_9",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "21.00 ° C",

    "sensorType": "NUMBER",

    "kind": "TEMPERATURE",

    "rawValue": "21.00",

    "units": "° C"

  },

  {

    "label": "13 - TEST DE BATERIAS",

    "guid": "B7e755e\_nbSNMPEnc60BA612C\_13\_\_\_TEST\_DE\_BATERIAS",

    "podId": "B7e755e\_nbSNMPEnc60BA612C",

    "severity": 0,

    "severityText": "None",

    "value": "DESHABILITADO",

    "sensorType": "STATE",

    "kind": "STATE"

  }

]





+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++















{

    "severity": 0,

    "severityText": "None",

    "inMaintenance": false,

    "isxcGuid": "B7e755e\_nbSNMPEncD1F128BD",

    "model": "ELTEK - SMARTPACK 2 TOUCH",

    "type": "DC Rectifier",

    "hostname": "10.170.203.6",

    "ipAddress": "10.170.203.6",

    "privateSide": false,

    "label": "RECT 01 - IDEO CALI - (10.170.203.6)",

    "location": "V. CAUCA - CALI"

  },





\[

  {

    "label": "07 - RECTIFICADORES INSTALADOS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_07\_\_\_RECTIFICADORES\_INSTALADOS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "21.0",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "21.0",

    "units": ""

  },

  {

    "label": "05 - MODO DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_05\_\_\_MODO\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Float",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "09 - CORRIENTE DC DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_09\_\_\_CORRIENTE\_DC\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "0.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "0.00",

    "units": "A"

  },

  {

    "label": "14 - ESTADO DE LA AC",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_14\_\_\_ESTADO\_DE\_LA\_AC",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "19 - ESTADO FUSIBLES DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_19\_\_\_ESTADO\_FUSIBLES\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "01 - VOLTAJE AC DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_01\_\_\_VOLTAJE\_AC\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "213.00 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "213.00",

    "units": "V"

  },

  {

    "label": "10 - TEMPERATURA DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_10\_\_\_TEMPERATURA\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "26.00 ° C",

    "sensorType": "NUMBER",

    "kind": "TEMPERATURE",

    "rawValue": "26.00",

    "units": "° C"

  },

  {

    "label": "15 - ESTADO DE LOS RECTIFICADORES",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_15\_\_\_ESTADO\_DE\_LOS\_RECTIFICADORES",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "Link Status",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_STATUS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Online",

    "sensorType": "STATE",

    "kind": "COMMUNICATION\_SENSOR"

  },

  {

    "label": "17 - ESTADO FUSIBLES DE LA CARGA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_17\_\_\_ESTADO\_FUSIBLES\_DE\_LA\_CARGA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "06 - NUMERO DE FASES",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_06\_\_\_NUMERO\_DE\_FASES",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "3.0",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "3.0",

    "units": ""

  },

  {

    "label": "03 - CORRIENTE DC DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_03\_\_\_CORRIENTE\_DC\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "119.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "119.00",

    "units": "A"

  },

  {

    "label": "18 - ESTADO DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_18\_\_\_ESTADO\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "08 - RECTIFICADORES FALLADOS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_08\_\_\_RECTIFICADORES\_FALLADOS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "0.0",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "0.0",

    "units": ""

  },

  {

    "label": "12 - ESTADO DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_12\_\_\_ESTADO\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "02 - VOLTAJE DC DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_02\_\_\_VOLTAJE\_DC\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "54.47 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "54.47",

    "units": "V"

  },

  {

    "label": "13 - ESTADO CONTROL DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_13\_\_\_ESTADO\_CONTROL\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "16 - ESTADO DE LA CARGA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_16\_\_\_ESTADO\_DE\_LA\_CARGA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "04 - PORCENTAJE DE CARGA DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_04\_\_\_PORCENTAJE\_DE\_CARGA\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "10.0 %",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "10.0",

    "units": "%"

  },

  {

    "label": "20 - ESTADO LVD DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_20\_\_\_ESTADO\_LVD\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "11 - CORRIENTE DC DE LA CARGA",

    "guid": "B7eef4c\_nbSNMPEncD1F128BD\_11\_\_\_CORRIENTE\_DC\_DE\_LA\_CARGA",

    "podId": "B7eef4c\_nbSNMPEncD1F128BD",

    "severity": 0,

    "severityText": "None",

    "value": "119.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "119.00",

    "units": "A"

  }

]



+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++





{

    "severity": 0,

    "severityText": "None",

    "inMaintenance": false,

    "isxcGuid": "B7e755e\_nbSNMPEnc7D425FC9",

    "model": "ELTEK - SMARTPACK 2 TOUCH",

    "type": "DC Rectifier",

    "hostname": "10.170.203.7",

    "ipAddress": "10.170.203.7",

    "privateSide": false,

    "label": "RECT 02 - IDEO CALI - (10.170.203.7)",

    "location": "V. CAUCA - CALI"

  },





\[

  {

    "label": "04 - PORCENTAJE DE CARGA DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_04\_\_\_PORCENTAJE\_DE\_CARGA\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "14.0 %",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "14.0",

    "units": "%"

  },

  {

    "label": "16 - ESTADO DE LA CARGA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_16\_\_\_ESTADO\_DE\_LA\_CARGA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "15 - ESTADO DE LOS RECTIFICADORES",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_15\_\_\_ESTADO\_DE\_LOS\_RECTIFICADORES",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "18 - ESTADO DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_18\_\_\_ESTADO\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "20 - ESTADO LVD DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_20\_\_\_ESTADO\_LVD\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "08 - RECTIFICADORES FALLADOS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_08\_\_\_RECTIFICADORES\_FALLADOS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "0.0",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "0.0",

    "units": ""

  },

  {

    "label": "09 - CORRIENTE DC DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_09\_\_\_CORRIENTE\_DC\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "0.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "0.00",

    "units": "A"

  },

  {

    "label": "05 - MODO DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_05\_\_\_MODO\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Float",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "Link Status",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_STATUS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Online",

    "sensorType": "STATE",

    "kind": "COMMUNICATION\_SENSOR"

  },

  {

    "label": "06 - NUMERO DE FASES",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_06\_\_\_NUMERO\_DE\_FASES",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "3.0",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "3.0",

    "units": ""

  },

  {

    "label": "19 - ESTADO FUSIBLES DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_19\_\_\_ESTADO\_FUSIBLES\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "07 - RECTIFICADORES INSTALADOS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_07\_\_\_RECTIFICADORES\_INSTALADOS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "19.0",

    "sensorType": "NUMBER",

    "kind": "NUMBER",

    "rawValue": "19.0",

    "units": ""

  },

  {

    "label": "01 - VOLTAJE AC DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_01\_\_\_VOLTAJE\_AC\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "211.00 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "211.00",

    "units": "V"

  },

  {

    "label": "11 - CORRIENTE DC DE LA CARGA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_11\_\_\_CORRIENTE\_DC\_DE\_LA\_CARGA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "157.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "157.00",

    "units": "A"

  },

  {

    "label": "13 - ESTADO CONTROL DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_13\_\_\_ESTADO\_CONTROL\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "14 - ESTADO DE LA AC",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_14\_\_\_ESTADO\_DE\_LA\_AC",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "02 - VOLTAJE DC DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_02\_\_\_VOLTAJE\_DC\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "54.47 V",

    "sensorType": "NUMBER",

    "kind": "VOLTAGE",

    "rawValue": "54.47",

    "units": "V"

  },

  {

    "label": "10 - TEMPERATURA DE LAS BATERIAS",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_10\_\_\_TEMPERATURA\_DE\_LAS\_BATERIAS",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "25.00 ° C",

    "sensorType": "NUMBER",

    "kind": "TEMPERATURE",

    "rawValue": "25.00",

    "units": "° C"

  },

  {

    "label": "12 - ESTADO DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_12\_\_\_ESTADO\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  },

  {

    "label": "03 - CORRIENTE DC DEL SISTEMA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_03\_\_\_CORRIENTE\_DC\_DEL\_SISTEMA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "157.00 A",

    "sensorType": "NUMBER",

    "kind": "AMP\_DETECTOR",

    "rawValue": "157.00",

    "units": "A"

  },

  {

    "label": "17 - ESTADO FUSIBLES DE LA CARGA",

    "guid": "B7eef4c\_nbSNMPEnc7D425FC9\_17\_\_\_ESTADO\_FUSIBLES\_DE\_LA\_CARGA",

    "podId": "B7eef4c\_nbSNMPEnc7D425FC9",

    "severity": 0,

    "severityText": "None",

    "value": "Normal",

    "sensorType": "STATE",

    "kind": "STATE"

  }

]





+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



  {

    "severity": 0,

    "severityText": "None",

    "inMaintenance": false,

    "isxcGuid": "B7e755e\_nbModbusEnc4B4D008D",

    "model": "COMAP - IL-NT-AMF25 - 3P",

    "type": "Generator",

    "hostname": "10.170.203.3",

    "ipAddress": "10.170.203.3",

    "privateSide": false,

    "label": "TR - IDEO CALI",

    "serialNumber": "20240D2A",

    "location": "V. CAUCA - CALI"

  },



{

    "severity": 0,

    "severityText": "None",

    "inMaintenance": false,

    "isxcGuid": "B7e755e\_nbModbusEnc11703964",

    "model": "COMAP - INTELILITE AMF25 - MRS - 3P",

    "type": "Generator",

    "hostname": "10.170.203.4",

    "ipAddress": "10.170.203.4",

    "privateSide": false,

    "label": "MG - IDEO CALI",

    "serialNumber": "204801DF",

    "location": "V. CAUCA - CALI"

  },

