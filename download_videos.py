"""
Script para descargar videos de Instagram desde las URLs del PDF.
Usa yt-dlp para descargar los videos y guarda el estado en Supabase.

Ejecutar:
  python download_videos.py              # Descarga los primeros 50 pendientes
  python download_videos.py --limit 100  # Descarga los primeros 100
  python download_videos.py --id 5       # Descarga solo el hook con ID 5
  python download_videos.py --retry      # Reintenta los que tuvieron error
"""
import os
import sys
import time
import random
import argparse
import subprocess
from config import VIDEOS_DIR, MAX_DOWNLOADS_PER_RUN, DOWNLOAD_DELAY_MIN, DOWNLOAD_DELAY_MAX
from db import get_db

# Usa el mismo Python que está corriendo este script para invocar yt-dlp,
# así funciona aunque el ejecutable no esté en el PATH del sistema.
YT_DLP_CMD = [sys.executable, "-m", "yt_dlp"]


def get_pending_hooks(db, limit=MAX_DOWNLOADS_PER_RUN, hook_id=None, retry_errors=False):
    """Obtiene los hooks pendientes de descarga desde Supabase"""
    if hook_id:
        result = db.table('hooks').select(
            'id, hook_template, reference_url'
        ).eq('id', hook_id).not_.is_('reference_url', None).execute()
    elif retry_errors:
        result = (
            db.table('hooks')
            .select('id, hook_template, reference_url')
            .eq('analyzed', 2)
            .not_.is_('reference_url', None)
            .limit(limit)
            .execute()
        )
    else:
        result = (
            db.table('hooks')
            .select('id, hook_template, reference_url')
            .eq('analyzed', 0)
            .not_.is_('reference_url', None)
            .is_('video_path', None)
            .order('id')
            .limit(limit)
            .execute()
        )

    return [(r['id'], r['hook_template'], r['reference_url']) for r in result.data]


def download_video(url, output_dir, hook_id):
    """
    Descarga un video usando yt-dlp.
    Retorna (success, file_path, error_message)
    """
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, f"hook_{hook_id:04d}.%(ext)s")

    cmd = [
        *YT_DLP_CMD,
        "--format", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best",
        "--output", output_template,
        "--no-playlist",
        "--socket-timeout", "30",
        "--retries", "3",
        "--merge-output-format", "mp4",
        url
    ]

    # Instagram requiere cookies del navegador para descargar (desde 2024).
    # Si existe cookies.txt en el directorio raíz, lo usa.
    # Si no, intenta extraer cookies del navegador automáticamente.
    cookies_file = os.path.join(os.path.dirname(output_dir), "cookies.txt")
    if os.path.exists(cookies_file):
        # Opción más confiable: archivo cookies.txt exportado con extensión del navegador
        cmd += ["--cookies", cookies_file]
    else:
        # Intenta extraer cookies del navegador (Chrome cerrado o Firefox)
        # Si Chrome está abierto fallará — ciérralo o usa cookies.txt
        for browser in ["firefox", "chrome", "edge"]:
            test = subprocess.run(
                [*YT_DLP_CMD, "--cookies-from-browser", browser, "--simulate", "--quiet", url],
                capture_output=True, text=True, timeout=15
            )
            if test.returncode == 0:
                cmd += ["--cookies-from-browser", browser]
                break
        # Si ningún navegador funcionó, intentamos sin cookies (puede fallar en contenido privado)


    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if result.returncode == 0:
            # Buscar el archivo descargado por extensión
            for ext in ['mp4', 'webm', 'mkv', 'mov']:
                path = os.path.join(output_dir, f"hook_{hook_id:04d}.{ext}")
                if os.path.exists(path):
                    return True, path, None

            # Búsqueda por prefijo (cualquier extensión)
            for f in os.listdir(output_dir):
                if f.startswith(f"hook_{hook_id:04d}"):
                    return True, os.path.join(output_dir, f), None

            return False, None, "yt-dlp salió sin error pero no creó el archivo (Instagram puede requerir cookies)"
        else:
            # Mostrar error real de yt-dlp
            error = (result.stderr or result.stdout or "Error desconocido").strip()
            # Sugerir solución si es error de login
            if "login" in error.lower() or "private" in error.lower() or "cookie" in error.lower():
                error += " → Exporta cookies de Instagram desde Chrome/Firefox (ver README)"
            return False, None, error[:600]

    except subprocess.TimeoutExpired:
        return False, None, "Timeout: la descarga tardó más de 180 segundos"
    except FileNotFoundError:
        return False, None, "yt-dlp no está instalado. Ejecuta: python -m pip install yt-dlp"
    except Exception as e:
        return False, None, str(e)[:500]


