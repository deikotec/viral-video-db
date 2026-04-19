"""
Viral Video DB — MCP Server para Claude
=========================================
Servidor MCP (Model Context Protocol) que expone las herramientas de la base de datos
viral directamente a Claude Desktop / Claude API.

Claude puede usar estas tools de forma nativa sin necesidad de una API externa.

Configurar en claude_desktop_config.json:
{
  "mcpServers": {
    "viral-video-db": {
      "command": "python",
      "args": ["c:/xampp/htdocs/claude/rrss ideas/mcp_server/server.py"]
    }
  }
}
"""

import sys
import os
import json
import sqlite3
import re
from typing import Optional

# Añadir directorio raíz al path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import GEMINI_API_KEY, GEMINI_MODEL, IDEA_GENERATION_PROMPT
from db import get_db

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError:
    print("ERROR: Instala el SDK de MCP: pip install mcp", file=sys.stderr)
    sys.exit(1)


# -------------------------------------------------------
# Helpers de BD (sin dependencia de FastAPI)
# -------------------------------------------------------

def db_stats():
    try:
        db = get_db()
        result = db.rpc('get_db_stats').execute()
        data = result.data
        return {
            "total_hooks": data.get("total_hooks", 0),
            "analizados": data.get("hooks_analizados", 0),
            "analisis_en_bd": data.get("analisis_guardados", 0),
            "ideas_generadas": data.get("ideas_generadas", 0)
        }
    except Exception:
        return {"total_hooks": 0, "analizados": 0, "analisis_en_bd": 0, "ideas_generadas": 0}


def db_nichos():
    try:
        db = get_db()
        rows = db.rpc('get_nichos_stats', {'p_limit': 20}).execute().data
        return [{"nicho": r["nicho"], "videos": r["total"]} for r in rows if r["nicho"]]
    except Exception:
        return []


def db_patrones():
    try:
        db = get_db()
        rows = db.rpc('get_patrones_stats', {'p_limit': 20}).execute().data
        return [{"patron": r["patron_viral"], "videos": r["total"]} for r in rows if r["patron_viral"]]
    except Exception:
        return []


def db_search_refs(empresa: str, nicho: Optional[str] = None,
                   patron: Optional[str] = None, num_refs: int = 5):
    try:
        db = get_db()
        
        # Consultamos hooks analizados
        res = db.table('video_analysis').select('id', count='exact').limit(0).execute()
        num_analyzed = res.count or 0
        
        if num_analyzed == 0:
            rows = db.rpc('get_random_hooks', {'p_limit': num_refs * 2}).execute().data
            return [{"id": r["id"], "hook": r["hook_template"],
                     "url": r["reference_url"], "analisis": None} for r in rows][:num_refs]

        params = {'p_limit': num_refs * 3}
        if nicho:
            params['p_nicho'] = nicho
        if patron:
            params['p_patron'] = patron
            
        rows = db.rpc('search_hooks_random', params).execute().data
        
        if not rows and (nicho or patron):
            rows = db.rpc('search_hooks_random', {'p_limit': num_refs * 3}).execute().data

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "hook": r["hook_template"],
                "url": r.get("reference_url"),
                "titulo": r.get("titulo_descriptivo", "Sin título"),
                "nicho": r.get("nicho"),
                "patron_viral": r.get("patron_viral"),
                "por_que_viral": r.get("por_que_es_viral"),
                "emocion": r.get("emocion_principal"),
                "audiencia": r.get("audiencia_objetivo"),
                "dificultad": r.get("nivel_dificultad", "N/A"),
                "costo": r.get("costo_produccion", "N/A"),
                "analisis_completo": r.get("analisis_json_completo"),
            })

        return result[:num_refs]
    except Exception as e:
        print(f"Error en db_search_refs: {e}", file=sys.stderr)
        return []


