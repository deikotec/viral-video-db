"""
Script principal para generar ideas de video basadas en la base de datos viral en Supabase.

Uso interactivo:
  python generate_video_idea.py

Uso con argumentos:
  python generate_video_idea.py --company "Clínica dental en Bogotá" --goal "Conseguir más pacientes" --platform Instagram

Opciones avanzadas:
  --nicho NICHO         Filtrar referencias por nicho específico
  --patron PATRON       Filtrar por patrón viral (antes/después, tutorial, etc)
  --num-refs N          Número de videos de referencia a incluir (default: 5)
  --output FILE         Guardar resultado en un archivo JSON
  --list-nichos         Listar todos los nichos disponibles en la BD
"""
import json
import argparse
from datetime import datetime
from config import GEMINI_API_KEY, GEMINI_MODEL, IDEA_GENERATION_PROMPT
from db import get_db

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def setup_gemini():
    """Configura Gemini para generación de ideas"""
    if not GEMINI_AVAILABLE:
        raise ImportError("Instala google-generativeai: pip install google-generativeai")

    if GEMINI_API_KEY == "TU_GEMINI_API_KEY_AQUI":
        raise ValueError("Configura GEMINI_API_KEY en config.py")

    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


def get_available_nichos(db):
    """Lista todos los nichos disponibles en Supabase"""
    result = db.rpc('get_nichos_stats', {'p_limit': 50}).execute()
    return [(r['nicho'], r['total']) for r in result.data]


def get_available_patrones(db):
    """Lista todos los patrones virales disponibles en Supabase"""
    result = db.rpc('get_patrones_stats', {'p_limit': 50}).execute()
    return [(r['patron_viral'], r['total']) for r in result.data]


def search_relevant_hooks(db, nicho=None, patron=None, num_refs=5):
    """
    Busca los hooks/análisis más relevantes para el contexto de la empresa.
    Usa RPC con ORDER BY RANDOM() y filtros opcionales.
    """
    # Verificar si hay análisis disponibles
    count_result = db.table('video_analysis').select('id', count='exact').limit(0).execute()
    num_analyzed = count_result.count or 0

    if num_analyzed == 0:
        # Sin análisis: usar hooks crudos del PDF
        print("ℹ️  No hay videos analizados aún. Usando hooks del PDF como referencia base.")
        result = db.rpc('get_random_hooks', {'p_limit': num_refs * 3}).execute()
        hooks_data = [
            {'id': r['id'], 'hook_template': r['hook_template'],
             'url': r['reference_url'], 'analisis': None}
            for r in result.data
        ]
        return hooks_data[:num_refs]

    # Búsqueda con filtros y orden aleatorio via RPC
    params = {
        'p_nicho':  nicho,
        'p_patron': patron,
        'p_limit':  num_refs * 3,
    }
    result = db.rpc('search_hooks_random', params).execute()
    rows = result.data

    if not rows and (nicho or patron):
        # Si no hay resultados con filtros, relajar la búsqueda
        print("ℹ️  No se encontraron análisis con esos filtros. Usando todos disponibles.")
        result = db.rpc('search_hooks_random', {'p_nicho': None, 'p_patron': None, 'p_limit': num_refs * 3}).execute()
        rows = result.data

    hooks_data = []
    for r in rows:
        # analisis_json_completo ya es un dict (JSONB en Supabase, no necesita json.loads)
        hooks_data.append({
            'id':            r['id'],
            'hook_template': r['hook_template'],
            'url':           r['reference_url'],
            'analisis':      r.get('analisis_json_completo'),
            'nicho':         r.get('nicho'),
            'patron_viral':  r.get('patron_viral'),
            'por_que_viral': r.get('por_que_es_viral'),
            'emocion':       r.get('emocion_principal'),
            'audiencia':     r.get('audiencia_objetivo'),
        })

    return hooks_data[:num_refs]


