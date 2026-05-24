"""
Сервис для прогнозирования (API слой)
"""

import numpy as np
from typing import Dict, Any
from database import with_db_connection
from calculations.auto_regression import auto_regression_forecast, compare_auto_regression_models


class ForecastService:
    """Сервис для прогнозирования"""
    
    AVAILABLE_MODELS = {
        'auto': 'Автоматический выбор',
        'linear': 'Линейная регрессия',
        'polynomial': 'Полиномиальная регрессия',
        'exponential': 'Экспоненциальная регрессия',
        'ridge': 'Ridge регрессия',
        'lasso': 'Lasso регрессия'
    }
    
    @staticmethod
    @with_db_connection
    def get_forecast(conn, country_id: int, indicator: str, steps: int = 5, 
                     model_type: str = 'auto', degree: int = 2, alpha: float = 1.0) -> Dict[str, Any]:
        """Получение прогноза для страны с выбором модели"""
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
            
            # Вызов расчётов с выбором модели
            if model_type == 'auto':
                result = compare_auto_regression_models(historical_values, steps)
                best_model_name = result.get('best_model')
                if best_model_name and best_model_name in result.get('all_models', {}):
                    best_result = result['all_models'][best_model_name]
                    result.update(best_result)
                    result['model_type'] = best_model_name
                    result['model_name'] = best_result.get('model_name', best_model_name)
                    result['best_model'] = best_model_name
                    result['best_model_name'] = result.get('best_model_name', best_model_name)
                    result['best_r2'] = result.get('best_r2', 0)
            else:
                result = auto_regression_forecast(historical_values, steps, model_type, degree=degree, alpha=alpha)
            
            if result.get('success'):
                last_year = historical_years[-1]
                forecast_years = [last_year + i + 1 for i in range(steps)]
                
                indicator_names = {
                    'export_value': 'Экспорт',
                    'import_value': 'Импорт',
                    'gdp_value': 'ВВП'
                }
                
                # Получаем метрики - ОБЯЗАТЕЛЬНО извлекаем r2, rmse, mae
                metrics = result.get('metrics', {})
                r2 = metrics.get('r2', result.get('r2', 0))
                rmse = metrics.get('rmse', result.get('rmse', 0))
                mae = metrics.get('mae', result.get('mae', 0))
                mape = metrics.get('mape', result.get('mape', 0))
                
                slope = result.get('slope')
                intercept = result.get('intercept')
                coefficients = result.get('coefficients')
                actual_model_type = result.get('model_type', model_type)
                
                response = {
                    'success': True,
                    'country_name': country['name'] if country else 'Unknown',
                    'indicator_name': indicator_names.get(indicator, indicator),
                    'historical_years': historical_years,
                    'historical_values': historical_values,
                    'forecast_years': forecast_years,
                    'forecast': result.get('forecast', []),
                    'model_type': actual_model_type,
                    'model_name': result.get('model_name', ForecastService.AVAILABLE_MODELS.get(model_type, model_type)),
                    'metrics': {
                        'r2': float(r2),
                        'rmse': float(rmse),
                        'mae': float(mae),
                        'mape': float(mape)
                    },
                    'formula': result.get('formula', ''),
                    'unit': 'млрд USD',
                    'r2': float(r2),
                    'rmse': float(rmse),
                    'mae': float(mae),
                    'slope': slope,
                    'intercept': intercept,
                    'coefficients': coefficients,
                    'degree': result.get('degree', degree)
                }
                
                # Добавляем предсказания модели
                n = len(historical_values)
                total_points = n + steps
                model_predictions = []
                
                for i in range(total_points):
                    x = i + 1
                    pred = 0
                    
                    if actual_model_type == 'linear' and slope is not None and intercept is not None:
                        pred = intercept + slope * x
                    elif actual_model_type == 'polynomial' and coefficients:
                        pred = intercept if intercept else 0
                        for power, coeff in enumerate(coefficients, 1):
                            pred += coeff * (x ** power)
                    elif actual_model_type == 'exponential' and slope is not None and intercept is not None:
                        pred = np.exp(intercept + slope * x)
                    elif actual_model_type in ['ridge', 'lasso'] and slope is not None:
                        pred = intercept + slope * x if intercept else slope * x
                    else:
                        if i < n:
                            pred = historical_values[i]
                        else:
                            forecast_list = result.get('forecast', [])
                            pred = forecast_list[i - n] if i - n < len(forecast_list) else 0
                    
                    model_predictions.append(pred)
                
                response['model_predictions'] = model_predictions
                
                if model_type == 'auto' and 'all_models' in result:
                    response['all_models'] = result['all_models']
                    response['best_model'] = result.get('best_model')
                    response['best_model_name'] = result.get('best_model_name')
                    response['best_r2'] = result.get('best_r2')
                
                return response
            
            return {'success': False, 'error': result.get('error', 'Ошибка прогнозирования')}
            
        except Exception as e:
            print(f"Исключение: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'forecast': []}
        finally:
            if cur:
                cur.close()