"""
Viral Video DB — Exportador de Contexto para IAs sin tools
============================================================
Genera un archivo Markdown con el contexto completo de la BD que puedes
pegar como system prompt en CUALQUIER IA (Claude, ChatGPT, Gemini, etc.)
aunque no tenga acceso a herramientas externas.

Uso:
    python export_context.py
    python export_context.py --output mi_contexto.md
    python export_context.py --max-hooks 50   # Incluir más hooks en el contexto
"""

import argparse
from datetime import datetime
from db import get_db


def export_context(max_hooks: int = 30, output_path: str = "viral_context.md"):
    """Genera el archivo de contexto para pegar en cualquier IA"""

    db = get_db()

    # --- Estadísticas ---
    try:
        stats = db.rpc('get_db_stats').execute().data
    except Exception:
        stats = {}

    total_hooks   = stats.get('total_hooks', 0)
    analyzed      = stats.get('hooks_analizados', 0)
    ideas_count   = stats.get('ideas_generadas', 0)

    # --- Nichos ---
    try:
        nichos = db.rpc('get_nichos_stats', {'p_limit': 20}).execute().data
    except Exception:
        nichos = []

    # --- Patrones virales ---
    try:
        patrones = db.rpc('get_patrones_stats', {'p_limit': 15}).execute().data
    except Exception:
        patrones = []

    # --- Emociones ---
    try:
        emociones = db.rpc('get_emociones_stats', {'p_limit': 10}).execute().data
    except Exception:
        emociones = []

    # --- Top hooks analizados (aleatorios) via RPC ---
    try:
        top_videos = db.rpc('get_export_videos', {'p_limit': max_hooks}).execute().data
    except Exception:
        top_videos = []

    # --- Hooks sin análisis (aleatorios) ---
    try:
        raw_result = db.rpc('get_random_hooks', {'p_limit': 50}).execute().data
        # Solo los que están pendientes (analyzed=0); el RPC devuelve todos,
        # filtramos en Python para no añadir otro RPC
        raw_hooks = raw_result
    except Exception:
        raw_hooks = []

    # -------------------------------------------------------
    # Generar el Markdown
    # -------------------------------------------------------

    lines = []
    lines.append("# SISTEMA: Viral Video DB — Base de Conocimiento Viral")
    lines.append(f"\n> Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
                 f"BD con {total_hooks} hooks virales | {analyzed} analizados con IA")
    lines.append("\n---\n")

    lines.append("## 🎯 Tu rol")
    lines.append("""
Eres un director creativo experto en contenido viral para redes sociales.
Tienes acceso a una base de conocimiento de videos virales analizados con IA.

Cuando el usuario te pida un guion o idea de video, debes:
1. Entender el contexto de su empresa y objetivo del video
2. Seleccionar los patrones virales más relevantes de tu base de conocimiento
3. Generar un guion COMPLETO y listo para producir

El guion debe incluir:
- ⚡ Hook exacto (primeros 3 segundos)
- 📝 Guion completo con tiempos
- 🎥 Plan de tomas detallado
- 🎬 Indicaciones de producción (escenario, iluminación, vestuario)
- 🎵 Música sugerida
- ✂️ Instrucciones de edición
- 📱 Caption y hashtags
- 🔗 Patrón viral de referencia utilizado
""")

    lines.append("---\n")
    lines.append("## 📊 Estadísticas de la base de conocimiento\n")
    lines.append(f"- **Total hooks virales analizados:** {total_hooks}")
    lines.append(f"- **Videos con análisis completo de IA:** {analyzed}")
    lines.append(f"- **Guiones generados previamente:** {ideas_count}")

    if nichos:
        lines.append("\n---\n")
        lines.append("## 🏷️ Nichos disponibles\n")
        for n in nichos:
            lines.append(f"- **{n['nicho']}**: {n['total']} videos analizados")

    if patrones:
        lines.append("\n---\n")
        lines.append("## 🔄 Patrones virales más efectivos\n")
        lines.append("Estos son los patrones que más veces aparecen en videos virales reales:\n")
        for p in patrones:
            lines.append(f"- **{p['patron_viral']}** ({p['total']} videos)")

    if emociones:
        lines.append("\n---\n")
        lines.append("## 💭 Emociones que generan viralidad\n")
        for e in emociones:
            lines.append(f"- **{e['emocion_principal']}** ({e['total']} videos)")

    if top_videos:
        lines.append("\n---\n")
        lines.append(f"## 🎬 Base de conocimiento — {len(top_videos)} videos virales analizados\n")
        lines.append("Usa estos videos como referencia al generar guiones:\n")

        for i, v in enumerate(top_videos, 1):
            lines.append(f"\n### Video #{i}: {v.get('titulo_descriptivo') or v.get('hook_template', '')[:60]}")
            lines.append(f"- **Hook template:** {v.get('hook_template', 'N/A')}")
            if v.get('hook_texto'):
                lines.append(f"- **Hook exacto:** {v['hook_texto']}")
            if v.get('hook_tecnica'):
                lines.append(f"- **Técnica hook:** {v['hook_tecnica']}")
            lines.append(f"- **Nicho:** {v.get('nicho') or 'N/A'}")
            lines.append(f"- **Patrón viral:** {v.get('patron_viral') or 'N/A'}")
            lines.append(f"- **Por qué es viral:** {v.get('por_que_es_viral') or 'N/A'}")
            lines.append(f"- **Emoción principal:** {v.get('emocion_principal') or 'N/A'}")
            lines.append(f"- **Audiencia objetivo:** {v.get('audiencia_objetivo') or 'N/A'}")
            lines.append(f"- **Ritmo:** {v.get('ritmo') or 'N/A'}")
            lines.append(f"- **Escenario:** {v.get('escenario') or 'N/A'}")
            lines.append(f"- **Música:** {v.get('musica_genero') or 'N/A'}")
            lines.append(f"- **Dificultad producción:** {v.get('nivel_dificultad') or 'N/A'} | "
                         f"**Costo:** {v.get('costo_produccion') or 'N/A'}")
            if v.get('guion_completo'):
                guion_preview = v['guion_completo'][:300].replace('\n', ' ')
                lines.append(f"- **Guion (extracto):** {guion_preview}...")
            lines.append(f"- **URL referencia:** {v.get('reference_url') or 'N/A'}")

    if raw_hooks:
        lines.append("\n---\n")
        lines.append(f"## 📋 Hooks virales adicionales (sin análisis detallado)\n")
        lines.append("Estos hooks virales pueden inspirar el gancho del video:\n")
        for h in raw_hooks[:30]:
            lines.append(f"- {h['hook_template']}")
            if h.get('reference_url'):
                lines.append(f"  *(Referencia: {h['reference_url']})*")

    lines.append("\n---\n")
    lines.append("## 📋 Estructura del guion que debes generar\n")
    lines.append("""
Cuando el usuario pida un guion, responde con esta estructura COMPLETA:

```
📌 CONCEPTO: [Nombre descriptivo de la idea]
⚡ HOOK (0-3 seg): "[Texto exacto del hook]"

💡 POR QUÉ FUNCIONARÁ:
[Justificación basada en el patrón viral]

🔗 REFERENCIA VIRAL:
   Patrón: [Patrón viral usado]
   URL: [URL del video de referencia]

📝 GUION COMPLETO:
   [0-3s]   Hook: [Texto exacto]
   [3-15s]  Desarrollo: [Texto]
   [15-25s] Cuerpo: [Texto]
   [25-30s] CTA: [Texto]

🎥 PLAN DE TOMAS:
   Toma 1: [Descripción] | Plano: [tipo] | Duración: Xs
           Nota: [Instrucción para el operador]
   Toma 2: ...

🎬 PRODUCCIÓN:
   Duración total: Xs | Formato: Vertical 9:16
   Escenario: [Dónde grabar]
   Iluminación: [Cómo iluminar]
   Props/Vestuario: [Qué usar]

🎵 MÚSICA:
   Género: [Tipo] | Búsqueda: "[Término en Epidemic Sound/Pixabay]"

✂️ EDICIÓN:
   Ritmo: [Rápido/Medio]
   Transiciones: [Tipo]
   Color grading: [Filtro/estilo]
   Herramientas: [CapCut / Premiere / etc.]

📱 PUBLICACIÓN:
   Mejor horario: [Día y hora]
   Caption: [Caption completo]
   Hashtags: [#hashtag1 #hashtag2 ...]

📊 MÉTRICAS OBJETIVO:
   KPI: [Reproducciones/Guardados/Leads]
   Expectativa: [Rango realista]
```
""")

    lines.append("---\n")
    lines.append("## 💬 Frases que activan la generación de guion\n")
    lines.append("""
Responde generando un guion completo cuando el usuario diga:
- "Genera un guion para [empresa] que quiere [objetivo]"
- "Crea un reel para mi [tipo de negocio]"
- "Necesito un video viral para [producto/servicio]"
- "Haz un script para conseguir [resultado]"
- "Quiero hacer un TikTok/Reel/Short para..."

Extrae automáticamente del mensaje del usuario:
- **empresa**: quién son, qué venden, dónde
- **objetivo**: conseguir leads / ventas / notoriedad / educación
- **plataforma**: si no dicen, usa "Instagram Reels"
""")

    content = "\n".join(lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    size_kb = len(content.encode('utf-8')) / 1024
    tokens_approx = len(content.split()) * 1.3

    print(f"\n✅ Contexto exportado: {output_path}")
    print(f"   Tamaño: {size_kb:.1f} KB")
    print(f"   Tokens aproximados: ~{int(tokens_approx):,}")
    print(f"   Videos incluidos: {len(top_videos)}")
    print(f"   Hooks adicionales: {min(len(raw_hooks), 30)}")
    print(f"\n📋 CÓMO USAR:")
    print(f"   1. Abre el archivo {output_path}")
    print(f"   2. Copia TODO el contenido")
    print(f"   3. Pégalo como 'System Prompt' o 'Custom Instructions' en tu IA favorita:")
    print(f"      • Claude: Configuración → Claude.ai → Custom Instructions")
    print(f"      • ChatGPT: Configuración → Personalizar ChatGPT → Instrucciones")
    print(f"      • Gemini: Gems → Crear Gem → Instrucciones")
    print(f"   4. Pide: 'Genera un guion para [empresa] que quiere [objetivo]'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Exporta el contexto de la BD de videos virales para usar en cualquier IA'
    )
    parser.add_argument('--output', type=str, default='viral_context.md',
                        help='Nombre del archivo de salida (default: viral_context.md)')
    parser.add_argument('--max-hooks', type=int, default=30,
                        help='Número máximo de videos analizados a incluir (default: 30)')
    args = parser.parse_args()

    print("=" * 60)
    print("EXPORTADOR DE CONTEXTO — VIRAL VIDEO DB")
    print("=" * 60)

    try:
        get_db()  # validación temprana de credenciales
    except ValueError as e:
        print(e)
        raise SystemExit(1)

    export_context(max_hooks=args.max_hooks, output_path=args.output)
