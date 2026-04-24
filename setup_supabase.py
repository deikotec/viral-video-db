"""
Viral Video DB — Setup de Supabase
====================================
Muestra el SQL que debes ejecutar en el SQL Editor de Supabase para crear
las tablas, índices y funciones RPC necesarias.

Uso:
    python setup_supabase.py          # Imprime el SQL para copiar y pegar
    python setup_supabase.py --verify # Verifica que las tablas ya existen
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# -------------------------------------------------------
# SQL SCHEMA COMPLETO
# -------------------------------------------------------

SCHEMA_SQL = """
-- ============================================================
-- VIRAL VIDEO DB — Schema para Supabase (PostgreSQL)
-- Ejecuta este SQL en: Supabase Dashboard → SQL Editor
-- ============================================================

-- Tabla principal: hooks virales del PDF
CREATE TABLE IF NOT EXISTS hooks (
    id              INTEGER PRIMARY KEY,   -- ID explícito del PDF (no autogenerado)
    hook_template   TEXT NOT NULL,
    reference_url   TEXT,
    analyzed        INTEGER DEFAULT 0,     -- 0=pendiente, 1=analizado, 2=error
    video_path      TEXT,                  -- ruta local del video descargado
    download_error  TEXT,
    analysis_error  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    analyzed_at     TIMESTAMPTZ,
    -- Estadísticas del video original en Instagram
    reproducciones  BIGINT DEFAULT NULL,
    me_gusta        BIGINT DEFAULT NULL,
    comentarios     BIGINT DEFAULT NULL,
    guardados       BIGINT DEFAULT NULL,
    compartidos     BIGINT DEFAULT NULL,
    stats_updated_at TIMESTAMPTZ DEFAULT NULL
);

