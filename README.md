  <h1 align="center">
Desarrollo de una aplicación de evaluación técnica para instalación de equipos en infraestructura de telecomunicaciones
</h1>

<h3 align="center">Mateo Hoyos Mesa</h3>


<p align="center">
  <img src="docs/img/logo_tigo.png" width="70" alt="Logo Tigo">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="docs/img/logo_udea.png" width="180" alt="Logo UdeA">
</p>

## Tabla de contenido

- [Objetivo general](#objetivo-general)
- [¿Por qué se desarrolló este sistema?](#por-qué-se-desarrolló-este-sistema)
- [Sistema eléctrico](#sistema-electrico)
- [Funcionalidades](#funcionalidades)
- [Arquitectura](#arquitectura)
- [Modelo de Inteligencia Artificial](#Modelo-de-Inteligencia-Artificial)
- [Resultados](#Resultados)
- [Mejoras futuras](#Mejoras-futuras)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Entorno de desarrollo](#entorno-de-desarrollo)


## Objetivo general

<p align="justify">
Desarrolló de una aplicación que permita verificar si un nodo de telecomunicaciones tiene capacidad técnica para instalar un nuevo equipo, automatizando el proceso de evaluación eléctrica y física que actualmente se realiza de forma manual, integrando datos de infraestructura en tiempo real y generando un resultado estructurado de aprobación o rechazo
</p>

### ¿Por qué se desarrolló este sistema?
<p align="justify">
Tigo opera una red de nodos de telecomunicaciones distribuidos en Colombia. Cada vez que ingeniería solicita instalar un nuevo equipo en un nodo, el equipo de infraestructura debe evaluar manualmente si el sitio tiene capacidad para recibirlo. Este proceso implica revisar el espacio físico disponible en los racks, verificar que el sistema eléctrico soporte la nueva carga, recorrer el circuito completo desde el punto de conexión hasta el transformador, y confirmar que ninguna protección quede sobrecargada. Todo esto se hace revisando planos, tomando mediciones en campo y haciendo cálculos a mano, lo que lo convierte en un proceso lento, propenso a errores y difícil de escalar cuando hay múltiples solicitudes activas.
</p>

## Sistema electrico
![alt text](docs/img/sistema_electrico.png)


## Funcionalidades

- Evaluación eléctrica del nodo
- Evaluación de capacidad física
- Detección de anomalías usando IA
- Generación automática de reportes en PDF
- Visualización interactiva


## Arquitectura

El sistema se compone de los siguientes módulos:
- ETL: procesamiento y limpieza de datos
- Evaluador: lógica de validación técnica
- Modelo de IA: detección de anomalías (Isolation Forest)
- Visualización: interfaz en Streamlit
- Reportes: generación de PDF

![Flujo general de operación del sistema](docs/img/pagina_16.png)
Flujo general de operación del sistema

![Flujo general del proceso de evaluación de prefactibilidad ](docs/img/Prefactibilidad.png)
Flujo general del proceso de evaluación de prefactibilidad 

![Arquitectura del sistema y herramientas asociadas](docs/img/flujo_general.png)
Arquitectura del sistema y herramientas asociadas


## Modelo de Inteligencia Artificial

Se utiliza el algoritmo Isolation Forest para detectar anomalías
en variables eléctricas y térmicas del nodo.

Este modelo permite identificar comportamientos fuera de lo normal
sin necesidad de datos etiquetados.


## Resultados

El sistema genera:

- Evaluación de viabilidad del nodo
- Identificación de anomalías
- Reporte técnico en PDF

![Interfaz con Streamlit - Inicio](docs/img/interfaz_streamlit.png)

![Tablero BI - Inicio](docs/img/TableroBI.PNG)

![Desviación de cada variable respecto a su media histórica](docs/img/newplot.PNG)
Una desviación de 1σ significa que el valor actual está 1 desviación estándar por encima o por debajo de lo normal. Valores >2σ merecen atención.

**Documentación adicional**  
![Arquitectura del sistema y herramientas asociadas](docs/img/pagina_21.png)
El *funcionamiento del programa* está explicado en la presentación ubicada en `docs/Presentaciones`.

## Mejoras futuras

- Integración con IA generativa
- Despliegue en la nube
- Sistema de usuarios y permisos

## Tecnologías utilizadas
- Python
- Streamlit (interfaz)
- Pandas (procesamiento de datos)
- Scikit-learn - isolation-forest (modelo de IA)
- MySQL (base de datos)
- Reportlab (generar PDF)

## Entorno de desarrollo
- Sistema operativo: Windows 11
- IDE: Visual Studio Code
- Python 3.13.9

   
