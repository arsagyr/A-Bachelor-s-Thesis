from dataclasses import dataclass
from typing import Optional

@dataclass
class Indicator:
    id: Optional[int]
    name: str  

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
        }