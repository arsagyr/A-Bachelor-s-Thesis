from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Country:
    """Модель страны"""
    id: Optional[int]
    name: str
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Country':
        """Создание из словаря"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            created_at=data.get('created_at')
        )