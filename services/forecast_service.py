"""
Сервис для прогнозирования временных рядов
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
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
    def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Расчет метрик качества модели"""
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if np.all(y_true != 0) else 100
        
        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape)
        }
    
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
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t"
            
            return {
                'success': True,
                'model_type': 'Linear Regression',
                'forecast': forecast_values,
                'metrics': metrics,
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0]),
                'formula': formula
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
            
            # Стандартизация для Ridge
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = Ridge(alpha=alpha)
            model.fit(X_scaled, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            future_X_scaled = scaler.transform(future_X)
            forecast = model.predict(future_X_scaled)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X_scaled)
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t (Ridge)"
            
            return {
                'success': True,
                'model_type': 'Ridge Regression',
                'forecast': forecast_values,
                'metrics': metrics,
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0]),
                'alpha': alpha,
                'formula': formula
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
            
            # Стандартизация для Lasso
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = Lasso(alpha=alpha)
            model.fit(X_scaled, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            future_X_scaled = scaler.transform(future_X)
            forecast = model.predict(future_X_scaled)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X_scaled)
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t (Lasso)"
            
            return {
                'success': True,
                'model_type': 'Lasso Regression',
                'forecast': forecast_values,
                'metrics': metrics,
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0]),
                'alpha': alpha,
                'formula': formula
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def forecast_polynomial(series: List[float], steps: int = 5, degree: int = 2) -> Dict[str, Any]:
        """Прогнозирование с помощью полиномиальной регрессии"""
        if len(series) < degree + 1:
            return {'error': f'Недостаточно данных для полинома степени {degree} (нужно минимум {degree+1} точек)', 'forecast': []}
        
        try:
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < degree + 1:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек, нужно {degree+1}', 'forecast': []}
            
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
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            coefficients = model.coef_
            formula = f"y = {model.intercept_:.4f}"
            for i, coef in enumerate(coefficients):
                if i == 0:
                    formula += f" + {coef:.4f}·t"
                elif i == 1:
                    formula += f" + {coef:.4f}·t²"
                else:
                    formula += f" + {coef:.4f}·t^{i+1}"
            
            return {
                'success': True,
                'model_type': f'Polynomial Regression (degree {degree})',
                'forecast': forecast_values,
                'metrics': metrics,
                'intercept': float(model.intercept_),
                'coefficients': [float(c) for c in coefficients],
                'degree': degree,
                'formula': formula
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    def find_best_model(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Находит лучшую модель для прогнозирования (по R²)"""
        if len(series) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(series)} точек', 'forecast': []}
        
        clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
        if len(clean_series) < 3:
            return {'success': False, 'error': f'Недостаточно чистых данных: {len(clean_series)} точек', 'forecast': []}
        
        models = []
        
        linear_result = ForecastService.forecast_linear(clean_series, steps)
        if linear_result.get('success'):
            models.append(('Линейная регрессия', linear_result))
        
        ridge_result = ForecastService.forecast_ridge(clean_series, steps)
        if ridge_result.get('success'):
            models.append(('Ridge регрессия', ridge_result))
        
        lasso_result = ForecastService.forecast_lasso(clean_series, steps)
        if lasso_result.get('success'):
            models.append(('Lasso регрессия', lasso_result))
        
        for degree in [2, 3]:
            if len(clean_series) >= degree + 1:
                poly_result = ForecastService.forecast_polynomial(clean_series, steps, degree)
                if poly_result.get('success'):
                    models.append((f'Полином степени {degree}', poly_result))
        
        if not models:
            return {'success': False, 'error': 'Не удалось построить ни одну модель', 'forecast': []}
        
        # Выбираем модель с наивысшим R²
        best_model_name, best_model = max(models, key=lambda x: x[1].get('metrics', {}).get('r2', -float('inf')))
        
        return {
            'success': True,
            'best_model': best_model_name,
            'forecast': best_model['forecast'],
            'metrics': best_model.get('metrics', {}),
            'formula': best_model.get('formula', ''),
            'intercept': best_model.get('intercept'),
            'slope': best_model.get('slope'),
            'coefficients': best_model.get('coefficients'),
            'degree': best_model.get('degree')
        }
    
    @staticmethod
    def forecast_with_model(series: List[float], steps: int = 5, 
                           model_type: str = 'linear', degree: int = 2) -> Dict[str, Any]:
        """Прогнозирование с выбранной моделью"""
        clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
        
        if model_type == 'linear':
            return ForecastService.forecast_linear(clean_series, steps)
        elif model_type == 'ridge':
            return ForecastService.forecast_ridge(clean_series, steps)
        elif model_type == 'lasso':
            return ForecastService.forecast_lasso(clean_series, steps)
        elif model_type == 'polynomial':
            return ForecastService.forecast_polynomial(clean_series, steps, degree)
        elif model_type == 'auto':
            return ForecastService.find_best_model(clean_series, steps)
        else:
            return ForecastService.forecast_linear(clean_series, steps)
    
    @staticmethod
    @with_db_connection
    def get_forecast_for_country(conn, country_id: int, indicator_type: str, 
                                    steps: int = 5, model_type: str = 'auto',
                                    degree: int = 2) -> Dict[str, Any]:
        """Получение прогноза для страны и показателя"""
        cur = None
        try:
            print(f"\n  --- get_forecast_for_country: country_id={country_id}, indicator={indicator_type} ---")
            
            cur = conn.cursor()
            query = f"""
                SELECT year, {indicator_type} as value
                FROM indicators 
                WHERE country_id = %s AND {indicator_type} IS NOT NULL
                ORDER BY year
            """
            print(f"  Выполняется запрос: {query}")
            cur.execute(query, (country_id,))
            data = cur.fetchall()
            cur.close()
            cur = None
            
            print(f"  Найдено записей: {len(data)}")
            
            if len(data) == 0:
                return {
                    'success': False,
                    'error': f'Нет данных для страны {country_id}',
                    'forecast': []
                }
            
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
                    try:
                        val = float(d['value'])
                        historical_values.append(val)
                        historical_years.append(int(d['year']))
                    except (ValueError, TypeError) as e:
                        print(f"  Ошибка преобразования: {e}, значение={d['value']}")
                        continue
            
            print(f"  Исторических значений: {len(historical_values)}")
            print(f"  Годы: {historical_years[0] if historical_years else 'N/A'} - {historical_years[-1] if historical_years else 'N/A'}")
            
            if len(historical_values) < 3:
                return {
                    'success': False,
                    'error': f'Недостаточно валидных данных: {len(historical_values)} точек',
                    'forecast': []
                }
            
            forecast_result = ForecastService.forecast_with_model(historical_values, steps, model_type, degree)
            
            # Проверка что forecast_result не None и имеет метод get
            if forecast_result is None:
                return {
                    'success': False,
                    'error': 'Ошибка: модель вернула None',
                    'forecast': []
                }
            
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
                    'forecast': forecast_result.get('forecast', []),
                    'model_type': forecast_result.get('model_type', model_type),
                    'metrics': forecast_result.get('metrics', {}),
                    'formula': forecast_result.get('formula', '')
                }
                
                if 'intercept' in forecast_result:
                    result['intercept'] = forecast_result['intercept']
                if 'slope' in forecast_result:
                    result['slope'] = forecast_result['slope']
                if 'coefficients' in forecast_result:
                    result['coefficients'] = forecast_result['coefficients']
                if 'degree' in forecast_result:
                    result['degree'] = forecast_result['degree']
                if 'alpha' in forecast_result:
                    result['alpha'] = forecast_result['alpha']
                
                print(f"  Прогноз успешно построен")
                return ForecastService.convert_to_serializable_dict(result)
            else:
                error_msg = forecast_result.get('error', 'Ошибка прогнозирования') if forecast_result else 'Неизвестная ошибка'
                print(f"  Ошибка прогнозирования: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'forecast': []
                }
            
        except Exception as e:
            print(f"  Исключение: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'forecast': []}
        finally:
            if cur:
                cur.close()