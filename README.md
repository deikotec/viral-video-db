# 🎬 Viral Video DB — Sistema de Guiones Virales con IA

Sistema completo para analizar ~1,000 videos virales de Instagram con IA y generar **guiones completos listos para producir** desde **cualquier IA** (Claude, ChatGPT, Gemini, o cualquier otra).

---

## 🧠 ¿Cómo funciona?

```
PDF con 1,000 hooks virales
        ↓
  extract_pdf_data.py     → Extrae hooks + URLs de Instagram
        ↓
  setup_supabase.py       → Genera SQL para crear tablas en Supabase
        ↓
  setup_database.py       → Sube los 1,003 hooks a Supabase
        ↓
  download_videos.py      → Descarga los videos con yt-dlp
        ↓
  analyze_with_gemini.py  → Analiza cada video: hook, tomas, guion,
                            música, estrategia viral, replicabilidad...
        ↓
  Supabase                → Base de datos en la nube con TODO el conocimiento viral
        ↓
  ┌─────────────────────────────────────────────────────┐
  │           3 FORMAS DE ACCEDER DESDE CUALQUIER IA    │
  │                                                     │
  │  🔌 MCP Server  →  Claude Desktop (nativo)          │
  │  🌐 API REST    →  ChatGPT / Gemini / cualquier IA  │
  │  📄 Contexto MD →  Pegar en cualquier chat IA       │
  └─────────────────────────────────────────────────────┘
        ↓
  La IA recibe: empresa + objetivo
  La IA busca: mejores referencias virales en la BD
  La IA genera: guion COMPLETO listo para producir
```

---

## 📁 Estructura del proyecto

```
rrss ideas/
├── 📄 1,000 Viral Hooks (PBL).pdf      → PDF fuente
├── ⚙️  config.py                        → API keys y configuración
├── 🔧 extract_pdf_data.py               → Extractor del PDF
├── 🗄️  setup_supabase.py                → Inicializador SQL para Supabase
├── 🗄️  setup_database.py                → Migra hooks a Supabase
├── ⬇️  download_videos.py               → Descargador de videos
├── 🤖 analyze_with_gemini.py            → Analizador con Gemini AI
├── 💡 generate_video_idea.py            → Generador CLI (uso local)
├── 📤 export_context.py                 → Exporta contexto para IAs
│
├── 📁 api/                              → API REST Universal
│   ├── main.py                          → FastAPI app completa
│   ├── openapi_chatgpt.json             → Spec OpenAPI para ChatGPT
│   └── __init__.py
│
├── 📁 mcp_server/                       → MCP para Claude Desktop
│   ├── server.py                        → Servidor MCP nativo
│   └── __init__.py
│
├── 🔧 claude_desktop_config.json        → Config lista para Claude
├── 📋 requirements.txt                  → Dependencias Python
├── 📊 hooks_data.json                   → 1,003 hooks extraídos
├── 🗄️  .env                             → Credenciales de Supabase y Gemini
└── 📁 videos/                           → Videos descargados
```

---

## 🚀 Instalación rápida

```bash
# 1. Instalar todas las dependencias
pip install -r requirements.txt

# 2. Configurar tu API key de Gemini en config.py
# Obtén tu key GRATIS en: https://aistudio.google.com/app/apikey

# 3. Inicializar la base de datos en Supabase
# Primero obtén el SQL para crear las tablas:
python setup_supabase.py
# (Ejecuta el SQL en el dashboard de Supabase)
# Luego sube los hooks:
python setup_database.py

# 4. Descargar los primeros 10 videos y analizarlos
python download_videos.py --limit 10
python analyze_with_gemini.py --limit 10
```

---

## 🤖 3 FORMAS DE USAR DESDE CUALQUIER IA

---

### 🔌 OPCIÓN 1: MCP Server para Claude Desktop (recomendado para Claude)

La forma más potente. Claude Desktop tendrá acceso directo a la BD con herramientas nativas.

#### Instalar

```bash
pip install mcp
```

#### Configurar Claude Desktop

