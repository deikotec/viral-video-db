"""
Configuración central del sistema Viral Video DB.
Edita este archivo con tus API keys antes de usar el sistema.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# =============================================================
# API KEYS - Definir en tu archivo .env
# =============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_GEMINI_API_KEY_AQUI")
# Obtén tu key en: https://aistudio.google.com/app/apikey

# =============================================================
# SUPABASE - Base de datos en la nube
# =============================================================
# Obtén tus credenciales en: Supabase Dashboard → Settings → API
# Usa la SERVICE ROLE key (no la anon key) para acceso completo desde scripts

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xyzabc.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "TU_SUPABASE_SERVICE_ROLE_KEY")
# Usa la "service_role" key para acceso sin restricciones desde el backend

# =============================================================
# RUTAS DEL SISTEMA
# =============================================================

BASE_DIR = "c:/xampp/htdocs/claude/rrss ideas"
VIDEOS_DIR = f"{BASE_DIR}/videos"
HOOKS_JSON = f"{BASE_DIR}/hooks_data.json"

# =============================================================
# CONFIGURACIÓN DE DESCARGA
# =============================================================

# Número máximo de videos a descargar en una ejecución (para no saturar)
MAX_DOWNLOADS_PER_RUN = 50

# Resolución máxima para descargar (360p es suficiente para análisis)
VIDEO_MAX_HEIGHT = 720

# Tiempo máximo de espera entre descargas (segundos) para no ser bloqueado
DOWNLOAD_DELAY_MIN = 2
DOWNLOAD_DELAY_MAX = 5

# Número máximo de workers paralelos para análisis
MAX_WORKERS = 3

# =============================================================
# CONFIGURACIÓN DE GEMINI
# =============================================================

# Modelo de Gemini a usar (gemini-1.5-flash es más económico, gemini-1.5-pro es más potente)
GEMINI_MODEL = "gemini-3-flash-preview"

# Prompt base para el análisis de videos
GEMINI_ANALYSIS_PROMPT = """
Eres un experto en marketing de contenido viral para redes sociales.
Analiza este video de Instagram de forma DETALLADA y EXHAUSTIVA.

Devuelve el análisis en formato JSON con exactamente esta estructura:

{
  "titulo_descriptivo": "Título corto que describe el video",
  "duracion_estimada": "duración en segundos",
  "formato": "Reel/Carrusel/Historia/Video largo",
  "plataforma": "Instagram/TikTok/YouTube Shorts",
  
  "hook": {
    "tipo": "Tipo de hook (pregunta/afirmación/shock/curiosidad/beneficio/etc)",
    "texto_hook": "Texto exacto del hook (primeros 3 segundos)",
    "duracion_hook_segundos": 3,
    "tecnica": "Técnica usada para captar atención",
    "elemento_visual_hook": "Qué se ve en pantalla durante el hook"
  },
  
  "estructura_narrativa": {
    "partes": [
      {
        "nombre": "Hook/Introducción/Desarrollo/CTA/etc",
        "duracion_segundos": 0,
        "descripcion": "Qué sucede en esta parte",
        "tecnica_narrativa": "Técnica usada"
      }
    ],
    "arco_emocional": "Descripción del viaje emocional del espectador",
    "ritmo": "Lento/Medio/Rápido/Muy rápido",
    "densidad_informacion": "Baja/Media/Alta/Muy alta"
  },
  
  "tomas_y_planos": [
    {
      "tipo_plano": "Primer plano/Plano medio/Plano general/etc",
      "angulo": "Frontal/Picado/Contrapicado/Lateral/etc",
      "movimiento": "Estático/Pan/Tilt/Zoom/Tracking/Handheld",
      "duracion_aprox": "duración en segundos",
      "proposito": "Por qué se usa este plano aquí"
    }
  ],
  
  "produccion": {
    "calidad_video": "Baja/Media/Alta/Muy alta",
    "iluminacion": "Natural/Artificial/Mixta - descripción",
    "escenario": "Descripción del lugar/fondo",
    "elementos_visuales": ["Lista de elementos visuales destacados"],
    "subtitulos": true,
    "texto_en_pantalla": "Descripción del texto superpuesto si hay",
    "efectos_visuales": ["Lista de efectos usados"],
    "transiciones": "Tipo de transiciones usadas",
    "color_grading": "Descripción del color/filtros"
  },
  
  "audio": {
    "voz_en_off": true,
    "habla_a_camara": true,
    "tono_voz": "Energético/Calmado/Urgente/Conversacional/etc",
    "musica": {
      "tiene_musica": true,
      "genero": "Pop/Hip-hop/Electrónica/Sin música/etc",
      "posicion": "Fondo/Principal",
      "proposito": "Crear urgencia/Relajar/Motivar/etc"
    },
    "efectos_sonido": ["Lista de efectos de sonido si hay"]
  },
  
  "guion": {
    "texto_completo": "Transcripción completa del guion/narración",
    "estilo_escritura": "Conversacional/Formal/Humorístico/Educativo/etc",
    "palabras_clave": ["palabras o frases que se repiten o son clave"],
    "call_to_action": "CTA usado al final si hay"
  },
  
  "estrategia_viral": {
    "por_que_es_viral": "Análisis de por qué este video funciona",
    "emocion_principal": "Emoción que genera (curiosidad/risa/sorpresa/etc)",
    "factor_compartir": "Por qué la gente lo comparte",
    "audiencia_objetivo": "A quién va dirigido",
    "nicho": "Nicho o industria del video",
    "patron_viral": "Patrón viral identificado (antes/después, ranking, tutorial, etc)"
  },
  
  "replicabilidad": {
    "nivel_dificultad": "Fácil/Medio/Difícil",
    "equipamiento_necesario": ["Lista de equipos necesarios"],
    "skills_necesarios": ["Habilidades requeridas"],
    "tiempo_produccion_estimado": "Estimado en horas",
    "costo_produccion": "Bajo/Medio/Alto",
    "adaptable_a_otros_nichos": true,
    "nichos_compatibles": ["Lista de nichos donde este formato funciona bien"]
  },
  
  "tags": ["etiquetas descriptivas del video para búsqueda"]
}

