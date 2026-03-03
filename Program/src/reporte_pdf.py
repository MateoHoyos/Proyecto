from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
import re

# ─────────────────────────────────────────────────────────────
#  PALETA CORPORATIVA
# ─────────────────────────────────────────────────────────────
C_AZUL_CORP   = colors.HexColor("#0D2B45")
C_AZUL_MED    = colors.HexColor("#1A5276")
C_AZUL_ACC    = colors.HexColor("#2E86C1")
C_VERDE       = colors.HexColor("#1E8449")
C_VERDE_CLR   = colors.HexColor("#D5F5E3")
C_ROJO        = colors.HexColor("#C0392B")
C_ROJO_CLR    = colors.HexColor("#FADBD8")
C_NARANJA     = colors.HexColor("#D35400")
C_GRIS_OSCURO = colors.HexColor("#2C3E50")
C_GRIS_MED    = colors.HexColor("#7F8C8D")
C_GRIS_LINEA  = colors.HexColor("#BDC3C7")
C_FONDO_ALT   = colors.HexColor("#F2F4F7")
C_FONDO_HDR   = colors.HexColor("#1A5276")
C_BARRA_BG    = colors.HexColor("#D6DBDF")

PAGE_W    = 8.5 * inch
MARGIN    = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


# ─────────────────────────────────────────────────────────────
#  FLOWABLES PERSONALIZADOS
# ─────────────────────────────────────────────────────────────
class BarraProgreso(Flowable):
    def __init__(self, porcentaje, ancho=160, alto=14):
        Flowable.__init__(self)
        self.porcentaje = min(max(porcentaje, 0), 100)
        self.ancho = ancho
        self.alto  = alto
        self.width  = ancho
        self.height = alto

    def draw(self):
        c     = self.canv
        radio = self.alto / 2
        c.setFillColor(C_BARRA_BG)
        c.roundRect(0, 0, self.ancho, self.alto, radio, fill=1, stroke=0)
        ancho_r = max((self.porcentaje / 100.0) * self.ancho, 0)
        if   self.porcentaje > 90: fill_color = C_ROJO
        elif self.porcentaje > 75: fill_color = C_NARANJA
        elif self.porcentaje > 50: fill_color = C_AZUL_ACC
        else:                      fill_color = C_VERDE
        c.setFillColor(fill_color)
        if ancho_r > 0:
            c.roundRect(0, 0, ancho_r, self.alto, radio, fill=1, stroke=0)
        c.setStrokeColor(C_GRIS_LINEA)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self.ancho, self.alto, radio, fill=0, stroke=1)


