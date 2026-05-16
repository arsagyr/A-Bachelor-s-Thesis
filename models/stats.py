from dataclasses import dataclass
from typing import Optional


@dataclass
class CountryStats:
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
    
    def to_dict(self) -> dict:
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
            'max_gdp': float(self.max_gdp) if self.max_gdp else None
        }