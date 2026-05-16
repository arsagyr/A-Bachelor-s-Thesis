from typing import Optional, List, Dict, Any, Tuple
from database import with_db_connection
from models.indicator import Indicator
from models.stats import CountryStats
from utils.validators import Validators


class IndicatorService:
    """Сервис для работы с экономическими показателями"""
    
    @staticmethod
    @with_db_connection
    def get_indicators_by_country(conn, country_id: int) -> List[Dict[str, Any]]:
        """Получение показателей по стране"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, country_id, year, export_value, import_value, gdp_value, updated_at
            FROM indicators 
            WHERE country_id = %s 
            ORDER BY year
        """, (country_id,))
        indicators_data = cur.fetchall()
        cur.close()
        
        indicators = [
            Indicator(
                id=i['id'],
                country_id=i['country_id'],
                year=i['year'],
                export_value=i['export_value'],
                import_value=i['import_value'],
                gdp_value=i['gdp_value'],
                updated_at=i['updated_at']
            ) for i in indicators_data
        ]
        
        return [i.to_dict() for i in indicators]
    
    @staticmethod
    @with_db_connection
    def filter_indicators(conn, 
                         country_id: Optional[int] = None, 
                         start_year: Optional[int] = None,
                         end_year: Optional[int] = None,
                         indicator_type: str = 'all') -> List[Dict[str, Any]]:
        """Фильтрация показателей"""
        query = """
            SELECT i.id, i.year, i.export_value, i.import_value, i.gdp_value, 
                   i.updated_at, c.id as country_id, c.name as country_name
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
        cur.execute(query, params)
        data = cur.fetchall()
        cur.close()
        
        # Фильтрация по типу показателя
        result = []
        for row in data:
            item = {
                'id': row['id'],
                'country_id': row['country_id'],
                'country_name': row['country_name'],
                'year': row['year'],
                'export_value': float(row['export_value']) if row['export_value'] else None,
                'import_value': float(row['import_value']) if row['import_value'] else None,
                'gdp_value': float(row['gdp_value']) if row['gdp_value'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            }
            
            if indicator_type != 'all':
                if indicator_type == 'export':
                    item['import_value'] = None
                    item['gdp_value'] = None
                elif indicator_type == 'import':
                    item['export_value'] = None
                    item['gdp_value'] = None
                elif indicator_type == 'gdp':
                    item['export_value'] = None
                    item['import_value'] = None
            
            result.append(item)
        
        return result
    
    @staticmethod
    @with_db_connection
    def get_country_stats(conn, country_id: int) -> Optional[Dict[str, Any]]:
        """Получение статистики по стране"""
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as years_count,
                MIN(year) as min_year,
                MAX(year) as max_year,
                AVG(export_value) as avg_export,
                AVG(import_value) as avg_import,
                AVG(gdp_value) as avg_gdp,
                MAX(export_value) as max_export,
                MAX(import_value) as max_import,
                MAX(gdp_value) as max_gdp,
                MIN(export_value) as min_export,
                MIN(import_value) as min_import,
                MIN(gdp_value) as min_gdp
            FROM indicators 
            WHERE country_id = %s
        """, (country_id,))
        stats_data = cur.fetchone()
        
        # Получаем имя страны
        cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
        country = cur.fetchone()
        cur.close()
        
        if stats_data and country:
            stats = CountryStats(
                country_id=country_id,
                country_name=country['name'],
                years_count=stats_data['years_count'] or 0,
                min_year=stats_data['min_year'],
                max_year=stats_data['max_year'],
                avg_export=float(stats_data['avg_export']) if stats_data['avg_export'] else None,
                avg_import=float(stats_data['avg_import']) if stats_data['avg_import'] else None,
                avg_gdp=float(stats_data['avg_gdp']) if stats_data['avg_gdp'] else None,
                max_export=float(stats_data['max_export']) if stats_data['max_export'] else None,
                max_import=float(stats_data['max_import']) if stats_data['max_import'] else None,
                max_gdp=float(stats_data['max_gdp']) if stats_data['max_gdp'] else None,
                min_export=float(stats_data['min_export']) if stats_data['min_export'] else None,
                min_import=float(stats_data['min_import']) if stats_data['min_import'] else None,
                min_gdp=float(stats_data['min_gdp']) if stats_data['min_gdp'] else None
            )
            return stats.to_dict()
        
        return None
    
    @staticmethod
    @with_db_connection
    def add_or_update_indicator(conn, 
                               country_id: int, 
                               year: int,
                               export_value: Optional[float] = None,
                               import_value: Optional[float] = None,
                               gdp_value: Optional[float] = None) -> Tuple[bool, str]:
        """Добавление или обновление показателя"""
        # Валидация
        is_valid, error = Validators.validate_indicator_data(
            country_id, year, export_value, import_value, gdp_value
        )
        if not is_valid:
            return False, error
        
        cur = conn.cursor()
        try:
            # Проверка существования страны
            cur.execute("SELECT id FROM countries WHERE id = %s", (country_id,))
            if not cur.fetchone():
                return False, "Страна не найдена"
            
            cur.execute("""
                INSERT INTO indicators (country_id, year, export_value, import_value, gdp_value, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (country_id, year) DO UPDATE SET
                    export_value = EXCLUDED.export_value,
                    import_value = EXCLUDED.import_value,
                    gdp_value = EXCLUDED.gdp_value,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (country_id, year, export_value, import_value, gdp_value))
            
            conn.commit()
            return True, "Показатель успешно сохранен"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при сохранении: {str(e)}"
        finally:
            cur.close()
    
    @staticmethod
    @with_db_connection
    def get_available_years(conn) -> List[int]:
        """Получение списка доступных годов"""
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT year FROM indicators ORDER BY year")
        years = [row['year'] for row in cur.fetchall()]
        cur.close()
        return years
    
    @staticmethod
    @with_db_connection
    def delete_indicator(conn, indicator_id: int) -> Tuple[bool, str]:
        """Удаление показателя"""
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
            return False, f"Ошибка при удалении: {str(e)}"
        finally:
            cur.close()