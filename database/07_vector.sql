-- =============================================================================
-- NEXUS-SQL | 07_vector.sql
-- Layer: VECTOR COLUMNS & INDEXES
--
-- This script inspects the Oracle version before adding VECTOR columns or
-- creating vector indexes. Oracle 23ai (23.x) is required for native VECTOR
-- support. On older versions the script emits a warning and exits cleanly so
-- that 01_schema.sql tables remain usable with the in-memory hashing fallback.
-- =============================================================================

DECLARE
    v_version   VARCHAR2(100);
    v_major     NUMBER;
BEGIN
    -- Extract major version number from the banner
    SELECT REGEXP_SUBSTR(version, '^\d+') INTO v_major
    FROM v$instance;

    DBMS_OUTPUT.PUT_LINE('Oracle major version detected: ' || v_major);

    IF v_major < 23 THEN
        DBMS_OUTPUT.PUT_LINE(
            'WARNING: Oracle 23ai required for native VECTOR type. ' ||
            'Skipping vector column/index creation. ' ||
            'The application will fall back to hashing-based in-memory vector search.'
        );
        RETURN;
    END IF;

    -- ── Add VECTOR columns to paper_embeddings ───────────────────────────────
    -- FP32 full precision
    EXECUTE IMMEDIATE
        'ALTER TABLE paper_embeddings ADD (embedding_f32 VECTOR(384, FLOAT32))';

    -- FP64 for baseline accuracy measurement only
    EXECUTE IMMEDIATE
        'ALTER TABLE paper_embeddings ADD (embedding_f64 VECTOR(384, FLOAT64))';

    -- INT8 quantized (compression experiment)
    EXECUTE IMMEDIATE
        'ALTER TABLE paper_embeddings ADD (embedding_i8  VECTOR(384, INT8))';

    DBMS_OUTPUT.PUT_LINE('VECTOR columns added to paper_embeddings.');

    -- ── HNSW index on FP32 column (primary search) ───────────────────────────
    -- Parameters chosen conservatively; tuned by the resource optimizer.
    EXECUTE IMMEDIATE
        'CREATE VECTOR INDEX ix_paper_embeddings_f32_hnsw
         ON paper_embeddings(embedding_f32)
         ORGANIZATION INMEMORY NEIGHBOR GRAPH
         DISTANCE COSINE
         WITH TARGET ACCURACY 90
         PARAMETERS (type HNSW, neighbors 32, efconstruction 200)';

    DBMS_OUTPUT.PUT_LINE('HNSW vector index created (FP32).');

    -- ── IVF index on INT8 column (compression experiment) ────────────────────
    EXECUTE IMMEDIATE
        'CREATE VECTOR INDEX ix_paper_embeddings_i8_ivf
         ON paper_embeddings(embedding_i8)
         ORGANIZATION NEIGHBOR PARTITIONS
         DISTANCE COSINE
         WITH TARGET ACCURACY 85
         PARAMETERS (type IVF, neighbor_partitions 64)';

    DBMS_OUTPUT.PUT_LINE('IVF vector index created (INT8).');

EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Error during vector setup: ' || SQLERRM);
        RAISE;
END;
/

PROMPT Vector column/index setup complete. Run 08_seed.sql next.
