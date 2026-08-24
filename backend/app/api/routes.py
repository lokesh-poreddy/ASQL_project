"""FastAPI route handlers.

Endpoints:
  POST /api/query          – main query pipeline
  POST /api/clarify        – submit clarification answer
  GET  /api/history/{cid}  – fetch conversation history
  GET  /api/schema         – schema snapshot
  GET  /api/health         – liveness + database health
  POST /api/optimize       – resource optimizer recommendation
  GET  /api/metrics        – experiment results summary
  GET  /api/explanation/{cid}/{turn} – explanation for a specific turn
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.ambiguity.detector import AmbiguityDetector
from app.ambiguity.models import AmbiguityResolution
from app.ambiguity.resolver import AmbiguityResolver
from app.api.models import (
    ClarifyRequest,
    HealthResponse,
    MetricsResponse,
    OptimizeRequest,
    OptimizeResponse,
    PaperResult,
    QueryRequest,
    QueryResponse,
    SchemaResponse,
)
from app.common.exceptions import (
    AmbiguityUnresolvedError,
    NexusSQLError,
    RecoveryExhaustedError,
)
from app.common.logging import get_logger
from app.config import get_settings
from app.conversation.manager import get_conversation_manager
from app.conversation.models import RetrievalMode
from app.explanation.explainer import ExplanationEngine
from app.hybrid.retriever import HybridRetriever
from app.optimization.optimizer import ResourceOptimizer
from app.planning.planner import get_planner
from app.recovery.recovery import ErrorRecoveryEngine
from app.schema.manager import get_schema_manager
from app.sql.executor import get_sql_executor
from app.sql.generator import get_sql_generator
from app.sql.validator import SQLValidator

router = APIRouter()
logger = get_logger("api.routes")
_ambiguity_detector = AmbiguityDetector()
_ambiguity_resolver = AmbiguityResolver()
_explainer = ExplanationEngine()
_optimizer = ResourceOptimizer()
_validator = SQLValidator()


def _build_paper_result(row: dict, source: str = "sql") -> PaperResult:
    return PaperResult(
        paper_id=row.get("paper_id", 0),
        title=row.get("title", ""),
        year=row.get("year"),
        citation_count=row.get("citation_count"),
        score=row.get("score"),
        source=source,
    )


# ── POST /api/query ───────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    started = time.perf_counter()
    manager = get_conversation_manager()
    settings = get_settings()

    # 1. Ambiguity detection
    context = manager.build_context(req.conversation_id)
    amb_result = _ambiguity_detector.detect(
        req.query, conversation_context=context
    )

    if amb_result.resolution == AmbiguityResolution.UNANSWERABLE:
        return QueryResponse(
            status="unanswerable",
            conversation_id=req.conversation_id,
            message=amb_result.message,
            ambiguity_type=amb_result.ambiguity_type.value,
        )

    if amb_result.resolution == AmbiguityResolution.ASK_USER:
        manager.add_turn(
            req.conversation_id,
            user_text=req.query,
            clarification_question=amb_result.message,
        )
        return QueryResponse(
            status="clarification_required",
            conversation_id=req.conversation_id,
            message=amb_result.message,
            ambiguity_type=amb_result.ambiguity_type.value,
            options=amb_result.options,
        )

    # 2. Planning
    try:
        plan = get_planner().plan(req.query, conversation_context=context)
    except Exception as exc:
        logger.error("Planning failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Query planning failed: {exc}",
        ) from exc

    alpha = req.alpha if req.alpha is not None else settings.hybrid_alpha
    effective_top_k = plan.structured_intent.limit if plan.structured_intent.limit is not None else req.top_k

    # 3. Retrieval
    results: list[PaperResult] = []
    sql_text: str | None = None
    sql_elapsed: float | None = None
    vector_elapsed: float | None = None
    correction_applied = False
    correction_count = 0

    executor = get_sql_executor()
    generator = get_sql_generator()

    try:
        if plan.retrieval_mode == RetrievalMode.SQL:
            sql_text, params = generator.generate(plan)
            _validator.validate(sql_text)
            recovery = ErrorRecoveryEngine(executor, _validator)
            rec_result = recovery.execute_with_recovery(sql_text, params)
            sql_elapsed = rec_result.total_elapsed_ms
            correction_applied = rec_result.correction_count > 0
            correction_count = rec_result.correction_count
            if rec_result.result:
                results = [
                    _build_paper_result(row, source="sql")
                    for row in rec_result.result.rows[: effective_top_k]
                ]
                sql_text = rec_result.final_sql

        elif plan.retrieval_mode == RetrievalMode.VECTOR:
            from app.vector.oracle_search import get_vector_search
            vs = get_vector_search()
            t0 = time.perf_counter()
            vec_res = vs.search(req.query, top_k=effective_top_k)
            vector_elapsed = (time.perf_counter() - t0) * 1000
            results = [
                PaperResult(
                    paper_id=r.paper_id,
                    title=r.title,
                    score=r.score,
                    source=r.source,
                )
                for r in vec_res
            ]

        else:  # HYBRID
            from app.vector.oracle_search import get_vector_search
            vs = get_vector_search()
            retriever = HybridRetriever(
                sql_executor=executor,
                sql_generator=generator,
                vector_search=vs,
                alpha=alpha,
            )
            hybrid = retriever.retrieve(plan, top_k=effective_top_k, alpha=alpha)
            vector_elapsed = hybrid.elapsed_ms
            results = [
                PaperResult(
                    paper_id=r.paper_id,
                    title=r.title,
                    score=r.final_score,
                    source="hybrid",
                )
                for r in hybrid.results
            ]
            try:
                sql_text, _ = generator.generate(plan)
            except Exception:
                pass

        # -- Global Fallback --
        if plan.needs_global_lookup or len(results) < (effective_top_k // 2):
            logger.info("Triggering Global Search Fallback.")
            from app.external.orchestrator import GlobalSearchOrchestrator
            from app.external.openalex import OpenAlexSource
            from app.external.semanticscholar import SemanticScholarSource
            from app.external.crossref import CrossrefSource
            from app.cache.manager import get_query_cache
            from app.ingestion.pipeline import IngestionPipeline
            from app.vector.provider import get_embedding_provider
            
            cache = get_query_cache()
            cached_global = cache.get(req.query)
            
            if cached_global is None:
                orch = GlobalSearchOrchestrator([
                    OpenAlexSource(),
                    SemanticScholarSource(),
                    CrossrefSource()
                ])
                cached_global = await orch.search(req.query, limit=10)
                if cached_global:
                    cache.set(req.query, cached_global)
                    pipeline = IngestionPipeline(get_embedding_provider())
                    await pipeline.ingest(cached_global)
                    
                    # Re-run local retrieval to fetch the updated answer
                    if plan.retrieval_mode == RetrievalMode.SQL:
                        rec_result = recovery.execute_with_recovery(sql_text, params)
                        if rec_result.result:
                            results = [
                                _build_paper_result(row, source="sql")
                                for row in rec_result.result.rows[: effective_top_k]
                            ]
                    elif plan.retrieval_mode == RetrievalMode.VECTOR:
                        vec_res = vs.search(req.query, top_k=effective_top_k)
                        results = [
                            PaperResult(paper_id=r.paper_id, title=r.title, score=r.score, source=r.source)
                            for r in vec_res
                        ]
                    else:
                        hybrid = retriever.retrieve(plan, top_k=effective_top_k, alpha=alpha)
                        results = [
                            PaperResult(paper_id=r.paper_id, title=r.title, score=r.final_score, source="hybrid")
                            for r in hybrid.results
                        ]

    except RecoveryExhaustedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except NexusSQLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    total_elapsed = (time.perf_counter() - started) * 1000

    # 4. Explanation
    explanation = _explainer.explain(
        user_query=req.query,
        retrieval_mode=plan.retrieval_mode.value,
        structured_intent={
            "filters": [
                {
                    "table": f.table, "column": f.column,
                    "operator": f.operator.value, "value": f.value,
                }
                for f in plan.structured_intent.filters
            ]
        },
        semantic_intent=plan.semantic_intent,
        sql=sql_text,
        sql_elapsed_ms=sql_elapsed,
        vector_elapsed_ms=vector_elapsed,
        total_elapsed_ms=total_elapsed,
        result_count=len(results),
        correction_applied=correction_applied,
        correction_count=correction_count,
        alpha_used=alpha if plan.retrieval_mode != RetrievalMode.SQL else None,
    )

    # 5. Persist turn
    manager.add_turn(
        req.conversation_id,
        user_text=req.query,
        intent={"mode": plan.retrieval_mode.value},
        retrieval_mode=plan.retrieval_mode,
        generated_sql=sql_text,
        result_paper_ids=[r.paper_id for r in results],
    )

    # Double-check gate: Ensure we never return more than effective_top_k
    results = results[:effective_top_k]

    return QueryResponse(
        status="ok",
        conversation_id=req.conversation_id,
        retrieval_mode=plan.retrieval_mode.value,
        results=results,
        result_count=len(results),
        sql=sql_text,
        latency_ms=round(total_elapsed, 2),
        explanation=explanation,
    )


# ── POST /api/clarify ─────────────────────────────────────────────────────────

@router.post("/clarify", response_model=QueryResponse)
async def clarify(req: ClarifyRequest) -> QueryResponse:
    """Merge the user's clarification into the query and re-run."""
    merged_query = f"{req.original_query} — clarification: {req.clarification}"
    return await query(
        QueryRequest(
            conversation_id=req.conversation_id,
            query=merged_query,
        )
    )


