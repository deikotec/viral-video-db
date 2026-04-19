"""Debug: ver coordenadas del PDF para entender el layout"""
import pdfplumber

PDF_PATH = 'c:/xampp/htdocs/claude/rrss ideas/1,000 Viral Hooks (PBL).pdf'

with pdfplumber.open(PDF_PATH) as pdf:
    page = pdf.pages[0]
    print(f"Tamaño página: {page.width} x {page.height}")
    print()
    words = page.extract_words(x_tolerance=5, y_tolerance=5)
    
    # Mostrar primeras 60 palabras con coordenadas
    print("PALABRAS CON COORDENADAS (primeras 80):")
    for w in words[:80]:
        print(f"  x0={w['x0']:.1f} x1={w['x1']:.1f} top={w['top']:.1f} | '{w['text']}'")
