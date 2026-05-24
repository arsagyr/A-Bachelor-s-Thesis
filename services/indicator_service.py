from typing import Optional, List, Dict, Any, Tuple
from database import with_db_connection


class IndicatorService:
    
    @staticmethod
    @with_db_connection
    def filter_indicators(conn, country_id: Optional[int] = None,
                         start_year: Optional[int] = None,
                         end_year: Optional[int] = None,
                         indicator_type: str = 'all') -> List[Dict[str, Any]]:
        query = """
            SELECT i.id, i.year, i.export_value, i.import_value, i.gdp_value, c.name as country_name
            FROM indicators i
            JOIN countries c ON i.country_id = c.id
            WHERE 1=1
        """
        params = []
        
        if country_id:
            query += " AND i.country_id = %s"
            params.append(country_id)
        if start_year:
            query += " AND i.year >= %s"
            params.append(start_year)
        if end_year:
            query += " AND i.year <= %s"
            params.append(end_year)
        
        query += " ORDER BY i.year"
        
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            data = cur.fetchall()
            return [dict(row) for row in data]
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def get_country_stats(conn, country_id: int) -> Optional[Dict[str, Any]]:
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT 
                    COUNT(*) as years_count,
                    MIN(year) as min_year,
                    MAX(year) as max_year,
                    AVG(export_value) as avg_export,
                    AVG(import_value) as avg_import,
                    AVG(gdp_value) as avg_gdp
                FROM indicators WHERE country_id = %s
            """, (country_id,))
            stats = cur.fetchone()
            return dict(stats) if stats else None
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def get_available_years(conn) -> List[int]:
        cur = conn.cursor()
        try:
            cur.execute("SELECT DISTINCT year FROM indicators ORDER BY year")
            return [row['year'] for row in cur.fetchall()]
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def delete_indicator(conn, indicator_id: int) -> Tuple[bool, str]:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM indicators WHERE id = %s RETURNING id", (indicator_id,))
            deleted = cur.fetchone()
            conn.commit()
            if deleted:
                return True, "Показатель успешно удален"
            return False, "Показатель не найден"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {str(e)}"
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def delete_indicators_by_country(conn, country_id: int) -> Tuple[bool, str]:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM indicators WHERE country_id = %s", (country_id,))
            deleted_count = cur.rowcount
            conn.commit()
            return True, f"Удалено {deleted_count} показателей"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {str(e)}"
        finally:
            cur.close()