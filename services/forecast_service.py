"""
Сервис для прогнозирования (API слой)
"""

from typing import Dict, Any
from database import with_db_connection
from calculations.auto_regression import (
    auto_regression_forecast,
    auto_regression_with_confidence,
    compare_auto_regression_models
)
from calculations.regression import compare_all_models, forecast_gdp
from calculations.preprocessing import convert_data_to_float, prepare_regression_features
import numpy as np


class ForecastService:
    """Сервис для прогнозирования (преобразует результаты calculations в JSON)"""
    
    @staticmethod
    def _clean_forecast_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """Удаляет несериализуемые объекты из результата прогноза"""
        if isinstance(result, dict):
            # Удаляем объекты моделей
            for key in ['model', 'scaler', 'poly']:
                if key in result:
                    del result[key]
            
            # Рекурсивно очищаем вложенные словари
            for key, value in result.items():
                if isinstance(value, dict):
                    ForecastService._clean_forecast_result(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            ForecastService._clean_forecast_result(item)
        return result
    
    @staticmethod
    @with_db_connection
    def get_auto_regression_forecast(conn, country_id: int, indicator: str, 
                                      steps: int = 5, model_type: str = 'linear',
                                      degree: int = 2, show_confidence: bool = False) -> Dict[str, Any]:
        """
        Получение авторегрессионного прогноза
        """
        # Получаем данные
        data = conn.cursor()
        data.execute(f"""
            SELECT year, {indicator}_value as value
            FROM indicators 
            WHERE country_id = %s AND {indicator}_value IS NOT NULL
            ORDER BY year
        """, (country_id,))
        rows = data.fetchall()
        data.close()
        
        if len(rows) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(rows)} точек'}
        
        # Получаем название страны
        cur = conn.cursor()
        cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
        country = cur.fetchone()
        cur.close()
        
        # Извлекаем временной ряд
        series = [float(row['value']) for row in rows]
        years = [row['year'] for row in rows]
        
        # Выполняем прогноз через calculations
        if model_type == 'compare':
            result = compare_auto_regression_models(series, steps)
        elif show_confidence:
            result = auto_regression_with_confidence(series, steps, model_type, confidence_level=0.95, degree=degree)
        else:
            result = auto_regression_forecast(series, steps, model_type, degree=degree)
        
        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Ошибка прогнозирования')}
        
        # Очищаем результат от несериализуемых объектов
        result = ForecastService._clean_forecast_result(result)
        
        # Добавляем метаинформацию
        result['country_id'] = country_id
        result['country_name'] = country['name']
        result['indicator'] = indicator
        result['indicator_name'] = {'export': 'Экспорт', 'import': 'Импорт', 'gdp': 'ВВП'}.get(indicator, indicator)
        result['years'] = years
        result['historical'] = series
        result['forecast_years'] = [years[-1] + i + 1 for i in range(steps)]
        result['success'] = True
        
        return result