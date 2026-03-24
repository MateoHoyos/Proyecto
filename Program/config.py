"""
config.py — Configuración de Conexión a la Base de Datos
──────────────────────────────────────────────────────────────────────────────
Archivo de configuración central del sistema. Define los parámetros de
conexión a la base de datos MySQL donde se almacenan todos los datos del nodo.

Este archivo es importado por src/db.py para construir la cadena de conexión
con SQLAlchemy. Es el único lugar donde se deben modificar las credenciales
si se cambia de servidor o base de datos.

Parámetros:
    user     : usuario de MySQL con permisos de lectura y escritura
    password : contraseña del usuario
    host     : dirección del servidor MySQL (localhost para instalación local)
    database : nombre de la base de datos del sistema IDEO

NOTA: En un entorno de producción, estas credenciales deberían cargarse
desde variables de entorno o un archivo .env para mayor seguridad,
en lugar de estar escritas directamente en el código.
──────────────────────────────────────────────────────────────────────────────
"""

# Parámetros de conexión a MySQL
# Todos los módulos del sistema acceden a la BD a través de src/db.py,
# que usa este diccionario para construir la URL de conexión con SQLAlchemy
DB_CONFIG = {
    "user":     "root",        # Usuario de MySQL
    "password": "admin",       # Contraseña del usuario
    "host":     "localhost",   # Servidor de base de datos (instalación local)
    "database": "nodo_ideo"    # Nombre de la base de datos del sistema
}
