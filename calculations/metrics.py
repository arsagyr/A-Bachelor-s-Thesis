"""
Метрики качества для оценки моделей
"""

import numpy as np
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


def calculate_metrics(y_true, y_pred):
    """
    Расчет метрик качества модели
    
    Args:
        y_true: фактические значения
        y_pred: предсказанные значения
    
    Returns:
        dict: словарь с метриками (r2, mae, rmse, mape)
    """
    # Преобразуем в float
    y_true = np.array([float(x) for x in y_true])
    y_pred = np.array([float(x) for x in y_pred])
    
    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    
    # MAPE (избегаем деления на ноль)
    mask = y_true != 0
    if np.any(mask):
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = 100.0
    
    return {
        'r2': r2,
        'mae': mae,
        'rmse': rmse,
        'mape': mape
    }


def calculate_r2(y_true, y_pred):
    """Только R²"""
    y_true = np.array([float(x) for x in y_true])
    y_pred = np.array([float(x) for x in y_pred])
    return r2_score(y_true, y_pred)


def calculate_rmse(y_true, y_pred):
    """Только RMSE"""
    y_true = np.array([float(x) for x in y_true])
    y_pred = np.array([float(x) for x in y_pred])
    return np.sqrt(mean_squared_error(y_true, y_pred))


def calculate_mae(y_true, y_pred):
    """Только MAE"""
    y_true = np.array([float(x) for x in y_true])
    y_pred = np.array([float(x) for x in y_pred])
    return mean_absolute_error(y_true, y_pred)


def calculate_mape(y_true, y_pred):
    """Только MAPE"""
    y_true = np.array([float(x) for x in y_true])
    y_pred = np.array([float(x) for x in y_pred])
    mask = y_true != 0
    if np.any(mask):
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    return 100.0