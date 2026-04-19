import pdfplumber

pdf_path = 'c:/xampp/htdocs/claude/rrss ideas/1,000 Viral Hooks (PBL).pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total páginas: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages[:10]):
        text = page.extract_text()
        print(f"\n{'='*60}")
        print(f"PÁGINA {i+1}:")
        print('='*60)
        if text:
            print(text[:2000])
        else:
            print("(sin texto)")
