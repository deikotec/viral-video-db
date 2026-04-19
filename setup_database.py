"""
Script para inicializar la base de datos en Supabase e importar los hooks del PDF.

PASOS PREVIOS:
  1. Crea tu proyecto en https://supabase.com
  2. Ejecuta el SQL de setup_supabase.py en el SQL Editor de Supabase
  3. Configura SUPABASE_URL y SUPABASE_KEY en config.py
  4. Ejecuta este script: python setup_database.py
"""
import json
import os
import sys
from config import HOOKS_JSON
from db import get_db


def import_hooks_from_json(db, hooks_json_path):
    """Importa los hooks del JSON a Supabase"""
    if not os.path.exists(hooks_json_path):
        print(f"❌ No se encontró el archivo: {hooks_json_path}")
        print("   Ejecuta primero: python extract_pdf_data.py")
        return 0

    with open(hooks_json_path, 'r', encoding='utf-8') as f:
        hooks = json.load(f)

    # Verificar cuántos ya existen
    result = db.table('hooks').select('id', count='exact').limit(0).execute()
    existing = result.count or 0

    if existing > 0:
        print(f"ℹ️  Ya existen {existing} hooks en Supabase. Saltando importación.")
        print("   Para reimportar, borra los registros en el dashboard y ejecuta de nuevo.")
        return existing

    # Preparar batch de inserción
    batch = []
    for hook in hooks:
        url = hook['reference_urls'][0] if hook.get('reference_urls') else None
        batch.append({
            'id': hook['id'],
            'hook_template': hook['hook_template'],
            'reference_url': url,
            'analyzed': 0,
        })

    # Insertar en lotes de 500 (límite seguro de Supabase)
    inserted = 0
    batch_size = 500
    for i in range(0, len(batch), batch_size):
        chunk = batch[i:i + batch_size]
        db.table('hooks').upsert(chunk, ignore_duplicates=True).execute()
        inserted += len(chunk)
        print(f"   Importados {inserted}/{len(batch)} hooks...")

    print(f"✅ Importados {inserted} hooks a Supabase")
    return inserted


def show_stats(db):
    """Muestra estadísticas de la base de datos"""
    try:
        result = db.rpc('get_db_stats').execute()
        s = result.data
    except Exception:
        # Fallback si la función RPC no está disponible aún
        s = {
            'total_hooks':        (db.table('hooks').select('id', count='exact').limit(0).execute().count or 0),
            'hooks_analizados':   (db.table('hooks').select('id', count='exact').eq('analyzed', 1).limit(0).execute().count or 0),
            'hooks_pendientes':   (db.table('hooks').select('id', count='exact').eq('analyzed', 0).limit(0).execute().count or 0),
            'hooks_con_error':    (db.table('hooks').select('id', count='exact').eq('analyzed', 2).limit(0).execute().count or 0),
            'analisis_guardados': (db.table('video_analysis').select('id', count='exact').limit(0).execute().count or 0),
            'ideas_generadas':    (db.table('ideas_generadas').select('id', count='exact').limit(0).execute().count or 0),
        }

    print("\n" + "=" * 50)
    print("📊 ESTADÍSTICAS DE LA BASE DE DATOS (Supabase)")
    print("=" * 50)
    print(f"  Total hooks:          {s.get('total_hooks', 0)}")
    print(f"  Hooks analizados:     {s.get('hooks_analizados', 0)}")
    print(f"  Hooks pendientes:     {s.get('hooks_pendientes', 0)}")
    print(f"  Hooks con error:      {s.get('hooks_con_error', 0)}")
    print(f"  Análisis guardados:   {s.get('analisis_guardados', 0)}")
    print(f"  Ideas generadas:      {s.get('ideas_generadas', 0)}")

    # Top nichos
    try:
        nichos = db.rpc('get_nichos_stats', {'p_limit': 10}).execute().data
        if nichos:
            print("\n  Top nichos analizados:")
            for row in nichos:
                print(f"    - {row['nicho']}: {row['total']}")
    except Exception:
        pass

    print("=" * 50)


if __name__ == "__main__":
    print("=" * 60)
    print("INICIALIZANDO BASE DE DATOS VIRAL VIDEO DB EN SUPABASE")
    print("=" * 60)

    # Verificar directorio de videos
    videos_dir = "c:/xampp/htdocs/claude/rrss ideas/videos"
    os.makedirs(videos_dir, exist_ok=True)
    print(f"✅ Directorio de videos: {videos_dir}")

    # Conectar a Supabase
    print("\nConectando a Supabase...")
    try:
        db = get_db()
        print("✅ Conexión a Supabase exitosa")
    except ValueError as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        sys.exit(1)

    # Verificar que las tablas existen
    try:
        db.table('hooks').select('id', count='exact').limit(0).execute()
    except Exception:
        print("\n❌ Las tablas no existen en Supabase.")
        print("   Ejecuta primero el SQL de setup_supabase.py:")
        print("   python setup_supabase.py  ← imprime el SQL a ejecutar")
        sys.exit(1)

    # Importar hooks
    import_hooks_from_json(db, HOOKS_JSON)

    # Mostrar estadísticas
    show_stats(db)

    print("\n✅ Base de datos Supabase lista.")
    print("   Siguiente paso: python download_videos.py")
