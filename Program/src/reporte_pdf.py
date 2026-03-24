"""
reporte_pdf.py — Generador de Informes PDF de Pre-Factibilidad
──────────────────────────────────────────────────────────────────────────────
Este módulo genera el informe técnico en formato PDF que resume los resultados
del análisis de pre-factibilidad para la instalación de un nuevo equipo.

El informe se produce automáticamente cuando el usuario hace clic en
"Descargar Informe PDF" en el panel_evaluador.py, ya sea para un resultado
aprobado o rechazado.

Librería utilizada: ReportLab (reportlab)
    Permite construir documentos PDF desde código Python, controlando
    el layout, estilos, tablas y gráficos de forma programática.

Contenido del informe generado:
    1. Encabezado con logo, nombre del nodo y fecha de generación
    2. Datos del equipo evaluado (nombre, potencia, fuentes, U requeridas)
    3. Resultado del análisis de espacio físico
       - Si requiere rack nuevo: plano gráfico de la sala con los racks
         actuales y los propuestos (generado por la clase MapaRacks)
       - Si va en rack existente: tabla con los bloques de U disponibles
    4. Resultado del análisis eléctrico y de protecciones
       - Lista de todos los checks con su resultado [OK] / [FALLO] / [ADVERTENCIA]
       - Código de color por severidad
    5. Veredicto final: APROBADO o RECHAZADO
    6. Ruta de conexión eléctrica propuesta (si fue aprobado)

Clase principal:
    MapaRacks(Flowable): elemento gráfico personalizado de ReportLab que
    dibuja el plano de la sala con las dos filas de racks. Usa colores
    diferenciados para racks instalados, posiciones libres y racks nuevos.

Función principal:
    generar_pdf_factibilidad(res_energia, racks_pdf, solicitud)
    → Retorna (exito: bool, ruta_del_archivo: str)
──────────────────────────────────────────────────────────────────────────────
"""

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
#  FLOWABLE: MAPA GRÁFICO DE RACKS (Ubicación Física - Suelo)
# ─────────────────────────────────────────────────────────────
class MapaRacks(Flowable):
    """
    Elemento gráfico personalizado de ReportLab que dibuja el plano de la sala.

    Hereda de Flowable para poder insertarse dentro del flujo del documento PDF
    como cualquier otro elemento (párrafo, tabla, espacio).

    Dibuja las dos filas de racks del nodo usando un sistema de coordenadas
    propio. Cada rack se representa como un rectángulo con colores distintos:

        Gris  (#cbd5e1) → Rack ya instalado
        Verde (#D5F5E3) → Posición libre disponible
        Amarillo (#fde68a) → Rack nuevo propuesto para este equipo

    También dibuja los elementos de infraestructura del nodo (rectificadores,
    PDB, ML) como referencia visual para el técnico.

    Parámetros:
        racks_f1       : lista de IDs de racks instalados en fila 1
        racks_f2       : lista de IDs de racks instalados en fila 2
        max_f1         : capacidad máxima de la fila 1
        max_f2         : capacidad máxima de la fila 2
        rack_nuevo_ids : lista de IDs de los racks nuevos propuestos
        resumen_txt    : texto de resumen que aparece al pie del plano
        ancho          : ancho disponible en el documento (CONTENT_W)
    """
    _C_INST_BG  = colors.HexColor('#cbd5e1')   # Fondo rack instalado
    _C_INST_BD  = colors.HexColor('#475569')   # Borde rack instalado
    _C_LIBRE_BG = colors.HexColor('#D5F5E3')   # Fondo posición libre
    _C_LIBRE_BD = colors.HexColor('#1E8449')   # Borde posición libre
    _C_NUEVO_BG = colors.HexColor('#fde68a')   # Fondo rack nuevo propuesto
    _C_NUEVO_BD = colors.HexColor('#d97706')   # Borde rack nuevo propuesto
    _C_INF_BG   = colors.HexColor('#e0f2fe')   # Fondo elemento infraestructura
    _C_INF_BD   = colors.HexColor('#0284c7')   # Borde elemento infraestructura
    _C_TXT_DK   = colors.HexColor('#1e293b')
    _C_TXT_ME   = colors.HexColor('#475569')
    _C_TXT_SU   = colors.HexColor('#64748b')
    _C_SALA     = colors.HexColor('#f8fafc')   # Fondo de la sala
    _C_BORDE    = colors.HexColor('#94a3b8')   # Borde exterior del plano
    _C_ESC      = colors.HexColor('#e2e8f0')

    def __init__(self, racks_f1, racks_f2, max_f1=6, max_f2=10,
                 rack_nuevo_ids=None, resumen_txt=None, ancho=None):
        Flowable.__init__(self)
        self.racks_f1       = racks_f1 or []
        self.racks_f2       = racks_f2 or []
        self.max_f1         = max_f1
        self.max_f2         = max_f2
        if isinstance(rack_nuevo_ids, str):
            self.rack_nuevo_ids = [rack_nuevo_ids] if rack_nuevo_ids else []
        else:
            self.rack_nuevo_ids = rack_nuevo_ids or []
        self.resumen_txt    = resumen_txt

        self._RH  = 54; self._RG  = 6
        self._IH  = 30; self._IW  = 54
        self._PAD = 12; self._TH  = 16
        self._EH  = 13; self._LH  = 20; self._SEP = 5
        self._RES_H = 18 if resumen_txt else 0

        aw = ancho or CONTENT_W
        self._aw = aw
        max_fila = max(max_f1, max_f2)
        self._rw = min((aw - self._PAD*2 - self._RG*(max_fila-1)) / max_fila, 66)

        self._altura = (self._TH + self._SEP
                        + self._EH + self._RH + self._SEP
                        + self._EH + self._RH + self._SEP
                        + self._LH
                        + self._PAD * 2
                        + self._RES_H)

        self.width  = aw
        self.height = self._altura

    def _rack(self, c, x, y, rack_id, estado):
        """Dibuja un rack individual con el color correspondiente a su estado."""
        w, h = self._rw, self._RH
        col  = {
            'instalado': (self._C_INST_BG, self._C_INST_BD),
            'libre':     (self._C_LIBRE_BG, self._C_LIBRE_BD),
            'nuevo':     (self._C_NUEVO_BG, self._C_NUEVO_BD)
        }
        bg, bd = col.get(estado, (self._C_LIBRE_BG, self._C_LIBRE_BD))
        c.setFillColor(bg); c.setStrokeColor(bd); c.setLineWidth(1.6)
        c.roundRect(x, y, w, h, radius=5, fill=1, stroke=1)
        if rack_id:
            c.setFillColor(self._C_TXT_DK); c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + w/2, y + h/2 - 4, rack_id)
            if estado == 'nuevo':
                c.setFont("Helvetica", 6); c.setFillColor(self._C_NUEVO_BD)
                c.drawCentredString(x + w/2, y + h/2 - 14, "NUEVO")
        else:
            c.setFillColor(self._C_LIBRE_BD); c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(x + w/2, y + h/2 - 7, "+")

    def _infra(self, c, x, y, l1, l2=""):
        """Dibuja un elemento de infraestructura (rectificador, PDB, ML)."""
        w, h = self._IW, self._IH
        c.setFillColor(self._C_INF_BG); c.setStrokeColor(self._C_INF_BD); c.setLineWidth(1)
        c.roundRect(x, y, w, h, radius=3, fill=1, stroke=1)
        c.setFillColor(colors.HexColor('#0369a1')); c.setFont("Helvetica-Bold", 6.5)
        if l2:
            c.drawCentredString(x+w/2, y+h-11, l1)
            c.setFont("Helvetica", 6); c.drawCentredString(x+w/2, y+h-21, l2)
        else:
            c.drawCentredString(x+w/2, y+h/2-3, l1)

    def draw(self):
        """
        Método principal de ReportLab que dibuja el plano completo en el canvas PDF.
        Se llama automáticamente cuando el documento se construye.
        """
        c   = self.canv
        x   = 0; aw = self._aw
        PAD = self._PAD; SEP = self._SEP
        RH  = self._RH;  EH  = self._EH
        TH  = self._TH;  LH  = self._LH

        y_top = self._altura

        # Recuadro exterior de la sala
        c.setFillColor(self._C_SALA); c.setStrokeColor(self._C_BORDE); c.setLineWidth(1.2)
        c.roundRect(x, 0, aw, self._altura, radius=6, fill=1, stroke=1)

        # Banda de título azul en la parte superior
        c.setFillColor(colors.HexColor('#1A5276'))
        c.roundRect(x, y_top-TH, aw, TH, radius=6, fill=1, stroke=0)
        c.rect(x, y_top-TH, aw, TH/2, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 8.5)
        c.drawString(x+8, y_top-TH+4, "UBICACION FISICA - PLANO DE SALA (Recomendacion)")
        n_inst = len(self.racks_f1) + len(self.racks_f2)
        n_lib  = (self.max_f1-len(self.racks_f1)) + (self.max_f2-len(self.racks_f2))
        c.setFont("Helvetica", 7.5)
        c.drawRightString(x+aw-8, y_top-TH+4,
                          f"{n_inst} instalados  |  {n_lib} disponibles  |  {self.max_f1+self.max_f2} max")

        cy = y_top - TH - SEP
        nuevo_counter = list(self.rack_nuevo_ids)

        def dibujar_fila(ids, max_r, label, cur_y):
            """Dibuja una fila completa de racks con su etiqueta."""
            n_l = max_r - len(ids)
            c.setFillColor(self._C_TXT_ME); c.setFont("Helvetica-Bold", 6.5)
            c.drawString(x+PAD, cur_y-EH+3,
                         f"{label}   ({len(ids)} instalados  ·  {n_l} libres  ·  max {max_r})")
            cur_y -= EH; xi = x + PAD
            for i in range(max_r):
                if i < len(ids):
                    rid    = ids[i]
                    estado = 'nuevo' if rid in self.rack_nuevo_ids else 'instalado'
                else:
                    # Posición libre: verificar si hay rack nuevo propuesto para aquí
                    if nuevo_counter:
                        rid    = nuevo_counter.pop(0)
                        estado = 'nuevo'
                    else:
                        rid    = None
                        estado = 'libre'
                self._rack(c, xi, cur_y - RH, rid, estado)
                xi += self._rw + self._RG
            return cur_y - RH - SEP

        cy = dibujar_fila(self.racks_f1, self.max_f1, "FILA 1", cy)
        cy = dibujar_fila(self.racks_f2, self.max_f2, "FILA 2", cy)

        # Leyenda de colores
        cy -= SEP
        elementos_leyenda = [
            (self._C_INST_BG, self._C_INST_BD, "Instalado"),
            (self._C_LIBRE_BG, self._C_LIBRE_BD, "Disponible"),
            (self._C_NUEVO_BG, self._C_NUEVO_BD, "Nuevo propuesto"),
        ]
        lx = x + PAD
        for bg, bd, txt in elementos_leyenda:
            c.setFillColor(bg); c.setStrokeColor(bd); c.setLineWidth(0.8)
            c.rect(lx, cy - 8, 14, 10, fill=1, stroke=1)
            c.setFillColor(self._C_TXT_ME); c.setFont("Helvetica", 6.5)
            c.drawString(lx + 17, cy - 5, txt)
            lx += 90

        # Barra de resumen al pie si hay texto
        if self.resumen_txt:
            c.setFillColor(colors.HexColor('#f0fdf4')); c.setStrokeColor(colors.HexColor('#16a34a'))
            c.setLineWidth(0.8)
            c.roundRect(x+PAD, 4, aw-PAD*2, self._RES_H-2, radius=3, fill=1, stroke=1)
            c.setFillColor(colors.HexColor('#15803d')); c.setFont("Helvetica", 6.5)
            c.drawString(x+PAD+4, 9, self.resumen_txt[:120])


