from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import os

def generar_pdf_factibilidad(datos_informe, racks_info, datos_usuario):
    # 1. Configuración del Archivo

    carpeta_sharepoint = os.path.join(os.path.expanduser("~"), "OneDrive - MIC", "Modelado de infraestructura de los nodos - Reportes 1")
    
    if os.path.exists(carpeta_sharepoint):
        carpeta = carpeta_sharepoint
    else:
        # Fallback local
        carpeta = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Reportes")

    # if not os.path.exists(carpeta): os.makedirs(carpeta)
    
    nombre_limpio = "".join(x for x in str(datos_usuario.get("Equipment", "Reporte")) if x.isalnum() or x in "_- ")
    nombre_limpio = nombre_limpio.replace(" ", "_")
    #timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    id_forms = datos_usuario.get("ID", "0")
    ruta_pdf = os.path.join(carpeta, f"PRE_Factibilidad_{nombre_limpio}_ID{id_forms}.pdf")

    # Creación del Documento
    doc = SimpleDocTemplate(ruta_pdf, pagesize=LETTER)
    elements = []
    styles = getSampleStyleSheet()

    # --- ESTILOS PERSONALIZADOS ---
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=1, fontSize=16, spaceAfter=20)
    estilo_subtitulo = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=12, textColor=colors.darkblue, spaceBefore=15, spaceAfter=10)
    estilo_normal = styles['BodyText']
    estilo_alerta = ParagraphStyle('Alerta', parent=styles['BodyText'], textColor=colors.red)
    
    # 1. ENCABEZADO
    elements.append(Paragraph("Informe de PRE-Factibilidad Infraestructura", estilo_titulo))
    elements.append(Paragraph(f"Fecha de Generación: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Estado Final
    estado = datos_informe.get("PRE-Factibilidad Infraestructura (Si / No)", "NO")
    color_estado = colors.green if estado == "SI" else colors.red
    texto_estado = f"<b>ESTADO FINAL: {'APROBADO' if estado == 'SI' else 'RECHAZADO'}</b>"
    elements.append(Paragraph(texto_estado, ParagraphStyle('Estado', parent=styles['Heading2'], alignment=1, textColor=color_estado)))
    elements.append(Spacer(1, 12))

    # 2. DATOS DEL PROYECTO (TABLA)
    elements.append(Paragraph("1. Datos del Proyecto Solicitado", estilo_subtitulo))
    
    data_proyecto = []
    
    # --- CAMBIO AQUÍ: Agregamos BTU_Label a la lista ---
    campos_clave = {
        "Equipment": "Equipo",
        "Quantity Equipment DC": "Cantidad",
        "Máx. Power DC (W)": "Potencia (W)",
        "Voltage(AC or DC)": "Voltaje",
        "Power sources": "Fuentes",
        "BTU_Label": "Aire / Disipación (BTU)", # <--- NUEVO CAMPO
        "Technical Site": "Sitio"
    }
    
    for key, label in campos_clave.items():
        # Usamos .get con un string vacío por si acaso
        valor = str(datos_usuario.get(key, "N/A"))
        data_proyecto.append([label, valor])
    
    # Agregar info de espacio requerido
    if datos_usuario.get("Requiere_Rack_Nuevo"):
        data_proyecto.append(["Requerimiento Espacio", f"{datos_usuario.get('Cantidad_Racks_Nuevos')} Racks Nuevos (Suelo)"])
    else:
        data_proyecto.append(["Requerimiento Espacio", f"{datos_usuario.get('U_Requeridas')} U (Rack Existente)"])

    # Crear Tabla Bonita
    tabla_proy = Table(data_proyecto, colWidths=[180, 270])
    tabla_proy.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(tabla_proy)

    # 3. UBICACIÓN FÍSICA
    titulo_u = "2. Ubicación Física (Suelo)" if datos_usuario.get("Requiere_Rack_Nuevo") else "2. Ubicación Física (Racks)"
    elements.append(Paragraph(titulo_u, estilo_subtitulo))

    if datos_usuario.get("Requiere_Rack_Nuevo"):
        # --- CAMBIO AQUÍ: Usamos el mensaje detallado que viene del main ---
        # Recuperamos el mensaje guardado en main.py
        msg_suelo = datos_usuario.get('Recomendacion_Instalacion_Fisica', "No hay información detallada de suelo.")
        
        # Limpiamos emojis por si acaso quedaron (opcional si usas reportlab, pero mejor prevenir)
        msg_limpio = msg_suelo.replace("✅", "").replace("❌", "").replace("⚠️", "").strip()
        
        elements.append(Paragraph(msg_limpio, estilo_normal))
    else:
        if racks_info:
            data_racks = [["Rack", "Espacios Disponibles (Bloques)"]]
            for r in racks_info:
                bloques = ", ".join([f"U{b['inicio']}-{b['fin']}" for b in r['bloques']])
                data_racks.append([r['rack'], bloques])
            
            t_racks = Table(data_racks, colWidths=[150, 300])
            t_racks.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(t_racks)
        else:
            elements.append(Paragraph("No se encontró espacio contiguo suficiente.", estilo_alerta))

    # 4. RECOMENDACIÓN TÉCNICA
    elements.append(Paragraph("3. Recomendacion de Conexión en PDB", estilo_subtitulo))
    instruccion = datos_informe.get("Recomendacion_Instalacion", "N/A")
    instruccion = instruccion.replace("/n", "<br/>")
    elements.append(Paragraph(instruccion, estilo_normal))

    # 5. VALIDACIONES TÉCNICAS
    elements.append(Paragraph("4. Detalle de Validaciones", estilo_subtitulo))
    
    checks = datos_informe.get("Checks", [])
    data_checks = []
    
    for check in checks:
        if "[FALLO]" in check or "❌" in check:
            texto_coloreado = f"<font color='red'>{check}</font>"
        elif "[ADVERTENCIA]" in check or "⚠️" in check:
            texto_coloreado = f"<font color='orange'>{check}</font>"
        elif "[OK]" in check or "✅" in check:
            texto_coloreado = f"<font color='green'>{check}</font>"
        else:
            texto_coloreado = check
            
        data_checks.append([Paragraph(texto_coloreado, styles['BodyText'])])

    t_checks = Table(data_checks, colWidths=[450])
    t_checks.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    elements.append(t_checks)

    # GENERAR PDF
    try:
        doc.build(elements)
        print(f"/n Informe PDF generado (ReportLab): {ruta_pdf}")
        return True, ruta_pdf  
    except Exception as e:
        print(f"/n Error generando PDF: {e}")
        return False, str(e)
    

