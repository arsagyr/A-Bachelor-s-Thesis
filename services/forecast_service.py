"""
Сервис для прогнозирования временных рядов
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
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
    def get_formula(model_type: str, intercept: float, slope: float = None, 
                    coefficients: List[float] = None, degree: int = 2) -> str:
        """Формирование формулы зависимости"""
        if model_type == 'Linear Regression':
            return f"y = {intercept:.4f} + {slope:.4f}·x"
        elif model_type == 'Ridge Regression':
            return f"y = {intercept:.4f} + {slope:.4f}·x (Ridge)"
        elif model_type == 'Lasso Regression':
            return f"y = {intercept:.4f} + {slope:.4f}·x (Lasso)"
        elif 'Polynomial' in model_type:
            if coefficients and len(coefficients) >= 1:
                formula = f"y = {intercept:.4f}"
                for i, coef in enumerate(coefficients):
                    if i == 0:
                        formula += f" + {coef:.4f}·x"
                    elif i == 1:
                        formula += f" + {coef:.4f}·x²"
                    else:
                        formula += f" + {coef:.4f}·x^{i+1}"
                return formula
            return f"y = {intercept:.4f} + полином степени {degree}"
        return f"y = {intercept:.4f}"
    
    @staticmethod
    def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Расчет метрик качества модели"""
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2)
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
            
            formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·x"
            
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
            
            model = Ridge(alpha=alpha)
            model.fit(X, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X)
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·x (Ridge)"
            
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
            
            model = Lasso(alpha=alpha)
            model.fit(X, y)
            
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X)
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·x (Lasso)"
            
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
            
            # Создаем временные метки (годы относительно начала)
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            
            # Создаем полиномиальные признаки
            poly = PolynomialFeatures(degree=degree, include_bias=False)
            X_poly = poly.fit_transform(X)
            
            # Обучаем модель
            model = LinearRegression()
            model.fit(X_poly, y)
            
            # Прогноз
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            future_X_poly = poly.transform(future_X)
            forecast = model.predict(future_X_poly)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            # Предсказания на обучающих данных
            y_pred = model.predict(X_poly)
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            # Формируем формулу полинома с правильными коэффициентами
            # Получаем названия признаков
            feature_names = poly.get_feature_names_out(['x'])
            
            # Собираем формулу
            formula = f"y = {model.intercept_:.4f}"
            for i, (name, coef) in enumerate(zip(feature_names, model.coef_)):
                if abs(coef) > 1e-10:  # Игнорируем очень маленькие коэффициенты
                    sign = '+' if coef > 0 else '-'
                    abs_coef = abs(coef)
                    
                    if '^' in name:
                        power = name.split('^')[1]
                        if abs_coef == 1:
                            formula += f" {sign} x^{power}"
                        else:
                            formula += f" {sign} {abs_coef:.4f}·x^{power}"
                    else:
                        if abs_coef == 1:
                            formula += f" {sign} x"
                        else:
                            formula += f" {sign} {abs_coef:.4f}·x"
            
            # Получаем коэффициенты для отображения
            coefficients = model.coef_.tolist()
            
            return {
                'success': True,
                'model_type': f'Polynomial Regression (degree {degree})',
                'forecast': forecast_values,
                'metrics': metrics,
                'intercept': float(model.intercept_),
                'coefficients': coefficients,
                'degree': degree,
                'formula': formula,
                'feature_names': feature_names.tolist()
            }
        except Exception as e:
            print(f"Error in polynomial forecast: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'forecast': []}

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
            return ForecastService.forecast_polynomial_manual(clean_series, steps, degree)  # Используем ручной метод
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
            print(f"\n=== get_forecast_for_country: country_id={country_id}, indicator={indicator_type} ===")
            
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
            
            print(f"Найдено записей: {len(data)}")
            
            if len(data) < 3:
                error_msg = f'Недостаточно данных: {len(data)} точек (нужно минимум 3)'
                print(f"Ошибка: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
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
            
            print(f"Исторических значений: {len(historical_values)}, годы: {historical_years[0] if historical_years else 'N/A'} - {historical_years[-1] if historical_years else 'N/A'}")
            
            if len(historical_values) < 3:
                error_msg = f'Недостаточно валидных данных: {len(historical_values)} точек'
                print(f"Ошибка: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'forecast': []
                }
            
            forecast_result = ForecastService.forecast_with_model(historical_values, steps, model_type, degree)
            
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
                
                print(f"Прогноз успешно построен")
                return ForecastService.convert_to_serializable_dict(result)
            else:
                print(f"Ошибка прогнозирования: {forecast_result.get('error')}")
                return {
                    'success': False,
                    'error': forecast_result.get('error', 'Ошибка прогнозирования'),
                    'forecast': []
                }
            
        except Exception as e:
            print(f"Исключение: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'forecast': []}
        finally:
            if cur:
                cur.close()


    @staticmethod
    def forecast_polynomial_manual(series: List[float], steps: int = 5, degree: int = 2) -> Dict[str, Any]:
        """Прогнозирование с помощью полиномиальной регрессии (ручное построение)"""
        if len(series) < degree + 1:
            return {'error': f'Недостаточно данных для полинома степени {degree} (нужно минимум {degree+1} точек)', 'forecast': []}
        
        try:
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < degree + 1:
                return {'error': f'Недостаточно чистых данных: {len(clean_series)} точек, нужно {degree+1}', 'forecast': []}
            
            # Создаем временные метки
            X = np.arange(len(clean_series))
            y = np.array(clean_series)
            
            # Ручное построение полиномиальных признаков
            X_poly = np.column_stack([X ** i for i in range(1, degree + 1)])
            
            # Добавляем столбец единиц для intercept
            X_with_intercept = np.column_stack([np.ones(len(X)), X_poly])
            
            # Решаем методом наименьших квадратов
            coefficients = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
            
            intercept = coefficients[0]
            poly_coeffs = coefficients[1:]
            
            # Функция предсказания
            def predict(x_vals):
                x_vals = np.array(x_vals)
                result = intercept
                for power, coeff in enumerate(poly_coeffs, 1):
                    result += coeff * (x_vals ** power)
                return result
            
            # Прогноз
            future_X = np.arange(len(clean_series), len(clean_series) + steps)
            forecast_values = predict(future_X).tolist()
            
            # Предсказания на обучающих данных
            y_pred = predict(X)
            metrics = ForecastService.calculate_metrics(y, y_pred)
            
            # Формируем формулу
            formula = f"y = {intercept:.4f}"
            for power, coeff in enumerate(poly_coeffs, 1):
                if abs(coeff) > 1e-10:
                    sign = '+' if coeff > 0 else '-'
                    abs_coeff = abs(coeff)
                    if power == 1:
                        formula += f" {sign} {abs_coeff:.4f}·x"
                    else:
                        formula += f" {sign} {abs_coeff:.4f}·x^{power}"
            
            return {
                'success': True,
                'model_type': f'Polynomial Regression (degree {degree})',
                'forecast': [float(x) for x in forecast_values],
                'metrics': metrics,
                'intercept': float(intercept),
                'coefficients': [float(c) for c in poly_coeffs],
                'degree': degree,
                'formula': formula
            }
        except Exception as e:
            print(f"Error in polynomial forecast: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'forecast': []}