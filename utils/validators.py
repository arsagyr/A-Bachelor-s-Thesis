from typing import Tuple, Optional


class Validators:
    
    @staticmethod
    def validate_country_name(name: str) -> Tuple[bool, Optional[str]]:
        if not name or not name.strip():
            return False, "Название страны не может быть пустым"
        if len(name) > 100:
            return False, "Название страны не может превышать 100 символов"
        return True, None
    
    @staticmethod
    def validate_year(year: int) -> Tuple[bool, Optional[str]]:
        if not year:
            return False, "Год обязателен"
        if year < 1900 or year > 2100:
            return False, "Год должен быть между 1900 и 2100"
        return True, None
    
    @staticmethod
    def validate_country_id(country_id: int) -> Tuple[bool, Optional[str]]:
        if not country_id or country_id <= 0:
            return False, "Некорректный ID страны"
        return True, None