def format_references_for_prompt(hooks_data):
    """Formatea los videos de referencia para incluirlos en el prompt"""
    refs = []

    for i, hook in enumerate(hooks_data, 1):
        ref = f"\n--- REFERENCIA #{i} ---"
        ref += f"\nHook template: {hook['hook_template']}"
        ref += f"\nURL de referencia: {hook.get('url', 'N/A')}"

        if hook.get('analisis'):
            a = hook['analisis']
            estrategia = a.get('estrategia_viral', {})
            guion      = a.get('guion', {})
            hook_data  = a.get('hook', {})
            prod       = a.get('produccion', {})
            audio      = a.get('audio', {})
            estructura = a.get('estructura_narrativa', {})

            ref += f"\nNicho: {estrategia.get('nicho', 'N/A')}"
            ref += f"\nPatrón viral: {estrategia.get('patron_viral', 'N/A')}"
            ref += f"\nPor qué es viral: {estrategia.get('por_que_es_viral', 'N/A')}"
            ref += f"\nEmoción principal: {estrategia.get('emocion_principal', 'N/A')}"
            ref += f"\nAudiencia: {estrategia.get('audiencia_objetivo', 'N/A')}"
            ref += f"\nHook visual: {hook_data.get('elemento_visual_hook', 'N/A')}"
            ref += f"\nTécnica hook: {hook_data.get('tecnica', 'N/A')}"
            ref += f"\nRitmo: {estructura.get('ritmo', 'N/A')}"
            ref += f"\nEscenario: {prod.get('escenario', 'N/A')}"
            ref += f"\nIluminación: {prod.get('iluminacion', 'N/A')}"
            ref += f"\nMúsica: {audio.get('musica', {}).get('genero', 'N/A')}"
            ref += f"\nGuion (extracto): {str(guion.get('texto_completo', 'N/A'))[:200]}..."
        else:
            ref += "\n(Sin análisis detallado - video pendiente de análisis)"

        refs.append(ref)

    return "\n".join(refs)


def generate_idea_with_gemini(model, company_context, video_objective, platform, hooks_data):
    """Genera la idea de video usando Gemini"""
    references_text = format_references_for_prompt(hooks_data)

    prompt = IDEA_GENERATION_PROMPT.format(
        num_references=len(hooks_data),
        company_context=company_context,
        video_objective=video_objective,
        platform=platform,
        reference_videos=references_text
    )

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "response_mime_type": "application/json"
        }
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"respuesta_texto": response.text}


def save_idea_to_db(db, company_context, video_objective, platform, hooks_used, idea_json):
    """Guarda la idea generada en el historial en Supabase"""
    hook_ids = [h['id'] for h in hooks_used]

    result = db.table('ideas_generadas').insert({
        'empresa_contexto': company_context,
        'objetivo_video':   video_objective,
        'plataforma':       platform,
        'hook_referencias': hook_ids,   # JSONB: lista directa
        'idea_json':        idea_json,  # JSONB: dict directamente
    }).execute()

    return result.data[0]['id']


