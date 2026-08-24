from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ScholarlySource(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search a scholarly source and return raw dict results."""
        raise NotImplementedError
