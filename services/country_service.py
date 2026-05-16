from typing import Optional, Tuple, List, Dict, Any
from database import with_db_connection, Database
from models.country import Country
from utils.validators import Validators


class CountryService:
    
    @staticmethod
    @with_db_connection
    def get_all_countries(conn) -> List[Dict[str, Any]]:
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at FROM countries ORDER BY name")
        countries = cur.fetchall()
        cur.close()
        return [Country(c['id'], c['name'], c['created_at']).to_dict() for c in countries]
    
    @staticmethod
    @with_db_connection
    def add_country(conn, name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        is_valid, error = Validators.validate_country_name(name)
        if not is_valid:
            return None, error
        
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO countries (name) VALUES (%s) RETURNING id, name, created_at",
                (name.strip(),)
            )
            new_country = cur.fetchone()
            conn.commit()
            return Country(new_country['id'], new_country['name'], new_country['created_at']).to_dict(), None
        except Exception as e:
            conn.rollback()
            return None, f"Ошибка: {str(e)}"
        finally:
            cur.close()
    
    @staticmethod
    def search_countries(search_term: str) -> List[Dict[str, Any]]:
        conn = Database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM countries WHERE name ILIKE %s", (f'%{search_term}%',))
            countries = cur.fetchall()
            cur.close()
            return [{'id': c['id'], 'name': c['name']} for c in countries]
        finally:
            Database.return_connection(conn)