#!/usr/bin/env python3
"""
Sincroniza video_path en la base de datos con los archivos .mp4 reales en disco.

Escenarios que corrige:
  1. video_path apunta a un .m4a o fdash que ya no existe → actualiza a hook_XXXX.mp4
  2. video_path es NULL pero existe hook_XXXX.mp4 en disco → registra el archivo
  3. video_path apunta a un .mp4 que ya no existe → limpia el path (NULL)

Ejecutar:
  python fix_video_paths.py            # modo dry-run (solo muestra cambios)
  python fix_video_paths.py --apply    # aplica los cambios en la BD
  python fix_video_paths.py --apply --limit 200
"""

import os
import re
import argparse
from pathlib import Path
from config import VIDEOS_DIR
from db import get_db


VIDEOS_PATH = Path(VIDEOS_DIR)


def scan_mp4_on_disk() -> dict[int, Path]:
    """
    Escanea la carpeta de videos y devuelve un dict:
      hook_number (int) -> Path del archivo hook_XXXX.mp4 combinado
    Solo considera los archivos con nombre limpio hook_XXXX.mp4 (ya combinados).
    """
    combined = {}
    pattern = re.compile(r"^hook_(\d+)\.mp4$")
    for f in VIDEOS_PATH.iterdir():
        m = pattern.match(f.name)
        if m:
            combined[int(m.group(1))] = f
    return combined


def fetch_hooks_with_videos(db) -> list[dict]:
    """Obtiene todos los hooks que tienen video_path o que están pendientes de análisis."""
    # Traer todos los que tienen video_path (incluyendo los mal puestos)
    # y también los que podrían no tener path pero sí tener archivo en disco
    result = (
        db.table('hooks')
        .select('id, video_path, analyzed')
        .order('id')
        .execute()
    )
    return result.data


def main():
    parser = argparse.ArgumentParser(description='Sincroniza video_path con archivos .mp4 reales')
    parser.add_argument('--apply', action='store_true',
                        help='Aplica los cambios en la BD (sin esto es solo dry-run)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limita el número de actualizaciones')
    args = parser.parse_args()

    mode = "APLICANDO CAMBIOS" if args.apply else "DRY-RUN (usa --apply para guardar)"
    print("=" * 60)
    print(f"SINCRONIZADOR DE VIDEO_PATH — {mode}")
    print("=" * 60)

    try:
        db = get_db()
    except ValueError as e:
        print(e)
        return

    print(f"Escaneando archivos en: {VIDEOS_PATH}")
    mp4_on_disk = scan_mp4_on_disk()
    print(f"  → {len(mp4_on_disk)} archivos hook_XXXX.mp4 encontrados en disco\n")

    hooks = fetch_hooks_with_videos(db)
    print(f"Hooks en la BD: {len(hooks)}\n")

    updates = []   # (hook_id, new_path)  new_path=None significa limpiar
    skipped_ok = 0

    for hook in hooks:
        hook_id   = hook['id']
        cur_path  = hook['video_path'] or ''
        analyzed  = hook['analyzed']
        mp4_file  = mp4_on_disk.get(hook_id)

        # Caso 1: ya apunta al mp4 correcto y el archivo existe → OK
        if cur_path and cur_path == str(mp4_file):
            skipped_ok += 1
            continue

        # Caso 2: tiene un path pero el archivo ya no existe (era .m4a o fdash eliminado)
        #         Y tenemos el mp4 combinado en disco → actualizar
        if cur_path and not os.path.exists(cur_path) and mp4_file:
            updates.append((hook_id, str(mp4_file)))
            continue

        # Caso 3: no tiene path pero existe el mp4 en disco → registrar
        if not cur_path and mp4_file:
            updates.append((hook_id, str(mp4_file)))
            continue

        # Caso 4: tiene path que existe pero es fdash/m4a (sin convertir aún) → saltar
        if cur_path and os.path.exists(cur_path) and not cur_path.endswith('.mp4'):
            # el archivo existe pero es solo audio, no lo tocamos
            skipped_ok += 1
            continue

        # Caso 5: tiene path que existe y es .mp4 → ya está bien aunque el nombre sea raro
        if cur_path and os.path.exists(cur_path) and cur_path.endswith('.mp4'):
            skipped_ok += 1
            continue

        # Caso 6: path apunta a archivo que no existe y no hay mp4 en disco → nada que hacer
        skipped_ok += 1

    print(f"Resumen:")
    print(f"  ✅ Correctos (sin cambios):     {skipped_ok}")
    print(f"  🔄 A actualizar:                {len(updates)}")

    if args.limit:
        updates = updates[:args.limit]
        print(f"  ✂️  Limitado a:                 {len(updates)} (--limit {args.limit})")

    if not updates:
        print("\nNada que actualizar.")
        return

    print()
    if not args.apply:
        print("Vista previa (primeros 20):")
        for hook_id, new_path in updates[:20]:
            print(f"  Hook #{hook_id:04d} → {os.path.basename(new_path) if new_path else 'NULL'}")
        if len(updates) > 20:
            print(f"  ... y {len(updates) - 20} más")
        print("\nEjecuta con --apply para guardar los cambios.")
        return

    # Aplicar cambios en la BD
    print("Aplicando actualizaciones...")
    ok = 0
    fail = 0
    for hook_id, new_path in updates:
        try:
            update_data = {'video_path': new_path}
            # Si ahora hay un mp4 válido y el hook tenía analyzed=2 (error), resetear a 0
            row = next(h for h in hooks if h['id'] == hook_id)
            if new_path and row['analyzed'] == 2:
                update_data['analyzed'] = 0
                update_data['download_error'] = None

            db.table('hooks').update(update_data).eq('id', hook_id).execute()
            print(f"  ✅ Hook #{hook_id:04d} → {os.path.basename(new_path) if new_path else 'NULL'}")
            ok += 1
        except Exception as e:
            print(f"  ❌ Hook #{hook_id:04d} ERROR: {e}")
            fail += 1

    print(f"\nResultado: {ok} actualizados, {fail} errores.")

    # Contar cuántos hooks quedan listos para analizar
    ready = db.table('hooks').select('id', count='exact').not_.is_('video_path', None).eq('analyzed', 0).execute()
    print(f"\n📋 Hooks listos para analizar (video_path + analyzed=0): {ready.count}")
    print("   Ejecuta: python analyze_with_gemini.py --limit 50")


if __name__ == "__main__":
    main()
