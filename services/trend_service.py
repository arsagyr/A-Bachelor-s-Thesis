"""
Сервис для трендового анализа (API слой)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any
from database import with_db_connection
from calculations.auto_regression import auto_regression_forecast


class TrendService:
    """Сервис для трендового анализа"""
    
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
        
        # Добавляем модельные предсказания для графиков
        n = len(historical_years)
        total_points = n + steps
        
        def add_model_predictions(result, hist_values):
            if not result.get('success'):
                return result
            slope = result.get('slope')
            intercept = result.get('intercept')
            coefficients = result.get('coefficients')
            model_type_actual = result.get('model_type', model_type)
            
            predictions = []
            for i in range(total_points):
                x = i + 1
                pred = 0
                if model_type_actual == 'linear' and slope is not None and intercept is not None:
                    pred = intercept + slope * x
                elif model_type_actual == 'polynomial' and coefficients:
                    pred = intercept if intercept else 0
                    for power, coeff in enumerate(coefficients, 1):
                        pred += coeff * (x ** power)
                elif model_type_actual == 'exponential' and slope is not None and intercept is not None:
                    pred = np.exp(intercept + slope * x)
                elif model_type_actual in ['ridge', 'lasso'] and slope is not None:
                    pred = intercept + slope * x if intercept else slope * x
                else:
                    if i < n:
                        pred = hist_values[i]
                    else:
                        forecast_list = result.get('forecast', [])
                        pred = forecast_list[i - n] if i - n < len(forecast_list) else 0
                predictions.append(pred)
            
            result['model_predictions'] = predictions
            return result
        
        export_result = add_model_predictions(export_result, historical_export)
        import_result = add_model_predictions(import_result, historical_import)
        gdp_result = add_model_predictions(gdp_result, historical_gdp)
        
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
                'slope': export_result.get('slope'),
                'intercept': export_result.get('intercept'),
                'coefficients': export_result.get('coefficients'),
                'model_predictions': export_result.get('model_predictions', []),
                'success': export_result.get('success', False)
            },
            'import': {
                'name': 'Прогноз импорта',
                'forecast': import_result.get('forecast', []),
                'metrics': import_result.get('metrics', {}),
                'formula': import_result.get('formula', ''),
                'slope': import_result.get('slope'),
                'intercept': import_result.get('intercept'),
                'coefficients': import_result.get('coefficients'),
                'model_predictions': import_result.get('model_predictions', []),
                'success': import_result.get('success', False)
            },
            'gdp': {
                'name': 'Прогноз ВВП',
                'forecast': gdp_result.get('forecast', []),
                'metrics': gdp_result.get('metrics', {}),
                'formula': gdp_result.get('formula', ''),
                'slope': gdp_result.get('slope'),
                'intercept': gdp_result.get('intercept'),
                'coefficients': gdp_result.get('coefficients'),
                'model_predictions': gdp_result.get('model_predictions', []),
                'success': gdp_result.get('success', False)
            }
        }