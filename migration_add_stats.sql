-- ============================================================
-- MIGRACIÓN: Estadísticas de video por hook
-- Ejecuta este SQL en: Supabase Dashboard → SQL Editor
-- ============================================================

-- 1. Agregar columnas de estadísticas a la tabla hooks
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS reproducciones   BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS me_gusta         BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS comentarios      BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS guardados        BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS compartidos      BIGINT DEFAULT NULL;
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS stats_updated_at TIMESTAMPTZ DEFAULT NULL;

-- 2. Actualizar función search_hooks_random para incluir estadísticas
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
