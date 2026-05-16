from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Indicator:
    """Модель экономического показателя"""
    id: Optional[int]
    country_id: int
    year: int
    export_value: Optional[float] = None
    import_value: Optional[float] = None
    gdp_value: Optional[float] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'country_id': self.country_id,
            'year': self.year,
            'export_value': float(self.export_value) if self.export_value else None,
            'import_value': float(self.import_value) if self.import_value else None,
            'gdp_value': float(self.gdp_value) if self.gdp_value else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Indicator':
        """Создание из словаря"""
        return cls(
            id=data.get('id'),
            country_id=data.get('country_id'),
            year=data.get('year'),
            export_value=data.get('export_value'),
            import_value=data.get('import_value'),
            gdp_value=data.get('gdp_value'),
            updated_at=data.get('updated_at')
        )