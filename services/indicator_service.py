from typing import Optional, List, Dict, Any, Tuple
from database import with_db_connection
from models.indicator import Indicator


class IndicatorService:
    
    @staticmethod
    @with_db_connection
    def filter_indicators(conn, country_id: Optional[int] = None,
                         start_year: Optional[int] = None,
                         end_year: Optional[int] = None,
                         indicator_type: str = 'all') -> List[Dict[str, Any]]:
        query = """
            SELECT i.year, i.export_value, i.import_value, i.gdp_value, c.name as country_name
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
        finally:
            cur.close()
        
        result = []
        for row in data:
            item = {
                'country_name': row['country_name'],
                'year': row['year'],
                'export_value': float(row['export_value']) if row['export_value'] else None,
                'import_value': float(row['import_value']) if row['import_value'] else None,
                'gdp_value': float(row['gdp_value']) if row['gdp_value'] else None
            }
            if indicator_type != 'all':
                if indicator_type == 'export':
                    item['import_value'] = item['gdp_value'] = None
                elif indicator_type == 'import':
                    item['export_value'] = item['gdp_value'] = None
                elif indicator_type == 'gdp':
                    item['export_value'] = item['import_value'] = None
            result.append(item)
        
        return result
    
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
        finally:
            cur.close()
        
        if stats and stats['years_count'] > 0:
            return {
                'years_count': stats['years_count'],
                'min_year': stats['min_year'],
                'max_year': stats['max_year'],
                'avg_export': float(stats['avg_export']) if stats['avg_export'] else None,
                'avg_import': float(stats['avg_import']) if stats['avg_import'] else None,
                'avg_gdp': float(stats['avg_gdp']) if stats['avg_gdp'] else None
            }
        return None
    
    @staticmethod
    @with_db_connection
    def add_or_update_indicator(conn, country_id: int, year: int,
                               export_value: Optional[float] = None,
                               import_value: Optional[float] = None,
                               gdp_value: Optional[float] = None) -> Tuple[bool, str]:
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO indicators (country_id, year, export_value, import_value, gdp_value)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (country_id, year) DO UPDATE SET
                    export_value = EXCLUDED.export_value,
                    import_value = EXCLUDED.import_value,
                    gdp_value = EXCLUDED.gdp_value
            """, (country_id, year, export_value, import_value, gdp_value))
            conn.commit()
            return True, "Успешно сохранено"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()