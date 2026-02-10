from fpdf import FPDF
from datetime import datetime
import os

class PDFReporte(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(self.epw, 10, 'Informe de Factibilidad Tecnica - Nodo IDEO', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('Arial', 'I', 10)
        self.cell(self.epw, 10, f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M")}', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(self.epw, 10, f'Pagina {self.page_no()}', align='C')
    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.set_x(self.l_margin)
        self.cell(self.epw, 10, label, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
    def chapter_body(self, text):
        self.set_font('Arial', '', 11)
        texto_seguro = str(text).encode('latin-1', 'replace').decode('latin-1')
        self.set_x(self.l_margin)
        self.multi_cell(w=self.epw, h=6, text=texto_seguro)
        self.ln()

def limpiar_texto_para_pdf(texto):
    if not isinstance(texto, str): return str(texto)
    texto_seguro = texto.replace("✅", "").replace("❌", "").replace("⚠️", "").replace("•", "-")
    return texto_seguro.encode('latin-1', 'replace').decode('latin-1').strip()

def generar_pdf_factibilidad(datos_informe, racks_info, datos_usuario):
    pdf = PDFReporte()
    pdf.add_page()
    
    # 1. ESTADO
    estado = datos_informe.get("PRE-Factibilidad Infraestructura (Si / No)", "NO")
    pdf.set_font('Arial', 'B', 14)
    if estado == "SI":
        pdf.set_text_color(0, 128, 0)
        texto_estado = "ESTADO FINAL: APROBADO"
    else:
        pdf.set_text_color(255, 0, 0)
        texto_estado = "ESTADO FINAL: RECHAZADO"
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.epw, 10, texto_estado, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # 2. DATOS DE ENTRADA (NUEVO BLOQUE)
    pdf.chapter_title("1. Datos del Proyecto Solicitado")
    pdf.set_font('Courier', '', 10)
    for k, v in datos_usuario.items():
        pdf.cell(w=90, h=6, text=f"{k}:", border=0)
        pdf.cell(w=0, h=6, text=f"{v}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln()

    # 3. UBICACIÓN FÍSICA (TODOS LOS RACKS)
    if racks_info:
        pdf.chapter_title("2. Opciones de Ubicacion Fisica (Racks)")
        pdf.set_font('Arial', '', 10)
        
        # CORRECCIÓN AQUÍ: Validamos que r['rack'] tenga datos
        for r in racks_info:
            nombre_rack = str(r.get('rack', 'Sin Nombre'))
            bloques = r.get('bloques', [])
            
            if bloques:
                bloques_str = ", ".join([f"U{b['inicio']}->U{b['fin']}" for b in bloques])
                texto = f"Rack: {nombre_rack} | Espacios: {bloques_str}"
                
                # Forzamos posición X antes de escribir
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(w=pdf.epw, h=6, text=limpiar_texto_para_pdf(texto))
        pdf.ln()
    else:
        pdf.chapter_title("2. Ubicacion Fisica")
        pdf.chapter_body("No hay espacio fisico disponible.")

    # 4. INSTRUCCIONES ELÉCTRICAS
    pdf.chapter_title("3. Instrucciones de Conexion Electrica")
    # Aseguramos que se imprima el detalle completo de PDB (Fuente A Pos X...)
    instruccion = datos_informe.get("Recomendacion_Instalacion", "Sin instruccion")
    pdf.set_font('Courier', '', 10)
    pdf.multi_cell(w=pdf.epw, h=6, text=limpiar_texto_para_pdf(instruccion))
    pdf.ln()

    # 5. VALIDACIONES TÉCNICAS
    pdf.chapter_title("4. Detalle de Validaciones (Ingenieria)")
    pdf.set_font('Courier', '', 10)
    checks = datos_informe.get("Checks", [])
    for check in checks:
        prefijo = "[INFO] "
        if "❌" in check:
            pdf.set_text_color(180, 0, 0); prefijo = "[FALLO] "
        elif "⚠️" in check:
            pdf.set_text_color(200, 100, 0); prefijo = "[ALERTA] "
        elif "✅" in check:
            pdf.set_text_color(0, 100, 0); prefijo = "[OK]    "
        else: pdf.set_text_color(0, 0, 0)
        
        mensaje = limpiar_texto_para_pdf(check)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w=pdf.epw, h=6, text=f"{prefijo}{mensaje}")

    # GUARDAR
    carpeta = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Reportes")
    if not os.path.exists(carpeta): os.makedirs(carpeta)
    nombre_limpio = str(datos_usuario.get("Equipment","Reporte")).replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta, f"Reporte_{nombre_limpio}_{timestamp}.pdf")
    pdf.output(ruta)
    print(f"\n📄 Informe PDF: {ruta}")