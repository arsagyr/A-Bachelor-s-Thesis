import pandas as pd
from typing import Dict, Any
from database import with_db_connection
from calculations.auto_regression import auto_regression_forecast


class TrendService:
    
    @staticmethod
    @with_db_connection
    def get_country_trends(conn, country_id: int, steps: int = 5, model_type: str = 'linear') -> Dict[str, Any]:
        """Получение прогнозов экспорта, импорта и ВВП для страны"""
        cur = conn.cursor()
        cur.execute("""
            SELECT year, export_value, import_value, gdp_value
            FROM indicators 
            WHERE country_id = %s 
              AND export_value IS NOT NULL 
              AND import_value IS NOT NULL 
              AND gdp_value IS NOT NULL
            ORDER BY year
        """, (country_id,))
        data = cur.fetchall()
        cur.close()
        
        if len(data) < 4:
            return {'success': False, 'error': f'Недостаточно данных: {len(data)} точек'}
        
        cur = conn.cursor()
        cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
        country = cur.fetchone()
        cur.close()
        
        df = pd.DataFrame(data)
        df.columns = ['year', 'export', 'import', 'gdp']
        
        historical_years = df['year'].tolist()
        historical_export = df['export'].tolist()
        historical_import = df['import'].tolist()
        historical_gdp = df['gdp'].tolist()
        last_year = historical_years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]
        
        # Прогноз экспорта
        export_result = auto_regression_forecast(historical_export, steps, model_type)
        
        # Прогноз импорта
        import_result = auto_regression_forecast(historical_import, steps, model_type)
        
        # Прогноз ВВП
        gdp_result = auto_regression_forecast(historical_gdp, steps, model_type)
        
        return {
            'success': True,
            'country_name': country['name'],
            'historical': {
                'years': historical_years,
                'export': historical_export,
                'import': historical_import,
                'gdp': historical_gdp
            },
            'forecast_years': forecast_years,
            'export': {
                'name': 'Прогноз экспорта',
                'forecast': export_result.get('forecast', []),
                'metrics': export_result.get('metrics', {}),
                'formula': export_result.get('formula', ''),
                'success': export_result.get('success', False)
            },
            'import': {
                'name': 'Прогноз импорта',
                'forecast': import_result.get('forecast', []),
                'metrics': import_result.get('metrics', {}),
                'formula': import_result.get('formula', ''),
                'success': import_result.get('success', False)
            },
            'gdp': {
                'name': 'Прогноз ВВП',
                'forecast': gdp_result.get('forecast', []),
                'metrics': gdp_result.get('metrics', {}),
                'formula': gdp_result.get('formula', ''),
                'success': gdp_result.get('success', False)
            }
        }