-- Tabla: análisis completo de cada video (uno por hook)
CREATE TABLE IF NOT EXISTS video_analysis (
    id                      BIGSERIAL PRIMARY KEY,
    hook_id                 INTEGER NOT NULL REFERENCES hooks(id) UNIQUE,

    -- Metadatos del video
    titulo_descriptivo      TEXT,
    duracion_estimada       TEXT,
    formato                 TEXT,
    plataforma              TEXT,

    -- Hook
    hook_tipo               TEXT,
    hook_texto              TEXT,
    hook_duracion_seg       FLOAT,
    hook_tecnica            TEXT,
    hook_elemento_visual    TEXT,

    -- Estructura narrativa
    ritmo                   TEXT,
    densidad_informacion    TEXT,
    arco_emocional          TEXT,

    -- Producción
    calidad_video           TEXT,
    iluminacion             TEXT,
    escenario               TEXT,
    tiene_subtitulos        BOOLEAN,
    texto_en_pantalla       TEXT,
    transiciones            TEXT,
    color_grading           TEXT,

    -- Audio
    voz_en_off              BOOLEAN,
    habla_a_camara          BOOLEAN,
    tono_voz                TEXT,
    musica_genero           TEXT,
    musica_posicion         TEXT,
    musica_proposito        TEXT,

    -- Guion
    guion_completo          TEXT,
    estilo_escritura        TEXT,
    call_to_action          TEXT,

    -- Estrategia viral
    por_que_es_viral        TEXT,
    emocion_principal       TEXT,
    factor_compartir        TEXT,
    audiencia_objetivo      TEXT,
    nicho                   TEXT,
    patron_viral            TEXT,

    -- Replicabilidad
    nivel_dificultad        TEXT,
    costo_produccion        TEXT,
    tiempo_produccion       TEXT,
    adaptable_otros_nichos  BOOLEAN,

    -- JSON completo para búsquedas avanzadas (JSONB = indexable en Postgres)
    analisis_json_completo  JSONB,
    tags                    JSONB,
    nichos_compatibles      JSONB,
    equipamiento            JSONB,

    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla: historial de ideas/guiones generados
CREATE TABLE IF NOT EXISTS ideas_generadas (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_contexto    TEXT,
    objetivo_video      TEXT,
    plataforma          TEXT,
    nicho_empresa       TEXT,
    hook_referencias    JSONB,   -- array de IDs de hooks usados
    idea_json           JSONB,   -- JSON completo de la idea
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_hooks_analyzed    ON hooks(analyzed);
CREATE INDEX IF NOT EXISTS idx_analysis_nicho    ON video_analysis(nicho);
CREATE INDEX IF NOT EXISTS idx_analysis_patron   ON video_analysis(patron_viral);
CREATE INDEX IF NOT EXISTS idx_analysis_hook_id  ON video_analysis(hook_id);
CREATE INDEX IF NOT EXISTS idx_analysis_emocion  ON video_analysis(emocion_principal);

-- ============================================================
-- FUNCIONES RPC (llamables desde supabase-py con client.rpc())
-- ============================================================

-- Búsqueda aleatoria de hooks con análisis, con filtros opcionales
CREATE OR REPLACE FUNCTION search_hooks_random(
    p_nicho   TEXT DEFAULT NULL,
    p_patron  TEXT DEFAULT NULL,
    p_limit   INT  DEFAULT 15
)
RETURNS TABLE(
    id                     INTEGER,
    hook_template          TEXT,
    reference_url          TEXT,
    analisis_json_completo JSONB,
    nicho                  TEXT,
    patron_viral           TEXT,
    por_que_es_viral       TEXT,
    emocion_principal      TEXT,
    audiencia_objetivo     TEXT,
    reproducciones         BIGINT,
    me_gusta               BIGINT,
    comentarios            BIGINT,
    guardados              BIGINT,
    compartidos            BIGINT
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.id,
        h.hook_template,
        h.reference_url,
        va.analisis_json_completo,
        va.nicho,
        va.patron_viral,
        va.por_que_es_viral,
        va.emocion_principal,
        va.audiencia_objetivo,
        h.reproducciones,
        h.me_gusta,
        h.comentarios,
        h.guardados,
        h.compartidos
    FROM hooks h
    JOIN video_analysis va ON h.id = va.hook_id
    WHERE (p_nicho  IS NULL OR va.nicho        ILIKE '%' || p_nicho  || '%')
      AND (p_patron IS NULL OR va.patron_viral ILIKE '%' || p_patron || '%')
    ORDER BY RANDOM()
    LIMIT p_limit;
END;
$$;

-- Hooks crudos (sin análisis) en orden aleatorio
CREATE OR REPLACE FUNCTION get_random_hooks(p_limit INT DEFAULT 15)
RETURNS TABLE(id INTEGER, hook_template TEXT, reference_url TEXT)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT h.id, h.hook_template, h.reference_url
    FROM hooks h
    ORDER BY RANDOM()
    LIMIT p_limit;
END;
$$;

-- Videos analizados aleatorios para exportar contexto
CREATE OR REPLACE FUNCTION get_export_videos(p_limit INT DEFAULT 30)
RETURNS TABLE(
    hook_template     TEXT,
    reference_url     TEXT,
    nicho             TEXT,
    patron_viral      TEXT,
    por_que_es_viral  TEXT,
    emocion_principal TEXT,
    audiencia_objetivo TEXT,
    nivel_dificultad  TEXT,
    costo_produccion  TEXT,
    ritmo             TEXT,
    escenario         TEXT,
    musica_genero     TEXT,
    guion_completo    TEXT,
    hook_texto        TEXT,
    hook_tecnica      TEXT,
    titulo_descriptivo TEXT
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.hook_template,
        h.reference_url,
        va.nicho,
        va.patron_viral,
        va.por_que_es_viral,
        va.emocion_principal,
        va.audiencia_objetivo,
        va.nivel_dificultad,
        va.costo_produccion,
        va.ritmo,
        va.escenario,
        va.musica_genero,
        va.guion_completo,
        va.hook_texto,
        va.hook_tecnica,
        va.titulo_descriptivo
    FROM hooks h
    JOIN video_analysis va ON h.id = va.hook_id
    ORDER BY RANDOM()
    LIMIT p_limit;
END;
$$;

-- Estadísticas globales de la BD
CREATE OR REPLACE FUNCTION get_db_stats()
RETURNS JSON
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE result JSON;
BEGIN
    SELECT json_build_object(
        'total_hooks',         (SELECT COUNT(*)  FROM hooks),
        'hooks_analizados',    (SELECT COUNT(*)  FROM hooks WHERE analyzed = 1),
        'hooks_pendientes',    (SELECT COUNT(*)  FROM hooks WHERE analyzed = 0),
        'hooks_con_error',     (SELECT COUNT(*)  FROM hooks WHERE analyzed = 2),
        'analisis_guardados',  (SELECT COUNT(*)  FROM video_analysis),
        'ideas_generadas',     (SELECT COUNT(*)  FROM ideas_generadas)
    ) INTO result;
    RETURN result;
END;
$$;

-- Nichos con conteo
CREATE OR REPLACE FUNCTION get_nichos_stats(p_limit INT DEFAULT 20)
RETURNS TABLE(nicho TEXT, total BIGINT)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT va.nicho, COUNT(*) AS total
    FROM video_analysis va
    WHERE va.nicho IS NOT NULL AND va.nicho != ''
    GROUP BY va.nicho
    ORDER BY total DESC
    LIMIT p_limit;
END;
$$;

-- Patrones virales con conteo
CREATE OR REPLACE FUNCTION get_patrones_stats(p_limit INT DEFAULT 15)
RETURNS TABLE(patron_viral TEXT, total BIGINT)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT va.patron_viral, COUNT(*) AS total
    FROM video_analysis va
    WHERE va.patron_viral IS NOT NULL AND va.patron_viral != ''
    GROUP BY va.patron_viral
    ORDER BY total DESC
    LIMIT p_limit;
END;
$$;

-- Emociones principales con conteo
CREATE OR REPLACE FUNCTION get_emociones_stats(p_limit INT DEFAULT 10)
RETURNS TABLE(emocion_principal TEXT, total BIGINT)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT va.emocion_principal, COUNT(*) AS total
    FROM video_analysis va
    WHERE va.emocion_principal IS NOT NULL AND va.emocion_principal != ''
    GROUP BY va.emocion_principal
    ORDER BY total DESC
    LIMIT p_limit;
END;
$$;

-- ============================================================
-- MIGRACIÓN: Agregar estadísticas a tabla hooks existente
-- (Si la tabla ya existe, ejecuta solo este bloque)
-- ============================================================
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS reproducciones   BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS me_gusta         BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS comentarios      BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS guardados        BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS compartidos      BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS stats_updated_at TIMESTAMPTZ DEFAULT NULL;

-- ============================================================
-- PERMISOS: Desactiva RLS en estas tablas para acceso total
-- desde el backend con la service_role key.
-- (Opcional si usas RLS con políticas personalizadas)
-- ============================================================
ALTER TABLE hooks            DISABLE ROW LEVEL SECURITY;
ALTER TABLE video_analysis   DISABLE ROW LEVEL SECURITY;
ALTER TABLE ideas_generadas  DISABLE ROW LEVEL SECURITY;
"""


def print_schema():
    print("=" * 70)
    print("VIRAL VIDEO DB — SQL Schema para Supabase")
    print("=" * 70)
    print()
    print("Copia y pega el siguiente SQL en:")
    print("  Supabase Dashboard → SQL Editor → New Query → Run")
    print()
    print("-" * 70)
    print(SCHEMA_SQL)
    print("-" * 70)
    print()
    print("Después de ejecutar el SQL, corre:")
    print("  python setup_database.py   ← importa los hooks del PDF a Supabase")
    print()


def verify_setup():
    """Verifica que las tablas existen en Supabase"""
    try:
        from db import get_db
    except ImportError:
        print("❌ No se encontró db.py. Asegúrate de estar en el directorio correcto.")
        return False

    print("Verificando conexión a Supabase...")
    try:
        db = get_db()
    except ValueError as e:
        print(e)
        return False
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        return False

    print("✅ Conexión a Supabase OK")

    tables = ["hooks", "video_analysis", "ideas_generadas"]
    all_ok = True

    for table in tables:
        try:
            result = db.table(table).select("*", count="exact").limit(0).execute()
            print(f"  ✅ Tabla '{table}' existe (filas: {result.count})")
        except Exception as e:
            print(f"  ❌ Tabla '{table}' NO encontrada — ejecuta el SQL primero")
            all_ok = False

    if all_ok:
        # Verificar funciones RPC
        rpc_functions = ["get_db_stats", "get_nichos_stats", "get_patrones_stats"]
        for fn in rpc_functions:
            try:
                db.rpc(fn).execute()
                print(f"  ✅ Función RPC '{fn}' OK")
            except Exception:
                print(f"  ⚠️  Función RPC '{fn}' no disponible — verifica el SQL")

    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup de Supabase para Viral Video DB")
    parser.add_argument("--verify", action="store_true",
                        help="Verificar que las tablas ya existen en Supabase")
    args = parser.parse_args()

    if args.verify:
        ok = verify_setup()
        sys.exit(0 if ok else 1)
    else:
        print_schema()
