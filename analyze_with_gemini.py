"""
Script para analizar videos con la API de Gemini.
Sube el video a Gemini, extrae análisis completo y lo guarda en Supabase.

Ejecutar:
  python analyze_with_gemini.py              # Analiza los videos descargados pendientes
  python analyze_with_gemini.py --limit 10   # Analiza solo 10
  python analyze_with_gemini.py --id 5       # Analiza solo el hook ID 5
  python analyze_with_gemini.py --url URL    # Analiza directamente una URL (sin descarga)
"""
import os
import json
import time
import argparse
from datetime import datetime
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_ANALYSIS_PROMPT
from db import get_db

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  google-generativeai no instalado. Ejecuta: pip install google-generativeai")


def setup_gemini():
    """Configura el cliente de Gemini"""
    if not GEMINI_AVAILABLE:
        raise ImportError("Instala: pip install google-generativeai")

    if GEMINI_API_KEY == "TU_GEMINI_API_KEY_AQUI":
        raise ValueError(
            "❌ Debes configurar tu GEMINI_API_KEY en config.py\n"
            "   Obtén tu key en: https://aistudio.google.com/app/apikey"
        )

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    print(f"✅ Gemini configurado: {GEMINI_MODEL}")
    return model


def upload_video_to_gemini(video_path):
    """
    Sube un video a Gemini Files API.
    Retorna el objeto file de Gemini o None si falla.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video no encontrado: {video_path}")

    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"         📤 Subiendo video ({size_mb:.1f} MB)...")

    video_file = genai.upload_file(
        path=video_path,
        display_name=os.path.basename(video_path),
        mime_type="video/mp4"
    )

    print(f"         ⏳ Procesando en Gemini...")
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise Exception(f"Gemini no pudo procesar el video: {video_file.state}")

    print(f"         ✅ Video procesado por Gemini")
    return video_file


def analyze_video_with_gemini(model, video_file, hook_template):
    """
    Envía el video a Gemini para análisis.
    Retorna el JSON de análisis o None si falla.
    """
    prompt = f"""
Hook viral de referencia para este video: "{hook_template}"

{GEMINI_ANALYSIS_PROMPT}
"""

    response = model.generate_content(
        [video_file, prompt],
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json"
        }
    )

    try:
        analysis = json.loads(response.text)
        return analysis
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(f"Gemini no devolvió JSON válido: {response.text[:200]}")


def analyze_url_directly(model, url, hook_template):
    """
    Analiza un video de Instagram directamente por URL sin descargarlo.
    """
    prompt = f"""
URL del video viral: {url}
Hook viral de referencia para este video: "{hook_template}"

Por favor, analiza el contenido de este video de Instagram.
Si no puedes acceder al video directamente, analiza basándote en el hook y lo que
puedas inferir del tipo de contenido que generaría este hook.

