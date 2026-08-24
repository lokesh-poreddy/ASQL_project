import httpx
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.external.base import ScholarlySource

class OpenAlexSource(ScholarlySource):
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        url = "https://api.openalex.org/works"
        params = {"search": query, "per-page": limit}
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []
        
        results = []
        for w in data.get("results", []):
            authors = [a.get("author", {}).get("display_name") for a in w.get("authorships", []) if a.get("author")]
            results.append({
                "paper_id": w.get("id"),
                "title": w.get("title") or "",
                "abstract": None, # OpenAlex inverted abstract requires parsing
                "authors": [{"name": a} for a in authors if a],
                "year": w.get("publication_year"),
                "citation_count": w.get("cited_by_count", 0),
                "venue": w.get("primary_location", {}).get("source", {}).get("display_name") if w.get("primary_location") else None,
                "doi": w.get("doi"),
                "source": "OpenAlex",
                "source_id": w.get("id"),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_url": w.get("id")
            })
        return results