1. Abre el archivo `claude_desktop_config.json` de este proyecto
2. Copia el bloque `mcpServers`
3. Pégalo en tu configuración real de Claude Desktop:
   - **Windows:** `C:\Users\TU_USUARIO\AppData\Roaming\Claude\claude_desktop_config.json`
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "viral-video-db": {
      "command": "python",
      "args": ["c:/xampp/htdocs/viral-video/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "c:/xampp/htdocs/viral-video"
      }
    }
  }
}
```

4. Reinicia Claude Desktop

#### Herramientas disponibles en Claude

| Herramienta               | Descripción                   |
| ------------------------- | ----------------------------- |
| `get_db_stats`            | Estadísticas de la BD         |
| `list_nichos`             | Nichos disponibles            |
| `list_patrones_virales`   | Patrones virales disponibles  |
| `search_viral_references` | Buscar referencias relevantes |
| `generate_video_script`   | ⭐ Generar guion completo     |
| `get_idea_history`        | Historial de guiones          |

#### Uso en Claude Desktop

Una vez configurado, simplemente escribe en Claude:

> _"Genera un guion para una clínica dental en Madrid que quiere conseguir leads para brackets invisibles"_

Claude automáticamente:

1. Buscará las mejores referencias virales en tu BD
2. Seleccionará el patrón más adecuado
3. Generará el guion completo con tomas, producción, música y publicación

---

### 🌐 OPCIÓN 2: API REST (para ChatGPT, Gemini, o cualquier IA con tools)

Una API REST local que cualquier IA puede consultar via HTTP.

#### Iniciar la API

```bash
# Iniciar el servidor
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Documentación interactiva disponible en:
# http://localhost:8000/docs
```

#### Endpoints principales

| Método | Endpoint         | Descripción                                |
| ------ | ---------------- | ------------------------------------------ |
| `GET`  | `/`              | Info de la API                             |
| `GET`  | `/stats`         | Estadísticas de la BD                      |
| `GET`  | `/nichos`        | Nichos disponibles                         |
| `GET`  | `/patrones`      | Patrones virales                           |
| `POST` | `/generate`      | ⭐ Generar guion completo                  |
| `POST` | `/search`        | Buscar referencias                         |
| `GET`  | `/ideas`         | Historial de guiones                       |
| `GET`  | `/ideas/{id}`    | Ver guion específico                       |
| `GET`  | `/system-prompt` | System prompt para configurar cualquier IA |

#### Generar un guion via API

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": "Clínica dental en Madrid especializada en ortodoncia invisible",
    "objetivo": "Conseguir leads de personas interesadas en brackets invisibles",
    "plataforma": "Instagram Reels",
    "nicho": "salud",
    "num_referencias": 5
  }'
```

#### Para ChatGPT — Custom GPT con Actions

