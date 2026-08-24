-- =============================================================================
-- NEXUS-SQL | 04_views.sql
-- Layer: VIEWS  –  Read-only projections used by the API and explanation layer.
-- =============================================================================

-- Full paper view with venue and area denormalized
CREATE OR REPLACE VIEW v_paper_full AS
SELECT
    p.paper_id,
    p.paper_code,
    p.title,
    p.abstract,
    p.year,
    v.venue_name,
    v.venue_type,
    p.citation_count,
    ra.area_name            AS research_area,
    p.doi,
    p.publication_type,
    p.extra_metadata,
    p.created_at,
    p.updated_at
FROM papers p
LEFT JOIN venues         v  ON v.venue_id = p.venue_id
LEFT JOIN research_areas ra ON ra.area_id = p.primary_research_area_id;

-- Authors aggregated per paper
CREATE OR REPLACE VIEW v_paper_authors_agg AS
SELECT
    pa.paper_id,
    LISTAGG(a.full_name, '; ') WITHIN GROUP (ORDER BY pa.author_order) AS authors
FROM paper_authors pa
JOIN authors a ON a.author_id = pa.author_id
GROUP BY pa.paper_id;

-- Keywords aggregated per paper
CREATE OR REPLACE VIEW v_paper_keywords_agg AS
SELECT
    pk.paper_id,
    LISTAGG(k.keyword_text, '; ') WITHIN GROUP (ORDER BY k.keyword_text) AS keywords
FROM paper_keywords pk
JOIN keywords k ON k.keyword_id = pk.keyword_id
GROUP BY pk.paper_id;

-- Catalog of research areas
CREATE OR REPLACE VIEW v_research_area_catalog AS
SELECT
    ra.area_id,
    ra.area_name,
    parent.area_name AS parent_area,
    ra.description
FROM research_areas ra
LEFT JOIN research_areas parent ON parent.area_id = ra.parent_area_id
ORDER BY ra.area_name;

-- Paper summary (lightweight, used by list endpoints)
CREATE OR REPLACE VIEW v_paper_summary AS
SELECT
    p.paper_id,
    p.paper_code,
    p.title,
    p.year,
    v.venue_name,
    p.citation_count,
    ra.area_name AS research_area
FROM papers p
LEFT JOIN venues         v  ON v.venue_id = p.venue_id
LEFT JOIN research_areas ra ON ra.area_id = p.primary_research_area_id;

PROMPT Views created. Run 05_materialized_views.sql next.