class BadgeEstado(Flowable):
    def __init__(self, texto, ok=True, ancho=50, alto=15):
        Flowable.__init__(self)
        self.texto = texto
        self.ok    = ok
        self.ancho = ancho
        self.alto  = alto
        self.width  = ancho
        self.height = alto

    def draw(self):
        c  = self.canv
        bg = C_VERDE if self.ok else C_ROJO
        c.setFillColor(bg)
        c.roundRect(0, 0, self.ancho, self.alto, 3, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(self.ancho / 2, (self.alto - 7) / 2 + 1, self.texto)


# ─────────────────────────────────────────────────────────────
#  ENCABEZADO Y PIE DE PÁGINA
# ─────────────────────────────────────────────────────────────
def header_footer(canv, doc):
    canv.saveState()
    page_w, page_h = LETTER

    hdr_h = 0.88 * inch
    y_hdr = page_h - hdr_h

    # Fondo azul oscuro
    canv.setFillColor(C_AZUL_CORP)
    canv.rect(0, y_hdr, page_w, hdr_h, fill=1, stroke=0)

    # Franja acento izquierda
    canv.setFillColor(C_AZUL_ACC)
    canv.rect(0, y_hdr, 0.20 * inch, hdr_h, fill=1, stroke=0)

    
    # logo Tigo
    if os.path.exists(LOGO_PATH):
        logo_w = 0.65 * inch   # ancho deseado
        logo_h = 0.55 * inch   # alto deseado
        canv.drawImage(
            LOGO_PATH,
            x=0.28 * inch,               # posición horizontal
            y=y_hdr + 0.15 * inch,       # posición vertical
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask='auto'                   # respeta transparencia en PNG
        )

    # Texto
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 14)
    canv.drawString(1.10*inch, y_hdr + 0.53*inch, "Informe de PRE-Factibilidad de Infraestructura")
    canv.setFillColor(C_GRIS_LINEA)
    canv.setFont("Helvetica", 9)
    canv.drawString(1.10*inch, y_hdr + 0.30*inch, "Analisis Tecnico de Capacidad y Disponibilidad de Red")
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 10)
    canv.drawRightString(page_w - 0.35*inch, y_hdr + 0.44*inch, f"Pag. {doc.page}")

    # Línea acento inferior
    canv.setFillColor(C_AZUL_ACC)
    canv.rect(0, y_hdr - 0.04*inch, page_w, 0.04*inch, fill=1, stroke=0)

    # Pie de página
    fy = 0.54 * inch
    canv.setStrokeColor(C_GRIS_LINEA)
    canv.setLineWidth(0.5)
    canv.line(MARGIN, fy, page_w - MARGIN, fy)
    fecha = datetime.now().strftime("%d/%m/%Y  %H:%M")
    canv.setFillColor(C_GRIS_MED)
    canv.setFont("Helvetica", 7.5)
    canv.drawString(MARGIN,               fy - 0.18*inch, f"Generado: {fecha}")
    canv.drawCentredString(page_w/2,      fy - 0.18*inch, "DOCUMENTO CONFIDENCIAL  -  USO INTERNO")
    canv.drawRightString(page_w - MARGIN, fy - 0.18*inch, "Departamento de Infraestructura TI")
    canv.restoreState()


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def limpiar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    texto = texto.replace("✅","").replace("❌","").replace("⚠️","").replace("•","-")
    return texto.encode('latin-1', 'replace').decode('latin-1').strip()

def estilo_tabla_base():
    return TableStyle([
        ('BACKGROUND',    (0,0),(-1, 0), C_FONDO_HDR),
        ('TEXTCOLOR',     (0,0),(-1, 0), colors.white),
        ('FONTNAME',      (0,0),(-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1, 0), 9),
        ('TOPPADDING',    (0,0),(-1, 0), 7),
        ('BOTTOMPADDING', (0,0),(-1, 0), 7),
        ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1),(-1,-1), 8.5),
        ('TOPPADDING',    (0,1),(-1,-1), 5),
        ('BOTTOMPADDING', (0,1),(-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, C_FONDO_ALT]),
        ('LINEBELOW',     (0,0),(-1,-1), 0.3, C_GRIS_LINEA),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ])

def titulo_seccion(numero, texto):
    t = Table([[f"{numero}.  {texto}"]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), C_AZUL_MED),
        ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
        ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,-1), 10),
        ('TOPPADDING',    (0,0),(-1,-1), 7),
        ('BOTTOMPADDING', (0,0),(-1,-1), 7),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
    ]))
    return t


