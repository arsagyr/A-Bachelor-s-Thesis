"""
Сервис для прогнозирования временных рядов
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from database import with_db_connection


class ForecastService:
    """Сервис для прогнозирования экономических показателей"""
    
    AVAILABLE_MODELS = {
        'auto': 'Автоматический выбор',
        'linear': 'Линейная регрессия',
        'ridge': 'Ridge регрессия',
        'lasso': 'Lasso регрессия',
        'polynomial': 'Полиномиальная регрессия'
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
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < 3:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
            
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            
            model = LinearRegression()
            model.fit(X, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
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
    def forecast_ridge(series: List[float], steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
        """Прогнозирование с помощью Ridge регрессии"""
        if len(series) < 3:
            return {'error': 'Недостаточно данных (минимум 3 точки)', 'forecast': []}
        
        try:
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < 3:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
            
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            
            model = Ridge(alpha=alpha)
            model.fit(X, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            
            return {
                'success': True,
                'model_type': 'Ridge Regression',
                'forecast': forecast_values,
                'rmse': float(rmse),
                'mae': float(mae),
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0]),
                'alpha': alpha
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def forecast_lasso(series: List[float], steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
        """Прогнозирование с помощью Lasso регрессии"""
        if len(series) < 3:
            return {'error': 'Недостаточно данных (минимум 3 точки)', 'forecast': []}
        
        try:
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < 3:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
            
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            
            model = Lasso(alpha=alpha)
            model.fit(X, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            
            return {
                'success': True,
                'model_type': 'Lasso Regression',
                'forecast': forecast_values,
                'rmse': float(rmse),
                'mae': float(mae),
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0]),
                'alpha': alpha
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def forecast_polynomial(series: List[float], steps: int = 5, degree: int = 2) -> Dict[str, Any]:
        """Прогнозирование с помощью полиномиальной регрессии"""
        if len(series) < 4:
            return {'error': 'Недостаточно данных (минимум 4 точки)', 'forecast': []}
        
        try:
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < 4:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
            
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            
            poly = PolynomialFeatures(degree=degree)
            X_poly = poly.fit_transform(X)
            
            model = LinearRegression()
            model.fit(X_poly, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            future_X_poly = poly.transform(future_X)
            forecast = model.predict(future_X_poly)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X_poly)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            
            return {
                'success': True,
                'model_type': f'Polynomial Regression (degree {degree})',
                'forecast': forecast_values,
                'rmse': float(rmse),
                'mae': float(mae),
                'intercept': float(model.intercept_),
                'degree': degree
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def find_best_model(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Находит лучшую модель для прогнозирования"""
        if len(series) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(series)} точек', 'forecast': []}
        
        clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
        if len(clean_series) < 3:
            return {'success': False, 'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
        
        models = []
        
        # Линейная регрессия
        linear_result = ForecastService.forecast_linear(clean_series, steps)
        if linear_result.get('success'):
            models.append(('linear', linear_result))
        
        # Ridge регрессия
        ridge_result = ForecastService.forecast_ridge(clean_series, steps)
        if ridge_result.get('success'):
            models.append(('ridge', ridge_result))
        
        # Lasso регрессия
        lasso_result = ForecastService.forecast_lasso(clean_series, steps)
        if lasso_result.get('success'):
            models.append(('lasso', lasso_result))
        
        # Полиномиальная регрессия
        poly_result = ForecastService.forecast_polynomial(clean_series, steps)
        if poly_result.get('success'):
            models.append(('polynomial', poly_result))
        
        if not models:
            return {'success': False, 'error': 'Не удалось построить ни одну модель', 'forecast': []}
        
        # Выбираем модель с наименьшей RMSE
        best_model_name, best_model = min(models, key=lambda x: x[1].get('rmse', float('inf')))
        
        return {
            'success': True,
            'best_model': best_model['model_type'],
            'forecast': best_model['forecast'],
            'metrics': {
                'rmse': best_model['rmse'],
                'mae': best_model['mae']
            }
        }
    
    @staticmethod
    def forecast_with_model(series: List[float], steps: int = 5, model_type: str = 'linear') -> Dict[str, Any]:
        """Прогнозирование с выбранной моделью"""
        clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
        
        if model_type == 'linear':
            return ForecastService.forecast_linear(clean_series, steps)
        elif model_type == 'ridge':
            return ForecastService.forecast_ridge(clean_series, steps)
        elif model_type == 'lasso':
            return ForecastService.forecast_lasso(clean_series, steps)
        elif model_type == 'polynomial':
            return ForecastService.forecast_polynomial(clean_series, steps)
        elif model_type == 'auto':
            return ForecastService.find_best_model(clean_series, steps)
        else:
            return ForecastService.forecast_linear(clean_series, steps)
    
    @staticmethod
    @with_db_connection
    def get_forecast_for_country(conn, country_id: int, indicator_type: str, 
                                 steps: int = 5, model_type: str = 'auto') -> Dict[str, Any]:
        """Получение прогноза для страны и показателя"""
        cur = None
        try:
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
            
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            cur = None
            
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
            
            forecast_result = ForecastService.forecast_with_model(historical_values, steps, model_type)
            
            if forecast_result.get('success'):
                last_year = historical_years[-1]
                forecast_years = [last_year + i + 1 for i in range(steps)]
                
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
                    'model_type': forecast_result.get('model_type', model_type),
                    'metrics': forecast_result.get('metrics', {})
                }
                
                # Добавляем дополнительные параметры модели
                if 'intercept' in forecast_result:
                    result['intercept'] = forecast_result['intercept']
                if 'slope' in forecast_result:
                    result['slope'] = forecast_result['slope']
                if 'degree' in forecast_result:
                    result['degree'] = forecast_result['degree']
                if 'alpha' in forecast_result:
                    result['alpha'] = forecast_result['alpha']
                
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