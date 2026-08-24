import asyncio
from typing import List
from app.external.normalizer import NormalizedPaper
from app.common.logging import get_logger
from app.config import get_settings
from app.sql.executor import InMemorySQLExecutor
from app.vector.oracle_search import InMemoryVectorSearch

logger = get_logger("ingestion.pipeline")

class IngestionPipeline:
    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider

    async def ingest(self, papers: List[NormalizedPaper]) -> None:
        """Insert papers into the local SQL DB and vector index."""
        if not papers:
            return
            
        logger.info("Ingesting %d global papers into local database.", len(papers))
        settings = get_settings()
        
        if settings.use_oracle:
            # Oracle ingestion logic goes here
            pass
        else:
            # InMemory mode: append to the static lists
            existing_ids = [r.get("paper_id", 0) for r in InMemorySQLExecutor.SEED_ROWS]
            next_id = max(existing_ids) + 1 if existing_ids else 1
            
            for p in papers:
                # check if already exists by title
                if any(r.get("title", "").lower() == p.title.lower() for r in InMemorySQLExecutor.SEED_ROWS):
                    continue
                    
                InMemorySQLExecutor.SEED_ROWS.append({
                    "paper_id": next_id,
                    "paper_code": f"P-{next_id:05d}",
                    "title": p.title,
                    "year": p.year or 2026,
                    "citation_count": p.citation_count,
                    "primary_research_area_id": 1,
                    "source": p.source,
                    "score": 0.0,
                })
                
                # Append to Vector Search SEED_PAPERS
                InMemoryVectorSearch.SEED_PAPERS.append((next_id, p.title))
                
                next_id += 1
