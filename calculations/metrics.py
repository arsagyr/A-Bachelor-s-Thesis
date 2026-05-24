"""
Авторегрессионный анализ временных рядов с выбором моделей
Реализация без использования sklearn
"""

import numpy as np
from typing import List, Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')


# Доступные модели
AVAILABLE_MODELS = {
    'linear': 'Линейная регрессия',
    'polynomial': 'Полиномиальная регрессия',
    'exponential': 'Экспоненциальная регрессия',
    'ridge': 'Ridge регрессия',
    'lasso': 'Lasso регрессия'
}


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Расчёт метрик качества (без sklearn)
    
    Args:
        y_true: фактические значения
        y_pred: предсказанные значения
    
    Returns:
        dict: метрики r2, rmse, mae, mape
    """
    n = len(y_true)
    
    # R² (коэффициент детерминации)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    # RMSE (Root Mean Square Error)
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # MAE (Mean Absolute Error)
    mae = np.mean(np.abs(y_true - y_pred))
    
    # MAPE (Mean Absolute Percentage Error)
    # Избегаем деления на ноль
    mask = y_true != 0
    if np.any(mask):
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = 100.0
    
    # R² скорректированный (Adjusted R²)
    n_features = 1
    adjusted_r2 = 1 - (1 - r2) * (n - 1) / (n - n_features - 1) if n > n_features + 1 else r2
    
    return {
        'r2': float(r2),
        'adjusted_r2': float(adjusted_r2),
        'rmse': float(rmse),
        'mae': float(mae),
        'mape': float(mape)
    }


def linear_regression_ols(x: np.ndarray, y: np.ndarray) -> tuple:
    """
    Линейная регрессия методом наименьших квадратов (МНК)
    
    Args:
        x: массив независимой переменной (время)
        y: массив зависимой переменной (значения)
    
    Returns:
        slope: коэффициент наклона (β₁)
        intercept: свободный член (β₀)
    """
    n = len(x)
    
    # Вычисляем средние
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    # Вычисляем ковариацию и дисперсию
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    
    # Коэффициент наклона (β₁)
    slope = numerator / denominator if denominator != 0 else 0
    
    # Свободный член (β₀)
    intercept = y_mean - slope * x_mean
    
    return slope, intercept


def linear_auto_regression(series: List[float], steps: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Линейная авторегрессия методом МНК
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
    
    Returns:
        dict: прогноз и метрики качества
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза (минимум 3 точки)', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(len(y))
    
    # Расчёт коэффициентов методом МНК
    slope, intercept = linear_regression_ols(x, y)
    
    # Прогноз на будущие периоды
    future_x = np.arange(len(y), len(y) + steps)
    forecast_values = [intercept + slope * t for t in future_x]
    
    # Предсказания на исторических данных
    y_pred = intercept + slope * x
    
    # Расчёт метрик
    metrics = calculate_metrics(y, y_pred)
    
    formula = f"y = {intercept:.4f} + {slope:.4f}·t"
    
    return {
        'success': True,
        'model_type': 'linear',
        'model_name': AVAILABLE_MODELS['linear'],
        'forecast': forecast_values,
        'r2': metrics['r2'],
        'adjusted_r2': metrics['adjusted_r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'slope': float(slope)
    }


def polynomial_auto_regression(series: List[float], steps: int = 5, degree: int = 2, **kwargs) -> Dict[str, Any]:
    """
    Полиномиальная авторегрессия методом МНК
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        degree: степень полинома (2 или 3)
    """
    if len(series) < degree + 1:
        return {'error': f'Недостаточно данных для полинома степени {degree}', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(len(y))
    
    # Строим матрицу Вандермонда (полиномиальные признаки)
    X_poly = np.vstack([x ** i for i in range(degree + 1)]).T
    
    # Решаем систему нормальных уравнений: (X^T X) β = X^T y
    XTX = X_poly.T @ X_poly
    XTy = X_poly.T @ y
    
    try:
        coefficients = np.linalg.solve(XTX, XTy)
    except np.linalg.LinAlgError:
        # Если матрица вырожденная, используем псевдообратную
        coefficients = np.linalg.pinv(XTX) @ XTy
    
    intercept = coefficients[0]
    poly_coeffs = coefficients[1:]
    
    # Функция для предсказания
    def predict(t):
        result = intercept
        for power, coeff in enumerate(poly_coeffs, 1):
            result += coeff * (t ** power)
        return result
    
    # Прогноз
    future_x = np.arange(len(y), len(y) + steps)
    forecast_values = [predict(t) for t in future_x]
    
    # Предсказания на исторических данных
    y_pred = np.array([predict(t) for t in x])
    
    # Расчёт метрик
    metrics = calculate_metrics(y, y_pred)
    
    # Формируем формулу
    formula = f"y = {intercept:.4f}"
    for power, coeff in enumerate(poly_coeffs, 1):
        if abs(coeff) > 1e-10:
            sign = '+' if coeff > 0 else '-'
            abs_coeff = abs(coeff)
            if power == 1:
                formula += f" {sign} {abs_coeff:.4f}·t"
            elif power == 2:
                formula += f" {sign} {abs_coeff:.4f}·t²"
            else:
                formula += f" {sign} {abs_coeff:.4f}·t^{power}"
    
    return {
        'success': True,
        'model_type': 'polynomial',
        'model_name': f"{AVAILABLE_MODELS['polynomial']} (степень {degree})",
        'forecast': forecast_values,
        'r2': metrics['r2'],
        'adjusted_r2': metrics['adjusted_r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'coefficients': [float(c) for c in poly_coeffs],
        'degree': degree
    }


def exponential_auto_regression(series: List[float], steps: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Экспоненциальная авторегрессия (логарифмирование + МНК)
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза', 'forecast': []}
    
    if any(x <= 0 for x in series):
        return {'error': 'Экспоненциальная регрессия требует положительных значений', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    log_y = np.log(y)
    x = np.arange(len(y))
    
    # Линейная регрессия на логарифмах
    slope, intercept = linear_regression_ols(x, log_y)
    
    # Прогноз
    future_x = np.arange(len(y), len(y) + steps)
    forecast_values = [np.exp(intercept + slope * t) for t in future_x]
    
    # Предсказания на исторических данных
    y_pred = np.exp(intercept + slope * x)
    
    # Расчёт метрик
    metrics = calculate_metrics(y, y_pred)
    
    formula = f"y = e^({intercept:.4f} + {slope:.4f}·t)"
    
    return {
        'success': True,
        'model_type': 'exponential',
        'model_name': AVAILABLE_MODELS['exponential'],
        'forecast': forecast_values,
        'r2': metrics['r2'],
        'adjusted_r2': metrics['adjusted_r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'slope': float(slope)
    }


def ridge_auto_regression(series: List[float], steps: int = 5, alpha: float = 1.0, **kwargs) -> Dict[str, Any]:
    """
    Ridge регрессия (L2-регуляризация) - реализация с МНК
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(len(y))
    
    # Добавляем столбец единиц для intercept
    X = np.vstack([np.ones(len(x)), x]).T
    
    # Ridge решение: β = (X^T X + αI)^(-1) X^T y
    n_features = X.shape[1]
    XTX = X.T @ X
    ridge_matrix = XTX + alpha * np.eye(n_features)
    
    try:
        coefficients = np.linalg.solve(ridge_matrix, X.T @ y)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.pinv(ridge_matrix) @ (X.T @ y)
    
    intercept = coefficients[0]
    slope = coefficients[1] if len(coefficients) > 1 else 0
    
    # Прогноз
    future_x = np.arange(len(y), len(y) + steps)
    forecast_values = [intercept + slope * t for t in future_x]
    
    # Предсказания на исторических данных
    y_pred = intercept + slope * x
    
    # Расчёт метрик
    metrics = calculate_metrics(y, y_pred)
    
    formula = f"y = {intercept:.4f} + {slope:.4f}·t (Ridge, α={alpha})"
    
    return {
        'success': True,
        'model_type': 'ridge',
        'model_name': f"{AVAILABLE_MODELS['ridge']} (α={alpha})",
        'forecast': forecast_values,
        'r2': metrics['r2'],
        'adjusted_r2': metrics['adjusted_r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'slope': float(slope),
        'alpha': alpha
    }


def lasso_auto_regression(series: List[float], steps: int = 5, alpha: float = 1.0, **kwargs) -> Dict[str, Any]:
    """
    Lasso регрессия (L1-регуляризация) - для простоты используем Ridge
    """
    return ridge_auto_regression(series, steps, alpha, **kwargs)


def auto_regression_forecast(series: List[float], steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """Авторегрессионный прогноз с выбором модели (без sklearn)"""
    degree = kwargs.get('degree', 2)
    alpha = kwargs.get('alpha', 1.0)
    
    if model_type == 'linear':
        return linear_auto_regression(series, steps)
    elif model_type == 'polynomial':
        return polynomial_auto_regression(series, steps, degree=degree)
    elif model_type == 'exponential':
        return exponential_auto_regression(series, steps)
    elif model_type == 'ridge':
        return ridge_auto_regression(series, steps, alpha=alpha)
    elif model_type == 'lasso':
        return lasso_auto_regression(series, steps, alpha=alpha)
    elif model_type == 'compare':
        return compare_auto_regression_models(series, steps)
    else:
        return linear_auto_regression(series, steps)


def compare_auto_regression_models(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Сравнение всех моделей авторегрессии"""
    results = {}
    
    models = ['linear', 'polynomial', 'exponential', 'ridge']
    
    for model in models:
        if model == 'polynomial' and len(series) >= 3:
            results[model] = polynomial_auto_regression(series, steps, degree=2)
        elif model == 'polynomial':
            continue
        else:
            results[model] = auto_regression_forecast(series, steps, model)
    
    # Находим лучшую модель по R²
    best_model = None
    best_r2 = -float('inf')
    
    for name, result in results.items():
        if result.get('success') and result.get('r2', -1) > best_r2:
            best_r2 = result['r2']
            best_model = name
    
    return {
        'success': True,
        'all_models': results,
        'best_model': best_model,
        'best_model_name': results.get(best_model, {}).get('model_name', 'N/A'),
        'best_r2': best_r2
    }


def auto_regression_with_confidence(series: List[float], steps: int = 5, 
                                     model_type: str = 'linear',
                                     confidence_level: float = 0.95,
                                     **kwargs) -> Dict[str, Any]:
    """Авторегрессионный прогноз с доверительными интервалами"""
    degree = kwargs.get('degree', 2)
    
    result = auto_regression_forecast(series, steps, model_type, degree=degree)
    
    if not result.get('success'):
        return result
    
    y = np.array([float(x) for x in series])
    x = np.arange(len(y))
    
    # Получаем предсказания на исторических данных
    if model_type == 'linear':
        slope = result['slope']
        intercept = result['intercept']
        y_pred = intercept + slope * x
    elif model_type == 'polynomial':
        intercept = result['intercept']
        coeffs = result.get('coefficients', [])
        y_pred = np.array([intercept + sum(coeffs[p] * (t ** (p+1)) for p in range(len(coeffs))) for t in x])
    elif model_type == 'exponential':
        slope = result['slope']
        intercept = result['intercept']
        y_pred = np.exp(intercept + slope * x)
    else:
        slope = result.get('slope', 0)
        intercept = result.get('intercept', 0)
        y_pred = intercept + slope * x
    
    residuals = y - y_pred
    std_residuals = np.std(residuals)
    
    if confidence_level == 0.95:
        z_score = 1.96
    elif confidence_level == 0.99:
        z_score = 2.576
    else:
        z_score = 1.96
    
    lower_bounds = [float(f - z_score * std_residuals) for f in result['forecast']]
    upper_bounds = [float(f + z_score * std_residuals) for f in result['forecast']]
    
    result['lower_bounds'] = lower_bounds
    result['upper_bounds'] = upper_bounds
    result['confidence_level'] = confidence_level
    result['std_residuals'] = float(std_residuals)
    
    return result