# ── GET /api/history/{cid} ────────────────────────────────────────────────────

@router.get("/history/{conversation_id}")
async def history(conversation_id: str) -> dict:
    turns = get_conversation_manager().get_history(conversation_id)
    return {"conversation_id": conversation_id, "turns": turns}


# ── GET /api/schema ───────────────────────────────────────────────────────────

@router.get("/schema", response_model=SchemaResponse)
async def schema() -> SchemaResponse:
    snap = get_schema_manager().get_snapshot()
    return SchemaResponse(
        tables=snap.all_table_names(),
        research_areas=snap.research_area_names(),
        venues=snap.venue_names(),
    )


# ── GET /api/health ───────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    db_status = "ok"

    if settings.use_oracle:
        from app.database.connection import get_pool
        db_status = "ok" if get_pool().health_check() else "error"
    else:
        db_status = "test_mode"

    return HealthResponse(
        status="ok",
        database=db_status,
        embedding_provider=settings.embedding_provider.value,
    )


# ── POST /api/optimize ────────────────────────────────────────────────────────

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize(req: OptimizeRequest) -> OptimizeResponse:
    config = _optimizer.select_configuration(
        storage_budget_mb=req.storage_budget_mb,
        latency_budget_ms=req.latency_budget_ms,
        accuracy_target=req.accuracy_target,
    )
    return OptimizeResponse(
        precision_mode=config.precision_mode,
        index_type=config.index_type,
        search_depth=config.search_depth,
        candidate_count=config.candidate_count,
        storage_budget_mb=config.storage_budget_mb,
        latency_budget_ms=config.latency_budget_ms,
        accuracy_target=config.accuracy_target,
    )


# ── GET /api/metrics ──────────────────────────────────────────────────────────

@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """Return summary of experiment results (Oracle) or empty list (test mode)."""
    settings = get_settings()
    experiments: list[dict] = []

    if settings.use_oracle:
        try:
            from app.database.connection import get_pool
            with get_pool().get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT experiment_name, run_id, metric_name, metric_value, created_at
                    FROM   experiment_results
                    ORDER  BY created_at DESC
                    FETCH  FIRST 100 ROWS ONLY
                    """
                )
                rows = cursor.fetchall()
                cursor.close()
            experiments = [
                {
                    "experiment_name": r[0],
                    "run_id": r[1],
                    "metric_name": r[2],
                    "metric_value": r[3],
                    "created_at": str(r[4]),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning("Could not load experiment results: %s", exc)

    return MetricsResponse(experiment_count=len(experiments), experiments=experiments)
