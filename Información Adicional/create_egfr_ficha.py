from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT = 'Ficha tecnica eGFR CKD EPI.docx'

NAVY = '17365D'
BLUE = 'DCEAF7'
PALE = 'F4F7FA'
GRID = 'D9D9D9'

def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tc_pr.append(shd)

def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in('w:tcMar')
    if tc_mar is None:
        tc_mar = OxmlElement('w:tcMar')
        tc_pr.append(tc_mar)
    for side, value in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = tc_mar.find(qn(f'w:{side}'))
        if node is None:
            node = OxmlElement(f'w:{side}')
            tc_mar.append(node)
        node.set(qn('w:w'), str(value))
        node.set(qn('w:type'), 'dxa')

def set_cell_border(cell, color=GRID):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in('w:tcBorders')
    if borders is None:
        borders = OxmlElement('w:tcBorders')
        tc_pr.append(borders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = qn(f'w:{edge}')
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f'w:{edge}')
            borders.append(element)
        element.set(qn('w:val'), 'single')
        element.set(qn('w:sz'), '4')
        element.set(qn('w:color'), color)

def set_font(run, size=10.5, bold=False, color='000000', italic=False):
    run.font.name = 'Aptos'
    run._element.rPr.rFonts.set(qn('w:ascii'), 'Aptos')
    run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Aptos')
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)

def p(doc, text='', style=None, bold_prefix=None):
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.line_spacing = 1.1
    if bold_prefix and text.startswith(bold_prefix):
        set_font(paragraph.add_run(bold_prefix), bold=True)
        set_font(paragraph.add_run(text[len(bold_prefix):]))
    else:
        set_font(paragraph.add_run(text))
    return paragraph

