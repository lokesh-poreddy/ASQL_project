import pytest
from app.external.normalizer import NormalizedPaper
from app.external.deduplicator import DuplicateResolver
from app.cache.manager import GlobalQueryCache

def test_deduplicator():
    papers = [
        NormalizedPaper(paper_id="1", title="Test Paper", source="A", source_id="1", retrieved_at="", doi="10.123/456"),
        NormalizedPaper(paper_id="2", title="test paper", source="B", source_id="2", retrieved_at="", doi="10.123/456"),
        NormalizedPaper(paper_id="3", title="Different Paper", source="C", source_id="3", retrieved_at="", doi=None)
    ]
    unique = DuplicateResolver.deduplicate(papers)
    assert len(unique) == 2
    assert unique[0].paper_id == "1"
    assert unique[1].paper_id == "3"

def test_cache():
    cache = GlobalQueryCache(ttl_seconds=10)
    papers = [NormalizedPaper(paper_id="1", title="A", source="S", source_id="1", retrieved_at="")]
    
    cache.set("transformers", papers)
    cached = cache.get("transformers")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].title == "A"
    
    assert cache.get("other query") is None
