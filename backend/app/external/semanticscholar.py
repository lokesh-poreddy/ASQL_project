import httpx
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.external.base import ScholarlySource

import os

class SemanticScholarSource(ScholarlySource):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "paperId,title,abstract,authors,year,citationCount,venue,url,externalIds"
        }
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []
                
        results = []
        for p in data.get("data", []):
            doi = p.get("externalIds", {}).get("DOI")
            results.append({
                "paper_id": p.get("paperId"),
                "title": p.get("title") or "",
                "abstract": p.get("abstract"),
                "authors": [{"name": a.get("name")} for a in p.get("authors", []) if a.get("name")],
                "year": p.get("year"),
                "citation_count": p.get("citationCount") or 0,
                "venue": p.get("venue"),
                "doi": doi,
                "source": "Semantic Scholar",
                "source_id": p.get("paperId"),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_url": p.get("url")
            })
        return results
