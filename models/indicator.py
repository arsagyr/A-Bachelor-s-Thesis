from dataclasses import dataclass
from typing import Optional


@dataclass
class Indicator:
    id: Optional[int]
    country_id: int
    year: int
    export_value: Optional[float] = None
    import_value: Optional[float] = None
    gdp_value: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'country_id': self.country_id,
            'year': self.year,
            'export_value': float(self.export_value) if self.export_value else None,
            'import_value': float(self.import_value) if self.import_value else None,
            'gdp_value': float(self.gdp_value) if self.gdp_value else None
        }