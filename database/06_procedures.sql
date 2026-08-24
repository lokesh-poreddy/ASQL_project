-- =============================================================================
-- NEXUS-SQL | 06_procedures.sql
-- Layer: STORED PROCEDURES  –  Utility PL/SQL used by the Python backend.
-- =============================================================================

-- Refresh all materialized views (called by the metrics aggregator after
-- a bulk experiment run).
CREATE OR REPLACE PROCEDURE nexus_refresh_mviews AS
BEGIN
    DBMS_MVIEW.REFRESH('MV_RESEARCH_AREA_STATS', method => 'C');
    DBMS_MVIEW.REFRESH('MV_VENUE_STATS',          method => 'C');
    DBMS_MVIEW.REFRESH('MV_PAPER_INTERNAL_CITATIONS', method => 'C');
    DBMS_OUTPUT.PUT_LINE('All materialized views refreshed at ' ||
                         TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'));
END nexus_refresh_mviews;
/

-- Increment citation count atomically (called when a new citation row is
-- inserted rather than relying on an application-level SELECT + UPDATE).
CREATE OR REPLACE PROCEDURE nexus_inc_citation_count (
    p_cited_paper_id IN papers.paper_id%TYPE
) AS
BEGIN
    UPDATE papers
    SET    citation_count = citation_count + 1,
           updated_at     = SYSTIMESTAMP
    WHERE  paper_id = p_cited_paper_id;

    IF SQL%ROWCOUNT = 0 THEN
        RAISE_APPLICATION_ERROR(-20001,
            'Paper ' || p_cited_paper_id || ' not found.');
    END IF;
END nexus_inc_citation_count;
/

-- Trigger to keep citation_count consistent automatically.
CREATE OR REPLACE TRIGGER trg_citations_after_insert
AFTER INSERT ON citations
FOR EACH ROW
BEGIN
    nexus_inc_citation_count(:NEW.cited_paper_id);
END;
/

-- Trigger to decrement on DELETE.
CREATE OR REPLACE TRIGGER trg_citations_after_delete
AFTER DELETE ON citations
FOR EACH ROW
BEGIN
    UPDATE papers
    SET    citation_count = GREATEST(citation_count - 1, 0),
           updated_at     = SYSTIMESTAMP
    WHERE  paper_id = :OLD.cited_paper_id;
END;
/

PROMPT Procedures and triggers created. Run 07_vector.sql next.
