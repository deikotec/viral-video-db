"""
Obtiene estadísticas reales de los videos de Instagram usando la API privada
(la misma que usa la app móvil) a través de instaloader con sesión autenticada.

Métricas obtenibles:
  ✅ reproducciones  — video_view_count / play_count
  ✅ me_gusta        — like_count
  ✅ comentarios     — comment_count
  ✅ compartidos     — reshare_count  (cuando está disponible en la API)
  ❌ guardados       — IMPOSIBLE: solo el dueño lo ve en Insights, nunca expuesto a terceros

Uso:
  python fetch_stats.py                       # Procesa analizados sin stats (default 100)
  python fetch_stats.py --limit 50            # Limita a 50 hooks
  python fetch_stats.py --id 42              # Solo el hook con ID 42
  python fetch_stats.py --all                # Todos, incluso los que ya tienen stats
  python fetch_stats.py --dry-run            # Muestra sin guardar en BD
  python fetch_stats.py --save-session       # Guarda la sesión para no re-logear cada vez

Requisito: pip install instaloader
"""

import os
import re
import sys
import time
import random
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_db

DEFAULT_LIMIT  = 100
SESSION_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".instagram_session")


# ---------------------------------------------------------------------------
# Instaloader helpers
# ---------------------------------------------------------------------------

def get_loader(username=None, password=None, save_session=False):
    """Inicializa instaloader y carga/guarda sesión."""
    try:
        import instaloader
    except ImportError:
        print("❌ instaloader no está instalado. Ejecuta:")
        print("   pip install instaloader")
        sys.exit(1)

    L = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        request_timeout=20,
    )

    # Intentar cargar sesión guardada
    if os.path.exists(SESSION_FILE) and username:
        try:
            L.load_session_from_file(username, SESSION_FILE)
            print(f"✅ Sesión cargada para @{username}")
            return L, instaloader
        except Exception:
            print("⚠️  Sesión expirada, re-logueando...")

    # Login interactivo si se dan credenciales
    if username and password:
        try:
            L.login(username, password)
            print(f"✅ Login exitoso como @{username}")
            if save_session:
                L.save_session_to_file(SESSION_FILE)
                print(f"   Sesión guardada en {SESSION_FILE}")
        except instaloader.exceptions.BadCredentialsException:
            print("❌ Usuario o contraseña incorrectos")
            sys.exit(1)
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            code = input("📱 Código de verificación 2FA: ").strip()
            L.two_factor_login(code)
            if save_session:
                L.save_session_to_file(SESSION_FILE)
    elif not os.path.exists(SESSION_FILE):
        print("⚠️  Sin credenciales — usando modo anónimo (menos métricas disponibles)")
        print("   Para login: --user TU_USUARIO --password TU_CONTRASEÑA")

    return L, instaloader


def extract_shortcode(url):
    """Extrae el shortcode de una URL de Instagram."""
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', url)
    return match.group(1) if match else None


def fetch_post_stats(L, instaloader_mod, shortcode):
    """
    Obtiene estadísticas de un post usando instaloader (API privada).
    Devuelve (stats_dict | None, error_str | None)
    """
    try:
        post = instaloader_mod.Post.from_shortcode(L.context, shortcode)

        stats = {
            "reproducciones": post.video_view_count if post.is_video else None,
            "me_gusta":       post.likes,
            "comentarios":    post.comments,
            "compartidos":    None,
        }

        # Intentar extraer share/reshare count del nodo raw de la API privada
        # Instagram a veces incluye estos campos según el tipo de cuenta y región
        node = post._node  # nodo JSON crudo de la respuesta privada
        if isinstance(node, dict):
            # Distintos nombres que usa Instagram internamente
            for field in ("reshare_count", "share_count", "ig_play_count"):
                val = node.get(field)
                if val is not None:
                    if field == "ig_play_count":
                        stats["reproducciones"] = stats["reproducciones"] or val
                    else:
                        stats["compartidos"] = val
                    break

            # play_count alternativo para Reels
            play = node.get("play_count") or node.get("ig_reels_video_info", {})
            if isinstance(play, dict):
                stats["reproducciones"] = stats["reproducciones"] or play.get("play_count")
            elif isinstance(play, int):
                stats["reproducciones"] = stats["reproducciones"] or play

        return stats, None

    except instaloader_mod.exceptions.LoginRequiredException:
        return None, "Post privado — requiere seguir al usuario"
    except instaloader_mod.exceptions.PostChangedException:
        return None, "Post eliminado o no disponible"
    except instaloader_mod.exceptions.QueryReturnedNotFoundException:
        return None, "Post no encontrado (eliminado)"
    except Exception as e:
        err = str(e)
        if "429" in err or "rate" in err.lower():
            return None, "RATE_LIMIT"
        return None, err[:200]


# ---------------------------------------------------------------------------
# BD helpers
# ---------------------------------------------------------------------------

