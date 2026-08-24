-- =============================================================================
-- NEXUS-SQL | 02_constraints.sql
-- Layer: CONSTRAINTS  –  FK, CHECK, and UNIQUE rules.
-- =============================================================================

-- ── venues ────────────────────────────────────────────────────────────────────
ALTER TABLE venues ADD CONSTRAINT chk_venues_type
    CHECK (venue_type IN ('CONFERENCE','JOURNAL','WORKSHOP','PREPRINT_SERVER'));

ALTER TABLE venues ADD CONSTRAINT uq_venues_name
    UNIQUE (venue_name);

-- ── research_areas ───────────────────────────────────────────────────────────
ALTER TABLE research_areas ADD CONSTRAINT uq_area_name
    UNIQUE (area_name);

ALTER TABLE research_areas ADD CONSTRAINT fk_area_parent
    FOREIGN KEY (parent_area_id) REFERENCES research_areas(area_id);

-- ── keywords ─────────────────────────────────────────────────────────────────
ALTER TABLE keywords ADD CONSTRAINT uq_keyword_text
    UNIQUE (keyword_text);

-- ── papers ───────────────────────────────────────────────────────────────────
ALTER TABLE papers ADD CONSTRAINT uq_paper_code
    UNIQUE (paper_code);

ALTER TABLE papers ADD CONSTRAINT chk_paper_year
    CHECK (year BETWEEN 1900 AND 2200);

ALTER TABLE papers ADD CONSTRAINT chk_citation_count
    CHECK (citation_count >= 0);

ALTER TABLE papers ADD CONSTRAINT chk_publication_type
    CHECK (publication_type IS NULL OR
           publication_type IN ('ARTICLE','CONFERENCE_PAPER','PREPRINT','BOOK_CHAPTER','THESIS'));

ALTER TABLE papers ADD CONSTRAINT fk_papers_venue
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id);

ALTER TABLE papers ADD CONSTRAINT fk_papers_area
    FOREIGN KEY (primary_research_area_id) REFERENCES research_areas(area_id);

-- ── paper_authors ─────────────────────────────────────────────────────────────
ALTER TABLE paper_authors ADD CONSTRAINT fk_pa_paper
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE;

ALTER TABLE paper_authors ADD CONSTRAINT fk_pa_author
    FOREIGN KEY (author_id) REFERENCES authors(author_id);

ALTER TABLE paper_authors ADD CONSTRAINT chk_pa_order
    CHECK (author_order >= 1);

-- ── paper_keywords ────────────────────────────────────────────────────────────
ALTER TABLE paper_keywords ADD CONSTRAINT fk_pk_paper
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE;

ALTER TABLE paper_keywords ADD CONSTRAINT fk_pk_keyword
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id);

-- ── citations ────────────────────────────────────────────────────────────────
ALTER TABLE citations ADD CONSTRAINT fk_cit_citing
    FOREIGN KEY (citing_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE;

ALTER TABLE citations ADD CONSTRAINT fk_cit_cited
    FOREIGN KEY (cited_paper_id)  REFERENCES papers(paper_id) ON DELETE CASCADE;

ALTER TABLE citations ADD CONSTRAINT chk_cit_no_self
    CHECK (citing_paper_id <> cited_paper_id);

ALTER TABLE citations ADD CONSTRAINT uq_citation
    UNIQUE (citing_paper_id, cited_paper_id);

-- ── paper_embeddings ─────────────────────────────────────────────────────────
ALTER TABLE paper_embeddings ADD CONSTRAINT fk_emb_paper
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE;

ALTER TABLE paper_embeddings ADD CONSTRAINT chk_emb_precision
    CHECK (precision_mode IN ('FP32','FP16','INT8'));

ALTER TABLE paper_embeddings ADD CONSTRAINT uq_emb_paper_model_precision
    UNIQUE (paper_id, model_name, precision_mode);

-- ── query_history ────────────────────────────────────────────────────────────
ALTER TABLE query_history ADD CONSTRAINT chk_qh_mode
    CHECK (retrieval_mode IS NULL OR retrieval_mode IN ('SQL','VECTOR','HYBRID'));

-- ── query_executions ─────────────────────────────────────────────────────────
ALTER TABLE query_executions ADD CONSTRAINT fk_qe_history
    FOREIGN KEY (history_id) REFERENCES query_history(history_id) ON DELETE CASCADE;

ALTER TABLE query_executions ADD CONSTRAINT chk_qe_status
    CHECK (status IN ('SUCCESS','FAILED'));

ALTER TABLE query_executions ADD CONSTRAINT fk_qe_corrected_from
    FOREIGN KEY (corrected_from_execution_id)
    REFERENCES query_executions(execution_id);

-- ── experiment_results ────────────────────────────────────────────────────────
ALTER TABLE experiment_results ADD CONSTRAINT chk_er_synthetic
    CHECK (is_synthetic_smoke_test IN (0,1));

PROMPT Constraints applied successfully. Run 03_indexes.sql next.
