  <h1 align="center">
Desarrollo de una aplicación de evaluación técnica para instalación de equipos en infraestructura de telecomunicaciones
</h1>

<h3 align="center">Mateo Hoyos Mesa</h3>


<p align="center">
  <img src="Archivos/img/logo_tigo.png" width="70" alt="Logo Tigo">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="Archivos/img/logo_udea.png" width="180" alt="Logo UdeA">
</p>



#### Objetivo general

<p align="justify">
Desarrolló de una aplicación que permita verificar si un nodo de telecomunicaciones tiene capacidad técnica para instalar un nuevo equipo, automatizando el proceso de evaluación eléctrica y física que actualmente se realiza de forma manual, integrando datos de infraestructura en tiempo real y generando un resultado estructurado de aprobación o rechazo
</p>


#### ¿Por qué se desarrolló este sistema?
<p align="justify">
Tigo opera una red de nodos de telecomunicaciones distribuidos en Colombia. Cada vez que ingeniería solicita instalar un nuevo equipo en un nodo, el equipo de infraestructura debe evaluar manualmente si el sitio tiene capacidad para recibirlo. Este proceso implica revisar el espacio físico disponible en los racks, verificar que el sistema eléctrico soporte la nueva carga, recorrer el circuito completo desde el punto de conexión hasta el transformador, y confirmar que ninguna protección quede sobrecargada. Todo esto se hace revisando planos, tomando mediciones en campo y haciendo cálculos a mano, lo que lo convierte en un proceso lento, propenso a errores y difícil de escalar cuando hay múltiples solicitudes activas.
</p>

#### Sistema electrico
![alt text](Archivos/img/sistema_electrico.png)

<p align="center">
  <em>
    Fuente:
    <a href="https://convertronic.net/potencia/fuentes-de-alimentacion/creacion-de-una-mejor-fuente-de-alimentacion-de-48-vcc-para-equipos-de-telecomunicaciones-5g-y-de-proxima-generacion.html" target="_blank">[Sistema eléctrico del nodo de telecomunicaciones.]</a>
  </em>
</p>

## Funcionalidades

- Evaluación eléctrica del nodo
- Evaluación de capacidad física
- Detección de anomalías usando IA
- Generación automática de reportes en PDF
- Visualización interactiva


#### Módulos
![alt text](Archivos/img/modulo.png)

## Arquitectura

El sistema se compone de los siguientes módulos:

- ETL: procesamiento y limpieza de datos
- Evaluador: lógica de validación técnica
- Modelo de IA: detección de anomalías (Isolation Forest)
- Visualización: interfaz en Streamlit
- Reportes: generación de PDF

#### flujo general
![alt text](Archivos/img/flujo_general.png)


## Requisitos
- Python 
- pip
- MySQL 

## Tecnologías utilizadas
- Python
- Streamlit (interfaz)
- Pandas (procesamiento de datos)
- Scikit-learn (modelo de IA)
- MySQL (base de datos)

## Entorno de desarrollo
- Sistema operativo: Windows 10
- IDE: VS Code
- Python: 3.10

   
