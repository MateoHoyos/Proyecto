
output_folder = "C:/Users/mhoyosme/Downloads"
pdf_path = "C:/Users/mhoyosme/Downloads/PF.pdf"


import fitz  # PyMuPDF
import os



os.makedirs(output_folder, exist_ok=True)

# Abrir el PDF
doc = fitz.open(pdf_path)

for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    
    # renderizar página como imagen
    pix = page.get_pixmap(dpi=300)
    
    output_file = f"{output_folder}/pagina_{page_num+1}.png"
    pix.save(output_file)

print("Conversión completada")