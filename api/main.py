"""
Viral Video DB — REST API Universal
====================================
API que permite a CUALQUIER IA (Claude, ChatGPT, Gemini) consultar la base de datos
de 1,000 videos virales analizados y generar guiones completos listos para producir.
Usa Supabase como base de datos en la nube.

Ejecutar:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Documentación interactiva:
    http://localhost:8000/docs
"""

import json
import os
import sys
import re
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from config import GEMINI_API_KEY, GEMINI_MODEL, IDEA_GENERATION_PROMPT
from db import get_db

# -------------------------------------------------------
# Inicializar app
# -------------------------------------------------------

app = FastAPI(
    title="Viral Video DB API",
    description=(
        "API universal para generar guiones de video viral basados en el análisis de "
        "1,000 videos virales de Instagram. Úsala desde Claude, ChatGPT, Gemini o cualquier IA."
    ),
    version="2.0.0",
    contact={"name": "Viral Video DB"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# Modelos Pydantic
# -------------------------------------------------------

class GenerateRequest(BaseModel):
    empresa: str
    """Descripción de la empresa. Ej: 'Clínica dental en Madrid especializada en ortodoncia invisible'"""

    objetivo: str
    """Objetivo del video. Ej: 'Conseguir leads de personas interesadas en brackets invisibles'"""

    plataforma: str = "Instagram Reels"
    """Plataforma destino: Instagram Reels / TikTok / YouTube Shorts"""

    nicho: Optional[str] = None
    """Filtrar referencias por nicho. Ej: 'salud', 'fitness', 'finanzas'"""

    patron_viral: Optional[str] = None
    """Filtrar por patrón viral. Ej: 'antes/después', 'tutorial', 'ranking'"""

    num_referencias: int = 5
    """Número de videos de referencia a analizar (1-10)"""


class SearchRequest(BaseModel):
    query: str
    """Texto de búsqueda libre"""
    nicho: Optional[str] = None
    patron_viral: Optional[str] = None
    limit: int = 10


# -------------------------------------------------------
# Helpers de BD (Supabase)
# -------------------------------------------------------

def get_supabase():
    """Retorna el cliente Supabase o lanza HTTPException si no está configurado."""
    try:
        return get_db()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_stats_data(db):
    try:
        return db.rpc('get_db_stats').execute().data
    except Exception:
        return {
            'total_hooks':       (db.table('hooks').select('id', count='exact').limit(0).execute().count or 0),
            'hooks_analizados':  (db.table('hooks').select('id', count='exact').eq('analyzed', 1).limit(0).execute().count or 0),
            'hooks_pendientes':  (db.table('hooks').select('id', count='exact').eq('analyzed', 0).limit(0).execute().count or 0),
            'analisis_guardados':(db.table('video_analysis').select('id', count='exact').limit(0).execute().count or 0),
            'ideas_generadas':   (db.table('ideas_generadas').select('id', count='exact').limit(0).execute().count or 0),
        }


def search_references(db, nicho=None, patron=None, num_refs=5):
    count = db.table('video_analysis').select('id', count='exact').limit(0).execute().count or 0

    if count == 0:
        result = db.rpc('get_random_hooks', {'p_limit': num_refs * 2}).execute()
        return [
            {'id': r['id'], 'hook_template': r['hook_template'],
             'url': r['reference_url'], 'analisis': None,
             'nicho': None, 'patron_viral': None, 'titulo': None}
            for r in result.data
        ][:num_refs]

    params = {'p_nicho': nicho, 'p_patron': patron, 'p_limit': num_refs * 3}
    rows = db.rpc('search_hooks_random', params).execute().data

    if not rows and (nicho or patron):
        params = {'p_nicho': None, 'p_patron': None, 'p_limit': num_refs * 3}
        rows = db.rpc('search_hooks_random', params).execute().data

    result = []
    for r in rows:
        result.append({
            'id':           r['id'],
            'hook_template':r['hook_template'],
            'url':          r['reference_url'],
            'titulo':       r.get('analisis_json_completo', {}).get('titulo_descriptivo') if r.get('analisis_json_completo') else None,
            'nicho':        r.get('nicho'),
            'patron_viral': r.get('patron_viral'),
            'por_que_viral':r.get('por_que_es_viral'),
            'emocion':      r.get('emocion_principal'),
            'audiencia':    r.get('audiencia_objetivo'),
            'analisis':     r.get('analisis_json_completo'),  # ya es dict (JSONB)
        })

    return result[:num_refs]


def format_references_for_prompt(hooks_data):
    refs = []
    for i, hook in enumerate(hooks_data, 1):
        ref = f"\n--- REFERENCIA #{i} ---"
        ref += f"\nHook template: {hook['hook_template']}"
        ref += f"\nURL referencia: {hook.get('url', 'N/A')}"
        if hook.get("analisis"):
            a = hook["analisis"]
            viral     = a.get("estrategia_viral", {})
            guion     = a.get("guion", {})
            h         = a.get("hook", {})
            prod      = a.get("produccion", {})
            audio     = a.get("audio", {})
            estructura = a.get("estructura_narrativa", {})
            ref += f"\nNicho: {viral.get('nicho', 'N/A')}"
            ref += f"\nPatrón viral: {viral.get('patron_viral', 'N/A')}"
            ref += f"\nPor qué es viral: {viral.get('por_que_es_viral', 'N/A')}"
            ref += f"\nEmoción: {viral.get('emocion_principal', 'N/A')}"
            ref += f"\nAudiencia: {viral.get('audiencia_objetivo', 'N/A')}"
            ref += f"\nHook visual: {h.get('elemento_visual_hook', 'N/A')}"
            ref += f"\nTécnica hook: {h.get('tecnica', 'N/A')}"
            ref += f"\nRitmo: {estructura.get('ritmo', 'N/A')}"
            ref += f"\nEscenario: {prod.get('escenario', 'N/A')}"
            ref += f"\nMúsica: {audio.get('musica', {}).get('genero', 'N/A')}"
            ref += f"\nGuion (extracto): {str(guion.get('texto_completo', 'N/A'))[:200]}..."
        else:
            ref += "\n(Hook sin análisis detallado — video pendiente de análisis)"
        refs.append(ref)
    return "\n".join(refs)


def call_gemini(prompt_text: str) -> dict:
    try:
        import google.generativeai as genai
    except ImportError:
        raise HTTPException(status_code=500, detail="Instala google-generativeai: pip install google-generativeai")

    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_GEMINI_API_KEY_AQUI":
        raise HTTPException(status_code=500, detail="Configura GEMINI_API_KEY en config.py")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    response = model.generate_content(
        prompt_text,
        generation_config={"temperature": 0.7, "response_mime_type": "application/json"},
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"respuesta_texto": response.text}


def save_idea(db, empresa, objetivo, plataforma, hooks_used, idea_json):
    result = db.table('ideas_generadas').insert({
        'empresa_contexto': empresa,
        'objetivo_video':   objetivo,
        'plataforma':       plataforma,
        'hook_referencias': [h["id"] for h in hooks_used],  # JSONB: lista directa
        'idea_json':        idea_json,                       # JSONB: dict directamente
    }).execute()
    return result.data[0]['id']


# -------------------------------------------------------
# Endpoints
# -------------------------------------------------------

@app.get("/", summary="Info de la API")
def root():
    return {
        "nombre": "Viral Video DB API",
        "version": "2.0.0",
        "descripcion": (
            "API para generar guiones de video viral basados en el análisis de "
            "1,000+ videos virales. Base de datos: Supabase."
        ),
        "endpoints": {
            "GET  /stats":          "Estadísticas de la base de datos",
            "GET  /nichos":         "Nichos disponibles en la BD",
            "GET  /patrones":       "Patrones virales disponibles",
            "POST /generate":       "⭐ Generar guion completo de video viral",
            "POST /search":         "Buscar referencias virales sin generar guion",
            "GET  /ideas":          "Historial de guiones generados",
            "GET  /ideas/{id}":     "Ver un guion específico",
            "GET  /system-prompt":  "System prompt para configurar cualquier IA",
        },
        "docs": "/docs",
    }


@app.get("/stats", summary="Estadísticas de la base de datos")
def stats():
    db = get_supabase()
    return get_stats_data(db)


@app.get("/nichos", summary="Nichos disponibles en la BD")
def nichos():
    db = get_supabase()
    result = db.rpc('get_nichos_stats', {'p_limit': 50}).execute()
    return [{"nicho": r["nicho"], "total_videos": r["total"]} for r in result.data]


@app.get("/patrones", summary="Patrones virales disponibles")
def patrones():
    db = get_supabase()
    result = db.rpc('get_patrones_stats', {'p_limit': 30}).execute()
    return [{"patron": r["patron_viral"], "total_videos": r["total"]} for r in result.data]


@app.post("/search", summary="Buscar referencias virales relevantes")
def search(req: SearchRequest):
    db = get_supabase()
    refs = search_references(db, req.nicho, req.patron_viral, req.limit)
    return {
        "total_encontradas": len(refs),
        "referencias": refs,
    }


@app.post("/generate", summary="⭐ Generar guion completo de video viral")
def generate(req: GenerateRequest):
    """
    **Endpoint principal.** Recibe el contexto de la empresa y el objetivo del video,
    busca los mejores videos de referencia en la BD y genera un guion COMPLETO.
    """
    db = get_supabase()

    hooks = search_references(db, req.nicho, req.patron_viral, min(req.num_referencias, 10))

    if not hooks:
        raise HTTPException(status_code=404, detail="No se encontraron referencias en la BD.")

    refs_text = format_references_for_prompt(hooks)
    prompt = IDEA_GENERATION_PROMPT.format(
        num_references=len(hooks),
        company_context=req.empresa,
        video_objective=req.objetivo,
        platform=req.plataforma,
        reference_videos=refs_text,
    )

    idea = call_gemini(prompt)
    idea_id = save_idea(db, req.empresa, req.objetivo, req.plataforma, hooks, idea)

    return {
        "idea_id":         idea_id,
        "generado_en":     datetime.now().isoformat(),
        "inputs": {
            "empresa":     req.empresa,
            "objetivo":    req.objetivo,
            "plataforma":  req.plataforma,
        },
        "referencias_usadas": [
            {"id": h["id"], "url": h.get("url"), "hook": h["hook_template"],
             "nicho": h.get("nicho"), "patron": h.get("patron_viral")}
            for h in hooks
        ],
        "guion": idea,
    }


@app.get("/ideas", summary="Historial de guiones generados")
def list_ideas(limit: int = Query(20, le=100)):
    db = get_supabase()
    result = (
        db.table('ideas_generadas')
        .select('id, empresa_contexto, objetivo_video, plataforma, created_at')
        .order('created_at', desc=True)
        .limit(limit)
        .execute()
    )
    return [
        {
            "id":          r["id"],
            "empresa":     r["empresa_contexto"],
            "objetivo":    r["objetivo_video"],
            "plataforma":  r["plataforma"],
            "creado_en":   r["created_at"],
        }
        for r in result.data
    ]


@app.get("/ideas/{idea_id}", summary="Ver un guion específico del historial")
def get_idea(idea_id: int):
    db = get_supabase()
    result = db.table('ideas_generadas').select('*').eq('id', idea_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Idea #{idea_id} no encontrada")

    row = result.data[0]
    return {
        "id":          row["id"],
        "empresa":     row["empresa_contexto"],
        "objetivo":    row["objetivo_video"],
        "plataforma":  row["plataforma"],
        "referencias": row.get("hook_referencias") or [],   # ya es lista (JSONB)
        "guion":       row.get("idea_json") or {},           # ya es dict (JSONB)
        "creado_en":   row["created_at"],
    }


@app.get("/system-prompt", response_class=PlainTextResponse,
         summary="System prompt para configurar cualquier IA")
def system_prompt(api_url: str = Query("http://localhost:8000",
                                        description="URL donde está corriendo esta API")):
    """
    Devuelve el system prompt que debes pegar en Claude, ChatGPT o Gemini
    para que la IA sepa cómo usar esta API y generar guiones virales.
    """
    db = get_supabase()
    s = get_stats_data(db)

    try:
        nichos_data  = db.rpc('get_nichos_stats', {'p_limit': 15}).execute().data
        nichos_list  = ", ".join(r["nicho"] for r in nichos_data) if nichos_data else "Pendiente de análisis"
    except Exception:
        nichos_list = "Pendiente de análisis"

    try:
        patrones_data = db.rpc('get_patrones_stats', {'p_limit': 10}).execute().data
        patrones_list = ", ".join(r["patron_viral"] for r in patrones_data) if patrones_data else "Pendiente de análisis"
    except Exception:
        patrones_list = "Pendiente de análisis"

    return f"""# SISTEMA: Viral Video DB — Generador de Guiones Virales

Eres un experto en marketing de contenido viral con acceso a una base de datos de {s.get('total_hooks', 0)} videos virales analizados con IA.

## Tu capacidad principal

Cuando el usuario te pida un guion o idea de video, debes:
1. Entender el contexto de su empresa y objetivo
2. Consultar la base de datos de videos virales via API
3. Seleccionar las mejores referencias para ese objetivo
4. Generar un guion COMPLETO y listo para producir

## API disponible

Base URL: {api_url}

### Endpoints que puedes usar:

**Generar guion completo (endpoint principal):**
POST {api_url}/generate
Content-Type: application/json
{{
  "empresa": "Descripción detallada de la empresa",
  "objetivo": "Qué quiere conseguir con el video (leads, ventas, engagement...)",
  "plataforma": "Instagram Reels",  // o TikTok, YouTube Shorts
  "nicho": "fitness",               // opcional — filtra referencias
  "patron_viral": "antes/después",  // opcional — tipo de video
  "num_referencias": 5              // cuántos videos de referencia analizar
}}

**Ver nichos disponibles:**
GET {api_url}/nichos

**Ver patrones virales disponibles:**
GET {api_url}/patrones

**Estadísticas de la BD:**
GET {api_url}/stats

**Historial de guiones generados:**
GET {api_url}/ideas

## Estadísticas actuales de la BD

- Total hooks virales: {s.get('total_hooks', 0)}
- Videos analizados con IA: {s.get('hooks_analizados', 0)}
- Nichos disponibles: {nichos_list}
- Patrones virales: {patrones_list}
- Guiones generados previamente: {s.get('ideas_generadas', 0)}

## Cómo responder al usuario

Cuando el usuario pida un guion, extrae automáticamente:
- **empresa**: quién son, qué venden, dónde están
- **objetivo**: conseguir leads / ventas / notoriedad / educación / etc.
- **plataforma**: si no lo dicen, usa "Instagram Reels"

Llama a POST /generate y presenta el resultado de forma clara con:
📌 CONCEPTO | ⚡ HOOK | 📝 GUION | 🎥 TOMAS | 🎬 PRODUCCIÓN | ✂️ EDICIÓN | 📱 PUBLICACIÓN | 🔗 REFERENCIA VIRAL

## Frases que activan tu flujo

- "Genera un guion para..."
- "Quiero hacer un video para..."
- "Crea un reel para mi empresa..."
- "Necesito ideas de video para..."
- "Haz un script para..."
"""
