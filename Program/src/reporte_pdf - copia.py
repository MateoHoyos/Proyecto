from fpdf import FPDF
from datetime import datetime
import os

class PDFReporte(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        # Título centrado
        self.cell(self.epw, 10, 'Informe de PRE-Factibilidad Infraestructura - Nodo IDEO', align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_font('Arial', 'I', 10)
        self.cell(self.epw, 10, f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M")}', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(self.epw, 10, f'Pagina {self.page_no()}', align='C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 11)
        self.set_fill_color(220, 220, 220)
        self.set_x(self.l_margin)
        self.cell(self.epw, 8, label, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def chapter_body(self, text):
        self.set_font('Arial', '', 10)
        t = str(text).encode('latin-1', 'replace').decode('latin-1')
        self.set_x(self.l_margin)
        self.multi_cell(w=self.epw, h=5, text=t)
        self.ln()

def limpiar_texto(texto):
    """Limpia caracteres incompatibles con PDF"""
    if not isinstance(texto, str):
        return str(texto)
    # Reemplazos básicos
    t = texto.replace("✅", "").replace("❌", "").replace("⚠️", "").replace("•", "-")
    # Codificación segura
    return t.encode('latin-1', 'replace').decode('latin-1').strip()

def generar_pdf_factibilidad(datos_informe, racks_info, datos_usuario):
    pdf = PDFReporte()
    pdf.add_page()
    
    # 1. ESTADO
    estado = datos_informe.get("PRE-Factibilidad Infraestructura (Si / No)", "NO")
    
    pdf.set_font('Arial', 'B', 12)
    if estado == "SI":
        pdf.set_text_color(0, 128, 0)
        texto_estado = "ESTADO FINAL: VIABLE"
    else:
        pdf.set_text_color(255, 0, 0)
        texto_estado = "ESTADO FINAL: NO VIABLE"
        
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.epw, 10, texto_estado, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # -----------------------------------------------------------
    # 2. DATOS DE ENTRADA (CORREGIDO EL ERROR DE ESPACIO)
    # -----------------------------------------------------------
    pdf.chapter_title("1. Datos del Proyecto")
    pdf.set_font('Arial', '', 9)
    
    campos_clave = {
        "Equipment": "Equipo",
        "Quantity Equipment DC": "Cantidad",
        "Máx. Power DC (W)": "Potencia Unit (W)",
        "Voltage(AC or DC)": "Voltaje",
        "Power sources": "Fuentes Requeridas",
        "BTU_Label": "Disipacion Calor (BTU)", # Sin tilde para evitar líos
        "Technical Site": "Sitio"
    }
    
    # Ancho para las etiquetas (Labels)
    ancho_label = 50
    # Ancho restante para el valor
    ancho_valor = pdf.epw - ancho_label
    
    for key, label in campos_clave.items():
        val = datos_usuario.get(key, "N/A")
        texto_val = limpiar_texto(str(val))
        
        # Guardamos la posición Y actual antes de escribir
        y_actual = pdf.get_y()
        
        # 1. Escribimos la etiqueta a la izquierda
        pdf.set_x(pdf.l_margin)
        pdf.cell(ancho_label, 5, f"{label}:", border=0)
        
        # 2. Movemos el cursor a la derecha para el valor
        pdf.set_x(pdf.l_margin + ancho_label)
        
        # 3. Escribimos el valor con MultiCell (por si es largo)
        # Aquí usamos el ancho calculado explícito, evitando el error "Not enough space"
        pdf.multi_cell(w=ancho_valor, h=5, text=texto_val)
        
        # Si multi_cell saltó de línea, el cursor Y bajó. 
        # No necesitamos hacer nada extra, el siguiente ciclo empezará abajo.

    # Requerimiento de espacio (Manual para controlar lógica)
    pdf.set_x(pdf.l_margin)
    pdf.cell(ancho_label, 5, "Espacio Requerido:", border=0)
    pdf.set_x(pdf.l_margin + ancho_label)
    
    if datos_usuario.get("Requiere_Rack_Nuevo"):
        txt_espacio = f"{datos_usuario.get('Cantidad_Racks_Nuevos')} Racks Nuevos (Suelo)"
    else:
        txt_espacio = f"{datos_usuario.get('U_Requeridas')} U (Rack Existente)"
    
    pdf.multi_cell(w=ancho_valor, h=5, text=limpiar_texto(txt_espacio))
    pdf.ln()

    # -----------------------------------------------------------
    # 3. UBICACIÓN FÍSICA
    # -----------------------------------------------------------
    titulo_u = "2. Ubicacion Fisica (Suelo)" if datos_usuario.get("Requiere_Rack_Nuevo") else "2. Ubicacion Fisica (Racks)"
    pdf.chapter_title(titulo_u)
    
    if datos_usuario.get("Requiere_Rack_Nuevo"):
        msg = "Espacio en suelo disponible." if estado == "SI" else "No hay espacio en suelo."
        pdf.chapter_body(msg)
    else:
        if racks_info:
            pdf.set_font('Arial', '', 9)
            for r in racks_info:
                bloques = ", ".join([f"U{b['inicio']}-{b['fin']}" for b in r['bloques']])
                texto = f"Rack: {r['rack']} | Disp: {bloques}"
                
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(w=pdf.epw, h=5, text=limpiar_texto(texto))
        else:
            pdf.chapter_body("No se encontro espacio contiguo suficiente en ningun rack.")
    pdf.ln()

    # -----------------------------------------------------------
    # 4. RECOMENDACIÓN ELÉCTRICA
    # -----------------------------------------------------------
    pdf.chapter_title("3. Recomendacion de Conexion Electrica")
    recom = datos_informe.get("Recomendacion_Instalacion", "N/A")
    pdf.chapter_body(limpiar_texto(recom))

    # -----------------------------------------------------------
    # 5. VALIDACIONES TÉCNICAS
    # -----------------------------------------------------------
    pdf.chapter_title("4. Detalle de Validaciones")
    pdf.set_font('Courier', '', 9)
    
    checks = datos_informe.get("Checks", [])
    for check in checks:
        linea = limpiar_texto(check)
        
        # Colores según palabras clave
        if "[FALLO]" in linea or "RECHAZADO" in linea:
            pdf.set_text_color(180, 0, 0)
        elif "[ADVERTENCIA]" in linea:
            pdf.set_text_color(200, 100, 0)
        elif "[OK]" in linea:
            pdf.set_text_color(0, 100, 0)
        else:
            pdf.set_text_color(0, 0, 0)
            
        # Si la línea ya tiene etiqueta [TAG], no agregamos prefijo
        # Usamos multi_cell con ancho completo explícito
        pdf.set_x(pdf.l_margin)
        if linea.startswith("["):
            pdf.multi_cell(w=pdf.epw, h=5, text=linea)
        else:
            pdf.multi_cell(w=pdf.epw, h=5, text=f"[INFO] {linea}")

    # GUARDAR
    carpeta = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Reportes")
    if not os.path.exists(carpeta): os.makedirs(carpeta)
    
    # Nombre de archivo seguro
    nombre_limpio = "".join(x for x in str(datos_usuario.get("Equipment", "Reporte")) if x.isalnum() or x in "_- ")
    nombre_limpio = nombre_limpio.replace(" ", "_")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta, f"PRE_Factibilidad_{nombre_limpio}_{timestamp}.pdf")
    
    try:
        pdf.output(ruta)
        print(f"\n📄 Informe PDF generado correctamente: {ruta}")
        return True
    except Exception as e:
        print(f"\n❌ Error final escribiendo PDF: {e}")
        return False