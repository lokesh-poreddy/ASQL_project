-- =============================================================================
-- NEXUS-SQL | 09_cleanup.sql
-- Layer: TEARDOWN (dev/test environments only)
--
-- Drops everything created by 01-08, then the application user itself.
-- Run the first block connected as nexus_sql_app, then the final DROP USER
-- connected as a DBA-privileged user (same session that ran 00_create_user.sql).
-- Guarded with existence checks so it is safe to re-run against a partially
-- torn-down environment.
-- =============================================================================

-- --- Materialized views (must go before their base tables) ---
BEGIN
    FOR mv IN (SELECT mview_name FROM user_mviews WHERE mview_name IN
        ('MV_RESEARCH_AREA_STATS', 'MV_VENUE_STATS', 'MV_PAPER_INTERNAL_CITATIONS'))
    LOOP
        EXECUTE IMMEDIATE 'DROP MATERIALIZED VIEW ' || mv.mview_name;
    END LOOP;
END;
/

-- --- Triggers ---
BEGIN
    FOR t IN (SELECT trigger_name FROM user_triggers WHERE trigger_name IN
        ('TRG_CITATIONS_AFTER_INSERT', 'TRG_CITATIONS_AFTER_DELETE'))
    LOOP
        EXECUTE IMMEDIATE 'DROP TRIGGER ' || t.trigger_name;
    END LOOP;
END;
/

-- --- Procedures ---
BEGIN
    FOR p IN (SELECT object_name FROM user_objects
              WHERE object_type = 'PROCEDURE' AND object_name IN
              ('NEXUS_REFRESH_MVIEWS', 'NEXUS_INC_CITATION_COUNT'))
    LOOP
        EXECUTE IMMEDIATE 'DROP PROCEDURE ' || p.object_name;
    END LOOP;
END;
/

-- --- Views ---
BEGIN
    FOR v IN (SELECT view_name FROM user_views WHERE view_name IN
        ('V_PAPER_FULL', 'V_PAPER_AUTHORS_AGG', 'V_PAPER_KEYWORDS_AGG',
         'V_RESEARCH_AREA_CATALOG', 'V_PAPER_SUMMARY'))
    LOOP
        EXECUTE IMMEDIATE 'DROP VIEW ' || v.view_name;
    END LOOP;
END;
/

-- --- Vector indexes ---
BEGIN
    FOR idx IN (SELECT index_name FROM user_indexes WHERE index_name IN
        ('IX_PAPER_EMBEDDINGS_F32_HNSW', 'IX_PAPER_EMBEDDINGS_I8_IVF'))
    LOOP
        EXECUTE IMMEDIATE 'DROP INDEX ' || idx.index_name;
    END LOOP;
END;
/

-- --- Tables (children before parents) ---
BEGIN
    FOR t IN (SELECT table_name FROM user_tables WHERE table_name IN (
        'EXPERIMENT_RESULTS', 'QUERY_EXECUTIONS', 'QUERY_HISTORY',
        'PAPER_EMBEDDINGS', 'CITATIONS', 'PAPER_KEYWORDS', 'PAPER_AUTHORS',
        'PAPERS', 'KEYWORDS', 'RESEARCH_AREAS', 'VENUES', 'AUTHORS'))
    LOOP
        EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' CASCADE CONSTRAINTS PURGE';
    END LOOP;
END;
/

PROMPT Schema objects dropped for nexus_sql_app.
PROMPT To remove the user entirely, reconnect as a DBA-privileged user and run:
PROMPT   DROP USER nexus_sql_app CASCADE;
