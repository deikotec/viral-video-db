Listo. El script fetch_stats.py está creado. Así funciona:

Cómo usarlo

# Procesar los primeros 100 hooks analizados sin stats (default)

python fetch_stats.py

# Limitar cuántos procesar por ejecución

python fetch_stats.py --limit 50

# Ver qué haría sin tocar la BD (recomendado probar primero)

python fetch_stats.py --dry-run --limit 5

# Un hook específico

python fetch_stats.py --id 42

# Re-actualizar todos aunque ya tengan stats

python fetch_stats.py --all --limit 200
Métricas disponibles vs. no disponibles
Métrica Disponible Por qué
▶ Reproducciones ✅ Pública en Instagram
❤ Me gusta ✅ Pública (puede ser null si el creador las ocultó)
💬 Comentarios ✅ Pública
🔖 Guardados ❌ Solo el dueño de la cuenta puede verlos
↗ Compartidos ❌ Solo el dueño de la cuenta puede verlos
Instagram no expone guardados ni compartidos de forma pública — ni yt-dlp, ni ninguna herramienta puede obtenerlos sin acceso a la cuenta dueña del video.

Flujo recomendado

Ejecuta la migración en Supabase primero: migration_add_stats.sql

Listo, warnings corregidos. El warning de instaloader es solo del linter porque no está instalado aún — el script lo maneja en tiempo de ejecución con un mensaje de error claro.

Para ejecutarlo necesitas primero instalar la dependencia y luego correrlo con tus credenciales de Instagram:

# 1. Instalar instaloader

pip install instaloader

# 2. Prueba primero con dry-run (5 hooks, sin guardar en BD)

python fetch_stats.py --user TU_USUARIO --password TU_CONTRASEÑA --dry-run --limit 5

# 3. Guardar la sesión para no tener que poner credenciales cada vez

python fetch_stats.py --user TU_USUARIO --password TU_CONTRASEÑA --save-session --limit 100

# 4. Las siguientes veces solo con --user (carga la sesión guardada)

python fetch_stats.py --user TU_USUARIO --limit 100
Nota sobre los compartidos: Instagram devuelve el campo reshare_count de forma inconsistente — algunos posts lo incluyen en la respuesta de la API privada y otros no, depende del tipo de cuenta y la región. El script lo extrae cuando está disponible.
