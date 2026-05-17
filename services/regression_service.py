import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from database import with_db_connection


class RegressionService:
    
    AVAILABLE_MODELS = {
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
            return {k: RegressionService.convert_to_serializable_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [RegressionService.convert_to_serializable_dict(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    @staticmethod
    @with_db_connection
    def get_historical_data(conn, country_id: int) -> pd.DataFrame:
        cur = None
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
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df.columns = ['year', 'export', 'import', 'gdp']
            
            for col in ['export', 'import', 'gdp']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df.dropna()
            
        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()
        finally:
            if cur:
                cur.close()
    
    @staticmethod
    def prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        if df.empty:
            return np.array([]), np.array([]), []
        
        export = df['export'].values.astype(float)
        import_val = df['import'].values.astype(float)
        gdp = df['gdp'].values.astype(float)
        
        features = np.column_stack([
            export, import_val,
            export * import_val,
            export ** 2, import_val ** 2,
            export - import_val,
            export + import_val
        ])
        
        feature_names = ['export', 'import', 'export_x_import', 'export_sq', 'import_sq', 'trade_balance', 'trade_turnover']
        
        return features, gdp, feature_names
    
    @staticmethod
    def forecast_indicator(series: List[float], steps: int = 5) -> Dict[str, Any]:
        """Прогнозирование отдельного показателя с помощью линейной регрессии"""
        if len(series) < 3:
            return {'error': 'Недостаточно данных', 'forecast': []}
        
        try:
            clean_series = [float(x) for x in series if x is not None and not np.isnan(x)]
            if len(clean_series) < 3:
                return {'error': 'Недостаточно чистых данных', 'forecast': []}
            
            X = np.arange(len(clean_series)).reshape(-1, 1)
            y = np.array(clean_series)
            model = LinearRegression()
            model.fit(X, y)
            future_X = np.arange(len(clean_series), len(clean_series) + steps).reshape(-1, 1)
            forecast = model.predict(future_X)
            forecast_values = [float(x) for x in forecast.tolist()]
            
            y_pred = model.predict(X)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            
            return {
                'success': True,
                'forecast': forecast_values,
                'rmse': float(rmse)
            }
        except Exception as e:
            return {'error': str(e), 'forecast': []}
    
    @staticmethod
    @with_db_connection
    def forecast_gdp_from_trade(conn, country_id: int, steps: int = 5, 
                                 model_type: str = 'linear') -> Dict[str, Any]:
        """
        Прогнозирование ВВП на основе прогнозов экспорта и импорта
        """
        try:
            # Получаем исторические данные
            df = RegressionService.get_historical_data(country_id=country_id)
            
            if df.empty:
                return {'success': False, 'error': 'Нет исторических данных'}
            
            if len(df) < 4:
                return {'success': False, 'error': f'Недостаточно данных: {len(df)} точек (нужно минимум 4)'}
            
            # Получаем название страны
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            
            # 1. Прогнозируем экспорт
            export_series = df['export'].tolist()
            export_forecast = RegressionService.forecast_indicator(export_series, steps)
            
            # 2. Прогнозируем импорт
            import_series = df['import'].tolist()
            import_forecast = RegressionService.forecast_indicator(import_series, steps)
            
            if export_forecast.get('error') or import_forecast.get('error'):
                return {
                    'success': False,
                    'error': 'Ошибка прогнозирования экспорта или импорта'
                }
            
            # 3. Обучаем регрессионную модель ВВП
            X, y, feature_names = RegressionService.prepare_features(df)
            
            if model_type == 'polynomial':
                poly = PolynomialFeatures(degree=2, include_bias=False)
                X = poly.fit_transform(X)
                model = LinearRegression()
            elif model_type == 'ridge':
                scaler = StandardScaler()
                X = scaler.fit_transform(X)
                model = Ridge(alpha=1.0)
            elif model_type == 'lasso':
                scaler = StandardScaler()
                X = scaler.fit_transform(X)
                model = Lasso(alpha=1.0)
            else:
                model = LinearRegression()
            
            model.fit(X, y)
            y_pred = model.predict(X)
            
            # 4. Прогнозируем ВВП
            gdp_forecast = []
            for i in range(steps):
                pred_export = export_forecast['forecast'][i]
                pred_import = import_forecast['forecast'][i]
                
                features = np.array([[
                    pred_export, pred_import,
                    pred_export * pred_import,
                    pred_export ** 2, pred_import ** 2,
                    pred_export - pred_import,
                    pred_export + pred_import
                ]])
                
                if model_type == 'polynomial':
                    features = poly.transform(features)
                elif model_type in ['ridge', 'lasso']:
                    scaler = StandardScaler()
                    features = scaler.fit_transform(features)
                
                pred_gdp = model.predict(features)[0]
                gdp_forecast.append(float(pred_gdp))
            
            historical_years = df['year'].tolist()
            last_year = historical_years[-1]
            forecast_years = [last_year + i + 1 for i in range(steps)]
            
            # Расчет доверительных интервалов
            residuals = y - y_pred
            std_residuals = np.std(residuals)
            
            result = {
                'success': True,
                'country_id': country_id,
                'country_name': country['name'],
                'steps': steps,
                'model_type': model_type,
                'historical': {
                    'years': historical_years,
                    'export': [float(x) for x in df['export'].tolist()],
                    'import': [float(x) for x in df['import'].tolist()],
                    'gdp': [float(x) for x in df['gdp'].tolist()]
                },
                'forecast': {
                    'years': forecast_years,
                    'export': export_forecast['forecast'],
                    'import': import_forecast['forecast'],
                    'gdp': gdp_forecast
                },
                'confidence_intervals': {
                    'lower': [gdp - 1.96 * std_residuals for gdp in gdp_forecast],
                    'upper': [gdp + 1.96 * std_residuals for gdp in gdp_forecast],
                    'confidence_level': 0.95
                },
                'metrics': {
                    'r2': float(r2_score(y, y_pred)),
                    'mae': float(mean_absolute_error(y, y_pred)),
                    'rmse': float(np.sqrt(mean_squared_error(y, y_pred))),
                    'export_rmse': export_forecast['rmse'],
                    'import_rmse': import_forecast['rmse']
                }
            }
            
            return RegressionService.convert_to_serializable_dict(result)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}