1. Inicia la API: `uvicorn api.main:app --port 8000`
2. Expón la API a internet (usa [ngrok](https://ngrok.com/): `ngrok http 8000`)
3. En ChatGPT → Explorar GPTs → Crear → Configuración → Acciones
4. Importa el schema desde `api/openapi_chatgpt.json`
   - Cambia la URL del servidor por tu URL de ngrok
5. En instrucciones del GPT, pega el contenido de: `GET http://localhost:8000/system-prompt`

#### Para Gemini — Extensions / API

1. Inicia la API y exponla con ngrok
2. En [Gemini Extensions](https://gemini.google.com/) o via API de Gemini con Function Calling
3. Registra los endpoints como funciones disponibles

#### Obtener el system prompt dinámico

```bash
# Genera el system prompt actualizado con las stats de tu BD
curl "http://localhost:8000/system-prompt?api_url=https://TU-URL-NGROK.ngrok.io"
```

Pega ese texto en las instrucciones de sistema de tu IA favorita.

---

### 📄 OPCIÓN 3: Exportar contexto (para cualquier IA, sin tools)

Si tu IA no tiene acceso a herramientas externas, exporta el conocimiento de la BD a un archivo Markdown y pégalo como system prompt.

#### Exportar el contexto

```bash
# Exportar con los primeros 30 videos analizados (recomendado)
python export_context.py

# Exportar más videos (mayor calidad, más tokens)
python export_context.py --max-hooks 50 --output mi_contexto_completo.md

# Exportar solo los patrones (menos tokens)
python export_context.py --max-hooks 10
```

El script genera `viral_context.md` con:

- Todos los patrones virales detectados
- Los N mejores videos analizados con sus técnicas
- Lista de todos los hooks virales
- Instrucciones para que la IA genere guiones
- Estructura exacta del guion a generar

#### Dónde pegar el contexto

| IA                 | Dónde pegarlo                                        |
| ------------------ | ---------------------------------------------------- |
| **Claude.ai**      | Configuración → Perfil → Instrucciones personales    |
| **ChatGPT**        | Configuración → Personalizar ChatGPT → Instrucciones |
| **Gemini**         | Gems → Crear Gem → Instrucciones del Gem             |
| **Cualquier chat** | Al inicio del chat como primer mensaje de sistema    |

#### Usar en cualquier IA (con o sin contexto previo)

Puedes también pegar el contexto directamente al inicio de cualquier conversación:

```
[pega aquí el contenido de viral_context.md]

---

Ahora genera un guion para: [descripción de la empresa]
que quiere: [objetivo del video]
```

---

## 💡 ¿Qué genera el sistema?

Para cada solicitud, el sistema entrega un guion COMPLETO:

```
📌 CONCEPTO: Nombre de la idea

⚡ HOOK (0-3 seg): "Texto exacto del gancho"

💡 POR QUÉ FUNCIONARÁ:
   Justificación basada en el patrón viral de referencia

🔗 REFERENCIA VIRAL:
   Patrón: [patrón viral usado, ej: "antes/después"]
   URL: https://www.instagram.com/p/... ← Video real que inspiró esto

📝 GUION COMPLETO:
   [0-3s]   Hook: Texto exacto
   [3-15s]  Desarrollo: Texto
   [15-25s] Cuerpo: Texto
   [25-30s] CTA: "Escríbenos AHORA y..."

🎥 PLAN DE TOMAS:
   Toma 1: [Qué se graba] | Primer plano | 3s
           → Instrucción exacta para el operador de cámara
   Toma 2: ...

🎬 PRODUCCIÓN:
   Duración: 30s | Formato: Vertical 9:16
   Escenario: Sala de tratamiento, fondo limpio y luminoso
   Iluminación: Luz natural + ring light frontal
   Props: Bata blanca, modelo Invisalign visible

🎵 MÚSICA:
   Género: Pop electrónico suave
   Búsqueda: "uplifting corporate soft" en Epidemic Sound

✂️ EDICIÓN:
   Ritmo: Rápido (corte cada 2-3 segundos)
   Transiciones: Corte directo + zoom suave
   Color: Filtro cálido, tonos blancos y azules
   Herramientas: CapCut o Adobe Premiere

📱 PUBLICACIÓN:
   Horario: Martes o jueves, 19:00-21:00h
   Caption: [caption completo listo para copiar]
   Hashtags: #ortodoncia #invisalign #dentista...

📊 MÉTRICAS OBJETIVO:
   KPI: Reproducciones + guardados
   Expectativa: 5,000-50,000 reproducciones (primeros 7 días)
```

---

## 📊 Flujo de trabajo completo

### PASO 1: Extraer hooks del PDF (ya completado)

```bash
python extract_pdf_data.py
# → Genera hooks_data.json con 1,003 hooks
```

### PASO 2: Inicializar BD en Supabase

```bash
# 1. Obtener SQL para Supabase y ejecutarlo en el SQL Editor
python setup_supabase.py

# 2. Subir los datos iniciales
python setup_database.py
# → Importa los hooks a tu proyecto de Supabase
```

### PASO 3: Descargar videos

```bash
python download_videos.py --limit 50
python download_videos.py --limit 100  # más videos
```

### PASO 4: Analizar con Gemini

```bash
python analyze_with_gemini.py --limit 50
# → Analiza y guarda en la BD: hook, tomas, guion, estrategia viral...
```

### PASO 5: Activar acceso desde IAs

```bash
# Opción A — MCP para Claude (configurar claude_desktop_config.json)
# Opción B — API REST para cualquier IA
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Opción C — Exportar contexto
python export_context.py
```

---

## ⚙️ Configuración en `config.py`

```python
GEMINI_API_KEY = "TU_API_KEY_AQUI"   # https://aistudio.google.com/app/apikey
GEMINI_MODEL   = "gemini-2.0-flash"  # o "gemini-1.5-pro" (más potente)

DOWNLOAD_DELAY_MIN = 2               # Segundos entre descargas
DOWNLOAD_DELAY_MAX = 5
MAX_DOWNLOADS_PER_RUN = 50
```

---

## 💰 Costos estimados

| Servicio                            | Costo         | Notas                            |
| ----------------------------------- | ------------- | -------------------------------- |
| **Gemini API** (análisis videos)    | ~$0.15/video  | ~$150 para 1,000 videos          |
| **Gemini API** (generación guiones) | ~$0.001/guion | Prácticamente gratis             |
| **yt-dlp** (descarga)               | Gratis        | Instagram puede requerir cookies |
| **FastAPI/MCP**                     | Gratis        | Corre local en tu máquina        |

> **Tip:** Con 50-100 videos analizados ya tienes una BD muy potente. No necesitas los 1,000.

---

## 🔧 Solución de problemas

### Instagram bloquea descargas

```bash
yt-dlp --cookies-from-browser chrome "URL_VIDEO"
# O configura cookies_path en config.py
```

### Error de cuota de Gemini

```bash
python analyze_with_gemini.py --limit 10 --delay 5
# Reduce el lote y aumenta el delay
```

### MCP no aparece en Claude

1. Verifica que Python está en el PATH del sistema
2. Comprueba la ruta en `claude_desktop_config.json`
3. Revisa los logs de Claude Desktop

### La API no arranca

```bash
pip install fastapi uvicorn
uvicorn api.main:app --port 8000
```

---

## 📊 Estructura de la base de datos (Supabase / PostgreSQL)

```sql
hooks           → 1,003 hooks virales + URL de referencia
video_analysis  → Análisis completo de cada video (hook, tomas, guion, viral...)
ideas_generadas → Historial de todos los guiones generados
```

---

## 🎯 Comparativa de las 3 opciones de acceso

|                            | MCP (Claude)   | API REST      | Contexto MD             |
| -------------------------- | -------------- | ------------- | ----------------------- |
| **Acceso a BD completa**   | ✅ Sí          | ✅ Sí         | ⚠️ Parcial (N videos)   |
| **Búsqueda inteligente**   | ✅ Sí          | ✅ Sí         | ❌ No (estático)        |
| **Funciona offline**       | ✅ Sí          | ✅ Local      | ✅ Sí                   |
| **Necesita setup técnico** | ⚠️ Config JSON | ⚠️ uvicorn    | ✅ No                   |
| **Compatible con**         | Claude Desktop | Cualquier IA  | Cualquier IA            |
| **Actualización BD**       | ✅ Automática  | ✅ Automática | ❌ Manual (re-exportar) |
| **Historial de guiones**   | ✅ Sí          | ✅ Sí         | ❌ No                   |
