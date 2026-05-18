"""
Сервис для комплексного трендового анализа и сравнения методов прогнозирования
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from database import with_db_connection


class TrendAnalysisService:
    """Сервис для трендового анализа и сравнения методов"""
    
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
            return {k: TrendAnalysisService.convert_to_serializable_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [TrendAnalysisService.convert_to_serializable_dict(item) for item in obj]
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
        """Расчет метрик качества"""
        r2 = r2_score(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if np.all(y_true != 0) else 100
        
        return {
            'r2': float(r2),
            'mae': float(mae),
            'rmse': float(rmse),
            'mape': float(mape)
        }
    
    @staticmethod
    def linear_trend(X: np.ndarray, y: np.ndarray, steps: int = 5) -> Dict[str, Any]:
        """Линейный тренд"""
        model = LinearRegression()
        model.fit(X.reshape(-1, 1), y)
        
        future_X = np.arange(len(X), len(X) + steps).reshape(-1, 1)
        forecast = model.predict(future_X)
        
        y_pred = model.predict(X.reshape(-1, 1))
        metrics = TrendAnalysisService.calculate_metrics(y, y_pred)
        
        return {
            'name': 'Линейная регрессия',
            'forecast': forecast.tolist(),
            'metrics': metrics,
            'formula': f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t",
            'color': '#3498db'
        }
    
    @staticmethod
    def ridge_trend(X: np.ndarray, y: np.ndarray, steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
        """Ridge тренд"""
        model = Ridge(alpha=alpha)
        model.fit(X.reshape(-1, 1), y)
        
        future_X = np.arange(len(X), len(X) + steps).reshape(-1, 1)
        forecast = model.predict(future_X)
        
        y_pred = model.predict(X.reshape(-1, 1))
        metrics = TrendAnalysisService.calculate_metrics(y, y_pred)
        
        return {
            'name': 'Ridge регрессия',
            'forecast': forecast.tolist(),
            'metrics': metrics,
            'formula': f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t",
            'color': '#2ecc71'
        }
    
    @staticmethod
    def lasso_trend(X: np.ndarray, y: np.ndarray, steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
        """Lasso тренд"""
        model = Lasso(alpha=alpha)
        model.fit(X.reshape(-1, 1), y)
        
        future_X = np.arange(len(X), len(X) + steps).reshape(-1, 1)
        forecast = model.predict(future_X)
        
        y_pred = model.predict(X.reshape(-1, 1))
        metrics = TrendAnalysisService.calculate_metrics(y, y_pred)
        
        return {
            'name': 'Lasso регрессия',
            'forecast': forecast.tolist(),
            'metrics': metrics,
            'formula': f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t",
            'color': '#e74c3c'
        }
    
    @staticmethod
    def polynomial_trend(X: np.ndarray, y: np.ndarray, steps: int = 5, degree: int = 2) -> Dict[str, Any]:
        """Полиномиальный тренд"""
        poly = PolynomialFeatures(degree=degree, include_bias=False)
        X_poly = poly.fit_transform(X.reshape(-1, 1))
        
        model = LinearRegression()
        model.fit(X_poly, y)
        
        future_X = np.arange(len(X), len(X) + steps).reshape(-1, 1)
        future_X_poly = poly.transform(future_X)
        forecast = model.predict(future_X_poly)
        
        y_pred = model.predict(X_poly)
        metrics = TrendAnalysisService.calculate_metrics(y, y_pred)
        
        formula = f"y = {model.intercept_:.4f}"
        feature_names = poly.get_feature_names_out(['t'])
        for i, (name, coef) in enumerate(zip(feature_names, model.coef_)):
            if abs(coef) > 1e-10:
                sign = '+' if coef > 0 else '-'
                abs_coef = abs(coef)
                if '^' in name:
                    power = name.split('^')[1]
                    if abs_coef == 1:
                        formula += f" {sign} t^{power}"
                    else:
                        formula += f" {sign} {abs_coef:.4f}·t^{power}"
                else:
                    if abs_coef == 1:
                        formula += f" {sign} t"
                    else:
                        formula += f" {sign} {abs_coef:.4f}·t"
        
        return {
            'name': f'Полиномиальный тренд (степень {degree})',
            'forecast': forecast.tolist(),
            'metrics': metrics,
            'formula': formula,
            'color': '#9b59b6'
        }
    
    @staticmethod
    def analyze_single_country(X: np.ndarray, y: np.ndarray, 
                                years: List[int], country_id: int, country_name: str,
                                indicator: str, steps: int = 5) -> Dict[str, Any]:
        """Анализ трендов для одной страны"""
        methods = []
        
        # Линейный тренд
        methods.append(TrendAnalysisService.linear_trend(X, y, steps))
        
        # Ridge тренд
        methods.append(TrendAnalysisService.ridge_trend(X, y, steps))
        
        # Lasso тренд
        methods.append(TrendAnalysisService.lasso_trend(X, y, steps))
        
        # Полиномиальные тренды
        if len(y) >= 3:
            methods.append(TrendAnalysisService.polynomial_trend(X, y, steps, 2))
        if len(y) >= 4:
            methods.append(TrendAnalysisService.polynomial_trend(X, y, steps, 3))
        
        # Находим лучший метод по R²
        best_method = max(methods, key=lambda m: m['metrics']['r2'])
        
        last_year = years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]
        
        return {
            'country_id': country_id,
            'country_name': country_name,
            'indicator': indicator,
            'indicator_name': {'export': 'Экспорт', 'import': 'Импорт', 'gdp': 'ВВП'}.get(indicator, indicator),
            'historical': {
                'years': years,
                'values': y.tolist()
            },
            'forecast_years': forecast_years,
            'methods': methods,
            'best_method': best_method['name'],
            'best_r2': best_method['metrics']['r2'],
            'best_forecast': best_method['forecast']
        }
    
    @staticmethod
    @with_db_connection
    def get_all_countries_trends(conn, indicator: str = 'gdp', steps: int = 5) -> Dict[str, Any]:
        """Получение трендов для всех стран"""
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM countries ORDER BY name")
            countries = cur.fetchall()
            cur.close()
            
            results = []
            
            for country in countries:
                cur = conn.cursor()
                query = f"""
                    SELECT year, {indicator}_value as value
                    FROM indicators 
                    WHERE country_id = %s AND {indicator}_value IS NOT NULL
                    ORDER BY year
                """
                cur.execute(query, (country['id'],))
                data = cur.fetchall()
                cur.close()
                
                if len(data) >= 3:
                    years = np.array([d['year'] for d in data])
                    values = np.array([float(d['value']) for d in data])
                    X = np.arange(len(values))
                    
                    trend_data = TrendAnalysisService.analyze_single_country(
                        X, values, years.tolist(), country['id'], country['name'], indicator, steps
                    )
                    results.append(trend_data)
            
            # Сортируем по лучшему R²
            results.sort(key=lambda x: x['best_r2'], reverse=True)
            
            return {
                'success': True,
                'indicator': indicator,
                'indicator_name': {'export': 'Экспорт', 'import': 'Импорт', 'gdp': 'ВВП'}.get(indicator, indicator),
                'steps': steps,
                'countries': results,
                'total_countries': len(results)
            }
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}