from dataclasses import dataclass

@dataclass
class Statistics:
    country_id: int
    year: int
    indicator_id: int
    value: float   # NUMERIC(20,2)

    def to_dict(self) -> dict:
        return {
            'country_id': self.country_id,
            'year': self.year,
            'indicator_id': self.indicator_id,
            'value': float(self.value),
        }