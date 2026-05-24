from typing import Dict, Any
from database import with_db_connection
from calculations.auto_regression import auto_regression_forecast


class ForecastService:
    
    @staticmethod
    @with_db_connection
    def get_forecast(conn, country_id: int, indicator: str, steps: int = 5, 
                     model_type: str = 'auto', degree: int = 2) -> Dict[str, Any]:
        """Получение прогноза для страны (значения в млрд USD)"""
        cur = None
        try:
            cur = conn.cursor()
            query = f"""
                SELECT year, {indicator} as value
                FROM indicators 
                WHERE country_id = %s AND {indicator} IS NOT NULL
                ORDER BY year
            """
            cur.execute(query, (country_id,))
            data = cur.fetchall()
            cur.close()
            cur = None
            
            if len(data) < 3:
                return {
                    'success': False,
                    'error': f'Недостаточно данных: {len(data)} точек',
                    'forecast': []
                }
            
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            cur = None
            
            historical_values = []
            historical_years = []
            for d in data:
                if d['value'] is not None:
                    try:
                        val = float(d['value'])
                        historical_values.append(val)
                        historical_years.append(int(d['year']))
                    except (ValueError, TypeError) as e:
                        print(f"Ошибка преобразования: {e}")
                        continue
            
            if len(historical_values) < 3:
                return {
                    'success': False,
                    'error': f'Недостаточно валидных данных: {len(historical_values)} точек',
                    'forecast': []
                }
            
            result = auto_regression_forecast(historical_values, steps, model_type, degree=degree)
            
            if result.get('success'):
                last_year = historical_years[-1]
                forecast_years = [last_year + i + 1 for i in range(steps)]
                
                indicator_names = {
                    'export_value': 'Экспорт',
                    'import_value': 'Импорт',
                    'gdp_value': 'ВВП'
                }
                
                return {
                    'success': True,
                    'country_name': country['name'] if country else 'Unknown',
                    'indicator_name': indicator_names.get(indicator, indicator),
                    'historical_years': historical_years,
                    'historical_values': historical_values,
                    'forecast_years': forecast_years,
                    'forecast': result['forecast'],
                    'model_type': result.get('model_type', model_type),
                    'metrics': {
                        'r2': result.get('r2', 0),
                        'rmse': result.get('rmse', 0),
                        'mae': result.get('mae', 0),
                        'mape': result.get('mape', 0)
                    },
                    'formula': result.get('formula', ''),
                    'unit': 'млрд USD'
                }
            
            return {'success': False, 'error': result.get('error', 'Ошибка прогнозирования')}
            
        except Exception as e:
            print(f"Исключение: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'forecast': []}
        finally:
            if cur:
                cur.close()