from typing import Tuple, Optional


class Validators:
    """Класс с методами валидации"""
    
    @staticmethod
    def validate_country_name(name: str) -> Tuple[bool, Optional[str]]:
        """Валидация названия страны"""
        if not name or not name.strip():
            return False, "Название страны не может быть пустым"
        
        if len(name) > 100:
            return False, "Название страны не может превышать 100 символов"
        
        if len(name.strip()) < 2:
            return False, "Название страны должно содержать минимум 2 символа"
        
        return True, None
    
    @staticmethod
    def validate_year(year: int) -> Tuple[bool, Optional[str]]:
        """Валидация года"""
        if not year:
            return False, "Год обязателен"
        
        if not isinstance(year, int) or year < 1900 or year > 2100:
            return False, "Год должен быть между 1900 и 2100"
        
        return True, None
    
    @staticmethod
    def validate_country_id(country_id: int) -> Tuple[bool, Optional[str]]:
        """Валидация ID страны"""
        if not country_id:
            return False, "ID страны обязателен"
        
        if not isinstance(country_id, int) or country_id <= 0:
            return False, "Некорректный ID страны"
        
        return True, None
    
    @staticmethod
    def validate_value(value: Optional[float], name: str) -> Tuple[bool, Optional[str]]:
        """Валидация числовых значений"""
        if value is not None:
            try:
                float_value = float(value)
                if float_value < 0:
                    return False, f"{name} не может быть отрицательным"
            except (ValueError, TypeError):
                return False, f"{name} должен быть числом"
        
        return True, None
    
    @staticmethod
    def validate_indicator_data(country_id: int, year: int, 
                                export_value: Optional[float] = None,
                                import_value: Optional[float] = None,
                                gdp_value: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """Валидация всех данных показателя"""
        
        # Валидация country_id
        is_valid, error = Validators.validate_country_id(country_id)
        if not is_valid:
            return False, error
        
        # Валидация года
        is_valid, error = Validators.validate_year(year)
        if not is_valid:
            return False, error
        
        # Валидация значений
        is_valid, error = Validators.validate_value(export_value, "Экспорт")
        if not is_valid:
            return False, error
        
        is_valid, error = Validators.validate_value(import_value, "Импорт")
        if not is_valid:
            return False, error
        
        is_valid, error = Validators.validate_value(gdp_value, "ВВП")
        if not is_valid:
            return False, error
        
        return True, None