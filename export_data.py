"""
Viral Video DB — Exportador Completo de Data
=============================================
Exporta TODA la data de los videos analizados en Supabase a:
  - JSON completo (para pasar a cualquier IA como contexto estructurado)
  - Markdown legible (para pegar como system prompt en Claude, ChatGPT, Gemini, etc.)

Uso:
    python export_data.py                        # Exporta JSON + MD con todos los videos
    python export_data.py --formato json         # Solo JSON
    python export_data.py --formato md           # Solo Markdown
    python export_data.py --limite 50            # Limitar número de videos
    python export_data.py --output mi_export     # Prefijo del archivo de salida
    python export_data.py --completo             # Incluye análisis JSON completo por video
"""

import argparse
import json
import sys
from datetime import datetime

from db import get_db


# ─────────────────────────────────────────────
# OBTENCIÓN DE DATOS
# ─────────────────────────────────────────────

def fetch_all_data(limite: int = None, completo: bool = False) -> dict:
    """Obtiene toda la data de Supabase directamente de las tablas."""
    db = get_db()

    print("[*] Conectando a Supabase...")

    # ── Estadísticas globales ──
    try:
        stats_raw = db.rpc("get_db_stats").execute().data
        if isinstance(stats_raw, list):
            stats = stats_raw[0] if stats_raw else {}
        else:
            stats = stats_raw or {}
    except Exception:
        # Fallback manual si el RPC no existe
        try:
            total_hooks = db.table("hooks").select("id", count="exact").execute().count or 0
            analizados  = db.table("hooks").select("id", count="exact").eq("analyzed", 1).execute().count or 0
            pendientes  = db.table("hooks").select("id", count="exact").eq("analyzed", 0).execute().count or 0
            errores     = db.table("hooks").select("id", count="exact").eq("analyzed", 2).execute().count or 0
            ideas       = db.table("ideas_generadas").select("id", count="exact").execute().count or 0
            stats = {
                "total_hooks": total_hooks,
                "hooks_analizados": analizados,
                "hooks_pendientes": pendientes,
                "hooks_con_error": errores,
                "ideas_generadas": ideas,
            }
        except Exception as e:
            print(f"  [!] No se pudieron obtener estadisticas: {e}")
            stats = {}

    print(f"  [OK] Stats: {stats.get('hooks_analizados', '?')} analizados / {stats.get('total_hooks', '?')} total")

    # ── Videos analizados (JOIN hooks + video_analysis) ──
    print("[*] Descargando videos analizados...")

    # Columnas con estadísticas de redes sociales (requieren migración)
    stats_cols = "reproducciones, me_gusta, comentarios, guardados, compartidos, stats_updated_at, "
    # Columnas base siempre disponibles
    base_cols = (
        "id, hook_template, reference_url, analyzed, analyzed_at, "
        "video_analysis(titulo_descriptivo, duracion_estimada, formato, plataforma, "
        "hook_tipo, hook_texto, hook_duracion_seg, hook_tecnica, hook_elemento_visual, "
        "ritmo, densidad_informacion, arco_emocional, "
        "calidad_video, iluminacion, escenario, tiene_subtitulos, texto_en_pantalla, "
        "transiciones, color_grading, "
        "voz_en_off, habla_a_camara, tono_voz, musica_genero, musica_posicion, musica_proposito, "
        "guion_completo, estilo_escritura, call_to_action, "
        "por_que_es_viral, emocion_principal, factor_compartir, audiencia_objetivo, "
        "nicho, patron_viral, nivel_dificultad, costo_produccion, tiempo_produccion, "
        "adaptable_otros_nichos, tags, nichos_compatibles, equipamiento, "
        + ("analisis_json_completo, " if completo else "")
        + "created_at)"
    )

    videos_raw = []
    for include_stats in (True, False):
        columns = (stats_cols + base_cols) if include_stats else base_cols
        try:
            query = (
                db.table("hooks")
                .select(columns)
                .eq("analyzed", 1)
                .order("id")
            )
            if limite:
                query = query.limit(limite)
            videos_raw = query.execute().data or []
            if include_stats:
                print("  [OK] Columnas de estadisticas incluidas")
            break
        except Exception as e:
            if include_stats:
                print("  [!] Columnas de stats no disponibles, reintentando sin ellas...")
                print(f"      (aplica migration_add_stats.sql para incluirlas)")
            else:
                print(f"  [ERROR] Error obteniendo videos: {e}")
                videos_raw = []

    # Aplanar el JOIN (video_analysis viene como objeto anidado)
    videos = []
    for row in videos_raw:
        va = row.pop("video_analysis", None) or {}
        if isinstance(va, list):
            va = va[0] if va else {}
        row.update(va)
        videos.append(row)

    print(f"  [OK] {len(videos)} videos con analisis obtenidos")

    # ── Nichos ──
    try:
        nichos = db.rpc("get_nichos_stats", {"p_limit": 30}).execute().data or []
    except Exception:
        try:
            rows = db.table("video_analysis").select("nicho").execute().data or []
            from collections import Counter
            cnt = Counter(r["nicho"] for r in rows if r.get("nicho"))
            nichos = [{"nicho": k, "total": v} for k, v in cnt.most_common(30)]
        except Exception:
            nichos = []

    # ── Patrones virales ──
    try:
        patrones = db.rpc("get_patrones_stats", {"p_limit": 20}).execute().data or []
    except Exception:
        try:
            rows = db.table("video_analysis").select("patron_viral").execute().data or []
            from collections import Counter
            cnt = Counter(r["patron_viral"] for r in rows if r.get("patron_viral"))
            patrones = [{"patron_viral": k, "total": v} for k, v in cnt.most_common(20)]
        except Exception:
            patrones = []

    # ── Emociones ──
    try:
        emociones = db.rpc("get_emociones_stats", {"p_limit": 15}).execute().data or []
    except Exception:
        try:
            rows = db.table("video_analysis").select("emocion_principal").execute().data or []
            from collections import Counter
            cnt = Counter(r["emocion_principal"] for r in rows if r.get("emocion_principal"))
            emociones = [{"emocion_principal": k, "total": v} for k, v in cnt.most_common(15)]
        except Exception:
            emociones = []

    return {
        "metadata": {
            "exportado_en": datetime.now().isoformat(),
            "version": "2.0",
            "descripcion": "Export completo de Viral Video DB — videos analizados con IA",
        },
        "estadisticas": stats,
        "nichos": nichos,
        "patrones_virales": patrones,
        "emociones": emociones,
        "videos_analizados": videos,
    }


