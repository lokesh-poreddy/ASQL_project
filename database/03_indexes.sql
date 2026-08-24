-- =============================================================================
-- NEXUS-SQL | 03_indexes.sql
-- Layer: INDEXES  –  B-tree and bitmap indexes for the SQL retrieval path.
-- Vector indexes are in 07_vector.sql.
-- =============================================================================

-- ── papers ───────────────────────────────────────────────────────────────────
CREATE INDEX ix_papers_year            ON papers(year);
CREATE INDEX ix_papers_citations       ON papers(citation_count);
CREATE INDEX ix_papers_venue           ON papers(venue_id);
CREATE INDEX ix_papers_area            ON papers(primary_research_area_id);
CREATE INDEX ix_papers_year_citations  ON papers(year, citation_count);
CREATE INDEX ix_papers_year_area       ON papers(year, primary_research_area_id);
CREATE INDEX ix_papers_code            ON papers(paper_code);

-- Full-text index on title for CONTAINS-based search
-- Requires Oracle Text (ctx) to be installed. Comment out if unavailable.
BEGIN
    CTX_DDL.CREATE_PREFERENCE('nexus_lexer', 'BASIC_LEXER');
EXCEPTION
    WHEN OTHERS THEN NULL;  -- ctx not available; skip silently
END;
/

BEGIN
    EXECUTE IMMEDIATE
        'CREATE INDEX ix_papers_title_ft ON papers(title) INDEXTYPE IS CTXSYS.CONTEXT';
EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Oracle Text not available; skipping full-text index.');
END;
/

-- ── authors ──────────────────────────────────────────────────────────────────
CREATE INDEX ix_authors_normalized ON authors(normalized_name);

-- ── paper_authors ─────────────────────────────────────────────────────────────
CREATE INDEX ix_pa_author ON paper_authors(author_id);
CREATE INDEX ix_pa_paper  ON paper_authors(paper_id);

-- ── paper_keywords ────────────────────────────────────────────────────────────
CREATE INDEX ix_pk_keyword ON paper_keywords(keyword_id);

-- ── citations ────────────────────────────────────────────────────────────────
CREATE INDEX ix_cit_cited   ON citations(cited_paper_id);
CREATE INDEX ix_cit_citing  ON citations(citing_paper_id);

-- ── paper_embeddings ─────────────────────────────────────────────────────────
CREATE INDEX ix_emb_paper  ON paper_embeddings(paper_id);
CREATE INDEX ix_emb_model  ON paper_embeddings(model_name, precision_mode);

-- ── query_history ────────────────────────────────────────────────────────────
CREATE INDEX ix_qh_conv    ON query_history(conversation_id);
CREATE INDEX ix_qh_created ON query_history(created_at);

-- ── experiment_results ────────────────────────────────────────────────────────
CREATE INDEX ix_er_name_run  ON experiment_results(experiment_name, run_id);
CREATE INDEX ix_er_metric    ON experiment_results(metric_name);
CREATE INDEX ix_er_created   ON experiment_results(created_at);

PROMPT Indexes created. Run 04_views.sql next.
