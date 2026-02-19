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
            #Datos manuales
            "info_nodo": """
                CREATE TABLE IF NOT EXISTS info_nodo (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_nodo VARCHAR(50), 
                    tipo VARCHAR(50), 
                    codigo VARCHAR(50),
                    regional VARCHAR(50), 
                    direccion VARCHAR(100),
                    capacidad_kva FLOAT, 
                    Racks INT,
                    maximo_racks INT
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
                    tipo VARCHAR(10),
                    calibre_cable_salida VARCHAR(50)
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
                    nombre_foto VARCHAR(2000), 
                    Detalle_rack VARCHAR(2000)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            # Datos DCE
           

           "tr_dce": """
                CREATE TABLE IF NOT EXISTS tr_dce (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha DATETIME,
                    voltaje_ac_l1_l2 FLOAT,
                    voltaje_ac_l2_l3 FLOAT,
                    voltaje_ac_l3_l1 FLOAT,
                    frecuencia_sistema FLOAT,
                    voltaje_bateria FLOAT,
                    voltaje_gen_l1_l2 FLOAT,
                    voltaje_gen_l2_l3 FLOAT,
                    voltaje_gen_l3_l1 FLOAT,
                    frecuencia_gen FLOAT,
                    rpm_gen INT,
                    corriente_ac_l1 FLOAT,
                    corriente_ac_l2 FLOAT,
                    corriente_ac_l3 FLOAT,
                    potencia_activa_kw FLOAT,
                    potencia_reactiva_kvar FLOAT,
                    potencia_aparente_kva FLOAT,
                    factor_potencia FLOAT,
                    modo_control VARCHAR(50),
                    ac_fail VARCHAR(20),
                    contactor_red VARCHAR(20),
                    generador_encendido VARCHAR(20),
                    contactor_generador VARCHAR(20),
                    alarma VARCHAR(50),
                    link_status VARCHAR(20)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,

            "ml_dce": """
                CREATE TABLE IF NOT EXISTS ml_dce (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha DATETIME,
                    corriente_ac_r FLOAT,
                    corriente_ac_s FLOAT,
                    corriente_ac_t FLOAT,
                    voltaje_ac_rs FLOAT,
                    voltaje_ac_st FLOAT,
                    voltaje_ac_tr FLOAT,
                    temp_sala_s01 FLOAT,
                    temp_sala_s02 FLOAT,
                    corriente_dc_baterias FLOAT,
                    link_status VARCHAR(20),
                    ml_ac_fail VARCHAR(20),
                    test_baterias VARCHAR(50)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,

            "rect_dce": """
                CREATE TABLE IF NOT EXISTS rect_dce (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    rectificador_id INT,         -- 1 o 2
                    fecha DATETIME,
                    voltaje_ac_entrada FLOAT,
                    voltaje_dc_salida FLOAT,
                    corriente_dc_total FLOAT,
                    porcentaje_carga FLOAT,
                    modo_sistema VARCHAR(20),    -- Float, Equalize...
                    num_fases INT,
                    modulos_instalados INT,
                    modulos_fallados INT,
                    corriente_baterias FLOAT,
                    temp_baterias FLOAT,
                    corriente_carga FLOAT,
                    estado_sistema VARCHAR(20),
                    link_status VARCHAR(20)
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