def update_hook_status(db, hook_id, success, video_path=None, error=None):
    """Actualiza el estado de descarga en Supabase"""
    if success and video_path:
        db.table('hooks').update({
            'video_path':     video_path,
            'download_error': None,
        }).eq('id', hook_id).execute()
    else:
        db.table('hooks').update({
            'download_error': error,
            'analyzed':       2,
        }).eq('id', hook_id).execute()


def check_yt_dlp():
    """Verifica que yt-dlp esté instalado (como módulo Python)"""
    try:
        result = subprocess.run(
            [*YT_DLP_CMD, "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ yt-dlp versión: {result.stdout.strip()}")
            return True
    except Exception:
        pass

    print("❌ yt-dlp no encontrado. Instalando...")
    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=False)
    return True


def main():
    parser = argparse.ArgumentParser(description='Descarga videos virales de Instagram')
    parser.add_argument('--limit', type=int, default=MAX_DOWNLOADS_PER_RUN,
                       help=f'Máximo de videos a descargar (default: {MAX_DOWNLOADS_PER_RUN})')
    parser.add_argument('--id', type=int, default=None,
                       help='Descargar solo un hook específico por ID')
    parser.add_argument('--retry', action='store_true',
                       help='Reintentar hooks con error de descarga')
    parser.add_argument('--delay-min', type=float, default=DOWNLOAD_DELAY_MIN,
                       help='Tiempo mínimo entre descargas en segundos')
    parser.add_argument('--delay-max', type=float, default=DOWNLOAD_DELAY_MAX,
                       help='Tiempo máximo entre descargas en segundos')
    args = parser.parse_args()

    print("=" * 60)
    print("DESCARGADOR DE VIDEOS VIRALES")
    print("=" * 60)

    check_yt_dlp()

    # Conectar a Supabase
    try:
        db = get_db()
    except ValueError as e:
        print(e)
        return

    # Obtener hooks pendientes
    hooks = get_pending_hooks(db, args.limit, args.id, args.retry)

    if not hooks:
        print("✅ No hay videos pendientes de descarga.")
        return

    print(f"\n📋 Videos a descargar: {len(hooks)}")
    print(f"📁 Directorio destino: {VIDEOS_DIR}")
    print(f"⏱️  Delay entre descargas: {args.delay_min}-{args.delay_max}s")
    print()

    success_count = 0
    error_count = 0

    for i, (hook_id, hook_template, url) in enumerate(hooks, 1):
        print(f"[{i:03d}/{len(hooks):03d}] Hook #{hook_id:04d}")
        print(f"         Hook: {hook_template[:80]}...")
        print(f"         URL:  {url}")

        success, video_path, error = download_video(url, VIDEOS_DIR, hook_id)

        if success:
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            print(f"         ✅ Descargado: {os.path.basename(video_path)} ({size_mb:.1f} MB)")
            update_hook_status(db, hook_id, True, video_path)
            success_count += 1
        else:
            print(f"         ❌ Error: {error[:100]}")
            update_hook_status(db, hook_id, False, error=error)
            error_count += 1

        if i < len(hooks):
            delay = random.uniform(args.delay_min, args.delay_max)
            print(f"         ⏳ Esperando {delay:.1f}s...")
            time.sleep(delay)

        print()

    print("=" * 60)
    print(f"✅ Descargas completadas: {success_count}")
    print(f"❌ Errores:              {error_count}")
    print("=" * 60)
    print(f"\nSiguiente paso: python analyze_with_gemini.py")


if __name__ == "__main__":
    main()
