import asyncio
from typing import List
from app.external.base import ScholarlySource
from app.external.normalizer import NormalizedPaper
from app.external.deduplicator import DuplicateResolver

class GlobalSearchOrchestrator:
    def __init__(self, sources: List[ScholarlySource]):
        self.sources = sources

    async def search(self, query: str, limit: int = 10) -> List[NormalizedPaper]:
        tasks = [source.search(query, limit=limit) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_papers = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                continue
            for record in res:
                all_papers.append(NormalizedPaper(**record))
                
        return DuplicateResolver.deduplicate(all_papers)
