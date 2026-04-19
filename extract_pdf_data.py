"""
Script para extraer todos los hooks y URLs del PDF de 1000 Viral Hooks.
El PDF tiene 2 columnas:
  - Columna izquierda (x0 < 325): texto del hook
  - Columna derecha  (x0 >= 325): URL de Instagram de referencia

Cada nueva URL en la columna derecha marca el inicio de un nuevo hook.
Guarda el resultado en hooks_data.json
"""
import pdfplumber
import json
import re

PDF_PATH = 'c:/xampp/htdocs/claude/rrss ideas/1,000 Viral Hooks (PBL).pdf'
OUTPUT_PATH = 'c:/xampp/htdocs/claude/rrss ideas/hooks_data.json'

COLUMN_DIVIDER = 325.0   # x >= 325 → columna URL
URL_START_PATTERN = re.compile(r'^https?://', re.IGNORECASE)


def build_lines(words, x_split=COLUMN_DIVIDER, y_tol=4):
    """
    Dado el listado de palabras de una página, construye dos listas de líneas:
      left_lines  → lista de (top_y, texto) para la columna izquierda
      right_lines → lista de (top_y, texto) para la columna derecha
    Las palabras se agrupan por proximidad vertical (y_tol puntos).
    """
    left = sorted([w for w in words if w['x0'] < x_split], key=lambda w: (w['top'], w['x0']))
    right = sorted([w for w in words if w['x0'] >= x_split], key=lambda w: (w['top'], w['x0']))

    def group_words(wlist):
        lines = []
        if not wlist:
            return lines
        cur_y = wlist[0]['top']
        cur_tokens = []
        for w in wlist:
            if abs(w['top'] - cur_y) <= y_tol:
                cur_tokens.append(w['text'])
            else:
                lines.append((cur_y, ' '.join(cur_tokens)))
                cur_tokens = [w['text']]
                cur_y = w['top']
        if cur_tokens:
            lines.append((cur_y, ' '.join(cur_tokens)))
        return lines

    return group_words(left), group_words(right)


def reconstruct_instagram_urls(right_lines):
    """
    Las URLs de Instagram a veces están partidas en 2-3 líneas.
    p.ej:
      https://www.instagram.com/reel/C9vqgHxuz1E/?ut
      m_source=ig_web_copy_link&igsh=MzRlODBiNWFl
      ZA==
    
    Esta función las reconstruye en objetos:
      { 'top': y_inicio, 'url': url_completa }
    """
    reconstructed = []
    current_url = None
    current_top = None

    for top, text in right_lines:
        if URL_START_PATTERN.match(text):
            # Nueva URL detectada
            if current_url:
                reconstructed.append({'top': current_top, 'url': current_url.rstrip('.,;')})
            current_url = text
            current_top = top
        elif current_url and not URL_START_PATTERN.match(text):
            # Continuación de la URL anterior (m_source=..., ZA==, etc.)
            # Solo si parece ser parte de una URL (no contiene espacios significativos)
            # o es un fragmento base64
            if re.match(r'^[A-Za-z0-9_\-=&%+./]+$', text.replace(' ', '')):
                current_url += text.replace(' ', '')
            # Si la línea tiene espacios y no parece ser URL, ignorarla
        # Líneas que no son URL y no hay URL activa → ignorar

    if current_url:
        reconstructed.append({'top': current_top, 'url': current_url.rstrip('.,;')})

    return reconstructed


