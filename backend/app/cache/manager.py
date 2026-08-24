import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.external.normalizer import NormalizedPaper

class GlobalQueryCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[float, List[NormalizedPaper]]] = {}
        
    def _hash(self, query: str) -> str:
        return hashlib.sha256(query.lower().strip().encode("utf-8")).hexdigest()
        
    def get(self, query: str) -> Optional[List[NormalizedPaper]]:
        q_hash = self._hash(query)
        if q_hash in self._cache:
            expiry, results = self._cache[q_hash]
            if datetime.now(timezone.utc).timestamp() < expiry:
                return results
            else:
                del self._cache[q_hash]
        return None
        
    def set(self, query: str, results: List[NormalizedPaper]):
        q_hash = self._hash(query)
        expiry = datetime.now(timezone.utc).timestamp() + self.ttl_seconds
        self._cache[q_hash] = (expiry, results)

_cache_instance = GlobalQueryCache()

def get_query_cache() -> GlobalQueryCache:
    return _cache_instance