def print_idea_pretty(idea):
    """Imprime la idea de video de forma legible"""
    print("\n" + "🎬" * 30)
    print("   IDEA DE VIDEO GENERADA")
    print("🎬" * 30)

    if "respuesta_texto" in idea:
        print(idea["respuesta_texto"])
        return

    print(f"\n📌 CONCEPTO: {idea.get('titulo_concepto', 'N/A')}")
    print(f"⚡ HOOK PRINCIPAL: \"{idea.get('hook_principal', 'N/A')}\"")
    print(f"\n💡 POR QUÉ FUNCIONARÁ:")
    print(f"   {idea.get('por_que_funcionara', 'N/A')}")

    ref = idea.get('referencia_viral', {})
    print(f"\n🔗 REFERENCIA VIRAL:")
    print(f"   Patrón: {ref.get('patron', 'N/A')}")
    print(f"   URL:    {ref.get('url', 'N/A')}")

    guion = idea.get('guion_completo', {})
    print(f"\n📝 GUION COMPLETO:")
    print(f"   [0-3s HOOK]:    {guion.get('hook_0_3seg', 'N/A')}")
    print(f"   [DESARROLLO]:   {guion.get('desarrollo', 'N/A')}")
    print(f"   [CIERRE/CTA]:   {guion.get('cierre_cta', 'N/A')}")

    tomas = idea.get('plan_de_tomas', [])
    if tomas:
        print(f"\n🎥 PLAN DE TOMAS ({len(tomas)} tomas):")
        for toma in tomas:
            print(f"   Toma {toma.get('numero', '?')}: {toma.get('descripcion', 'N/A')}")
            print(f"          Plano: {toma.get('tipo_plano', 'N/A')} | Duración: {toma.get('duracion', 'N/A')}")
            print(f"          Nota: {toma.get('notas_direccion', 'N/A')}")

    prod = idea.get('produccion', {})
    print(f"\n🎬 PRODUCCIÓN:")
    print(f"   Duración total: {prod.get('duracion_total', 'N/A')}")
    print(f"   Formato:        {prod.get('formato', 'N/A')}")
    print(f"   Escenario:      {prod.get('escenario', 'N/A')}")
    print(f"   Iluminación:    {prod.get('iluminacion', 'N/A')}")
    print(f"   Props/Vestuario:{prod.get('vestuario_props', 'N/A')}")
    print(f"   Música:         {prod.get('musica_sugerida', 'N/A')}")
    print(f"   Subtítulos:     {prod.get('subtitulos', 'N/A')}")

    edicion = idea.get('edicion', {})
    print(f"\n✂️  EDICIÓN:")
    print(f"   Ritmo:          {edicion.get('ritmo', 'N/A')}")
    print(f"   Transiciones:   {edicion.get('transiciones', 'N/A')}")
    print(f"   Color:          {edicion.get('color', 'N/A')}")
    tools = edicion.get('herramientas_sugeridas', [])
    if tools:
        print(f"   Herramientas:   {', '.join(tools)}")

    pub = idea.get('estrategia_publicacion', {})
    print(f"\n📱 PUBLICACIÓN:")
    print(f"   Mejor horario:  {pub.get('mejor_horario', 'N/A')}")
    print(f"   Caption:")
    print(f"   {pub.get('caption_sugerido', 'N/A')}")
    hashtags = pub.get('hashtags', [])
    if hashtags:
        print(f"   Hashtags: {' '.join(hashtags)}")

    metricas = idea.get('metricas_objetivo', {})
    print(f"\n📊 MÉTRICAS OBJETIVO:")
    print(f"   KPI principal:  {metricas.get('kpi_principal', 'N/A')}")
    print(f"   Expectativa:    {metricas.get('expectativa_realista', 'N/A')}")

    print("\n" + "🎬" * 30)


def interactive_mode():
    """Modo interactivo para generar ideas"""
    print("\n" + "=" * 60)
    print("  GENERADOR DE IDEAS DE VIDEO VIRAL")
    print("=" * 60)
    print("Responde las siguientes preguntas para generar tu idea:\n")

    print("1️⃣  CONTEXTO DE LA EMPRESA")
    print("   (Ej: 'Clínica dental en Madrid, especializada en blanqueamiento')")
    company_context = input("   > ").strip()
    if not company_context:
        company_context = "Empresa de servicios/productos"

    print("\n2️⃣  OBJETIVO DEL VIDEO")
    print("   (Ej: 'Conseguir consultas', 'Educar sobre el producto', 'Generar confianza')")
    video_objective = input("   > ").strip()
    if not video_objective:
        video_objective = "Generar reconocimiento de marca"

    print("\n3️⃣  PLATAFORMA")
    print("   [1] Instagram Reels  [2] TikTok  [3] YouTube Shorts  [4] Todas")
    platform_choice = input("   > ").strip()
    platforms = {
        "1": "Instagram Reels", "2": "TikTok",
        "3": "YouTube Shorts", "4": "Instagram/TikTok/YouTube Shorts"
    }
    platform = platforms.get(platform_choice, "Instagram Reels")

    print("\n4️⃣  ¿FILTRAR POR NICHO? (opcional, Enter para omitir)")
    print("   (Ej: fitness, finanzas, educación, cocina, tecnología)")
    nicho = input("   > ").strip() or None

    print("\n5️⃣  ¿FILTRAR POR PATRÓN VIRAL? (opcional, Enter para omitir)")
    print("   (Ej: antes/después, tutorial, ranking, historia, tip rápido)")
    patron = input("   > ").strip() or None

    return company_context, video_objective, platform, nicho, patron


