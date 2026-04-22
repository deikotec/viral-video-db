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

BASE_DIR = "c:/xampp/htdocs/viral-video"
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
Eres un director creativo experto en marketing de contenido viral con 10+ años de experiencia creando videos que superan el millón de reproducciones.

Tienes acceso a {num_references} videos virales REALES analizados con IA, con sus técnicas exactas documentadas.

═══════════════════════════════════════════════════════════════
CONTEXTO DE LA EMPRESA:
{company_context}

OBJETIVO ESPECÍFICO DEL VIDEO:
{video_objective}

PLATAFORMA TARGET:
{platform}
═══════════════════════════════════════════════════════════════

VIDEOS VIRALES DE REFERENCIA (análisis completo de cada uno):
{reference_videos}

═══════════════════════════════════════════════════════════════
INSTRUCCIONES CRÍTICAS — LEE ANTES DE GENERAR:

1. Analiza TODAS las referencias y elige la que mejor encaje con el negocio y objetivo.
2. El campo "referencia_viral.url" DEBE ser la URL EXACTA del video que aparece en la lista de referencias de arriba. NO inventes ni modifiques URLs.
3. Adapta el guion al negocio específico — nada genérico. Cada frase debe sonar real para esa empresa.
4. El hook DEBE capturar atención en los primeros 3 segundos usando exactamente el patrón del video de referencia elegido.
5. Las instrucciones de toma deben ser tan claras que alguien sin experiencia pueda grabarlas solo.
6. Sé lo MÁS DETALLADO POSIBLE en cada sección — más detalle = mejor producción = más posibilidades virales.
7. El guion_completo.texto_completo debe ser el guion entero, listo para leer en cámara, incluyendo pausas y énfasis.
═══════════════════════════════════════════════════════════════

Devuelve la respuesta en formato JSON con esta estructura COMPLETA (no omitas ningún campo):

