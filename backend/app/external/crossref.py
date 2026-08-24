import httpx
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.external.base import ScholarlySource

class CrossrefSource(ScholarlySource):
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        url = "https://api.crossref.org/works"
        params = {"query": query, "rows": limit}
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []
                
        results = []
        for item in data.get("message", {}).get("items", []):
            title = item.get("title", [""])[0] if item.get("title") else ""
            authors = [a.get("given", "") + " " + a.get("family", "") for a in item.get("author", [])]
            venue = item.get("container-title", [""])[0] if item.get("container-title") else None
            
            year = None
            try:
                year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
            except Exception:
                pass
                
            results.append({
                "paper_id": item.get("DOI"),
                "title": title,
                "abstract": item.get("abstract"),
                "authors": [{"name": a.strip()} for a in authors if a.strip()],
                "year": year,
                "citation_count": item.get("is-referenced-by-count", 0),
                "venue": venue,
                "doi": item.get("DOI"),
                "source": "Crossref",
                "source_id": item.get("DOI"),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_url": item.get("URL")
            })
        return results
