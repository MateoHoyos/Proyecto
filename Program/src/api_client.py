import requests
import urllib3
import time


# Desactivar alertas SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GestorDCE:
    def __init__(self, ip, usuario, password):
        self.base_url = f"https://{ip}/isxg/v1"       
        self.auth_url = f"https://{ip}/isxg/oauth/token"
        self.usuario = usuario
        self.password = password
        self.token = None
        self.token_time = 0
        self.TTL = 250  # 4 minutos de vida útil (renueva antes de los 5 min)

    def _obtener_nuevo_token(self):
        """Pide un token nuevo automáticamente"""
        print("Renovando Token de acceso...")
        
        # Datos para OAuth2
        payload = {
            "username": self.usuario,
            "password": self.password,
            "grant_type": "password"
        }
        
        try:
            resp = requests.post(self.auth_url, data=payload, verify=False, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                self.token = data['access_token']
                self.token_time = time.time()
                print("Token renovado exitosamente.")
            else:
                # Si falla, imprimimos el error crudo para depurar
                raise Exception(f"Error Login ({resp.status_code}): {resp.text}")
                
        except Exception as e:
            print(f"Error crítico obteniendo token: {e}")
            raise e

    def get_headers(self):
        """Devuelve las cabeceras con un token válido"""
        ahora = time.time()
        # Si no hay token o ya casi vence, pedimos uno nuevo
        if not self.token or (ahora - self.token_time > self.TTL):
            self._obtener_nuevo_token()
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    def consultar_equipo(self, device_id):
        """Consulta todos los sensores de un equipo"""
        endpoint = f"{self.base_url}/devices/{device_id}/sensors"
        
        try:
            headers = self.get_headers() # Aquí se hace el login automático si hace falta
            resp = requests.get(endpoint, headers=headers, verify=False, timeout=15)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f" Error consultando equipo {device_id}: {resp.status_code}")
                return None
        except Exception as e:
            print(f" Error de conexión consultando equipo: {e}")
            return None