{GEMINI_ANALYSIS_PROMPT}
"""

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
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
        raise ValueError(f"Respuesta no válida: {response.text[:200]}")


def save_analysis_to_db(db, hook_id, analysis_data):
    """Guarda el análisis completo en Supabase"""
    a = analysis_data

    hook_data   = a.get('hook', {})
    estructura  = a.get('estructura_narrativa', {})
    produccion  = a.get('produccion', {})
    audio       = a.get('audio', {})
    musica      = audio.get('musica', {})
    guion       = a.get('guion', {})
    estrategia  = a.get('estrategia_viral', {})
    replicab    = a.get('replicabilidad', {})

    row = {
        'hook_id':                hook_id,
        'titulo_descriptivo':     a.get('titulo_descriptivo'),
        'duracion_estimada':      a.get('duracion_estimada'),
        'formato':                a.get('formato'),
        'plataforma':             a.get('plataforma'),

        'hook_tipo':              hook_data.get('tipo'),
        'hook_texto':             hook_data.get('texto_hook'),
        'hook_duracion_seg':      hook_data.get('duracion_hook_segundos'),
        'hook_tecnica':           hook_data.get('tecnica'),
        'hook_elemento_visual':   hook_data.get('elemento_visual_hook'),

        'ritmo':                  estructura.get('ritmo'),
        'densidad_informacion':   estructura.get('densidad_informacion'),
        'arco_emocional':         estructura.get('arco_emocional'),

        'calidad_video':          produccion.get('calidad_video'),
        'iluminacion':            produccion.get('iluminacion'),
        'escenario':              produccion.get('escenario'),
        'tiene_subtitulos':       bool(produccion.get('subtitulos', False)),
        'texto_en_pantalla':      produccion.get('texto_en_pantalla'),
        'transiciones':           produccion.get('transiciones'),
        'color_grading':          produccion.get('color_grading'),

        'voz_en_off':             bool(audio.get('voz_en_off', False)),
        'habla_a_camara':         bool(audio.get('habla_a_camara', False)),
        'tono_voz':               audio.get('tono_voz'),
        'musica_genero':          musica.get('genero'),
        'musica_posicion':        musica.get('posicion'),
        'musica_proposito':       musica.get('proposito'),

        'guion_completo':         guion.get('texto_completo'),
        'estilo_escritura':       guion.get('estilo_escritura'),
        'call_to_action':         guion.get('call_to_action'),

        'por_que_es_viral':       estrategia.get('por_que_es_viral'),
        'emocion_principal':      estrategia.get('emocion_principal'),
        'factor_compartir':       estrategia.get('factor_compartir'),
        'audiencia_objetivo':     estrategia.get('audiencia_objetivo'),
        'nicho':                  estrategia.get('nicho'),
        'patron_viral':           estrategia.get('patron_viral'),

        'nivel_dificultad':       replicab.get('nivel_dificultad'),
        'costo_produccion':       replicab.get('costo_produccion'),
        'tiempo_produccion':      replicab.get('tiempo_produccion_estimado'),
        'adaptable_otros_nichos': bool(replicab.get('adaptable_a_otros_nichos', False)),

        # JSONB: pasar dict/list directamente (no json.dumps)
        'analisis_json_completo': a,
        'tags':                   a.get('tags', []),
        'nichos_compatibles':     replicab.get('nichos_compatibles', []),
        'equipamiento':           replicab.get('equipamiento_necesario', []),
    }

    # Upsert por hook_id (columna UNIQUE en video_analysis)
    db.table('video_analysis').upsert(row, on_conflict='hook_id').execute()

    # Actualizar estado del hook
    db.table('hooks').update({
        'analyzed': 1,
        'analyzed_at': datetime.now().isoformat(),
    }).eq('id', hook_id).execute()


VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.mov', '.avi', '.m4v'}


def analyze_with_retry(fn, max_retries=3):
    """Llama fn() con reintentos y backoff exponencial para errores 429 de Gemini."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:
            err = str(e)
            if ("429" in err or "quota" in err.lower()) and attempt < max_retries:
                wait = 60 * attempt  # 60s, 120s, 180s
                print(f"         ⏸️  Cuota Gemini (429) — esperando {wait}s (intento {attempt}/{max_retries})...")
                time.sleep(wait)
            else:
                raise


def get_hooks_to_analyze(db, limit=20, hook_id=None, from_url=None):
    """Obtiene hooks con videos descargados listos para analizar.
    Omite archivos de solo audio (.m4a, .mp3, etc.) — ocurren cuando ffmpeg no está instalado.
    """
    if hook_id:
        result = db.table('hooks').select(
            'id, hook_template, reference_url, video_path'
        ).eq('id', hook_id).execute()
    elif from_url:
        result = db.table('hooks').select(
            'id, hook_template, reference_url, video_path'
        ).eq('reference_url', from_url).execute()
    else:
        result = (
            db.table('hooks')
            .select('id, hook_template, reference_url, video_path')
            .not_.is_('video_path', None)
            .eq('analyzed', 0)
            .order('id')
            .limit(limit * 3)   # pedir más para compensar los que se filtran
            .execute()
        )

    hooks = []
    skipped = 0
    for r in result.data:
        path = r['video_path'] or ''
        ext = os.path.splitext(path)[1].lower()
        if ext and ext not in VIDEO_EXTENSIONS:
            print(f"   ⚠️  Hook #{r['id']} omitido — archivo solo-audio: {os.path.basename(path)}")
            skipped += 1
            continue
        hooks.append((r['id'], r['hook_template'], r['reference_url'], r['video_path']))
        if len(hooks) >= limit:
            break

    if skipped:
        print(f"   ℹ️  {skipped} archivos de solo-audio omitidos (instala ffmpeg para evitarlo)\n")

    return hooks