# ─────────────────────────────────────────────
# EXPORTAR JSON
# ─────────────────────────────────────────────

def export_json(data: dict, output_path: str):
    """Guarda el export completo como JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    size_kb = len(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")) / 1024
    print(f"\n[OK] JSON exportado: {output_path}")
    print(f"   Tamano: {size_kb:.1f} KB")
    print(f"   Videos: {len(data['videos_analizados'])}")


# ─────────────────────────────────────────────
# EXPORTAR MARKDOWN
# ─────────────────────────────────────────────

def export_markdown(data: dict, output_path: str):
    """Genera un Markdown optimizado para pegar como contexto en cualquier IA."""

    stats   = data["estadisticas"]
    nichos  = data["nichos"]
    pat     = data["patrones_virales"]
    emo     = data["emociones"]
    videos  = data["videos_analizados"]
    ts      = datetime.fromisoformat(data["metadata"]["exportado_en"]).strftime("%d/%m/%Y %H:%M")

    lines = []

    # ── Cabecera ──
    lines += [
        "# BASE DE CONOCIMIENTO — Viral Video DB",
        f"\n> Generado el {ts} | "
        f"{stats.get('total_hooks', '?')} hooks totales | "
        f"{stats.get('hooks_analizados', len(videos))} analizados con IA | "
        f"{stats.get('ideas_generadas', '?')} guiones generados",
        "\n---\n",
    ]

    # ── Rol ──
    lines += [
        "## 🎯 Tu rol como IA",
        """
Eres un director creativo experto en contenido viral para redes sociales.
Tienes acceso a una base de conocimiento de videos virales REALES analizados con IA.

Cuando el usuario te pida un guion o idea de video:
1. Comprende el contexto de su empresa y el objetivo del video.
2. Selecciona los patrones virales más relevantes de esta base de conocimiento.
3. Genera un guion COMPLETO y listo para producir, con:
   - ⚡ Hook exacto (primeros 3 segundos)
   - 📝 Guion completo con tiempos
   - 🎥 Plan de tomas detallado
   - 🎬 Indicaciones de producción (escenario, iluminación, vestuario)
   - 🎵 Música sugerida
   - ✂️ Instrucciones de edición
   - 📱 Caption y hashtags
   - 🔗 URL del video viral de referencia usado