# ─────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DEL DOCUMENTO
# ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = LETTER
MARGIN         = 0.65 * inch
CONTENT_W      = PAGE_W - 2 * MARGIN


def _limpiar(txt):
    """Elimina caracteres de control que podrían romper el XML de ReportLab."""
    if not isinstance(txt, str):
        txt = str(txt)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', txt)


def generar_pdf_factibilidad(res_energia: dict, racks_pdf: list, solicitud: dict):
    """
    Genera el informe PDF completo de pre-factibilidad técnica.

    Construye el documento usando el motor de flujo de ReportLab (Platypus),
    que organiza automáticamente los elementos en páginas según su tamaño.

    Parámetros:
        res_energia : dict con los checks eléctricos y el veredicto
                      (resultado de analisis_potencia.evaluar_solicitud)
        racks_pdf   : list con los racks viables y sus bloques de U libres
                      (resultado de racks.buscar_espacio_en_racks)
        solicitud   : dict completo de la solicitud evaluada
                      (resultado de gestor_solicitudes.obtener_detalle_solicitud)

    Retorna:
        (True, ruta_pdf)  si el PDF se generó correctamente
        (False, mensaje)  si ocurrió un error durante la generación
    """
    try:
        # Definir nombre y ruta del archivo PDF
        equipo_limpio = re.sub(r'[^\w\s-]', '', str(solicitud.get('Equipment', 'Equipo')))
        equipo_limpio = equipo_limpio.replace(' ', '_')[:40]
        id_sol        = solicitud.get('ID', 'X')
        nombre_pdf    = f"PRE_Factibilidad_{equipo_limpio}_ID{id_sol}.pdf"
        carpeta       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Reportes")
        os.makedirs(carpeta, exist_ok=True)
        ruta_pdf      = os.path.join(carpeta, nombre_pdf)

        # Crear el documento con márgenes definidos
        doc   = SimpleDocTemplate(ruta_pdf, pagesize=LETTER,
                                  leftMargin=MARGIN, rightMargin=MARGIN,
                                  topMargin=MARGIN, bottomMargin=MARGIN)
        story = []   # Lista de elementos del documento (flujo de contenido)
        styles = getSampleStyleSheet()

        # Definir estilos personalizados
        estilo_titulo = ParagraphStyle(
            'Titulo', parent=styles['Title'],
            fontSize=16, textColor=colors.HexColor('#1A5276'),
            spaceAfter=4
        )
        estilo_subtitulo = ParagraphStyle(
            'Subtitulo', parent=styles['Heading2'],
            fontSize=11, textColor=colors.HexColor('#1A5276'),
            spaceBefore=10, spaceAfter=4
        )
        estilo_normal = ParagraphStyle(
            'Normal2', parent=styles['Normal'],
            fontSize=9, spaceAfter=3
        )
        estilo_ok   = ParagraphStyle('OK',   parent=estilo_normal,
                                     textColor=colors.HexColor('#1E8449'))
        estilo_warn = ParagraphStyle('WARN', parent=estilo_normal,
                                     textColor=colors.HexColor('#D35400'))
        estilo_fail = ParagraphStyle('FAIL', parent=estilo_normal,
                                     textColor=colors.HexColor('#C0392B'))

        # ── ENCABEZADO ────────────────────────────────────────────────────
        story.append(Paragraph("INFORME DE PRE-FACTIBILIDAD TÉCNICA", estilo_titulo))
        story.append(Paragraph(f"Nodo: IDEO CALI — COL-VAL-CLO-IDO", estilo_normal))
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_normal))
        story.append(Spacer(1, 0.15*inch))

        # ── DATOS DEL EQUIPO ──────────────────────────────────────────────
        story.append(Paragraph("1. Datos del Equipo Solicitado", estilo_subtitulo))

        datos_tabla = [
            ["Campo", "Valor"],
            ["Equipo",           _limpiar(solicitud.get('Equipment', ''))],
            ["ID Solicitud",     _limpiar(solicitud.get('ID', ''))],
            ["Sitio Técnico",    _limpiar(solicitud.get('Technical Site', ''))],
            ["Cantidad",         str(solicitud.get('Quantity Equipment DC', 1))],
            ["Potencia Máx DC",  f"{solicitud.get('Máx. Power DC (W)', 0)} W"],
            ["Fuentes DC",       str(solicitud.get('Power sources', 1))],
            ["Disipación",       _limpiar(solicitud.get('BTU_Label', ''))],
        ]

        if solicitud.get('Requiere_Rack_Nuevo'):
            datos_tabla.append(["Espacio", f"{solicitud.get('Cantidad_Racks_Nuevos', 0)} rack(s) nuevos"])
        else:
            datos_tabla.append(["Espacio", f"{solicitud.get('U_Requeridas', 0)} U en rack existente"])

        t = Table(datos_tabla, colWidths=[CONTENT_W*0.35, CONTENT_W*0.65])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A5276')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8.5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [colors.HexColor('#f8fafc'), colors.white]),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING',(0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.12*inch))

        # ── ANÁLISIS DE ESPACIO FÍSICO ────────────────────────────────────
        story.append(Paragraph("2. Análisis de Espacio Físico", estilo_subtitulo))

        msg_espacio = _limpiar(solicitud.get('Recomendacion_Instalacion_Fisica', 'Sin evaluación'))

        if solicitud.get('Requiere_Rack_Nuevo'):
            # Mostrar el plano gráfico de la sala con MapaRacks
            racks_f1    = solicitud.get('Racks_Instalados_F1', [])
            racks_f2    = solicitud.get('Racks_Instalados_F2', [])
            max_f1      = solicitud.get('Max_Racks_F1', 6)
            max_f2      = solicitud.get('Max_Racks_F2', 10)
            nuevos_ids  = solicitud.get('Racks_Nuevos_Propuestos', [])

            story.append(MapaRacks(
                racks_f1       = racks_f1,
                racks_f2       = racks_f2,
                max_f1         = max_f1,
                max_f2         = max_f2,
                rack_nuevo_ids = nuevos_ids,
                resumen_txt    = msg_espacio,
                ancho          = CONTENT_W
            ))
        else:
            # Mostrar tabla con los bloques de U disponibles
            if racks_pdf:
                story.append(Paragraph(msg_espacio, estilo_ok))
                tabla_racks = [["Rack", "Bloques Disponibles"]]
                for r in racks_pdf:
                    bloques_str = ", ".join([f"U{b['inicio']}-U{b['fin']}" for b in r['bloques']])
                    tabla_racks.append([r['rack'], bloques_str])

                t_racks = Table(tabla_racks, colWidths=[CONTENT_W*0.3, CONTENT_W*0.7])
                t_racks.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A5276')),
                    ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                    ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE',   (0,0), (-1,-1), 8.5),
                    ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1),
                     [colors.HexColor('#f0fdf4'), colors.white]),
                    ('LEFTPADDING',(0,0), (-1,-1), 8),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(t_racks)
            else:
                story.append(Paragraph(f"⚠️ {msg_espacio}", estilo_warn))

        story.append(Spacer(1, 0.12*inch))

        # ── ANÁLISIS ELÉCTRICO ────────────────────────────────────────────
        story.append(Paragraph("3. Análisis Eléctrico y de Protecciones", estilo_subtitulo))

        for check in res_energia.get('Checks', []):
            check_limpio = _limpiar(check)
            if   "[FALLO]"       in check: story.append(Paragraph(f"❌ {check_limpio}", estilo_fail))
            elif "[ADVERTENCIA]" in check: story.append(Paragraph(f"⚠️ {check_limpio}", estilo_warn))
            elif "[OK]"          in check: story.append(Paragraph(f"✅ {check_limpio}", estilo_ok))
            else:                          story.append(Paragraph(check_limpio, estilo_normal))

        story.append(Spacer(1, 0.15*inch))

        # ── VEREDICTO FINAL ───────────────────────────────────────────────
        story.append(Paragraph("4. Veredicto Final", estilo_subtitulo))

        energia_ok  = res_energia.get("PRE-Factibilidad Infraestructura (Si / No)") == "SI"
        espacio_ok  = "Espacio" not in msg_espacio.upper() or "OK" in msg_espacio.upper() or racks_pdf

        if energia_ok:
            estilo_veredicto = ParagraphStyle(
                'Veredicto', parent=styles['Normal'],
                fontSize=13, fontName='Helvetica-Bold',
                textColor=colors.HexColor('#1E8449'),
                borderPad=8, backColor=colors.HexColor('#D5F5E3'),
                borderColor=colors.HexColor('#1E8449'), borderWidth=1.5,
                borderRadius=6, spaceAfter=8
            )
            story.append(Paragraph("✅ PRE-FACTIBILIDAD TÉCNICA: APROBADA", estilo_veredicto))
            rec = _limpiar(res_energia.get('Recomendacion_Instalacion', ''))
            story.append(Paragraph(f"<b>Instrucción de instalación:</b> {rec}", estilo_ok))
        else:
            estilo_veredicto = ParagraphStyle(
                'Veredicto', parent=styles['Normal'],
                fontSize=13, fontName='Helvetica-Bold',
                textColor=colors.HexColor('#C0392B'),
                borderPad=8, backColor=colors.HexColor('#FADBD8'),
                borderColor=colors.HexColor('#C0392B'), borderWidth=1.5,
                borderRadius=6, spaceAfter=8
            )
            story.append(Paragraph("❌ PRE-FACTIBILIDAD TÉCNICA: RECHAZADA", estilo_veredicto))
            story.append(Paragraph(
                "La instalación no puede realizarse con la infraestructura actual. "
                "Revisar los puntos marcados como FALLO en la sección anterior.", estilo_fail))

        # ── RUTA DE CONEXIÓN (si fue aprobado) ────────────────────────────
        ruta = res_energia.get('Ruta_Conexion', [])
        if ruta:
            story.append(Spacer(1, 0.12*inch))
            story.append(Paragraph("5. Ruta de Conexión Eléctrica Propuesta", estilo_subtitulo))
            for paso in ruta:
                story.append(Paragraph(f"• {_limpiar(paso)}", estilo_normal))

        # ── PIE DE PÁGINA ─────────────────────────────────────────────────
        story.append(Spacer(1, 0.2*inch))
        estilo_pie = ParagraphStyle('Pie', parent=styles['Normal'],
                                    fontSize=7, textColor=colors.HexColor('#94a3b8'),
                                    alignment=1)
        story.append(Paragraph(
            "Documento generado automáticamente por el Sistema IDEO — "
            "Gerencia de Infraestructura — Tigo Colombia",
            estilo_pie
        ))

        # Construir el PDF
        doc.build(story)
        return True, ruta_pdf

    except Exception as e:
        return False, f"Error generando PDF: {e}"