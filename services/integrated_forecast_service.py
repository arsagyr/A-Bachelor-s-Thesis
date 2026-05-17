"""
Интегрированный сервис прогнозирования: 
1. Прогноз экспорта и импорта через временные ряды (ARIMA, Holt-Winters и др.)
2. Прогноз ВВП на основе прогнозных значений экспорта и импорта через регрессию
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
import traceback
warnings.filterwarnings('ignore')

from database import with_db_connection
from services.forecast_service import ForecastService
from services.regression_service import RegressionService


class IntegratedForecastService:
    """Интегрированный сервис прогнозирования экономических показателей"""
    
    @staticmethod
    def convert_to_serializable(obj):
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
        if isinstance(obj, dict):
            return {k: IntegratedForecastService.convert_to_serializable_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [IntegratedForecastService.convert_to_serializable_dict(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    @staticmethod
    @with_db_connection
    def get_historical_data(conn, country_id: int) -> pd.DataFrame:
        """Получение исторических данных для страны"""
        try:
            cur = conn.cursor()
            query = """
                SELECT year, export_value, import_value, gdp_value
                FROM indicators 
                WHERE country_id = %s 
                  AND export_value IS NOT NULL 
                  AND import_value IS NOT NULL 
                  AND gdp_value IS NOT NULL
                ORDER BY year
            """
            cur.execute(query, (country_id,))
            data = cur.fetchall()
            cur.close()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df.columns = ['year', 'export', 'import', 'gdp']
            
            for col in ['export', 'import', 'gdp']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            print(f"Получено {len(df)} строк исторических данных")
            return df
            
        except Exception as e:
            print(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def forecast_indicator_with_best_model(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """
        Прогнозирование отдельного показателя с выбором лучшей модели
        """
        if len(series) < 4:
            return {'error': 'Недостаточно данных', 'forecast': []}
        
        clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
        
        # Пробуем разные модели
        models = []
        
        # ARIMA
        try:
            from statsmodels.tsa.arima.model import ARIMA
            order = (1, 1, 1)
            model = ARIMA(clean_series, order=order)
            fitted = model.fit()
            forecast = fitted.forecast(steps=steps)
            forecast_values = [float(x) for x in forecast.tolist()]
            models.append({
                'name': 'ARIMA',
                'forecast': forecast_values,
                'rmse': np.sqrt(mean_squared_error(clean_series, fitted.fittedvalues))
            })
        except:
            pass
        
        # Простое экспоненциальное сглаживание
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            model = ExponentialSmoothing(clean_series, trend='add', seasonal=None)
            fitted = model.fit()
            forecast = fitted.forecast(steps=steps)
            forecast_values = [float(x) for x in forecast.tolist()]
            models.append({
                'name': 'Holt-Winters',
                'forecast': forecast_values,
                'rmse': np.sqrt(mean_squared_error(clean_series, fitted.fittedvalues))
            })
        except:
            pass
        
        # Линейная регрессия
        try:
            from sklearn.linear_model import LinearRegression
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            model = LinearRegression()
            model.fit(X, y)
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            y_pred = model.predict(X)
            models.append({
                'name': 'Linear',
                'forecast': forecast_values,
                'rmse': np.sqrt(mean_squared_error(y, y_pred))
            })
        except:
            pass
        
        if not models:
            return {'error': 'Не удалось построить ни одну модель', 'forecast': []}
        
        # Выбираем модель с наименьшей ошибкой
        best_model = min(models, key=lambda x: x['rmse'])
        
        return {
            'success': True,
            'model_used': best_model['name'],
            'forecast': best_model['forecast'],
            'rmse': best_model['rmse']
        }
    
    @staticmethod
    def build_regression_model(df: pd.DataFrame, model_type: str = 'linear') -> Dict[str, Any]:
        """
        Построение регрессионной модели для прогноза ВВП на основе экспорта и импорта
        """
        if len(df) < 4:
            return {'error': 'Недостаточно данных для регрессии'}
        
        X = df[['export', 'import']].values
        y = df['gdp'].values
        
        # Добавляем дополнительные признаки
        export = X[:, 0]
        import_val = X[:, 1]
        
        features = np.column_stack([
            export,
            import_val,
            export * import_val,
            export ** 2,
            import_val ** 2,
            export - import_val,
            export + import_val
        ])
        
        if model_type == 'linear':
            model = LinearRegression()
        elif model_type == 'ridge':
            model = Ridge(alpha=1.0)
        elif model_type == 'lasso':
            model = Lasso(alpha=1.0)
        else:
            model = LinearRegression()
        
        model.fit(features, y)
        y_pred = model.predict(features)
        
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        
        return {
            'success': True,
            'model': model,
            'r2': float(r2),
            'mae': float(mae),
            'rmse': float(rmse),
            'coefficients': model.coef_.tolist(),
            'intercept': float(model.intercept_)
        }
    
    @staticmethod
    @with_db_connection
    def integrated_forecast(conn, country_id: int, steps: int = 5, 
                           forecast_model: str = 'auto',
                           regression_model: str = 'linear') -> Dict[str, Any]:
        """
        Интегрированный прогноз:
        1. Прогноз экспорта
        2. Прогноз импорта  
        3. Прогноз ВВП на основе прогнозов экспорта и импорта
        """
        try:
            # Получаем исторические данные
            df = IntegratedForecastService.get_historical_data(country_id=country_id)
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'Нет исторических данных для прогнозирования'
                }
            
            if len(df) < 4:
                return {
                    'success': False,
                    'error': f'Недостаточно данных: {len(df)} точек, нужно минимум 4'
                }
            
            # Получаем название страны
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            
            # 1. Прогнозирование экспорта
            print("Прогнозирование экспорта...")
            export_forecast = IntegratedForecastService.forecast_indicator_with_best_model(
                df['export'].tolist(), steps
            )
            
            # 2. Прогнозирование импорта
            print("Прогнозирование импорта...")
            import_forecast = IntegratedForecastService.forecast_indicator_with_best_model(
                df['import'].tolist(), steps
            )
            
            if export_forecast.get('error') or import_forecast.get('error'):
                return {
                    'success': False,
                    'error': 'Ошибка прогнозирования экспорта/импорта',
                    'export_error': export_forecast.get('error'),
                    'import_error': import_forecast.get('error')
                }
            
            # 3. Построение регрессионной модели для ВВП
            print("Построение регрессионной модели для ВВП...")
            regression = IntegratedForecastService.build_regression_model(df, regression_model)
            
            if regression.get('error'):
                return {
                    'success': False,
                    'error': regression['error']
                }
            
            # 4. Прогнозирование ВВП на основе прогнозов экспорта и импорта
            forecast_export_values = export_forecast['forecast']
            forecast_import_values = import_forecast['forecast']
            
            # Подготовка признаков для прогноза
            forecast_export = np.array(forecast_export_values)
            forecast_import = np.array(forecast_import_values)
            
            forecast_features = np.column_stack([
                forecast_export,
                forecast_import,
                forecast_export * forecast_import,
                forecast_export ** 2,
                forecast_import ** 2,
                forecast_export - forecast_import,
                forecast_export + forecast_import
            ])
            
            gdp_forecast = regression['model'].predict(forecast_features)
            gdp_forecast_values = [float(x) for x in gdp_forecast.tolist()]
            
            # Прогнозные годы
            last_year = df['year'].iloc[-1]
            forecast_years = [last_year + i + 1 for i in range(steps)]
            
            # Формирование результата
            result = {
                'success': True,
                'country_id': country_id,
                'country_name': country['name'] if country else 'Unknown',
                'steps': steps,
                'historical': {
                    'years': df['year'].tolist(),
                    'export': df['export'].tolist(),
                    'import': df['import'].tolist(),
                    'gdp': df['gdp'].tolist()
                },
                'forecast': {
                    'years': forecast_years,
                    'export': forecast_export_values,
                    'import': forecast_import_values,
                    'gdp': gdp_forecast_values
                },
                'models': {
                    'export': {
                        'type': export_forecast['model_used'],
                        'rmse': export_forecast['rmse']
                    },
                    'import': {
                        'type': import_forecast['model_used'],
                        'rmse': import_forecast['rmse']
                    },
                    'gdp_regression': {
                        'type': regression_model,
                        'r2': regression['r2'],
                        'mae': regression['mae'],
                        'rmse': regression['rmse']
                    }
                }
            }
            
            print("Интегрированный прогноз успешно завершен")
            return IntegratedForecastService.convert_to_serializable_dict(result)
            
        except Exception as e:
            print(f"Error in integrated_forecast: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    @with_db_connection
    def integrated_forecast_with_confidence(conn, country_id: int, steps: int = 5,
                                           forecast_model: str = 'auto',
                                           regression_model: str = 'linear') -> Dict[str, Any]:
        """
        Интегрированный прогноз с доверительными интервалами
        """
        result = IntegratedForecastService.integrated_forecast(
            country_id, steps, forecast_model, regression_model
        )
        
        if not result.get('success'):
            return result
        
        # Расчет доверительных интервалов для ВВП
        # Используем стандартное отклонение остатков регрессии
        df = IntegratedForecastService.get_historical_data(country_id=country_id)
        
        if len(df) > 0:
            X = df[['export', 'import']].values
            y = df['gdp'].values
            
            export = X[:, 0]
            import_val = X[:, 1]
            
            features = np.column_stack([
                export, import_val,
                export * import_val, export ** 2, import_val ** 2,
                export - import_val, export + import_val
            ])
            
            if regression_model == 'linear':
                model = LinearRegression()
            elif regression_model == 'ridge':
                model = Ridge(alpha=1.0)
            elif regression_model == 'lasso':
                model = Lasso(alpha=1.0)
            else:
                model = LinearRegression()
            
            model.fit(features, y)
            y_pred = model.predict(features)
            residuals = y - y_pred
            std_residuals = np.std(residuals)
            
            # Добавляем доверительные интервалы (95%)
            gdp_forecast = result['forecast']['gdp']
            lower_bounds = [gdp - 1.96 * std_residuals for gdp in gdp_forecast]
            upper_bounds = [gdp + 1.96 * std_residuals for gdp in gdp_forecast]
            
            result['confidence_intervals'] = {
                'lower': lower_bounds,
                'upper': upper_bounds,
                'confidence_level': 0.95,
                'std_residuals': float(std_residuals)
            }
        
        return result