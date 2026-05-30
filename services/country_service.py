from typing import Optional, Tuple, List, Dict, Any
from database import with_db_connection
from repositories.country_repository import CountryRepository
from models.country import Country
from utils.validators import Validators


class CountryService:

    @staticmethod
    @with_db_connection
    def get_all_countries(conn) -> List[Dict[str, Any]]:
        repo = CountryRepository(conn)
        countries = repo.get_all()
        # Для совместимости добавляем created_at=None (раньше поле было)
        return [
            {
                'id': c.id,
                'name': c.name,
                'created_at': None   # в новой схеме нет created_at
            }
            for c in countries
        ]

    @staticmethod
    @with_db_connection
    def add_country(conn, name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        is_valid, error = Validators.validate_country_name(name)
        if not is_valid:
            return None, error

        repo = CountryRepository(conn)
        try:
            country = repo.create(name.strip())
            conn.commit()
            return {
                'id': country.id,
                'name': country.name,
                'created_at': None
            }, None
        except Exception as e:
            conn.rollback()
            return None, f"Ошибка: {str(e)}"

    @staticmethod
    @with_db_connection
    def delete_country(conn, country_id: int) -> Tuple[bool, str]:
        repo = CountryRepository(conn)
        country = repo.get_by_id(country_id)
        if not country:
            return False, "Страна не найдена"

        try:
            deleted = repo.delete(country_id)
            conn.commit()
            if deleted:
                return True, f"Страна '{country.name}' успешно удалена"
            return False, "Ошибка при удалении"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {str(e)}"