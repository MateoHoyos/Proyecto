
from sqlalchemy import create_engine, text
import sys
import os

# Importar configuración
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_CONFIG

def get_engine():
    conn_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    return create_engine(conn_str)

def inicializar_base_datos_completa():
    engine = get_engine()
    print("Inicializando esquema completo de Base de Datos...")
    
    with engine.connect() as conn:

        tablas_maestras = {
            "info_nodo": """
                CREATE TABLE IF NOT EXISTS info_nodo (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_nodo VARCHAR(50), 
                    tipo VARCHAR(50), 
                    codigo VARCHAR(50),
                    regional VARCHAR(50), 
                    direccion VARCHAR(100),
                    capacidad_kva FLOAT, 
                    voltaje_sistema_dc FLOAT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,

            "protecciones": """
                CREATE TABLE IF NOT EXISTS protecciones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ubicacion VARCHAR(50), 
                    componente VARCHAR(50), 
                    marca VARCHAR(50),
                    referencia VARCHAR(100), 
                    capacidad_amps FLOAT, 
                    calibre_cable_awg VARCHAR(50)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,

            "inventario_dc_pdb": """
                CREATE TABLE IF NOT EXISTS inventario_dc_pdb (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pdb_nombre VARCHAR(20), 
                    fuente VARCHAR(10), 
                    posicion INT,
                    estado VARCHAR(20), 
                    capacidad INT, 
                    corriente FLOAT,
                    equipo_refencia VARCHAR(100)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,

            "inventario_racks": """
                CREATE TABLE IF NOT EXISTS inventario_racks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_rack VARCHAR(50), 
                    Label VARCHAR(50), 
                    u_totales INT,
                    Espacio VARCHAR(50), 
                    u_ocupadas_listado TEXT,
                    u_libres_listado TEXT,
                    nombre_foto VARCHAR(50), 
                    Detalle_rack VARCHAR(50)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        }

        # Ejecución en bucle (Más limpio que copiar y pegar conn.execute 20 veces)
        todas_las_tablas = {**tablas_maestras}
        
        for nombre, sql in todas_las_tablas.items():
            conn.execute(text(sql))
            print(f"Tabla '{nombre}' verificada.")
            
        conn.commit()
    
    print("Base de datos lista y estructurada.")
    return engine
