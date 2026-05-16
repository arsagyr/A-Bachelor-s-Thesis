from dataclasses import dataclass
from typing import Optional


@dataclass
class CountryStats:
    """Статистика по стране"""
    country_id: int
    country_name: str
    years_count: int
    min_year: Optional[int]
    max_year: Optional[int]
    avg_export: Optional[float]
    avg_import: Optional[float]
    avg_gdp: Optional[float]
    max_export: Optional[float]
    max_import: Optional[float]
    max_gdp: Optional[float]
    min_export: Optional[float]
    min_import: Optional[float]
    min_gdp: Optional[float]
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'country_id': self.country_id,
            'country_name': self.country_name,
            'years_count': self.years_count,
            'min_year': self.min_year,
            'max_year': self.max_year,
            'avg_export': float(self.avg_export) if self.avg_export else None,
            'avg_import': float(self.avg_import) if self.avg_import else None,
            'avg_gdp': float(self.avg_gdp) if self.avg_gdp else None,
            'max_export': float(self.max_export) if self.max_export else None,
            'max_import': float(self.max_import) if self.max_import else None,
            'max_gdp': float(self.max_gdp) if self.max_gdp else None,
            'min_export': float(self.min_export) if self.min_export else None,
            'min_import': float(self.min_import) if self.min_import else None,
            'min_gdp': float(self.min_gdp) if self.min_gdp else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CountryStats':
        """Создание из словаря"""
        return cls(
            country_id=data.get('country_id'),
            country_name=data.get('country_name'),
            years_count=data.get('years_count', 0),
            min_year=data.get('min_year'),
            max_year=data.get('max_year'),
            avg_export=data.get('avg_export'),
            avg_import=data.get('avg_import'),
            avg_gdp=data.get('avg_gdp'),
            max_export=data.get('max_export'),
            max_import=data.get('max_import'),
            max_gdp=data.get('max_gdp'),
            min_export=data.get('min_export'),
            min_import=data.get('min_import'),
            min_gdp=data.get('min_gdp')
        )