def parse_pdf(pdf_path):
    """
    Extrae todos los pares (hook_template, url_referencia) del PDF.
    
    Estrategia:
    1. Por cada página, extraer líneas izquierda y derecha con sus coordenadas Y
    2. Reconstruir las URLs completas del lado derecho
    3. Usar los Y de inicio de cada URL como marcador de inicio de hook
    4. Agrupar líneas izquierdas entre marcadores consecutivos → texto del hook
    """
    all_left  = []  # lista global de (top_global, texto, pagina)
    all_right = []  # lista global de (top_global, texto)

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Leyendo {len(pdf.pages)} páginas...")
        
        # Offset acumulado para que los tops sean únicos entre páginas
        y_offset = 0
        PAGE_HEIGHT = 850  # más que la altura real para que no haya solapamientos

        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(x_tolerance=5, y_tolerance=4)
            if not words:
                y_offset += PAGE_HEIGHT
                continue

            left_lines, right_lines = build_lines(words)

            for top, text in left_lines:
                all_left.append((top + y_offset, text, page_num + 1))
            for top, text in right_lines:
                all_right.append((top + y_offset, text))

            y_offset += PAGE_HEIGHT

    # Ordenar por top global
    all_left  = sorted(all_left,  key=lambda x: x[0])
    all_right = sorted(all_right, key=lambda x: x[0])

    # Reconstruir URLs
    url_entries = reconstruct_instagram_urls([(t, txt) for t, txt in [(r[0], r[1]) for r in all_right]])

    print(f"URLs reconstruidas: {len(url_entries)}")

    # Ahora asignar líneas izquierdas a cada hook
    # Un hook cubre desde el top de su URL hasta el top de la siguiente URL
    hooks = []
    
    for i, url_entry in enumerate(url_entries):
        start_y = url_entry['top']
        end_y   = url_entries[i + 1]['top'] if i + 1 < len(url_entries) else float('inf')
        url     = url_entry['url']

        # Tomar líneas izquierdas cuyo top está en [start_y - margen, end_y)
        margin = 20  # líneas que están un poco antes del inicio de la URL
        hook_lines = [
            text for (top, text, _) in all_left
            if (start_y - margin) <= top < end_y
        ]

        hook_text = ' '.join(hook_lines).strip()

        # Limpiar el hook
        hook_text = clean_hook(hook_text)

        if len(hook_text) < 15:
            continue

        hooks.append({
            "id": len(hooks) + 1,
            "hook_template": hook_text,
            "reference_urls": [url],
            "analyzed": False,
            "videos_downloaded": []
        })

    return hooks


def clean_hook(text):
    """Limpia el texto de un hook"""
    # Eliminar cualquier URL que se haya colado
    text = re.sub(r'https?://\S+', '', text)
    # Limpiar caracteres raros de base64 que se puedan haber colado
    text = re.sub(r'\b[A-Za-z0-9+/]{20,}={0,2}\b', '', text)
    # Limpiar encabezados de sección
    text = re.sub(r'\b1000\s+VIRAL\s+HOOKS?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(EDUCATIONAL|MOTIVATIONAL|STORY|CURIOSITY|PAIN\s+POINT|RESULTS?|'
                  r'CONTROVERSIAL|CHALLENGE|COMPARISON|LISTICLE|QUESTION|HUMOR|AUTHORITY|'
                  r'TRANSFORMATION|FEAR|SOCIAL\s+PROOF|BENEFIT|HOW-TO|SECRET|WARNING|'
                  r'IDENTITY|TREND|EMOTIONAL|INSPO|LIFESTYLE|VIRAL)\s+HOOKS?:?\s*',
                  '', text, flags=re.IGNORECASE)
    # Limpiar parámetros UTM
    text = re.sub(r'm_source=\S+', '', text)
    text = re.sub(r'igsh=\S+', '', text)
    # Limpiar múltiples espacios
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


if __name__ == "__main__":
    print("=" * 60)
    print("EXTRAYENDO HOOKS Y URLs DEL PDF (MODO PRECISO)")
    print("=" * 60)

    hooks = parse_pdf(PDF_PATH)

    print(f"\n✅ Total hooks extraídos: {len(hooks)}")

    # Guardar
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(hooks, f, ensure_ascii=False, indent=2)

    print(f"✅ Guardado en: {OUTPUT_PATH}")

    # Muestra
    print("\n--- MUESTRA DE LOS PRIMEROS 15 HOOKS ---")
    for h in hooks[:15]:
        print(f"\n[{h['id']:04d}] {h['hook_template'][:130]}")
        print(f"       URL: {h['reference_urls'][0] if h['reference_urls'] else 'N/A'}")

    # Estadísticas
    with_url = sum(1 for h in hooks if h['reference_urls'])
    print(f"\n📊 Hooks con URL:    {with_url}")
    print(f"📊 Hooks sin URL:    {len(hooks) - with_url}")