Sé específico y detallado. Si no puedes ver/escuchar algo claramente, indícalo con "No visible" o "No audible".
"""

# =============================================================
# CONFIGURACIÓN DE GENERACIÓN DE IDEAS
# =============================================================

IDEA_GENERATION_PROMPT = """
Eres un director creativo experto en contenido viral para redes sociales.

Tienes acceso a una base de datos de {num_references} videos virales analizados.

CONTEXTO DE LA EMPRESA:
{company_context}

OBJETIVO DEL VIDEO:
{video_objective}

PLATAFORMA TARGET:
{platform}

VIDEOS VIRALES DE REFERENCIA MÁS RELEVANTES:
{reference_videos}

Basándote en los videos virales de referencia y el contexto de la empresa, crea una idea de video COMPLETA y DETALLADA.

La idea debe ser:
1. Adaptada al nicho/industria de la empresa
2. Basada en un patrón viral COMPROBADO (de la referencia)
3. Lista para producir (guion completo, planos, música)
4. Realista con los recursos de una empresa mediana

Devuelve la respuesta en formato JSON con esta estructura:

{{
  "titulo_concepto": "Nombre descriptivo de la idea",
  "hook_principal": "El hook exacto para empezar el video",
  "por_que_funcionara": "Justificación basada en el patrón viral de referencia",
  "referencia_viral": {{
    "url": "URL del video viral de referencia",
    "patron": "Qué patrón viral se está usando"
  }},
  
  "guion_completo": {{
    "hook_0_3seg": "Texto exacto del hook (primeros 3 segundos)",
    "desarrollo": "Texto del desarrollo del video",
    "cierre_cta": "Texto del cierre y call to action"
  }},
  
  "plan_de_tomas": [
    {{
      "numero": 1,
      "descripcion": "Qué se graba",
      "tipo_plano": "Tipo de plano",
      "duracion": "X segundos",
      "notas_direccion": "Instrucciones para el operador de cámara/persona que graba"
    }}
  ],
  
  "produccion": {{
    "duracion_total": "X segundos",
    "formato": "Vertical 9:16 / Cuadrado 1:1",
    "escenario": "Dónde grabar",
    "iluminacion": "Cómo iluminar",
    "vestuario_props": "Qué usar/traer",
    "musica_sugerida": "Tipo de música + búsqueda sugerida en Epidemic Sound/Pixabay",
    "efectos_visuales": "Efectos a agregar en edición",
    "subtitulos": "Sí/No y estilo sugerido",
    "texto_en_pantalla": "Texto extra a superponer si aplica"
  }},
  
  "edicion": {{
    "ritmo": "Rápido/Medio - instrucciones de ritmo",
    "transiciones": "Tipo de transiciones",
    "color": "Filtro/color grading sugerido",
    "herramientas_sugeridas": ["CapCut", "Premiere", "etc"]
  }},
  
  "estrategia_publicacion": {{
    "mejor_horario": "Día y hora sugerida",
    "caption_sugerido": "Caption completo para el post",
    "hashtags": ["lista de hashtags sugeridos"],
    "cta_caption": "Call to action para el caption"
  }},
  
  "metricas_objetivo": {{
    "kpi_principal": "Reproducciones/Guardados/Clics/Ventas",
    "expectativa_realista": "Rango esperado según el patrón viral"
  }}
}}
"""