def format_refs_for_prompt(hooks_data):
    refs = []
    for i, hook in enumerate(hooks_data, 1):
        ref = f"\n--- REFERENCIA #{i} ---"
        ref += f"\nHook: {hook['hook']}"
        ref += f"\nURL: {hook.get('url', 'N/A')}"
        a = hook.get("analisis_completo")
        if a:
            viral = a.get("estrategia_viral", {})
            guion = a.get("guion", {})
            h = a.get("hook", {})
            prod = a.get("produccion", {})
            audio = a.get("audio", {})
            est = a.get("estructura_narrativa", {})
            ref += f"\nNicho: {viral.get('nicho', 'N/A')}"
            ref += f"\nPatrón viral: {viral.get('patron_viral', 'N/A')}"
            ref += f"\nPor qué viral: {viral.get('por_que_es_viral', 'N/A')}"
            ref += f"\nEmoción: {viral.get('emocion_principal', 'N/A')}"
            ref += f"\nAudiencia: {viral.get('audiencia_objetivo', 'N/A')}"
            ref += f"\nHook visual: {h.get('elemento_visual_hook', 'N/A')}"
            ref += f"\nTécnica: {h.get('tecnica', 'N/A')}"
            ref += f"\nRitmo: {est.get('ritmo', 'N/A')}"
            ref += f"\nEscenario: {prod.get('escenario', 'N/A')}"
            ref += f"\nMúsica: {audio.get('musica', {}).get('genero', 'N/A')}"
            ref += f"\nGuion: {str(guion.get('texto_completo', ''))[:200]}..."
        else:
            ref += "\n(Sin análisis detallado)"
        refs.append(ref)
    return "\n".join(refs)


def call_gemini_for_script(empresa, objetivo, plataforma, hooks_data):
    try:
        import google.generativeai as genai
    except ImportError:
        return {"error": "Instala google-generativeai: pip install google-generativeai"}

    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_GEMINI_API_KEY_AQUI":
        return {"error": "Configura GEMINI_API_KEY en config.py"}

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = IDEA_GENERATION_PROMPT.format(
        num_references=len(hooks_data),
        company_context=empresa,
        video_objective=objetivo,
        platform=plataforma,
        reference_videos=format_refs_for_prompt(hooks_data),
    )

    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.7, "response_mime_type": "application/json"},
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"respuesta_texto": response.text}


def save_idea_to_db(empresa, objetivo, plataforma, hooks_used, idea_json):
    try:
        db = get_db()
        row = {
            'empresa_contexto': empresa,
            'objetivo_video': objetivo,
            'plataforma': plataforma,
            'hook_referencias': [h.get("id") for h in hooks_used] if hooks_used else [],
            'idea_json': idea_json,
        }
        result = db.table('ideas_generadas').insert(row).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]['id']
        return 0
    except Exception as e:
        print(f"Error al guardar idea en db: {e}", file=sys.stderr)
        return 0


# -------------------------------------------------------
# MCP Server
# -------------------------------------------------------