{{
  "titulo_concepto": "Nombre descriptivo y memorable de la idea de video",

  "hook_principal": "El hook exacto para los primeros 3 segundos — texto listo para decir/mostrar en cámara",

  "por_que_funcionara": "Análisis detallado: qué patrón viral de la referencia se aplica, por qué genera la emoción correcta en esta audiencia, y cómo se adapta al negocio específico",

  "referencia_viral": {{
    "url": "URL EXACTA copiada del listado de referencias (no inventes)",
    "patron": "Nombre del patrón viral aplicado (ej: antes/después, tutorial paso a paso, ranking, historia personal, shock/sorpresa, tip rápido)",
    "por_que_elegida": "Por qué esta referencia específica es la más relevante para este negocio y objetivo",
    "elementos_adaptados": "Qué técnicas concretas del video de referencia se están usando en este guion"
  }},

  "guion_completo": {{
    "hook_0_3seg": "Texto exacto del hook — las primeras palabras que se dicen o aparecen en pantalla",
    "desarrollo_3_20seg": "Texto exacto del desarrollo — contenido principal con argumentos o beneficios",
    "cuerpo_20_27seg": "Texto exacto del cuerpo — demostración, prueba social o refuerzo emocional",
    "cierre_cta": "Texto exacto del cierre con llamada a la acción directa y urgente",
    "texto_completo": "GUION COMPLETO de principio a fin, exactamente como se debe leer en cámara, con [PAUSA], [ÉNFASIS], [MOSTRAR X] como indicaciones de dirección"
  }},

  "plan_de_tomas": [
    {{
      "numero": 1,
      "timestamp": "0s - 3s",
      "descripcion": "Descripción detallada de exactamente qué se ve en pantalla",
      "tipo_plano": "Primer plano / Plano medio / Plano general / Plano detalle / Plano americano",
      "angulo_camara": "Frontal / Picado / Contrapicado / Lateral / 45 grados",
      "movimiento": "Estático / Pan lento / Zoom in / Zoom out / Handheld (tembloroso natural)",
      "duracion": "X segundos",
      "dialogo_en_toma": "Texto exacto que se dice durante esta toma",
      "notas_director": "Instrucciones precisas: posición del cuerpo, expresión, qué mostrar, qué evitar, velocidad de movimiento"
    }}
  ],

  "produccion": {{
    "duracion_total": "XX segundos",
    "formato": "Vertical 9:16",
    "escenario": "Dónde grabar exactamente y cómo preparar ese espacio (qué poner, qué quitar del fondo)",
    "iluminacion": "Instrucciones detalladas: tipo de luz, posición, qué evitar (sombras duras, contraluz), alternativa económica si no hay equipo",
    "vestuario": "Qué ponerse y qué NO ponerse, con justificación según el tono del video",
    "props": "Lista de objetos o elementos necesarios en escena y cómo usarlos",
    "musica_sugerida": "Género + mood + tempo + búsqueda sugerida en Epidemic Sound o Pixabay (ej: 'uplifting corporate soft 120bpm')",
    "volumen_musica": "Nivel de volumen respecto a la voz (ej: 15-20% de fondo, que no tape la voz)",
    "efectos_visuales": "Lista de efectos a agregar en edición: texto animado, stickers, zoom, etc. con el momento exacto",
    "subtitulos": "Sí/No — estilo recomendado (ej: fuente bold grande centrada, blanco con sombra negra, cada 3-4 palabras)",
    "texto_en_pantalla": "Textos o títulos extra a superponer, en qué segundo y con qué estilo"
  }},

  "edicion": {{
    "ritmo": "Descripción del ritmo de cortes con instrucciones específicas (ej: corte cada 2s en el hook, cada 3-4s en el desarrollo)",
    "transiciones": "Tipos de transición y en qué momentos usarlas (ej: corte directo en el hook, fundido suave al cierre)",
    "color_grading": "Filtro o ajustes de color específicos (ej: +15 saturación, +10 contraste, temperatura cálida 5500K)",
    "efectos_especiales": "Efectos específicos con timing (ej: zoom rápido al decir la palabra clave, slow-motion en el resultado)",
    "herramientas_sugeridas": ["CapCut (gratis, móvil)", "Adobe Premiere", "DaVinci Resolve (gratis, PC)"],
    "tips_edicion": ["Consejo 1 clave de edición", "Consejo 2 clave", "Consejo 3 clave para que el video se vea profesional"]
  }},

  "estrategia_publicacion": {{
    "mejor_horario": "Día(s) de la semana y franja horaria con justificación según la plataforma y audiencia objetivo",
    "caption_sugerido": "Caption completo listo para copiar y pegar — con emojis, saltos de línea naturales, storytelling breve y CTA al final",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "cta_caption": "Call to action específico para el caption (ej: 'Escríbenos CONSULTA al DM y te damos precio')",
    "primer_comentario": "Texto para el primer comentario propio justo después de publicar (mejora el SEO y engagement inicial)",
    "estrategia_primeras_horas": "Qué hacer en las primeras 2 horas después de publicar para maximizar el alcance orgánico"
  }},

  "variaciones_ab": [
    {{
      "nombre": "Variación A — descripción breve",
      "hook_alternativo": "Hook diferente para testear (mismo video, diferente inicio)",
      "diferencia_clave": "En qué se diferencia del video principal y qué hipótesis estás testando"
    }},
    {{
      "nombre": "Variación B — descripción breve",
      "hook_alternativo": "Otro hook diferente",
      "diferencia_clave": "En qué se diferencia"
    }}
  ],

  "metricas_objetivo": {{
    "kpi_principal": "Métrica principal (ej: reproducciones, guardados, clics en enlace, mensajes directos)",
    "kpi_secundario": "Métrica secundaria de soporte",
    "expectativa_realista": "Rango esperado en los primeros 7 días basado en el patrón viral de referencia",
    "senales_exito_24h": "Números mínimos en las primeras 24h que indican que el video tiene potencial viral",
    "cuando_reutilizar": "Si el video funciona, cuándo y cómo reutilizarlo o convertirlo en anuncio pagado"
  }},

  "checklist_preproduccion": [
    "Verificación 1 antes de grabar",
    "Verificación 2",
    "Verificación 3"
  ],

  "errores_frecuentes": [
    "Error común 1 al producir este tipo de video y cómo evitarlo",
    "Error común 2",
    "Error común 3"
  ]
}}
"""
