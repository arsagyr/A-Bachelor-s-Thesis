"""
Сервис для регрессионного анализа зависимости ВВП от экспорта и импорта
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
import warnings
import traceback
warnings.filterwarnings('ignore')

from database import with_db_connection


class RegressionService:
    """Сервис для регрессионного анализа экономических показателей"""
    
    AVAILABLE_MODELS = {
        'linear': 'Линейная регрессия',
        'ridge': 'Ridge регрессия (L2 регуляризация)',
        'lasso': 'Lasso регрессия (L1 регуляризация)',
        'polynomial': 'Полиномиальная регрессия (степень 2)'
    }
    
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
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    @staticmethod
    @with_db_connection
    def get_economic_data(conn, country_id: int) -> pd.DataFrame:
        """Получение экономических данных для конкретной страны"""
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
            
            print(f"Получено {len(df)} строк для страны {country_id}")
            if len(df) > 0:
                print(f"  Годы: {df['year'].iloc[0]} - {df['year'].iloc[-1]}")
                print(f"  Экспорт: {df['export'].min():.2f} - {df['export'].max():.2f}")
                print(f"  Импорт: {df['import'].min():.2f} - {df['import'].max():.2f}")
                print(f"  ВВП: {df['gdp'].min():.2f} - {df['gdp'].max():.2f}")
            
            return df
            
        except Exception as e:
            print(f"Error getting economic data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Подготовка признаков для регрессии"""
        if df.empty:
            return np.array([]), np.array([]), []
        
        # Базовые признаки
        export = df['export'].values.astype(float)
        import_val = df['import'].values.astype(float)
        gdp = df['gdp'].values.astype(float)
        
        # Создаем признаки
        features = []
        feature_names = []
        
        features.append(export)
        feature_names.append('export')
        
        features.append(import_val)
        feature_names.append('import')
        
        features.append(export * import_val)
        feature_names.append('export_x_import')
        
        features.append(export ** 2)
        feature_names.append('export_sq')
        
        features.append(import_val ** 2)
        feature_names.append('import_sq')
        
        features.append(export - import_val)
        feature_names.append('trade_balance')
        
        features.append(export + import_val)
        feature_names.append('trade_turnover')
        
        X = np.column_stack(features)
        y = gdp
        
        print(f"Подготовлено {X.shape[1]} признаков, {X.shape[0]} наблюдений")
        
        return X, y, feature_names
    
    @staticmethod
    def train_regression_model(X: np.ndarray, y: np.ndarray, 
                               model_type: str = 'linear') -> Dict[str, Any]:
        """Обучение регрессионной модели"""
        
        if len(X) < 4:
            return {'success': False, 'error': f'Недостаточно данных: {len(X)} точек, нужно минимум 4'}
        
        try:
            # Проверка на нулевую дисперсию
            if np.std(y) < 1e-6:
                print("Предупреждение: Целевая переменная имеет нулевую дисперсию")
            
            # Разделение на train/test
            if len(X) >= 8:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
            else:
                X_train, y_train = X, y
                X_test, y_test = X, y
            
            # Выбор модели
            if model_type == 'linear':
                model = LinearRegression()
                X_train_fit = X_train
                X_test_fit = X_test
            elif model_type == 'ridge':
                scaler = StandardScaler()
                X_train_fit = scaler.fit_transform(X_train)
                X_test_fit = scaler.transform(X_test) if len(X_test) > 0 else X_test
                model = Ridge(alpha=1.0)
            elif model_type == 'lasso':
                scaler = StandardScaler()
                X_train_fit = scaler.fit_transform(X_train)
                X_test_fit = scaler.transform(X_test) if len(X_test) > 0 else X_test
                model = Lasso(alpha=1.0)
            elif model_type == 'polynomial':
                poly = PolynomialFeatures(degree=2, include_bias=False)
                X_train_fit = poly.fit_transform(X_train)
                X_test_fit = poly.transform(X_test) if len(X_test) > 0 else X_test
                model = LinearRegression()
            else:
                model = LinearRegression()
                X_train_fit = X_train
                X_test_fit = X_test
            
            # Обучение
            model.fit(X_train_fit, y_train)
            
            # Предсказания
            y_train_pred = model.predict(X_train_fit)
            y_test_pred = model.predict(X_test_fit) if len(X_test) > 0 else y_train_pred
            
            # Расчет метрик
            train_r2 = r2_score(y_train, y_train_pred)
            train_mae = mean_absolute_error(y_train, y_train_pred)
            train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
            
            test_r2 = r2_score(y_test, y_test_pred)
            test_mae = mean_absolute_error(y_test, y_test_pred)
            test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
            
            # Коэффициенты
            coefficients = model.coef_.tolist() if hasattr(model, 'coef_') else []
            
            print(f"Train R²: {train_r2:.4f}, Test R²: {test_r2:.4f}")
            print(f"Train MAE: {train_mae:.2f}, Test MAE: {test_mae:.2f}")
            
            return {
                'success': True,
                'model_type': model_type,
                'train_metrics': {
                    'r2': float(train_r2),
                    'mae': float(train_mae),
                    'rmse': float(train_rmse),
                    'samples': len(y_train)
                },
                'test_metrics': {
                    'r2': float(test_r2),
                    'mae': float(test_mae),
                    'rmse': float(test_rmse),
                    'samples': len(y_test)
                },
                'coefficients': coefficients,
                'intercept': float(model.intercept_) if hasattr(model, 'intercept_') else 0.0
            }
            
        except Exception as e:
            print(f"Error training model: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    @with_db_connection
    def analyze_country(conn, country_id: int, model_type: str = 'linear') -> Dict[str, Any]:
        """Регрессионный анализ для конкретной страны"""
        try:
            # Получаем страну
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            
            if not country:
                return {'success': False, 'error': 'Страна не найдена'}
            
            # Получаем данные
            df = RegressionService.get_economic_data(country_id=country_id)
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'Нет данных для анализа',
                    'country_name': country['name'],
                    'suggestion': 'Загрузите данные через CSV'
                }
            
            if len(df) < 4:
                return {
                    'success': False,
                    'error': f'Недостаточно данных: {len(df)} точек, нужно минимум 4',
                    'country_name': country['name'],
                    'data_points': len(df),
                    'years': df['year'].tolist()
                }
            
            # Подготовка признаков
            X, y, feature_names = RegressionService.prepare_features(df)
            
            if len(X) == 0:
                return {'success': False, 'error': 'Ошибка подготовки признаков'}
            
            # Обучение модели
            model_result = RegressionService.train_regression_model(X, y, model_type)
            
            if not model_result.get('success'):
                return {'success': False, 'error': model_result.get('error', 'Ошибка обучения')}
            
            # Получение предсказаний для графика
            try:
                if model_type == 'polynomial':
                    poly = PolynomialFeatures(degree=2, include_bias=False)
                    X_pred = poly.fit_transform(X)
                    final_model = LinearRegression()
                elif model_type in ['ridge', 'lasso']:
                    scaler = StandardScaler()
                    X_pred = scaler.fit_transform(X)
                    final_model = Ridge(alpha=1.0) if model_type == 'ridge' else Lasso(alpha=1.0)
                else:
                    X_pred = X
                    final_model = LinearRegression()
                
                final_model.fit(X_pred, y)
                predicted_gdp = final_model.predict(X_pred)
            except Exception as e:
                print(f"Error in predictions: {e}")
                predicted_gdp = [0] * len(y)
            
            result = {
                'success': True,
                'country_id': country_id,
                'country_name': country['name'],
                'model_type': model_type,
                'feature_names': feature_names,
                'data_points': len(df),
                'years': df['year'].tolist(),
                'actual_values': {
                    'export': df['export'].tolist(),
                    'import': df['import'].tolist(),
                    'gdp': df['gdp'].tolist()
                },
                'predicted_values': {
                    'gdp': [float(x) for x in predicted_gdp]
                },
                'train_metrics': model_result['train_metrics'],
                'test_metrics': model_result['test_metrics'],
                'coefficients': model_result['coefficients'],
                'intercept': model_result['intercept']
            }
            
            return RegressionService.convert_to_serializable_dict(result)
            
        except Exception as e:
            print(f"Error in analyze_country: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    @with_db_connection
    def predict_gdp(conn, country_id: int, export_value: float, 
                   import_value: float, model_type: str = 'linear') -> Dict[str, Any]:
        """Прогнозирование ВВП на основе экспорта и импорта"""
        try:
            # Получаем данные
            df = RegressionService.get_economic_data(country_id=country_id)
            
            if df.empty:
                return {'success': False, 'error': 'Нет данных для обучения'}
            
            if len(df) < 4:
                return {'success': False, 'error': f'Недостаточно данных: {len(df)} точек'}
            
            # Получаем название страны
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            
            # Подготовка признаков
            X, y, feature_names = RegressionService.prepare_features(df)
            
            # Обучение модели
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
            
            # Подготовка признаков для прогноза
            temp_df = pd.DataFrame({
                'export': [export_value],
                'import': [import_value],
                'gdp': [0]
            })
            X_pred, _, _ = RegressionService.prepare_features(temp_df)
            
            if model_type == 'polynomial':
                X_pred = poly.transform(X_pred)
            elif model_type in ['ridge', 'lasso']:
                X_pred = scaler.transform(X_pred)
            
            # Прогноз
            prediction = model.predict(X_pred)[0]
            
            # Если прогноз отрицательный
            if prediction < 0:
                # Простая линейная зависимость
                coeff = np.polyfit(df['export'] + df['import'], df['gdp'], 1)
                prediction = coeff[0] * (export_value + import_value) + coeff[1]
            
            # Метрики
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)
            mae = mean_absolute_error(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            
            return {
                'success': True,
                'country_id': country_id,
                'country_name': country['name'] if country else 'Unknown',
                'model_type': model_type,
                'input_values': {
                    'export': float(export_value),
                    'import': float(import_value)
                },
                'predicted_gdp': float(prediction),
                'model_metrics': {
                    'r2': float(r2),
                    'mae': float(mae),
                    'rmse': float(rmse)
                },
                'data_points': len(df)
            }
            
        except Exception as e:
            print(f"Error in predict_gdp: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}