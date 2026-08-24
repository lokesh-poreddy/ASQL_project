from pydantic import BaseModel
from typing import List, Optional

class NormalizedAuthor(BaseModel):
    name: str

class NormalizedPaper(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str] = None
    authors: List[NormalizedAuthor] = []
    year: Optional[int] = None
    citation_count: int = 0
    venue: Optional[str] = None
    doi: Optional[str] = None
    source: str
    source_id: str
    retrieved_at: str
    source_url: Optional[str] = None