""",
        "---\n",
    ]

    # ── Estadísticas ──
    lines += [
        "## 📊 Estadísticas de la base de conocimiento\n",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Total hooks virales | {stats.get('total_hooks', '?')} |",
        f"| Videos analizados con IA | {stats.get('hooks_analizados', len(videos))} |",
        f"| Videos pendientes | {stats.get('hooks_pendientes', '?')} |",
        f"| Guiones generados | {stats.get('ideas_generadas', '?')} |",
    ]

    # ── Nichos ──
    if nichos:
        lines += ["\n---\n", "## 🏷️ Nichos disponibles\n"]
        lines += [f"- **{n['nicho']}** ({n['total']} videos)" for n in nichos]

    # ── Patrones ──
    if pat:
        lines += ["\n---\n", "## 🔄 Patrones virales más frecuentes\n"]
        lines += [f"- **{p['patron_viral']}** — {p['total']} videos" for p in pat]

    # ── Emociones ──
    if emo:
        lines += ["\n---\n", "## 💭 Emociones que generan viralidad\n"]
        lines += [f"- **{e['emocion_principal']}** — {e['total']} videos" for e in emo]

    # ── Videos analizados ──
    if videos:
        lines += [
            "\n---\n",
            f"## 🎬 Base de conocimiento — {len(videos)} videos virales analizados\n",
            "Usa estos videos como referencia al generar guiones.\n",
        ]

        for i, v in enumerate(videos, 1):
            titulo = v.get("titulo_descriptivo") or v.get("hook_template", "")[:60]
            lines.append(f"\n### Video #{i}: {titulo}")

            # Stats de redes sociales
            repro = v.get("reproducciones")
            if repro:
                lines.append(
                    f"📈 **Stats:** {repro:,} repros | "
                    f"{v.get('me_gusta') or 0:,} likes | "
                    f"{v.get('comentarios') or 0:,} comentarios | "
                    f"{v.get('guardados') or 0:,} guardados"
                )

            # Datos clave en tabla compacta
            fields = [
                ("Hook template", v.get("hook_template")),
                ("Hook exacto",   v.get("hook_texto")),
                ("Técnica hook",  v.get("hook_tecnica")),
                ("Nicho",         v.get("nicho")),
                ("Patrón viral",  v.get("patron_viral")),
                ("Por qué es viral", v.get("por_que_es_viral")),
                ("Emoción principal", v.get("emocion_principal")),
                ("Factor compartir",  v.get("factor_compartir")),
                ("Audiencia objetivo", v.get("audiencia_objetivo")),
                ("Plataforma",    v.get("plataforma")),
                ("Formato",       v.get("formato")),
                ("Duración",      v.get("duracion_estimada")),
                ("Ritmo",         v.get("ritmo")),
                ("Densidad info", v.get("densidad_informacion")),
                ("Arco emocional", v.get("arco_emocional")),
                ("Escenario",     v.get("escenario")),
                ("Iluminación",   v.get("iluminacion")),
                ("Música género", v.get("musica_genero")),
                ("Tono de voz",   v.get("tono_voz")),
                ("Dificultad",    v.get("nivel_dificultad")),
                ("Costo producción", v.get("costo_produccion")),
                ("Tiempo producción", v.get("tiempo_produccion")),
                ("Estilo escritura", v.get("estilo_escritura")),
                ("CTA",           v.get("call_to_action")),
                ("Subtítulos",    str(v.get("tiene_subtitulos")) if v.get("tiene_subtitulos") is not None else None),
                ("Texto en pantalla", v.get("texto_en_pantalla")),
                ("Transiciones",  v.get("transiciones")),
                ("Color grading", v.get("color_grading")),
            ]
            for label, val in fields:
                if val:
                    lines.append(f"- **{label}:** {val}")

            # Tags
            tags = v.get("tags")
            if tags:
                if isinstance(tags, list):
                    lines.append(f"- **Tags:** {', '.join(str(t) for t in tags)}")
                elif isinstance(tags, str):
                    lines.append(f"- **Tags:** {tags}")

            # Nichos compatibles
            nc = v.get("nichos_compatibles")
            if nc:
                if isinstance(nc, list):
                    lines.append(f"- **Nichos compatibles:** {', '.join(str(n) for n in nc)}")

            # Guion (preview)
            guion = v.get("guion_completo")
            if guion:
                preview = guion[:400].replace("\n", " ")
                suffix = "..." if len(guion) > 400 else ""
                lines.append(f"- **Guion (extracto):** {preview}{suffix}")

            lines.append(f"- **URL referencia:** {v.get('reference_url') or 'N/A'}")

    # ── Instrucciones para generar guiones ──
    lines += [
        "\n---\n",
        "## 📋 Estructura del guion que debes generar\n",
        """Cuando el usuario pida un guion, responde con esta estructura COMPLETA:

```
📌 CONCEPTO: [Nombre descriptivo de la idea]
⚡ HOOK (0-3 seg): "[Texto exacto del hook]"

💡 POR QUÉ FUNCIONARÁ:
[Justificación basada en el patrón viral de referencia]

🔗 REFERENCIA VIRAL:
   Patrón: [Patrón viral usado]
   URL: [URL EXACTA del video de la lista de arriba]

📝 GUION COMPLETO:
   [0-3s]   Hook: [Texto exacto]
   [3-15s]  Desarrollo: [Texto]
   [15-25s] Cuerpo: [Texto]
   [25-30s] CTA: [Texto]

🎥 PLAN DE TOMAS:
   Toma 1: [Descripción] | Plano: [tipo] | Duración: Xs
           Nota: [Instrucción para el operador]

🎬 PRODUCCIÓN:
   Duración total: Xs | Formato: Vertical 9:16
   Escenario: [Dónde grabar y cómo prepararlo]
   Iluminación: [Instrucciones detalladas]
   Vestuario: [Qué ponerse y qué evitar]
   Props: [Objetos necesarios]

🎵 MÚSICA:
   Género: [Tipo] | Búsqueda: "[Término en Epidemic Sound/Pixabay]"
   Volumen: [% respecto a la voz]

✂️ EDICIÓN:
   Ritmo: [Rápido/Medio/Lento]
   Transiciones: [Tipo y en qué momentos]
   Color grading: [Filtro/estilo]
   Herramientas: [CapCut / Premiere / DaVinci]

📱 PUBLICACIÓN:
   Mejor horario: [Día y hora]
   Caption: [Caption completo listo para copiar]
   Hashtags: [#hashtag1 #hashtag2 ...]

📊 MÉTRICAS OBJETIVO:
   KPI: [Reproducciones/Guardados/Leads]
   Expectativa 7 días: [Rango realista]
```
""",
        "\n---\n",
        "## 💬 Frases que activan la generación de guion\n",
        """Responde con un guion completo cuando el usuario diga:
- "Genera un guion para [empresa] que quiere [objetivo]"
- "Crea un reel para mi [tipo de negocio]"
- "Necesito un video viral para [producto/servicio]"
- "Haz un script para conseguir [resultado]"

Extrae del mensaje del usuario:
- **empresa**: quién son, qué venden
- **objetivo**: leads / ventas / notoriedad / educación
- **plataforma**: si no dicen, usa "Instagram Reels"
""",
    ]

    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    size_kb = len(content.encode("utf-8")) / 1024
    tokens_approx = int(len(content.split()) * 1.3)

    print(f"\n[OK] Markdown exportado: {output_path}")
    print(f"   Tamano: {size_kb:.1f} KB")
    print(f"   Tokens aproximados: ~{tokens_approx:,}")
    print(f"   Videos incluidos: {len(videos)}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Exporta toda la data de Viral Video DB a JSON y/o Markdown"
    )
    parser.add_argument(
        "--formato",
        choices=["json", "md", "ambos"],
        default="ambos",
        help="Formato de exportacion: json | md | ambos (default: ambos)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="viral_export",
        help="Prefijo del archivo de salida (default: viral_export -> viral_export.json / viral_export.md)",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Numero maximo de videos a exportar (default: todos)",
    )
    parser.add_argument(
        "--completo",
        action="store_true",
        help="Incluir el campo analisis_json_completo por cada video (mas pesado)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("EXPORTADOR COMPLETO - VIRAL VIDEO DB")
    print("=" * 60)

    # Validar conexión
    try:
        get_db()
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Obtener datos
    data = fetch_all_data(limite=args.limite, completo=args.completo)

    if not data["videos_analizados"]:
        print("\n[!] No se encontraron videos analizados en la base de datos.")
        print("    Asegurate de haber ejecutado analyze_with_gemini.py primero.")
        sys.exit(0)

    # Exportar según formato
    if args.formato in ("json", "ambos"):
        export_json(data, f"{args.output}.json")

    if args.formato in ("md", "ambos"):
        export_markdown(data, f"{args.output}.md")

    print("\n" + "=" * 60)
    print("COMO USAR EL EXPORT:")
    print("=" * 60)
    print()
    print("[A] Como JSON (para IAs con capacidad de leer archivos):")
    print(f"    Adjunta '{args.output}.json' directamente al chat")
    print()
    print("[B] Como Markdown (para cualquier IA):")
    print(f"    Abre '{args.output}.md' y copia TODO el contenido")
    print("    Pegalo como 'System Prompt' o 'Custom Instructions':")
    print("      - Claude:  Configuracion -> Custom Instructions")
    print("      - ChatGPT: Configuracion -> Personalizar ChatGPT")
    print("      - Gemini:  Gems -> Crear Gem -> Instrucciones")
    print()
    print("[C] Adjuntar el .md como archivo:")
    print(f"    En Claude, ChatGPT o Gemini puedes subir '{args.output}.md'")
    print("    como archivo de contexto al inicio del chat")
    print()


if __name__ == "__main__":
    main()
