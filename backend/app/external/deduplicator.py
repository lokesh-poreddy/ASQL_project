from typing import List
from app.external.normalizer import NormalizedPaper

class DuplicateResolver:
    @staticmethod
    def deduplicate(papers: List[NormalizedPaper]) -> List[NormalizedPaper]:
        """Deduplicate by DOI or title (case-insensitive)."""
        seen_dois = set()
        seen_titles = set()
        unique = []
        
        for paper in papers:
            is_dup = False
            if paper.doi:
                doi = paper.doi.lower().strip()
                if doi in seen_dois:
                    is_dup = True
                else:
                    seen_dois.add(doi)
                    
            if not is_dup and paper.title:
                title = paper.title.lower().strip()
                if title in seen_titles:
                    is_dup = True
                else:
                    seen_titles.add(title)
                    
            if not is_dup:
                unique.append(paper)
                
        return unique