def get_hooks_to_process(db, limit, hook_id=None, force_all=False):
    query = db.table('hooks').select('id, reference_url')

    if hook_id:
        query = query.eq('id', hook_id)
    else:
        query = query.eq('analyzed', 1).not_.is_('reference_url', None)
        if not force_all:
            query = query.is_('reproducciones', None)
        query = query.order('id').limit(limit)

    result = query.execute()
    return [(r['id'], r['reference_url']) for r in result.data if r.get('reference_url')]


def save_stats(db, hook_id, stats):
    data = {k: v for k, v in stats.items() if v is not None}
    data["stats_updated_at"] = datetime.now().isoformat()
    db.table('hooks').update(data).eq('id', hook_id).execute()


# ---------------------------------------------------------------------------
# Formato de salida
# ---------------------------------------------------------------------------

def fmt(value, label, emoji):
    if value is None:
        return f"{emoji} {label}: —"
    if value >= 1_000_000:
        return f"{emoji} {label}: {value/1_000_000:.1f}M"
    if value >= 1_000:
        return f"{emoji} {label}: {value/1_000:.1f}K"
    return f"{emoji} {label}: {value:,}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Obtiene estadísticas de Instagram para hooks analizados")
    parser.add_argument("--limit",        type=int,   default=DEFAULT_LIMIT, help=f"Máximo de hooks (default: {DEFAULT_LIMIT})")
    parser.add_argument("--id",           type=int,   default=None,          help="Procesar solo este hook ID")
    parser.add_argument("--all",          action="store_true",               help="Incluir hooks que ya tienen stats")
    parser.add_argument("--dry-run",      action="store_true",               help="No guardar en BD")
    parser.add_argument("--user",         type=str,   default=None,          help="Usuario de Instagram")
    parser.add_argument("--password",     type=str,   default=None,          help="Contraseña de Instagram")
    parser.add_argument("--save-session", action="store_true",               help="Guardar sesión localmente")
    parser.add_argument("--delay-min",    type=float, default=3.0,           help="Segundos mínimos entre peticiones (default: 3)")
    parser.add_argument("--delay-max",    type=float, default=7.0,           help="Segundos máximos entre peticiones (default: 7)")
    args = parser.parse_args()

    print("=" * 60)
    print("FETCH STATS — API privada de Instagram")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  MODO DRY-RUN: no se guardará nada en la BD\n")

    # Inicializar instaloader
    L, instaloader_mod = get_loader(args.user, args.password, args.save_session)

    # Conectar a BD
    try:
        db = get_db()
    except ValueError as e:
        print(e)
        return

    hooks = get_hooks_to_process(db, args.limit, args.id, args.all)

    if not hooks:
        print("✅ No hay hooks pendientes.")
        print("   (Usa --all para re-procesar todos los hooks analizados)")
        return

    print(f"\n📋 Hooks a procesar: {len(hooks)}")
    print(f"⏱️  Delay entre peticiones: {args.delay_min}-{args.delay_max}s\n")

    ok_count      = 0
    error_count   = 0
    skipped_count = 0

    for i, (hook_id, url) in enumerate(hooks, 1):
        shortcode = extract_shortcode(url)
        if not shortcode:
            print(f"[{i:03d}/{len(hooks):03d}] Hook #{hook_id:04d} — URL inválida: {url}")
            skipped_count += 1
            print()
            continue

        print(f"[{i:03d}/{len(hooks):03d}] Hook #{hook_id:04d} — /{shortcode}")

        stats, error = fetch_post_stats(L, instaloader_mod, shortcode)

        if error == "RATE_LIMIT":
            print(f"         ⚠️  Rate limit de Instagram — esperando 60s...")
            time.sleep(60)
            stats, error = fetch_post_stats(L, instaloader_mod, shortcode)

        if error:
            print(f"         ❌ {error}")
            error_count += 1
        else:
            has_data = any(v is not None for v in stats.values())
            print(f"         {fmt(stats.get('reproducciones'), 'Reproducciones', '▶')}  "
                  f"{fmt(stats.get('me_gusta'), 'Likes', '❤')}  "
                  f"{fmt(stats.get('comentarios'), 'Comentarios', '💬')}  "
                  f"{fmt(stats.get('compartidos'), 'Compartidos', '↗')}")

            if not has_data:
                print(f"         ⚠️  Post sin métricas públicas")
                skipped_count += 1
            elif not args.dry_run:
                save_stats(db, hook_id, stats)
                ok_count += 1
            else:
                ok_count += 1

        if i < len(hooks):
            delay = random.uniform(args.delay_min, args.delay_max)
            time.sleep(delay)

        print()

    print("=" * 60)
    print(f"✅ Guardados:          {ok_count}")
    print(f"⚠️  Sin métricas:       {skipped_count}")
    print(f"❌ Errores:            {error_count}")
    print("=" * 60)

    if ok_count > 0 and not args.dry_run:
        print(f"\n💡 Ve las stats en: Supabase Dashboard → Table Editor → hooks")
        print(f"   o en la API: GET /hooks (próximamente) / POST /search")


if __name__ == "__main__":
    main()