def main():
    parser = argparse.ArgumentParser(description='Genera ideas de video viral')
    parser.add_argument('--company', type=str, help='Contexto de la empresa')
    parser.add_argument('--goal', type=str, help='Objetivo del video')
    parser.add_argument('--platform', type=str, default='Instagram Reels',
                       choices=['Instagram Reels', 'TikTok', 'YouTube Shorts', 'All'],
                       help='Plataforma target')
    parser.add_argument('--nicho', type=str, help='Filtrar referencias por nicho')
    parser.add_argument('--patron', type=str, help='Filtrar por patrón viral')
    parser.add_argument('--num-refs', type=int, default=5,
                       help='Número de videos de referencia (default: 5)')
    parser.add_argument('--output', type=str, help='Guardar resultado en archivo JSON')
    parser.add_argument('--list-nichos', action='store_true',
                       help='Listar nichos disponibles en la BD')
    parser.add_argument('--no-ai', action='store_true',
                       help='Solo buscar referencias sin generar con IA')
    args = parser.parse_args()

    print("=" * 60)
    print("GENERADOR DE IDEAS DE VIDEO VIRAL")
    print("Powered by Gemini AI + Supabase (1,000 Videos Virales)")
    print("=" * 60)

    # Conectar a Supabase
    try:
        db = get_db()
    except ValueError as e:
        print(e)
        return

    # Listar nichos disponibles
    if args.list_nichos:
        nichos = get_available_nichos(db)
        if nichos:
            print("\n📊 NICHOS DISPONIBLES EN SUPABASE:")
            for nicho, count in nichos:
                print(f"   {nicho}: {count} videos")
        else:
            print("ℹ️  Aún no hay análisis en la BD.")
            print("   Ejecuta: python analyze_with_gemini.py")
        return

    # Obtener parámetros
    if args.company and args.goal:
        company_context = args.company
        video_objective = args.goal
        platform = args.platform
        nicho = args.nicho
        patron = args.patron
    else:
        company_context, video_objective, platform, nicho, patron = interactive_mode()

    print(f"\n🔍 Buscando referencias virales relevantes en Supabase...")

    # Buscar hooks relevantes
    hooks_data = search_relevant_hooks(db, nicho, patron, args.num_refs)

    if not hooks_data:
        print("❌ No se encontraron referencias. Asegúrate de tener la BD con datos.")
        return

    print(f"✅ Encontradas {len(hooks_data)} referencias virales")

    # Mostrar referencias encontradas
    print("\n📚 REFERENCIAS SELECCIONADAS:")
    for h in hooks_data:
        print(f"   #{h['id']:04d}: {h['hook_template'][:80]}...")
        print(f"          URL: {h.get('url', 'N/A')}")
        if h.get('nicho'):
            print(f"          Nicho: {h['nicho']} | Patrón: {h.get('patron_viral', 'N/A')}")

    if args.no_ai:
        print("\nℹ️  Modo --no-ai: Solo se muestran las referencias, sin generar idea con IA.")
        return

    # Generar idea con Gemini
    print(f"\n🤖 Generando idea con Gemini ({GEMINI_MODEL})...")

    try:
        model = setup_gemini()
    except Exception as e:
        print(f"❌ Error configurando Gemini: {e}")
        print("\nℹ️  Puedes usar --no-ai para solo ver las referencias.")
        return

    try:
        idea = generate_idea_with_gemini(
            model, company_context, video_objective, platform, hooks_data
        )

        # Guardar en historial
        idea_id = save_idea_to_db(db, company_context, video_objective, platform, hooks_data, idea)

        # Mostrar resultado
        print_idea_pretty(idea)

        print(f"\n💾 Idea guardada en Supabase con ID: #{idea_id}")

        # Guardar en archivo si se especificó
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    "generated_at": datetime.now().isoformat(),
                    "inputs": {
                        "company_context": company_context,
                        "video_objective": video_objective,
                        "platform": platform,
                    },
                    "references": [
                        {"id": h["id"], "url": h.get("url"), "hook": h["hook_template"]}
                        for h in hooks_data
                    ],
                    "idea": idea,
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 Guardado también en: {args.output}")

    except Exception as e:
        print(f"❌ Error generando idea: {e}")

    print("\n✅ ¡Listo! Ejecuta de nuevo para generar otra idea diferente.")


if __name__ == "__main__":
    main()
