"""
Сервис для прогнозирования временных рядов (упрощенная версия)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from database import with_db_connection


class ForecastService:
    """Сервис для прогнозирования экономических показателей"""
    
    AVAILABLE_MODELS = {
        'auto': 'Автоматический выбор',
        'linear': 'Линейная регрессия'
    }
    
    @staticmethod
    def convert_to_serializable(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    @staticmethod
    def convert_to_serializable_dict(obj):
        if isinstance(obj, dict):
            return {k: ForecastService.convert_to_serializable_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ForecastService.convert_to_serializable_dict(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    @staticmethod
    def forecast_linear(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Прогнозирование с помощью линейной регрессии"""
        if len(series) < 3:
            return {'error': 'Недостаточно данных (минимум 3 точки)', 'forecast': []}
        
        try:
            # Очищаем данные
            clean_series = []
            for x in series:
                if x is not None and not np.isnan(x):
                    clean_series.append(float(x))
            
            if len(clean_series) < 3:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
            
            # Создаем признаки (годы)
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            
            # Обучаем модель
            model = LinearRegression()
            model.fit(X, y)
            
            # Прогноз
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            # Оценка качества
            y_pred = model.predict(X)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            
            return {
                'success': True,
                'model_type': 'Linear Regression',
                'forecast': forecast_values,
                'rmse': float(rmse),
                'mae': float(mae),
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0])
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def find_best_model(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Находит лучшую модель для прогнозирования"""
        if len(series) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(series)} точек', 'forecast': []}
        
        # Очищаем данные
        clean_series = []
        for x in series:
            if x is not None and not np.isnan(x):
                clean_series.append(float(x))
        
        if len(clean_series) < 3:
            return {'success': False, 'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
        
        # Используем линейную регрессию
        result = ForecastService.forecast_linear(clean_series, steps)
        
        if result.get('success'):
            return {
                'success': True,
                'best_model': result['model_type'],
                'forecast': result['forecast'],
                'metrics': {
                    'rmse': result['rmse'],
                    'mae': result['mae']
                }
            }
        
        return {'success': False, 'error': result.get('error', 'Не удалось построить модель'), 'forecast': []}
    
    @staticmethod
    @with_db_connection
    def get_forecast_for_country(conn, country_id: int, indicator_type: str, 
                                 steps: int = 5, model_type: str = 'auto') -> Dict[str, Any]:
        """Получение прогноза для страны и показателя"""
        cur = None
        try:
            # Получаем данные
            cur = conn.cursor()
            query = f"""
                SELECT year, {indicator_type} as value
                FROM indicators 
                WHERE country_id = %s AND {indicator_type} IS NOT NULL
                ORDER BY year
            """
            cur.execute(query, (country_id,))
            data = cur.fetchall()
            cur.close()
            cur = None
            
            if len(data) < 3:
                return {
                    'success': False,
                    'error': f'Недостаточно данных: {len(data)} точек (нужно минимум 3)',
                    'forecast': []
                }
            
            # Получаем название страны
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            cur = None
            
            # Подготавливаем данные
            historical_values = []
            historical_years = []
            for d in data:
                if d['value'] is not None:
                    historical_values.append(float(d['value']))
                    historical_years.append(int(d['year']))
            
            if len(historical_values) < 3:
                return {
                    'success': False,
                    'error': f'Недостаточно валидных данных: {len(historical_values)} точек',
                    'forecast': []
                }
            
            # Получаем прогноз
            forecast_result = ForecastService.find_best_model(historical_values, steps)
            
            if forecast_result.get('success'):
                last_year = historical_years[-1]
                forecast_years = [last_year + i + 1 for i in range(steps)]
                
                # Определяем название показателя
                indicator_names = {
                    'export_value': 'Экспорт',
                    'import_value': 'Импорт',
                    'gdp_value': 'ВВП'
                }
                
                result = {
                    'success': True,
                    'country_id': country_id,
                    'country_name': country['name'] if country else 'Unknown',
                    'indicator_type': indicator_type,
                    'indicator_name': indicator_names.get(indicator_type, indicator_type),
                    'historical_years': historical_years,
                    'historical_values': historical_values,
                    'forecast_years': forecast_years,
                    'forecast': forecast_result['forecast'],
                    'best_model': forecast_result['best_model'],
                    'metrics': forecast_result['metrics']
                }
                return ForecastService.convert_to_serializable_dict(result)
            else:
                return {
                    'success': False,
                    'error': forecast_result.get('error', 'Ошибка прогнозирования'),
                    'forecast': []
                }
            
        except Exception as e:
            print(f"Error in get_forecast_for_country: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'forecast': []}
        finally:
            if cur:
                cur.close()