server = Server("viral-video-db")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_db_stats",
            description=(
                "Muestra las estadísticas de la base de datos de videos virales: "
                "total de hooks, cuántos han sido analizados, cuántas ideas generadas, etc."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_nichos",
            description=(
                "Lista todos los nichos de mercado disponibles en la base de datos de videos virales "
                "(ej: fitness, finanzas, salud, tecnología). Útil para filtrar referencias."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="list_patrones_virales",
            description=(
                "Lista todos los patrones virales disponibles en la base de datos "
                "(ej: antes/después, tutorial, ranking, historia personal). "
                "Útil para especificar el tipo de video a generar."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="search_viral_references",
            description=(
                "Busca videos virales de referencia en la base de datos que se ajusten "
                "al contexto de la empresa y objetivo del video. Devuelve los mejores "
                "candidatos con su análisis de por qué funcionaron."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "empresa": {
                        "type": "string",
                        "description": "Descripción de la empresa (quién son, qué venden, dónde están)",
                    },
                    "nicho": {
                        "type": "string",
                        "description": "Nicho para filtrar (ej: salud, fitness, finanzas). Opcional.",
                    },
                    "patron_viral": {
                        "type": "string",
                        "description": "Patrón viral a buscar (ej: antes/después, tutorial). Opcional.",
                    },
                    "num_referencias": {
                        "type": "integer",
                        "description": "Número de referencias a devolver (1-10). Default: 5",
                        "default": 5,
                    },
                },
                "required": ["empresa"],
            },
        ),
        types.Tool(
            name="generate_video_script",
            description=(
                "⭐ HERRAMIENTA PRINCIPAL. Genera un guion COMPLETO y listo para producir "
                "para un video viral, basándose en el análisis de 1,000+ videos virales reales. "
                "Incluye: hook exacto, guion completo, plan de tomas, producción, edición, "
                "estrategia de publicación y URL del video viral de referencia."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "empresa": {
                        "type": "string",
                        "description": (
                            "Descripción completa de la empresa. "
                            "Ej: 'Clínica dental en Madrid, especializada en ortodoncia invisible Invisalign. "
                            "Precios desde 2.500€. Público: adultos 25-45 años con poder adquisitivo medio-alto.'"
                        ),
                    },
                    "objetivo": {
                        "type": "string",
                        "description": (
                            "Objetivo específico del video. "
                            "Ej: 'Conseguir leads de personas interesadas en alineadores invisibles' / "
                            "'Generar confianza mostrando casos de éxito' / "
                            "'Vender el pack de blanqueamiento dental de 99€'"
                        ),
                    },
                    "plataforma": {
                        "type": "string",
                        "description": "Plataforma destino: Instagram Reels / TikTok / YouTube Shorts",
                        "default": "Instagram Reels",
                    },
                    "nicho": {
                        "type": "string",
                        "description": "Nicho para filtrar referencias. Opcional — si no se especifica, usa todos.",
                    },
                    "patron_viral": {
                        "type": "string",
                        "description": "Patrón viral preferido. Opcional. Ej: 'antes/después', 'tutorial', 'ranking'",
                    },
                    "num_referencias": {
                        "type": "integer",
                        "description": "Referencias virales a analizar para generar el guion (1-10). Default: 5",
                        "default": 5,
                    },
                },
                "required": ["empresa", "objetivo"],
            },
        ),
        types.Tool(
            name="get_idea_history",
            description=(
                "Devuelve el historial de guiones de video generados previamente. "
                "Útil para ver ideas anteriores o recuperar un guion específico."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de ideas a devolver. Default: 10",
                        "default": 10,
                    },
                    "idea_id": {
                        "type": "integer",
                        "description": "ID específico de idea a recuperar. Opcional.",
                    },
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    try:
        # ---- get_db_stats ----
        if name == "get_db_stats":
            stats = db_stats()
            result = (
                f"📊 ESTADÍSTICAS DE LA BASE DE DATOS\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎣 Total hooks virales:     {stats['total_hooks']}\n"
                f"✅ Videos analizados con IA: {stats['analizados']}\n"
                f"📁 Análisis guardados:      {stats['analisis_en_bd']}\n"
                f"💡 Guiones generados:       {stats['ideas_generadas']}\n"
            )
            if stats["analizados"] == 0:
                result += "\n⚠️  Aún no hay videos analizados. Ejecuta: python analyze_with_gemini.py"
            return [types.TextContent(type="text", text=result)]

        # ---- list_nichos ----
        elif name == "list_nichos":
            nichos = db_nichos()
            if not nichos:
                return [types.TextContent(type="text",
                    text="ℹ️  No hay nichos disponibles aún. Ejecuta: python analyze_with_gemini.py")]
            lines = ["🏷️  NICHOS DISPONIBLES EN LA BD\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for n in nichos:
                lines.append(f"  • {n['nicho']}: {n['videos']} videos")
            return [types.TextContent(type="text", text="\n".join(lines))]

        # ---- list_patrones_virales ----
        elif name == "list_patrones_virales":
            patrones = db_patrones()
            if not patrones:
                return [types.TextContent(type="text",
                    text="ℹ️  No hay patrones disponibles aún. Ejecuta: python analyze_with_gemini.py")]
            lines = ["🔄 PATRONES VIRALES DISPONIBLES\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for p in patrones:
                lines.append(f"  • {p['patron']}: {p['videos']} videos")
            return [types.TextContent(type="text", text="\n".join(lines))]

        # ---- search_viral_references ----
        elif name == "search_viral_references":
            empresa = arguments.get("empresa", "")
            nicho = arguments.get("nicho")
            patron = arguments.get("patron_viral")
            num_refs = int(arguments.get("num_referencias", 5))

            refs = db_search_refs(empresa, nicho, patron, num_refs)
            if not refs:
                return [types.TextContent(type="text",
                    text="❌ No se encontraron referencias. Asegúrate de tener la BD con datos.")]

            lines = [f"🔍 REFERENCIAS VIRALES ENCONTRADAS ({len(refs)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for r in refs:
                lines.append(f"\n#{r['id']:04d} — {r.get('titulo', r['hook'][:60])}")
                lines.append(f"  Hook: {r['hook'][:100]}...")
                lines.append(f"  URL: {r.get('url', 'N/A')}")
                lines.append(f"  Nicho: {r.get('nicho', 'N/A')} | Patrón: {r.get('patron_viral', 'N/A')}")
                lines.append(f"  Emoción: {r.get('emocion', 'N/A')} | Dificultad: {r.get('dificultad', 'N/A')}")
                if r.get("por_que_viral"):
                    lines.append(f"  Por qué viral: {r['por_que_viral'][:150]}...")

            return [types.TextContent(type="text", text="\n".join(lines))]

        # ---- generate_video_script ----
        elif name == "generate_video_script":
            empresa = arguments.get("empresa", "")
            objetivo = arguments.get("objetivo", "")
            plataforma = arguments.get("plataforma", "Instagram Reels")
            nicho = arguments.get("nicho")
            patron = arguments.get("patron_viral")
            num_refs = int(arguments.get("num_referencias", 5))

            if not empresa or not objetivo:
                return [types.TextContent(type="text",
                    text="❌ Se requiere 'empresa' y 'objetivo' para generar el guion.")]

            # Buscar referencias
            refs = db_search_refs(empresa, nicho, patron, num_refs)
            if not refs:
                return [types.TextContent(type="text",
                    text="❌ No se encontraron referencias en la BD.")]

            # Generar guion con Gemini
            idea = call_gemini_for_script(empresa, objetivo, plataforma, refs)

            # Guardar en historial
            idea_id = save_idea_to_db(empresa, objetivo, plataforma, refs, idea)

            # Formatear respuesta
            if "error" in idea:
                return [types.TextContent(type="text", text=f"❌ Error: {idea['error']}")]

            if "respuesta_texto" in idea:
                return [types.TextContent(type="text", text=idea["respuesta_texto"])]

            lines = [
                f"🎬 GUION VIRAL GENERADO (ID #{idea_id})",
                "━" * 50,
                f"\n📌 CONCEPTO: {idea.get('titulo_concepto', 'N/A')}",
                f"⚡ HOOK: \"{idea.get('hook_principal', 'N/A')}\"",
                f"\n💡 POR QUÉ FUNCIONARÁ:",
                f"   {idea.get('por_que_funcionara', 'N/A')}",
            ]

            ref = idea.get("referencia_viral", {})
            lines += [
                f"\n🔗 REFERENCIA VIRAL:",
                f"   Patrón: {ref.get('patron', 'N/A')}",
                f"   URL: {ref.get('url', 'N/A')}",
            ]

            guion = idea.get("guion_completo", {})
            lines += [
                f"\n📝 GUION COMPLETO:",
                f"   [0-3s HOOK]:   {guion.get('hook_0_3seg', 'N/A')}",
                f"   [DESARROLLO]:  {guion.get('desarrollo', 'N/A')}",
                f"   [CIERRE/CTA]:  {guion.get('cierre_cta', 'N/A')}",
            ]

            tomas = idea.get("plan_de_tomas", [])
            if tomas:
                lines.append(f"\n🎥 PLAN DE TOMAS ({len(tomas)} tomas):")
                for t in tomas:
                    lines.append(f"   Toma {t.get('numero', '?')}: {t.get('descripcion', 'N/A')}")
                    lines.append(f"      Plano: {t.get('tipo_plano', 'N/A')} | {t.get('duracion', 'N/A')}")
                    lines.append(f"      → {t.get('notas_direccion', '')}")

            prod = idea.get("produccion", {})
            lines += [
                f"\n🎬 PRODUCCIÓN:",
                f"   Duración: {prod.get('duracion_total', 'N/A')} | Formato: {prod.get('formato', 'N/A')}",
                f"   Escenario: {prod.get('escenario', 'N/A')}",
                f"   Iluminación: {prod.get('iluminacion', 'N/A')}",
                f"   Props: {prod.get('vestuario_props', 'N/A')}",
                f"   🎵 Música: {prod.get('musica_sugerida', 'N/A')}",
                f"   Subtítulos: {prod.get('subtitulos', 'N/A')}",
            ]

            edicion = idea.get("edicion", {})
            herramientas = edicion.get("herramientas_sugeridas", [])
            lines += [
                f"\n✂️ EDICIÓN:",
                f"   Ritmo: {edicion.get('ritmo', 'N/A')}",
                f"   Transiciones: {edicion.get('transiciones', 'N/A')}",
                f"   Color: {edicion.get('color', 'N/A')}",
                f"   Herramientas: {', '.join(herramientas) if herramientas else 'N/A'}",
            ]

            pub = idea.get("estrategia_publicacion", {})
            hashtags = pub.get("hashtags", [])
            lines += [
                f"\n📱 PUBLICACIÓN:",
                f"   Horario: {pub.get('mejor_horario', 'N/A')}",
                f"   Caption: {pub.get('caption_sugerido', 'N/A')}",
                f"   Hashtags: {' '.join(hashtags[:10]) if hashtags else 'N/A'}",
            ]

            metricas = idea.get("metricas_objetivo", {})
            lines += [
                f"\n📊 MÉTRICAS OBJETIVO:",
                f"   KPI: {metricas.get('kpi_principal', 'N/A')}",
                f"   Expectativa: {metricas.get('expectativa_realista', 'N/A')}",
                f"\n━" * 25,
                f"💾 Guion guardado en historial con ID #{idea_id}",
            ]

            return [types.TextContent(type="text", text="\n".join(lines))]

        # ---- get_idea_history ----
        elif name == "get_idea_history":
            limit = int(arguments.get("limit", 10))
            idea_id = arguments.get("idea_id")

            try:
                db = get_db()
                if idea_id:
                    res = db.table('ideas_generadas').select('*').eq('id', idea_id).execute()
                    if not res.data:
                        return [types.TextContent(type="text",
                            text=f"❌ Idea #{idea_id} no encontrada.")]
                    row = res.data[0]
                    idea = row.get("idea_json", {})
                    return [types.TextContent(type="text",
                        text=f"Idea #{idea_id} — {row.get('empresa_contexto', '')}\n{json.dumps(idea, ensure_ascii=False, indent=2)}")]
                else:
                    res = db.table('ideas_generadas').select('id, empresa_contexto, objetivo_video, plataforma, created_at').order('created_at', desc=True).limit(limit).execute()
                    rows = res.data
                    if not rows:
                        return [types.TextContent(type="text",
                            text="ℹ️ No hay guiones generados todavía.")]
                    lines = ["💡 HISTORIAL DE GUIONES GENERADOS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
                    for r in rows:
                        dt = str(r.get('created_at', ''))[:19].replace('T', ' ') if r.get('created_at') else 'N/A'
                        emp = str(r.get('empresa_contexto', ''))[:50]
                        obj = str(r.get('objetivo_video', ''))[:60]
                        lines.append(f"  #{r.get('id')} | {dt} | {emp}")
                        lines.append(f"       Objetivo: {obj}")
                    return [types.TextContent(type="text", text="\n".join(lines))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"❌ Error consultando historial: {e}")]

        else:
            return [types.TextContent(type="text", text=f"❌ Herramienta desconocida: {name}")]

    except FileNotFoundError as e:
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error: {str(e)}")]


# -------------------------------------------------------
# Punto de entrada
# -------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
