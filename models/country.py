from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Country:
    id: Optional[int]
    name: str
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }