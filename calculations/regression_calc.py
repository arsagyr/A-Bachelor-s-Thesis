"""
Расчёты для регрессионного анализа ВВП от экспорта и импорта
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from calculations.auto_regression import linear_trend


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Расчёт метрик качества"""
    n = len(y_true)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))
    
    mask = y_true != 0
    if np.any(mask):
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = 100.0
    
    return {'r2': float(r2), 'rmse': float(rmse), 'mae': float(mae), 'mape': float(mape)}


def prepare_regression_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Подготовка признаков для регрессии ВВП от экспорта и импорта
    """
    if df.empty:
        return np.array([]), np.array([]), []
    
    # Преобразуем все значения в float
    export = df['export'].astype(float).values
    import_val = df['import'].astype(float).values
    gdp = df['gdp'].astype(float).values
    
    # Признаки: экспорт, импорт, их произведение, квадраты, разность, сумма
    features = np.column_stack([
        export,
        import_val,
        export * import_val,
        export ** 2,
        import_val ** 2,
        export - import_val,
        export + import_val
    ])
    
    feature_names = [
        'экспорт', 'импорт', 'экспорт×импорт',
        'экспорт²', 'импорт²', 'торговое сальдо', 'торговый оборот'
    ]
    
    return features, gdp, feature_names


def linear_regression_fit(X: np.ndarray, y: np.ndarray) -> tuple:
    """
    Линейная регрессия методом наименьших квадратов
    """
    # Добавляем столбец единиц для intercept
    X_with_intercept = np.column_stack([np.ones(len(X)), X])
    
    # Решаем нормальные уравнения: β = (X^T X)^(-1) X^T y
    XTX = X_with_intercept.T @ X_with_intercept
    XTy = X_with_intercept.T @ y
    
    try:
        coefficients = np.linalg.solve(XTX, XTy)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.pinv(XTX) @ XTy
    
    intercept = coefficients[0]
    slopes = coefficients[1:]
    
    return slopes, intercept


def ridge_regression_fit(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> tuple:
    """
    Ridge регрессия (L2-регуляризация)
    """
    X_with_intercept = np.column_stack([np.ones(len(X)), X])
    n_features = X_with_intercept.shape[1]
    
    # Ridge решение: β = (X^T X + αI)^(-1) X^T y
    XTX = X_with_intercept.T @ X_with_intercept
    ridge_matrix = XTX + alpha * np.eye(n_features)
    
    try:
        coefficients = np.linalg.solve(ridge_matrix, X_with_intercept.T @ y)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.pinv(ridge_matrix) @ (X_with_intercept.T @ y)
    
    intercept = coefficients[0]
    slopes = coefficients[1:]
    
    return slopes, intercept


def lasso_regression_fit(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> tuple:
    """
    Lasso регрессия - используем Ridge как приближение
    """
    return ridge_regression_fit(X, y, alpha)


def train_regression_model(X: np.ndarray, y: np.ndarray, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """
    Обучение регрессионной модели
    """
    if len(X) < 4:
        return {'error': f'Недостаточно данных: {len(X)} точек'}
    
    try:
        if model_type == 'linear':
            slopes, intercept = linear_regression_fit(X, y)
        elif model_type == 'ridge':
            alpha = kwargs.get('alpha', 1.0)
            slopes, intercept = ridge_regression_fit(X, y, alpha)
        elif model_type == 'lasso':
            alpha = kwargs.get('alpha', 1.0)
            slopes, intercept = lasso_regression_fit(X, y, alpha)
        else:
            slopes, intercept = linear_regression_fit(X, y)
        
        # Предсказания
        X_with_intercept = np.column_stack([np.ones(len(X)), X])
        y_pred = X_with_intercept @ np.concatenate([[intercept], slopes])
        metrics = calculate_metrics(y, y_pred)
        
        return {
            'success': True,
            'coefficients': slopes.tolist() if hasattr(slopes, 'tolist') else [float(slopes)],
            'intercept': float(intercept),
            'metrics': metrics
        }
    except Exception as e:
        return {'error': str(e)}


def predict_gdp_by_regression(df: pd.DataFrame, steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """
    Прогноз ВВП через регрессию от экспорта и импорта
    """
    if len(df) < 4:
        return {'error': 'Недостаточно данных для регрессии', 'forecast': []}
    
    try:
        # Преобразуем все значения в float
        df_float = df.copy()
        df_float['export'] = df_float['export'].astype(float)
        df_float['import'] = df_float['import'].astype(float)
        df_float['gdp'] = df_float['gdp'].astype(float)
        
        # 1. Прогноз экспорта
        export_series = df_float['export'].tolist()
        export_forecast = linear_trend(export_series, steps)
        
        # 2. Прогноз импорта
        import_series = df_float['import'].tolist()
        import_forecast = linear_trend(import_series, steps)
        
        if export_forecast.get('error') or import_forecast.get('error'):
            return {'error': 'Ошибка прогнозирования экспорта/импорта', 'forecast': []}
        
        # 3. Подготовка признаков
        X, y, feature_names = prepare_regression_features(df_float)
        
        # 4. Обучение модели
        regression = train_regression_model(X, y, model_type, **kwargs)
        
        if regression.get('error'):
            return {'error': regression['error'], 'forecast': []}
        
        # 5. Прогноз ВВП
        gdp_forecast = []
        coefficients = np.array(regression['coefficients'], dtype=float)
        intercept = float(regression['intercept'])
        
        for i in range(steps):
            pred_export = float(export_forecast['forecast'][i])
            pred_import = float(import_forecast['forecast'][i])
            
            features = np.array([
                pred_export, pred_import,
                pred_export * pred_import,
                pred_export ** 2,
                pred_import ** 2,
                pred_export - pred_import,
                pred_export + pred_import
            ], dtype=float)
            
            pred_gdp = intercept + np.sum(coefficients * features)
            gdp_forecast.append(float(pred_gdp))
        
        # Предсказания на исторических данных для графика
        X_with_intercept = np.column_stack([np.ones(len(X)), X])
        all_coeffs = np.concatenate([[intercept], coefficients])
        y_pred = (X_with_intercept @ all_coeffs).tolist()
        
        return {
            'success': True,
            'forecast': gdp_forecast,
            'metrics': regression['metrics'],
            'coefficients': regression['coefficients'],
            'intercept': regression['intercept'],
            'export_forecast': [float(x) for x in export_forecast['forecast']],
            'import_forecast': [float(x) for x in import_forecast['forecast']],
            'historical_predictions': [float(x) for x in y_pred]
        }
        
    except Exception as e:
        print(f"Error in predict_gdp_by_regression: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'forecast': []}