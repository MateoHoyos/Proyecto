"""
api_client.py — Cliente HTTP para la API de Data Center Expert
──────────────────────────────────────────────────────────────────────────────
Este módulo implementa el cliente que se comunica con la API REST de la
plataforma EcoStruxure IT Data Center Expert (DCE) de Schneider Electric.

La API del DCE usa autenticación OAuth2 con tokens de acceso temporales
que expiran cada 5 minutos. La clase GestorDCE maneja automáticamente
la renovación del token antes de cada consulta, de modo que el resto
del sistema no necesita preocuparse por la autenticación.

Endpoints utilizados:
    POST /oauth/token              → obtener token de acceso
    GET  /v1/devices/{id}/sensors  → leer todos los sensores de un equipo

Este módulo es usado exclusivamente por etl_dce.py para extraer las
lecturas en tiempo real de los equipos del nodo.
──────────────────────────────────────────────────────────────────────────────
"""

import requests
import urllib3
import time

# Desactivar advertencias de certificado SSL no verificado.
# El servidor DCE usa un certificado autofirmado en la red interna,
# por lo que la verificación SSL se deshabilita para evitar errores
# de conexión. Esto es aceptable en una red corporativa privada.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GestorDCE:
    """
    Cliente para la API REST de Data Center Expert.

    Gestiona la autenticación OAuth2 y las consultas a los sensores
    de los equipos registrados en la plataforma DCE.

    Atributos:
        base_url   : URL base de la API REST del DCE
        auth_url   : URL del endpoint de autenticación OAuth2
        token      : token de acceso actual (se renueva automáticamente)
        token_time : timestamp de la última renovación del token
        TTL        : tiempo de vida útil del token en segundos (250s = ~4 min)
                     Se renueva antes de los 5 minutos para evitar expiración
                     en mitad de una consulta
    """

    def __init__(self, ip, usuario, password):
        """
        Inicializa el cliente con la IP del servidor DCE y las credenciales.

        El token no se obtiene en el constructor sino de forma lazy:
        se solicita la primera vez que se necesita hacer una consulta.
        """
        self.base_url   = f"https://{ip}/isxg/v1"
        self.auth_url   = f"https://{ip}/isxg/oauth/token"
        self.usuario    = usuario
        self.password   = password
        self.token      = None
        self.token_time = 0
        self.TTL        = 250   # Renovar token cada 250 segundos (~4 minutos)

    def _obtener_nuevo_token(self):
        """
        Solicita un nuevo token de acceso al servidor DCE mediante OAuth2.

        El protocolo OAuth2 con grant_type='password' permite autenticarse
        directamente con usuario y contraseña para obtener un Bearer token
        que se incluye en el header Authorization de cada consulta posterior.

        Si la autenticación falla (credenciales incorrectas, servidor no
        disponible, VPN desconectada), lanza una excepción que se propaga
        al módulo etl_dce.py para informar al usuario.
        """
        print("Renovando Token de acceso...")

        # Payload OAuth2: credenciales del usuario de la plataforma DCE
        payload = {
            "username":   self.usuario,
            "password":   self.password,
            "grant_type": "password"
        }

        try:
            resp = requests.post(
                self.auth_url,
                data=payload,
                verify=False,   # SSL deshabilitado (certificado autofirmado)
                timeout=15      # Timeout de 15 segundos para evitar bloqueos
            )

            if resp.status_code == 200:
                data            = resp.json()
                self.token      = data['access_token']
                self.token_time = time.time()
                print("Token renovado exitosamente.")
            else:
                raise Exception(f"Error Login ({resp.status_code}): {resp.text}")

        except Exception as e:
            print(f"Error crítico obteniendo token: {e}")
            raise e

    def get_headers(self):
        """
        Retorna los headers HTTP con un token de acceso válido.

        Verifica si el token actual sigue siendo válido comparando el tiempo
        transcurrido desde la última renovación con el TTL definido.
        Si el token está por vencer o no existe, lo renueva automáticamente
        antes de retornar los headers.

        Este método garantiza que todas las consultas a la API siempre
        se realicen con un token vigente, sin intervención manual.
        """
        ahora = time.time()

        # Renovar si no hay token o si ya superó el tiempo de vida útil
        if not self.token or (ahora - self.token_time > self.TTL):
            self._obtener_nuevo_token()

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept":        "application/json"
        }

    def consultar_equipo(self, device_id):
        """
        Consulta todos los sensores de un equipo registrado en el DCE.

        Llama al endpoint GET /v1/devices/{device_id}/sensors que retorna
        la lista completa de sensores del dispositivo con sus valores actuales.

        Cada sensor en la respuesta tiene la forma:
            {
                "label": "01 - VOLTAJE AC DEL SISTEMA L1-L2",
                "value": "215.5 V",
                "kind":  "VOLTAGE",
                "units": "V"
            }

        El módulo etl_dce.py usa el campo 'label' para identificar cada sensor
        y el campo 'value' para extraer el valor numérico.

        Retorna la lista de sensores si la consulta es exitosa, o None si falla.
        """
        endpoint = f"{self.base_url}/devices/{device_id}/sensors"

        try:
            # get_headers() renueva el token automáticamente si es necesario
            headers = self.get_headers()
            resp    = requests.get(
                endpoint,
                headers=headers,
                verify=False,
                timeout=15
            )

            if resp.status_code == 200:
                return resp.json()
            else:
                print(f" Error consultando equipo {device_id}: {resp.status_code}")
                return None

        except Exception as e:
            print(f" Error de conexión consultando equipo: {e}")
            return None
