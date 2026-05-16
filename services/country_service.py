from typing import Optional, Tuple, List, Dict, Any
from database import with_db_connection
from models.country import Country
from utils.validators import Validators


class CountryService:
    """Сервис для работы со странами"""
    
    @staticmethod
    @with_db_connection
    def get_all_countries(conn) -> List[Dict[str, Any]]:
        """Получение всех стран"""
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at FROM countries ORDER BY name")
        countries_data = cur.fetchall()
        cur.close()
        
        countries = [
            Country(
                id=c['id'],
                name=c['name'],
                created_at=c['created_at']
            ) for c in countries_data
        ]
        
        return [c.to_dict() for c in countries]
    
    @staticmethod
    @with_db_connection
    def get_country_by_id(conn, country_id: int) -> Optional[Dict[str, Any]]:
        """Получение страны по ID"""
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at FROM countries WHERE id = %s", (country_id,))
        country_data = cur.fetchone()
        cur.close()
        
        if country_data:
            country = Country(
                id=country_data['id'],
                name=country_data['name'],
                created_at=country_data['created_at']
            )
            return country.to_dict()
        return None
    
    @staticmethod
    @with_db_connection
    def add_country(conn, name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Добавление новой страны"""
        # Валидация
        is_valid, error = Validators.validate_country_name(name)
        if not is_valid:
            return None, error
        
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO countries (name) VALUES (%s) RETURNING id, name, created_at",
                (name.strip(),)
            )
            new_country_data = cur.fetchone()
            conn.commit()
            
            new_country = Country(
                id=new_country_data['id'],
                name=new_country_data['name'],
                created_at=new_country_data['created_at']
            )
            return new_country.to_dict(), None
        except Exception as e:
            conn.rollback()
            if 'unique constraint' in str(e).lower():
                return None, "Страна уже существует"
            return None, f"Ошибка при добавлении страны: {str(e)}"
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def delete_country(conn, country_id: int) -> Tuple[bool, Optional[str]]:
        """Удаление страны"""
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM countries WHERE id = %s RETURNING id", (country_id,))
            deleted = cur.fetchone()
            conn.commit()
            return deleted is not None, None
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при удалении: {str(e)}"
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def search_countries(conn, search_term: str) -> List[Dict[str, Any]]:
        """Поиск стран по названию"""
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, created_at FROM countries WHERE name ILIKE %s ORDER BY name",
            (f'%{search_term}%',)
        )
        countries_data = cur.fetchall()
        cur.close()
        
        countries = [
            Country(
                id=c['id'],
                name=c['name'],
                created_at=c['created_at']
            ) for c in countries_data
        ]
        
        return [c.to_dict() for c in countries]
    
    # Добавьте этот метод в класс CountryService

@staticmethod
def search_countries(search_term: str) -> List[Dict[str, Any]]:
    """Поиск стран по названию (без декоратора для внешних вызовов)"""
    from database import Database
    
    conn = Database.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, created_at FROM countries WHERE name ILIKE %s ORDER BY name",
            (f'%{search_term}%',)
        )
        countries_data = cur.fetchall()
        cur.close()
        
        countries = [
            Country(
                id=c['id'],
                name=c['name'],
                created_at=c['created_at']
            ) for c in countries_data
        ]
        
        return [c.to_dict() for c in countries]
    finally:
        Database.return_connection(conn)


@staticmethod
def add_country_simple(name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Добавление новой страны (без декоратора для внешних вызовов)"""
    from database import Database
    
    # Валидация
    is_valid, error = Validators.validate_country_name(name)
    if not is_valid:
        return None, error
    
    conn = Database.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id, name, created_at",
            (name.strip(),)
        )
        new_country_data = cur.fetchone()
        conn.commit()
        
        if new_country_data:
            new_country = Country(
                id=new_country_data['id'],
                name=new_country_data['name'],
                created_at=new_country_data['created_at']
            )
            return new_country.to_dict(), None
        else:
            # Пробуем получить существующую
            cur.execute("SELECT id, name, created_at FROM countries WHERE name = %s", (name.strip(),))
            existing = cur.fetchone()
            if existing:
                country = Country(
                    id=existing['id'],
                    name=existing['name'],
                    created_at=existing['created_at']
                )
                return country.to_dict(), None
            return None, "Не удалось добавить страну"
    except Exception as e:
        conn.rollback()
        return None, f"Ошибка при добавлении страны: {str(e)}"
    finally:
        Database.return_connection(conn)