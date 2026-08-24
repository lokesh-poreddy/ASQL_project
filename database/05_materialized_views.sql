-- =============================================================================
-- NEXUS-SQL | 05_materialized_views.sql
-- Layer: MATERIALIZED VIEWS  –  Pre-aggregated stats for the metrics layer.
-- =============================================================================

-- Research area publication statistics
CREATE MATERIALIZED VIEW mv_research_area_stats
    BUILD IMMEDIATE
    REFRESH COMPLETE ON DEMAND
AS
SELECT
    ra.area_id,
    ra.area_name,
    COUNT(p.paper_id)              AS paper_count,
    AVG(p.citation_count)          AS avg_citations,
    MAX(p.citation_count)          AS max_citations,
    MIN(p.year)                    AS earliest_year,
    MAX(p.year)                    AS latest_year
FROM research_areas ra
LEFT JOIN papers p ON p.primary_research_area_id = ra.area_id
GROUP BY ra.area_id, ra.area_name;

-- Venue statistics
CREATE MATERIALIZED VIEW mv_venue_stats
    BUILD IMMEDIATE
    REFRESH COMPLETE ON DEMAND
AS
SELECT
    v.venue_id,
    v.venue_name,
    v.venue_type,
    COUNT(p.paper_id)   AS paper_count,
    AVG(p.citation_count) AS avg_citations
FROM venues v
LEFT JOIN papers p ON p.venue_id = v.venue_id
GROUP BY v.venue_id, v.venue_name, v.venue_type;

-- Internal citation graph (citing → cited within the same corpus)
CREATE MATERIALIZED VIEW mv_paper_internal_citations
    BUILD IMMEDIATE
    REFRESH COMPLETE ON DEMAND
AS
SELECT
    c.citing_paper_id,
    c.cited_paper_id,
    p_citing.title AS citing_title,
    p_cited.title  AS cited_title
FROM citations c
JOIN papers p_citing ON p_citing.paper_id = c.citing_paper_id
JOIN papers p_cited  ON p_cited.paper_id  = c.cited_paper_id;

PROMPT Materialized views created. Run 06_procedures.sql next.
