"""
Сервис для авторегрессионного прогнозирования экономических показателей
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from database import with_db_connection


class ForecastService:
    """Сервис для прогнозирования временных рядов"""
    
    # Доступные модели
    AVAILABLE_MODELS = {
        'auto': 'Автоматический выбор',
        'arima': 'ARIMA (Авторегрессия)',
        'holt_winters': 'Хольта-Винтерса',
        'linear': 'Линейная регрессия',
        'exponential': 'Экспоненциальное сглаживание'
    }
    
    @staticmethod
    def convert_to_serializable(obj):
        """Конвертирует numpy типы в стандартные Python типы"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return obj
    
    @staticmethod
    def convert_to_serializable_dict(obj):
        """Рекурсивно конвертирует словарь с numpy типами в стандартные Python типы"""
        if isinstance(obj, dict):
            return {k: ForecastService.convert_to_serializable_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ForecastService.convert_to_serializable_dict(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        else:
            return obj
    
    @staticmethod
    def check_stationarity(series: List[float]) -> Dict[str, Any]:
        """Проверка ряда на стационарность (тест Дики-Фуллера)"""
        if len(series) < 3:
            return {'is_stationary': False, 'p_value': 1.0, 'is_stationary_after_diff': False}
        
        try:
            result = adfuller(series, autolag='AIC')
            p_value = float(result[1])
            is_stationary = bool(p_value < 0.05)
            
            diff_series = np.diff(series)
            is_stationary_after_diff = False
            if len(diff_series) > 2:
                result_diff = adfuller(diff_series, autolag='AIC')
                p_value_diff = float(result_diff[1])
                is_stationary_after_diff = bool(p_value_diff < 0.05)
            
            return {
                'is_stationary': is_stationary,
                'p_value': p_value,
                'is_stationary_after_diff': is_stationary_after_diff,
                'test_statistic': float(result[0]),
                'critical_values': {k: float(v) for k, v in result[4].items()}
            }
        except Exception as e:
            return {'is_stationary': False, 'p_value': 1.0, 'error': str(e)}
    
    @staticmethod
    def determine_arima_order(series: List[float], max_p: int = 3, max_q: int = 3) -> Tuple[int, int, int]:
        """Определение оптимальных параметров ARIMA (p, d, q) по AIC"""
        if len(series) < 10:
            return (1, 0, 1)
        
        best_aic = np.inf
        best_order = (1, 0, 1)
        
        stationarity = ForecastService.check_stationarity(series)
        d = 1 if not stationarity['is_stationary'] else 0
        
        try:
            for p in range(0, min(max_p, len(series)//2) + 1):
                for q in range(0, min(max_q, len(series)//2) + 1):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
        except:
            pass
        
        return best_order
    
    @staticmethod
    def forecast_arima(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Прогнозирование с помощью ARIMA модели"""
        if len(series) < 4:
            return {'error': 'Недостаточно данных для прогнозирования', 'forecast': []}
        
        try:
            order = ForecastService.determine_arima_order(series)
            model = ARIMA(series, order=order)
            fitted = model.fit()
            
            forecast = fitted.forecast(steps=steps)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            forecast_result = fitted.get_forecast(steps=steps)
            conf_int = forecast_result.conf_int()
            
            fitted_values = fitted.fittedvalues
            min_len = min(len(series), len(fitted_values))
            
            mae = float(mean_absolute_error(series[-min_len:], fitted_values[-min_len:]))
            rmse = float(np.sqrt(mean_squared_error(series[-min_len:], fitted_values[-min_len:])))
            
            return {
                'success': True,
                'model_type': 'ARIMA',
                'order': order,
                'forecast': forecast_values,
                'lower_bounds': [float(x) for x in conf_int[:, 0].tolist()] if len(conf_int) > 0 else [],
                'upper_bounds': [float(x) for x in conf_int[:, 1].tolist()] if len(conf_int) > 0 else [],
                'mae': mae,
                'rmse': rmse,
                'aic': float(fitted.aic),
                'bic': float(fitted.bic)
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def forecast_holt_winters(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Прогнозирование с помощью модели Хольта-Винтерса"""
        if len(series) < 6:
            return {'error': 'Недостаточно данных для прогнозирования', 'forecast': []}
        
        try:
            seasonal_periods = None
            if len(series) >= 12:
                seasonal_periods = 4
            
            if seasonal_periods:
                model = ExponentialSmoothing(
                    series, trend='add', seasonal='add', seasonal_periods=seasonal_periods
                )
            else:
                model = ExponentialSmoothing(series, trend='add', seasonal=None)
            
            fitted = model.fit()
            forecast = fitted.forecast(steps=steps)
            
            fitted_values = fitted.fittedvalues
            min_len = min(len(series), len(fitted_values))
            
            mae = float(mean_absolute_error(series[-min_len:], fitted_values[-min_len:]))
            rmse = float(np.sqrt(mean_squared_error(series[-min_len:], fitted_values[-min_len:])))
            
            result = {
                'success': True,
                'model_type': 'Holt-Winters',
                'forecast': [float(x) for x in forecast.tolist()],
                'mae': mae,
                'rmse': rmse
            }
            
            if hasattr(fitted, 'aic'):
                result['aic'] = float(fitted.aic)
            
            return result
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def forecast_linear(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Прогнозирование с помощью линейной регрессии"""
        if len(series) < 3:
            return {'error': 'Недостаточно данных для прогнозирования', 'forecast': []}
        
        try:
            X = np.arange(len(series)).reshape(-1, 1)
            y = np.array(series)
            
            model = LinearRegression()
            model.fit(X, y)
            
            future_X = np.arange(len(series), len(series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            predictions = model.predict(X)
            mae = float(mean_absolute_error(y, predictions))
            rmse = float(np.sqrt(mean_squared_error(y, predictions)))
            
            residuals = y - predictions
            std_residuals = np.std(residuals)
            lower_bounds = [float(f - 1.96 * std_residuals) for f in forecast_values]
            upper_bounds = [float(f + 1.96 * std_residuals) for f in forecast_values]
            
            return {
                'success': True,
                'model_type': 'Linear Regression',
                'forecast': forecast_values,
                'lower_bounds': lower_bounds,
                'upper_bounds': upper_bounds,
                'mae': mae,
                'rmse': rmse,
                'r2': float(model.score(X, y)),
                'slope': float(model.coef_[0]),
                'intercept': float(model.intercept_)
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def forecast_exponential(series: List[float], steps: int = 5, alpha: float = 0.3) -> Dict[str, Any]:
        """Простое экспоненциальное сглаживание"""
        if len(series) < 3:
            return {'error': 'Недостаточно данных для прогнозирования', 'forecast': []}
        
        try:
            smoothed = [series[0]]
            for i in range(1, len(series)):
                smoothed.append(alpha * series[i] + (1 - alpha) * smoothed[-1])
            
            last_smoothed = smoothed[-1]
            forecast_values = [last_smoothed] * steps
            
            predictions = smoothed
            mae = float(mean_absolute_error(series, predictions))
            rmse = float(np.sqrt(mean_squared_error(series, predictions)))
            
            residuals = np.array(series) - np.array(predictions)
            std_residuals = np.std(residuals)
            lower_bounds = [float(last_smoothed - 1.96 * std_residuals)] * steps
            upper_bounds = [float(last_smoothed + 1.96 * std_residuals)] * steps
            
            return {
                'success': True,
                'model_type': 'Exponential Smoothing',
                'forecast': forecast_values,
                'lower_bounds': lower_bounds,
                'upper_bounds': upper_bounds,
                'mae': mae,
                'rmse': rmse,
                'alpha': alpha
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def find_best_model(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Находит оптимальную модель для прогнозирования (автоматический выбор)"""
        if len(series) < 4:
            return {
                'success': False,
                'error': 'Недостаточно данных (минимум 4 точки)',
                'forecast': []
            }
        
        clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
        
        if len(clean_series) < 4:
            return {
                'success': False,
                'error': 'Недостаточно валидных данных',
                'forecast': []
            }
        
        models = []
        
        arima_result = ForecastService.forecast_arima(clean_series, steps)
        if arima_result.get('success', False):
            models.append(arima_result)
        
        holt_result = ForecastService.forecast_holt_winters(clean_series, steps)
        if holt_result.get('success', False):
            models.append(holt_result)
        
        linear_result = ForecastService.forecast_linear(clean_series, steps)
        if linear_result.get('success', False):
            models.append(linear_result)
        
        exp_result = ForecastService.forecast_exponential(clean_series, steps)
        if exp_result.get('success', False):
            models.append(exp_result)
        
        if not models:
            return {
                'success': False,
                'error': 'Не удалось построить ни одну модель',
                'forecast': []
            }
        
        best_model = min(models, key=lambda x: x.get('rmse', float('inf')))
        
        stationarity = ForecastService.check_stationarity(clean_series)
        
        return {
            'success': True,
            'best_model': best_model['model_type'],
            'models_tested': [m['model_type'] for m in models],
            'forecast': best_model['forecast'],
            'lower_bounds': best_model.get('lower_bounds', []),
            'upper_bounds': best_model.get('upper_bounds', []),
            'metrics': {
                'mae': best_model.get('mae'),
                'rmse': best_model.get('rmse'),
                'aic': best_model.get('aic'),
                'bic': best_model.get('bic'),
                'r2': best_model.get('r2')
            },
            'stationarity': stationarity,
            'data_points': len(clean_series)
        }
    
    @staticmethod
    def forecast_with_model(series: List[float], model_type: str, steps: int = 5) -> Dict[str, Any]:
        """Прогнозирование с выбранной моделью"""
        if model_type == 'arima':
            return ForecastService.forecast_arima(series, steps)
        elif model_type == 'holt_winters':
            return ForecastService.forecast_holt_winters(series, steps)
        elif model_type == 'linear':
            return ForecastService.forecast_linear(series, steps)
        elif model_type == 'exponential':
            return ForecastService.forecast_exponential(series, steps)
        elif model_type == 'auto':
            return ForecastService.find_best_model(series, steps)
        else:
            return {'error': f'Неизвестная модель: {model_type}', 'forecast': []}
    
    @staticmethod
    @with_db_connection
    def get_forecast_for_country(conn, country_id: int, indicator_type: str, 
                                 steps: int = 5, model_type: str = 'auto') -> Dict[str, Any]:
        """
        Получение прогноза для конкретной страны и показателя с выбором модели
        """
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
            
            if len(data) < 4:
                return {
                    'success': False,
                    'error': f'Недостаточно данных для прогнозирования (найдено {len(data)} точек)',
                    'forecast': [],
                    'historical_years': [d['year'] for d in data],
                    'historical_values': [float(d['value']) for d in data] if data else []
                }
            
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            
            historical_values = [float(d['value']) for d in data]
            historical_years = [d['year'] for d in data]
            
            if model_type == 'auto':
                forecast_result = ForecastService.find_best_model(historical_values, steps)
            else:
                forecast_result = ForecastService.forecast_with_model(historical_values, model_type, steps)
                if forecast_result.get('success', False):
                    forecast_result['best_model'] = forecast_result['model_type']
            
            if forecast_result.get('success', False):
                forecast_result['country_id'] = country_id
                forecast_result['country_name'] = country['name'] if country else 'Unknown'
                forecast_result['indicator_type'] = indicator_type
                indicator_names = {
                    'export_value': 'Экспорт',
                    'import_value': 'Импорт',
                    'gdp_value': 'ВВП'
                }
                forecast_result['indicator_name'] = indicator_names.get(indicator_type, indicator_type)
                forecast_result['historical_years'] = historical_years
                forecast_result['historical_values'] = historical_values
                forecast_result['forecast_years'] = [historical_years[-1] + i + 1 for i in range(steps)]
                forecast_result['model_used'] = model_type
            
            return ForecastService.convert_to_serializable_dict(forecast_result)
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'forecast': []
            }
    
    @staticmethod
    @with_db_connection
    def get_all_forecasts_for_country(conn, country_id: int, steps: int = 5, model_type: str = 'auto') -> Dict[str, Any]:
        """
        Получение прогнозов для всех показателей страны
        """
        indicators = ['export_value', 'import_value', 'gdp_value']
        results = {}
        
        for indicator in indicators:
            forecast = ForecastService.get_forecast_for_country(conn, country_id, indicator, steps, model_type)
            indicator_name = indicator.replace('_value', '')
            results[indicator_name] = forecast
        
        return {
            'country_id': country_id,
            'country_name': results.get('export', {}).get('country_name', 'Unknown'),
            'forecasts': results,
            'model_used': model_type,
            'timestamp': pd.Timestamp.now().isoformat()
        }