def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    for i, header in enumerate(headers):
        cell = t.rows[0].cells[i]
        set_cell_shading(cell, NAVY)
        set_cell_margins(cell)
        set_cell_border(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        r = cell.paragraphs[0].add_run(header)
        set_font(r, 9, bold=True, color='FFFFFF')
    for n, row in enumerate(rows):
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            if n % 2:
                set_cell_shading(cell, PALE)
            set_cell_margins(cell)
            set_cell_border(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            run = cell.paragraphs[0].add_run(str(value))
            set_font(run, 8.8)
            cell.paragraphs[0].paragraph_format.space_after = Pt(0)
            cell.paragraphs[0].paragraph_format.line_spacing = 1.05
    if widths:
        for row in t.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return t

def egfrcr(age, sex, scr):
    k, a, female = (0.7, -0.241, True) if sex == 'Mujer' else (0.9, -0.302, False)
    ratio = scr / k
    return 142 * min(ratio, 1) ** a * max(ratio, 1) ** -1.200 * 0.9938 ** age * (1.012 if female else 1)

def egfrcys(age, sex, scys):
    return 133 * min(scys / 0.8, 1) ** -0.499 * max(scys / 0.8, 1) ** -1.328 * 0.996 ** age * (0.932 if sex == 'Mujer' else 1)

def egfrcrcys(age, sex, scr, scys):
    k, a, female = (0.7, -0.219, True) if sex == 'Mujer' else (0.9, -0.144, False)
    ratio = scr / k
    return (135 * min(ratio, 1) ** a * max(ratio, 1) ** -0.544 *
            min(scys / 0.8, 1) ** -0.323 * max(scys / 0.8, 1) ** -0.778 *
            0.9961 ** age * (0.963 if female else 1))

doc = Document()
sec = doc.sections[0]
sec.top_margin = Cm(1.8)
sec.bottom_margin = Cm(1.8)
sec.left_margin = Cm(2.0)
sec.right_margin = Cm(2.0)

styles = doc.styles
styles['Normal'].font.name = 'Aptos'
styles['Normal']._element.rPr.rFonts.set(qn('w:ascii'), 'Aptos')
styles['Normal']._element.rPr.rFonts.set(qn('w:hAnsi'), 'Aptos')
styles['Normal'].font.size = Pt(10.5)
for name, size in [('Title', 20), ('Heading 1', 14), ('Heading 2', 11.5)]:
    st = styles[name]
    st.font.name = 'Aptos Display' if name == 'Title' else 'Aptos'
    st._element.rPr.rFonts.set(qn('w:ascii'), st.font.name)
    st._element.rPr.rFonts.set(qn('w:hAnsi'), st.font.name)
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor.from_string('000000')
    st.font.bold = True

title = doc.add_paragraph(style='Title')
title.alignment = WD_ALIGN_PARAGRAPH.LEFT
set_font(title.add_run('Ficha técnica de calculadora eGFR'), 20, bold=True)
sub = doc.add_paragraph()
set_font(sub.add_run('Creatinina, cistatina C y creatinina cistatina C'), 11, color='4D4D4D')
sub.paragraph_format.space_after = Pt(10)

p(doc, 'Esta ficha define el módulo renal N1 de MED CALC. Incluye las tres ecuaciones CKD EPI para población adulta: creatinina, cistatina C y creatinina cistatina C. La combinación de ambos biomarcadores se mostrará como la estimación preferente cuando estén disponibles.', bold_prefix='Esta ficha define')

p(doc, '1. Identificación y alcance', style='Heading 1')
table(doc, ['Campo', 'Definición'], [
    ('Identificador', 'N1 eGFR CKD EPI'),
    ('Ecuaciones incluidas', 'CKD EPI 2021 eGFRcr; CKD EPI 2012 eGFRcys; CKD EPI 2021 eGFRcr cys. Todas sin término de raza.'),
    ('Tipo de modelo', 'Ecuación de estimación de la tasa de filtrado glomerular; no es una puntuación diagnóstica.'),
    ('Finalidad', 'Estimar la función de filtración renal a partir de creatinina sérica, cistatina C o ambas, junto con edad y sexo.'),
    ('Población', 'Personas adultas de 18 años o más. No usar para población pediátrica.'),
    ('Resultado', 'eGFR en mL/min/1,73 m².'),
    ('Estado en MED CALC', 'Módulo completo: las tres ecuaciones estarán disponibles. Con Scr y Scys, se presentará eGFRcr cys como estimación preferente.'),
], [4.2, 12.8])

p(doc, '2. Entradas y validación', style='Heading 1')
table(doc, ['Variable', 'Unidad y formato', 'Validación de interfaz'], [
    ('Edad', 'Años cumplidos', 'Obligatoria. Entero; debe ser ≥18. Si no, bloquear el cálculo y mostrar que esta ecuación es para adultos.'),
    ('Sexo', 'Mujer / Hombre', 'Obligatorio. Determina los coeficientes κ y α; documentar que es una variable del modelo publicado.'),
    ('Creatinina sérica Scr', 'mg/dL', 'Obligatoria. Valor numérico positivo. Si se ofrece µmol/L, convertir: mg/dL = µmol/L ÷ 88,4 antes del cálculo.'),
    ('Cistatina C Scys', 'mg/L', 'Obligatoria para eGFRcys y eGFRcr cys. Valor numérico positivo; no necesaria si se calcula únicamente eGFRcr.'),
], [3.2, 4.0, 9.8])
p(doc, 'Requisito analítico: la creatinina debe proceder de un método estandarizado trazable a IDMS. Para las variantes con cistatina C, la determinación debe estar estandarizada frente al material ERM DA471 IFCC. La interfaz no debe afirmar que la eGFR equivale a una medición directa de la TFG.')

p(doc, '3. Algoritmos del módulo', style='Heading 1')
p(doc, 'Ecuación CKD EPI 2021 eGFRcr:')
eq = doc.add_paragraph()
eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(eq.add_run('eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^−1,200 × 0,9938^edad × 1,012 [si mujer]'), 10.5, bold=True)
eq.paragraph_format.space_after = Pt(6)
table(doc, ['Parámetro', 'Mujer', 'Hombre'], [
    ('κ', '0,7', '0,9'),
    ('α', '−0,241', '−0,302'),
    ('Factor por sexo', '1,012', '1'),
], [5.0, 6.0, 6.0])
p(doc, 'Definiciones: min(x, 1) es el menor valor entre x y 1; max(x, 1) es el mayor valor entre x y 1. Conservar precisión interna suficiente y redondear solo al presentar el resultado; la política propuesta es una cifra decimal.')

p(doc, 'Ecuación CKD EPI 2012 eGFRcys:')
eq = doc.add_paragraph()
eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(eq.add_run('eGFR = 133 × min(Scys/0,8, 1)^−0,499 × max(Scys/0,8, 1)^−1,328 × 0,996^edad × 0,932 [si mujer]'), 10.5, bold=True)
eq.paragraph_format.space_after = Pt(6)
p(doc, 'Scys es la cistatina C sérica estandarizada en mg/L. La edad se expresa en años cumplidos. La ecuación utiliza el factor 0,932 para mujeres y 1 para hombres.')

p(doc, 'Ecuación CKD EPI 2021 eGFRcr cys:')
eq = doc.add_paragraph()
eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(eq.add_run('eGFR = 135 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^−0,544 × min(Scys/0,8, 1)^−0,323 × max(Scys/0,8, 1)^−0,778 × 0,9961^edad × 0,963 [si mujer]'), 10.5, bold=True)
eq.paragraph_format.space_after = Pt(6)
table(doc, ['Parámetro', 'Mujer', 'Hombre'], [
    ('κ', '0,7', '0,9'),
    ('α', '−0,219', '−0,144'),
    ('Factor por sexo', '0,963', '1'),
], [5.0, 6.0, 6.0])
p(doc, 'Scr es la creatinina sérica estandarizada en mg/dL y Scys la cistatina C sérica estandarizada en mg/L. min y max se aplican por separado a cada biomarcador.')
p(doc, 'Cuando estén disponibles ambos biomarcadores, la ecuación combinada se mostrará como estimación preferente por su mayor precisión media frente a creatinina sola. Se conservarán también eGFRcr y eGFRcys para hacer visible cualquier discrepancia clínicamente relevante. La interpretación debe considerar los determinantes no relacionados con la TFG que pueden afectar a creatinina o cistatina C.')

p(doc, '4. Resultado y comunicación en pantalla', style='Heading 1')
table(doc, ['Elemento', 'Requisito'], [
    ('Resultado principal', 'Mostrar cada estimación calculable con una cifra decimal y la unidad mL/min/1,73 m².'),
    ('Resultado preferente', 'Si existen Scr y Scys, destacar eGFRcr cys 2021 como estimación preferente; identificar siempre qué ecuación produjo cada valor.'),
    ('Etiqueta', 'Indicar siempre “tasa de filtrado glomerular estimada (eGFR)”.'),
    ('Interpretación', 'Mostrar que es una estimación y no un diagnóstico. No generar recomendaciones terapéuticas automáticas.'),
    ('Relación con KDIGO', 'Puede reutilizarse como entrada de clasificación KDIGO si se dispone de albuminuria; esa clasificación es otro módulo y no debe confundirse con el valor eGFR.'),
    ('Dosificación', 'No presentar eGFR indexada a 1,73 m² como equivalente automático a Cockcroft Gault u otra medida exigida por una ficha farmacológica.'),
], [4.4, 12.6])

p(doc, '5. Límites y advertencias', style='Heading 1')
for text in [
    'No aplicar esta ecuación a menores de 18 años.',
    'La creatinina puede verse influida por masa muscular, dieta, estado nutricional y otros determinantes ajenos a la TFG.',
    'La cistatina C puede alterarse en contextos no relacionados con la TFG, entre ellos trastornos tiroideos no tratados y uso de corticoides; documentar esta advertencia si se habilitan sus variantes.',
    'No usar el resultado aislado para diagnosticar enfermedad renal crónica, establecer estadio clínico completo ni decidir tratamientos. Debe interpretarse junto con contexto clínico y, cuando proceda, albuminuria.',
    'MED CALC es un prototipo académico y no está destinado a uso asistencial.',
]:
    para = doc.add_paragraph(style=None)
    para.style = doc.styles['Normal']
    para.paragraph_format.left_indent = Cm(0.45)
    para.paragraph_format.first_line_indent = Cm(-0.45)
    para.paragraph_format.space_after = Pt(3)
    set_font(para.add_run('• ' + text))

p(doc, '6. Casos de prueba de regresión', style='Heading 1')

p(doc, '7. Criterios de finalización del módulo', style='Heading 1')
for text in [
    'Las tres ecuaciones están en módulos de cálculo independientes de la interfaz.',
    'El formulario valida edad adulta, unidades, números positivos y qué biomarcadores están disponibles.',
    'Las ecuaciones quedarán pendientes de pruebas de regresión hasta disponer de casos de referencia revisados.',
    'La pantalla muestra las estimaciones calculables, su ecuación de origen, unidad, significado y advertencias de interpretación.',
    'La ficha, el código y las pruebas quedan enlazados mediante el identificador N1 y la versión de la ecuación.',
]:
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(0.45)
    para.paragraph_format.first_line_indent = Cm(-0.45)
    para.paragraph_format.space_after = Pt(3)
    set_font(para.add_run('□ ' + text))

p(doc, '8. Referencias', style='Heading 1')
refs = [
    'Inker LA, Eneanya ND, Coresh J, et al. New Creatinine and Cystatin C Based Equations to Estimate GFR without Race. New England Journal of Medicine. 2021;385:1737-1749. doi:10.1056/NEJMoa2102953.',
    'Inker LA, Schmid CH, Tighiouart H, et al. Estimating Glomerular Filtration Rate from Serum Creatinine and Cystatin C. New England Journal of Medicine. 2012;367:20-29. doi:10.1056/NEJMoa1114248.',
    'National Institute of Diabetes and Digestive and Kidney Diseases. eGFR Equations for Adults. Consulta técnica de ecuaciones, unidades, estandarización y población adulta. https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/adults',
    'National Kidney Foundation. CKD EPI Creatinine Cystatin Equation 2021. https://www.kidney.org/professionals/ckd-epi-creatinine-cystatin-equation-2021',
]
for ref in refs:
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(0.5)
    para.paragraph_format.first_line_indent = Cm(-0.5)
    para.paragraph_format.space_after = Pt(4)
    set_font(para.add_run(ref), 9)

footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(footer.add_run('MED CALC | Ficha N1 | Versión 1.1 | 05/11/2026'), 8, color='666666')

doc.save(OUT)
print(OUT)