def main():
    parser = argparse.ArgumentParser(description='Analiza videos virales con Gemini AI')
    parser.add_argument('--limit', type=int, default=20,
                       help='Máximo de videos a analizar (default: 20)')
    parser.add_argument('--id', type=int, default=None,
                       help='Analizar solo el hook con este ID')
    parser.add_argument('--url', type=str, default=None,
                       help='Analizar directamente esta URL (sin descarga previa)')
    parser.add_argument('--delay', type=float, default=3.0,
                       help='Segundos de espera entre análisis (default: 3)')
    args = parser.parse_args()

    print("=" * 60)
    print("ANALIZADOR DE VIDEOS VIRALES CON GEMINI AI")
    print("=" * 60)

    # Configurar Gemini
    try:
        model = setup_gemini()
    except (ImportError, ValueError) as e:
        print(f"❌ {e}")
        return

    # Conectar a Supabase
    try:
        db = get_db()
    except ValueError as e:
        print(e)
        return

    # Obtener hooks a analizar
    hooks = get_hooks_to_analyze(db, args.limit, args.id, args.url)

    if not hooks:
        print("ℹ️  No hay videos listos para analizar.")
        print("   Primero descarga videos con: python download_videos.py")
        return

    print(f"📋 Videos a analizar: {len(hooks)}\n")

    success_count = 0
    error_count = 0

    for i, (hook_id, hook_template, url, video_path) in enumerate(hooks, 1):
        print(f"[{i:03d}/{len(hooks):03d}] Hook #{hook_id:04d}")
        print(f"         Template: {hook_template[:80]}...")

        try:
            video_file = None

            if video_path and os.path.exists(video_path):
                print(f"         📁 Usando video local: {os.path.basename(video_path)}")
                video_file = upload_video_to_gemini(video_path)
                analysis = analyze_with_retry(
                    lambda: analyze_video_with_gemini(model, video_file, hook_template)
                )
            elif url:
                print(f"         🌐 Analizando por URL: {url[:60]}...")
                analysis = analyze_with_retry(
                    lambda: analyze_url_directly(model, url, hook_template)
                )
            else:
                print(f"         ⚠️  Sin video ni URL. Saltando.")
                continue

            save_analysis_to_db(db, hook_id, analysis)

            nicho  = analysis.get('estrategia_viral', {}).get('nicho', 'N/A')
            patron = analysis.get('estrategia_viral', {}).get('patron_viral', 'N/A')
            print(f"         ✅ Analizado | Nicho: {nicho} | Patrón: {patron[:50]}")
            success_count += 1

            if video_file:
                try:
                    genai.delete_file(video_file.name)
                except Exception:
                    pass

        except Exception as e:
            err_str = str(e)
            print(f"         ❌ Error: {err_str[:150]}")
            if "429" in err_str or "quota" in err_str.lower():
                print("         ⏸️  Cuota de Gemini agotada. Esperando 60s antes de continuar...")
                time.sleep(60)
            db.table('hooks').update({
                'analysis_error': err_str[:500]
            }).eq('id', hook_id).execute()
            error_count += 1

        if i < len(hooks):
            print(f"         ⏳ Esperando {args.delay}s...")
            time.sleep(args.delay)
        print()

    print("=" * 60)
    print(f"✅ Analizados correctamente: {success_count}")
    print(f"❌ Errores:                  {error_count}")
    print("=" * 60)
    print(f"\nSiguiente paso: python generate_video_idea.py")


if __name__ == "__main__":
    main()
