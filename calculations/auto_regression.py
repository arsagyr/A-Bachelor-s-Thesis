"""
Авторегрессионный анализ временных рядов
Реализация без использования sklearn
"""

import numpy as np
from typing import List, Dict, Any


AVAILABLE_MODELS = {
    'linear': 'Линейная регрессия',
    'polynomial': 'Полиномиальная регрессия',
    'exponential': 'Экспоненциальная регрессия'
}


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


def linear_regression_ols(x: np.ndarray, y: np.ndarray) -> tuple:
    """Линейная регрессия методом наименьших квадратов"""
    n = len(x)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_x2 = np.sum(x ** 2)
    
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
    intercept = (sum_y - slope * sum_x) / n
    
    return slope, intercept


def linear_auto_regression(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Линейная авторегрессия"""
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(1, len(y) + 1)
    
    slope, intercept = linear_regression_ols(x, y)
    
    last_x = len(y)
    future_x = np.arange(last_x + 1, last_x + steps + 1)
    forecast_values = [intercept + slope * t for t in future_x]
    
    y_pred = intercept + slope * x
    metrics = calculate_metrics(y, y_pred)
    
    return {
        'success': True,
        'model_type': 'linear',
        'model_name': AVAILABLE_MODELS['linear'],
        'forecast': forecast_values,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': f"y = {intercept:.4f} + {slope:.4f}·x",
        'intercept': float(intercept),
        'slope': float(slope)
    }


def auto_regression_forecast(series: List[float], steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """Авторегрессионный прогноз с выбором модели"""
    if model_type == 'linear':
        return linear_auto_regression(series, steps)
    else:
        return linear_auto_regression(series, steps)