# ─────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────
def generar_pdf_factibilidad(datos_informe, racks_info, datos_usuario):
    
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

    doc = SimpleDocTemplate(ruta_pdf, pagesize=LETTER,
        topMargin=1.10*inch, bottomMargin=0.90*inch,
        leftMargin=MARGIN,   rightMargin=MARGIN)
    story  = []
    styles = getSampleStyleSheet()

    normal   = ParagraphStyle('N',  parent=styles['Normal'], fontSize=9, leading=13, textColor=C_GRIS_OSCURO)
    normal_b = ParagraphStyle('NB', parent=normal, fontName='Helvetica-Bold')
    small    = ParagraphStyle('S',  parent=normal, fontSize=8, textColor=C_GRIS_MED)
    center   = ParagraphStyle('C',  parent=normal, alignment=TA_CENTER)
    wht_b    = ParagraphStyle('WB', parent=normal_b, textColor=colors.white)
    wht_b_c  = ParagraphStyle('WBC',parent=wht_b, alignment=TA_CENTER)

    # 0. BANNER
    estado      = datos_informe.get("PRE-Factibilidad Infraestructura (Si / No)","NO")
    es_aprobado = (estado == "SI")
    col_banner  = C_VERDE if es_aprobado else C_ROJO
    banner = Table([[
        Paragraph(f"<b><font size=15 color='white'>{'APROBADO' if es_aprobado else 'RECHAZADO'}</font></b>",
                  ParagraphStyle('BL', alignment=TA_LEFT, leftIndent=12)),
        Paragraph(f"<font size=8 color='white'>PRE-Factibilidad de Infraestructura</font><br/>"
                  f"<font size=7 color='white'>{datetime.now().strftime('%d/%m/%Y')}</font>",
                  ParagraphStyle('BR', alignment=TA_RIGHT, rightIndent=12)),
    ]], colWidths=[CONTENT_W*0.6, CONTENT_W*0.4])
    banner.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), col_banner),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),(-1,-1), 12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 12),
        ('LEFTPADDING',   (0,0),(0, 0),  14),
        ('RIGHTPADDING',  (1,0),(1, 0),  14),
    ]))
    story.append(banner)
    story.append(Spacer(1, 14))

    # 1. DATOS DEL PROYECTO
    story.append(titulo_seccion("1","Datos del Proyecto Solicitado"))
    story.append(Spacer(1, 6))
    keys_map = {
        "Equipment":"Equipo Solicitado","Quantity Equipment DC":"Cantidad",
        "Máx. Power DC (W)":"Potencia Max. DC (W)","Voltage(AC or DC)":"Voltaje de Operacion",
        "Power sources":"Numero de Fuentes","BTU_Label":"Disipacion de Calor",
        "Technical Site":"Sitio Tecnico",
    }
    rows_d = [[Paragraph("<b>Parametro</b>",wht_b), Paragraph("<b>Valor</b>",wht_b)]]
    for k,label in keys_map.items():
        rows_d.append([Paragraph(label,normal), Paragraph(str(datos_usuario.get(k,"—")),normal)])
    espacio = (f"{datos_usuario.get('Cantidad_Racks_Nuevos')} Racks Nuevos (Suelo)"
               if datos_usuario.get("Requiere_Rack_Nuevo")
               else f"{datos_usuario.get('U_Requeridas')} U en Rack Existente")
    rows_d.append([Paragraph("Espacio Requerido",normal), Paragraph(espacio,normal)])
    t_d = Table(rows_d, colWidths=[CONTENT_W*0.38, CONTENT_W*0.62])
    t_d.setStyle(estilo_tabla_base())
    story.append(t_d)
    story.append(Spacer(1, 14))

    # 2. RACKS
    lbl = "Ubicacion Fisica (Suelo)" if datos_usuario.get("Requiere_Rack_Nuevo") else "Disponibilidad en Racks"
    story.append(titulo_seccion("2", lbl))
    story.append(Spacer(1, 6))
    if datos_usuario.get("Requiere_Rack_Nuevo"):
        story.append(Paragraph(datos_usuario.get('Recomendacion_Instalacion_Fisica','N/A'), normal))
    elif racks_info:
        hdr_r = [Paragraph("<b>Rack</b>",wht_b), Paragraph("<b>Nomenclatura</b>",wht_b),
                 Paragraph("<b>Bloques Disponibles</b>",wht_b), Paragraph("<b>U Libres</b>",wht_b_c)]
        rows_r = []
        for r in racks_info:
            bloques_txt = ", ".join(re.sub(r'\(\d+u\)','',f"U{b['inicio']}-U{b['fin']}") for b in r['bloques'])
            u_tot = sum(b['total_u'] for b in r['bloques'])
            col_u = C_VERDE if u_tot >= 10 else C_NARANJA
            rows_r.append([Paragraph(r['rack'],normal), Paragraph(r['rack'],small),
                           Paragraph(bloques_txt,normal),
                           Paragraph(f"<b><font color='{col_u.hexval()}'>{u_tot}</font></b>",center)])
        t_r = Table([hdr_r]+rows_r, colWidths=[CONTENT_W*0.22,CONTENT_W*0.30,CONTENT_W*0.37,CONTENT_W*0.11])
        t_r.setStyle(estilo_tabla_base())
        story.append(t_r)
    else:
        story.append(Paragraph("No hay racks disponibles.", normal))
    story.append(Spacer(1, 14))

    story.append(PageBreak()) 

    # 3. CONEXIÓN PDB
    story.append(titulo_seccion("3","Recomendacion de Conexion en PDB"))
    story.append(Spacer(1, 6))
    inst_raw = datos_informe.get("Recomendacion_Instalacion","").replace("Instalación APROBADA en","La instalacion es realizable en")
    story.append(Paragraph(f"<b>{inst_raw.split(chr(10))[0]}</b>", normal_b))
    story.append(Spacer(1, 6))
    items_c = []
    for i, line in enumerate(inst_raw.split("\n")[1:]):
        m = re.search(r"Fuente ([AB]):\s*(\w+)\s*-\s*Pos\s*(\d+)", line)
        if m:
            items_c.append([Paragraph(str(i+1),center), Paragraph(m.group(2),normal),
                             Paragraph(f"Fuente {m.group(1)}",normal), Paragraph(f"Pos. {m.group(3)}",center)])
    if items_c:
        hdr_c = [Paragraph("<b>#</b>",wht_b_c), Paragraph("<b>PDB</b>",wht_b),
                 Paragraph("<b>Fuente</b>",wht_b), Paragraph("<b>Posicion</b>",wht_b_c)]
        t_c = Table([hdr_c]+items_c, colWidths=[CONTENT_W*0.08,CONTENT_W*0.32,CONTENT_W*0.32,CONTENT_W*0.28])
        t_c.setStyle(estilo_tabla_base())
        story.append(t_c)
    story.append(Spacer(1, 14))

    # 4. VALIDACIONES
    story.append(titulo_seccion("4","Detalle de Validaciones Tecnicas"))
    story.append(Spacer(1, 8))

    checks=datos_informe.get("Checks",[])
    avisos_sistema=[]; datos_barras=[]
    for check in checks:
        txt = check.replace("[OK]","").replace("[FALLO]","").replace("[ADVERTENCIA]","").replace("[INFO]","").strip()
        if "Redundancia" in txt or "Descartado" in txt or "Advertencia" in txt or "ALERTA" in check:
            tipo = "ok" if "OK" in check else ("info" if "Descartado" in txt else "fallo")
            avisos_sistema.append((tipo, txt))
        else:
            nums = re.findall(r"([\d\.]+)\s*(?:A|kVA)", txt)
            if len(nums) >= 2:
                actual,limite = float(nums[0]),float(nums[1])
                nombre_c = txt.split(":")[0].strip().replace("OK","").strip()
                status = "OK" if ("OK" in check or "OK" in txt) else "FALLO"
                unit   = "kVA" if "kVA" in check else "A"
                datos_barras.append({"nombre":nombre_c,"actual":actual,"limite":limite,"status":status,"unit":unit})

    # 4A. Avisos
    if avisos_sistema:
        story.append(Paragraph("<b>Avisos y Estado del Sistema</b>", normal_b))
        story.append(Spacer(1, 4))
        rows_av = []
        for tipo, txt in avisos_sistema:
            if tipo=="ok":    icon,tc,ic="OK",C_VERDE,C_VERDE
            elif tipo=="fallo": icon,tc,ic="!!",C_ROJO,C_ROJO
            else:             icon,tc,ic="i", C_GRIS_OSCURO,C_AZUL_ACC
            rows_av.append([
                Paragraph(f"<b><font color='{ic.hexval()}'>{icon}</font></b>",
                          ParagraphStyle('IC',alignment=TA_CENTER,fontSize=8)),
                Paragraph(f"<font color='{tc.hexval()}'>{txt}</font>", normal),
            ])
        t_av = Table(rows_av, colWidths=[0.45*inch, CONTENT_W-0.45*inch])
        t_av.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),6),
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,C_FONDO_ALT]),
            ('LINEBELOW',(0,0),(-1,-1),0.3,C_GRIS_LINEA),
            ('BOX',(0,0),(-1,-1),0.5,C_GRIS_LINEA),
        ]))
        story.append(t_av)
        story.append(Spacer(1, 12))

    # 4B. Ruta
    story.append(Paragraph("<b>Elementos de Conduccion (Ruta de Conexion)</b>", normal_b))
    story.append(Spacer(1, 4))
    ruta = datos_informe.get("Ruta_Conexion",["No se genero ruta detallada"])
    col_chk = C_VERDE.hexval() if es_aprobado else C_GRIS_MED.hexval()
    rows_rt = [[Paragraph(f"<font color='{col_chk}'><b>&#10004;</b></font>",
                       ParagraphStyle('IC2',alignment=TA_CENTER,fontSize=11)),
            Paragraph(item, normal)] for item in ruta]
    t_rt = Table(rows_rt, colWidths=[0.35*inch, CONTENT_W-0.35*inch])
    t_rt.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),4),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,C_FONDO_ALT]),
        ('LINEBELOW',(0,0),(-1,-1),0.3,C_GRIS_LINEA),
        ('BOX',(0,0),(-1,-1),0.5,C_GRIS_LINEA),
    ]))
    story.append(t_rt)
    story.append(Spacer(1, 14))

    story.append(PageBreak()) 

    # 4C. Barras
    if datos_barras:
        story.append(Paragraph("<b>Resumen de Capacidad por Componente</b>", normal_b))
        story.append(Spacer(1, 4))
        hdr_b=[Paragraph("<b>Componente</b>",wht_b),Paragraph("<b>Utilizacion</b>",wht_b_c),
               Paragraph("<b>Valores</b>",wht_b_c),Paragraph("<b>Estado</b>",wht_b_c)]
        rows_b=[hdr_b]
        for item in datos_barras:
            pct   = (item['actual']/item['limite'])*100
            barra = BarraProgreso(pct, ancho=148, alto=13)
            pct_p = Paragraph(f"<font size=7 color='{C_GRIS_MED.hexval()}'>{int(pct)}%</font>",
                              ParagraphStyle('P',alignment=TA_CENTER))
            sub = Table([[barra],[pct_p]], colWidths=[150])
            sub.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1),
            ]))
            val_p = Paragraph(f"<font size=8><b>{item['actual']}</b> / {item['limite']} {item['unit']}</font>",
                              ParagraphStyle('V',alignment=TA_CENTER,fontSize=8))
            badge = BadgeEstado(item['status'], ok=(item['status']=="OK"), ancho=46, alto=14)
            rows_b.append([Paragraph(item['nombre'],normal), sub, val_p, badge])
        ts_b = estilo_tabla_base()
        ts_b.add('ALIGN',(1,0),(3,-1),'CENTER')
        t_b = Table(rows_b, colWidths=[CONTENT_W*0.30,CONTENT_W*0.36,CONTENT_W*0.20,CONTENT_W*0.14])
        t_b.setStyle(ts_b)
        story.append(t_b)

    try:
        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        print(f"\n  PDF corporativo generado: {ruta_pdf}")
        return True, ruta_pdf
    except Exception as e:
        print(f"\n  Error generando PDF: {e}")
        return False, str(e)