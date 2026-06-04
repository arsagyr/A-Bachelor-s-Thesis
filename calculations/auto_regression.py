"""
Авторегрессионный анализ временных рядов с выбором моделей
"""

import numpy as np
from typing import List, Dict, Any
from sklearn.linear_model import Ridge, Lasso
from calculations.metrics import calculate_metrics

AVAILABLE_MODELS = {
    'linear': 'Линейная регрессия',
    'polynomial': 'Полиномиальная регрессия',
    'exponential': 'Экспоненциальная регрессия',
    'ridge': 'Ridge регрессия',
    'lasso': 'Lasso регрессия'
}


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


def linear_trend(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Линейный тренд"""
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
        'metrics': metrics,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': f"y = {intercept:.4f} + {slope:.4f}·x",
        'intercept': float(intercept),
        'slope': float(slope)
    }


def polynomial_trend(series: List[float], steps: int = 5, degree: int = 2) -> Dict[str, Any]:
    """
    Полиномиальный тренд
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        degree: степень полинома (2 или 3)
    """
    if len(series) < degree + 1:
        return {'error': f'Недостаточно данных для полинома степени {degree}', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(1, len(y) + 1)
    
    # Строим полиномиальные признаки
    X_poly = np.column_stack([x ** i for i in range(1, degree + 1)])
    X_with_intercept = np.column_stack([np.ones(len(x)), X_poly])
    
    # Решаем нормальные уравнения
    XTX = X_with_intercept.T @ X_with_intercept
    XTy = X_with_intercept.T @ y
    
    try:
        coefficients = np.linalg.solve(XTX, XTy)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.pinv(XTX) @ XTy
    
    intercept = coefficients[0]
    poly_coeffs = coefficients[1:]
    
    # Прогноз
    last_x = len(y)
    future_x = np.arange(last_x + 1, last_x + steps + 1)
    forecast_values = []
    
    for t in future_x:
        pred = intercept
        for power, coeff in enumerate(poly_coeffs, 1):
            pred += coeff * (t ** power)
        forecast_values.append(float(pred))
    
    # Предсказания на исторических данных
    y_pred = []
    for t in x:
        pred = intercept
        for power, coeff in enumerate(poly_coeffs, 1):
            pred += coeff * (t ** power)
        y_pred.append(pred)
    
    y_pred = np.array(y_pred)
    metrics = calculate_metrics(y, y_pred)
    
    # Формируем формулу
    formula = f"y = {intercept:.4f}"
    for power, coeff in enumerate(poly_coeffs, 1):
        if abs(coeff) > 1e-10:
            sign = '+' if coeff > 0 else '-'
            abs_coeff = abs(coeff)
            if power == 1:
                formula += f" {sign} {abs_coeff:.4f}·x"
            elif power == 2:
                formula += f" {sign} {abs_coeff:.4f}·x²"
            else:
                formula += f" {sign} {abs_coeff:.4f}·x^{power}"
    
    return {
        'success': True,
        'model_type': 'polynomial',
        'model_name': f"{AVAILABLE_MODELS['polynomial']} (степень {degree})",
        'forecast': forecast_values,
        'metrics': metrics,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'coefficients': [float(c) for c in poly_coeffs],
        'degree': degree
    }


def exponential_trend(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Экспоненциальный тренд"""
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}
    
    if any(x <= 0 for x in series):
        return {'error': 'Экспоненциальная регрессия требует положительных значений', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    log_y = np.log(y)
    x = np.arange(1, len(y) + 1)
    
    slope, intercept = linear_regression_ols(x, log_y)
    
    last_x = len(y)
    future_x = np.arange(last_x + 1, last_x + steps + 1)
    forecast_values = [np.exp(intercept + slope * t) for t in future_x]
    
    y_pred = np.exp(intercept + slope * x)
    metrics = calculate_metrics(y, y_pred)
    
    formula = f"y = e^({intercept:.4f} + {slope:.4f}·x)"
    
    return {
        'success': True,
        'model_type': 'exponential',
        'model_name': AVAILABLE_MODELS['exponential'],
        'forecast': forecast_values,
        'metrics': metrics,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'slope': float(slope)
    }


def ridge_trend(series: List[float], steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
    """
    Ridge регрессия (L2-регуляризация) с использованием sklearn
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        alpha: коэффициент регуляризации (чем больше, тем сильнее сжатие коэффициентов)
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(1, len(y) + 1).reshape(-1, 1)  # sklearn ожидает 2D массив
    
    # Обучаем модель Ridge
    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(x, y)
    
    intercept = model.intercept_
    slope = model.coef_[0]
    
    # Прогноз на будущие годы
    last_x = len(y)
    future_x = np.arange(last_x + 1, last_x + steps + 1).reshape(-1, 1)
    forecast_values = model.predict(future_x).tolist()
    
    # Предсказания на исторических данных
    y_pred = model.predict(x)
    metrics = calculate_metrics(y, y_pred)
    
    formula = f"y = {intercept:.4f} + {slope:.4f}·x (Ridge, α={alpha})"
    
    return {
        'success': True,
        'model_type': 'ridge',
        'model_name': f"{AVAILABLE_MODELS['ridge']} (α={alpha})",
        'forecast': forecast_values,
        'metrics': metrics,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'slope': float(slope),
        'alpha': alpha
    }


def lasso_trend(series: List[float], steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
    """
    Lasso регрессия (L1-регуляризация) с использованием sklearn
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        alpha: коэффициент регуляризации (чем больше, тем больше коэффициентов обнуляется)
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    x = np.arange(1, len(y) + 1).reshape(-1, 1)
    
    # Обучаем модель Lasso
    model = Lasso(alpha=alpha, fit_intercept=True, max_iter=10000)
    model.fit(x, y)
    
    intercept = model.intercept_
    slope = model.coef_[0]
    
    # Прогноз на будущие годы
    last_x = len(y)
    future_x = np.arange(last_x + 1, last_x + steps + 1).reshape(-1, 1)
    forecast_values = model.predict(future_x).tolist()
    
    # Предсказания на исторических данных
    y_pred = model.predict(x)
    metrics = calculate_metrics(y, y_pred)
    
    formula = f"y = {intercept:.4f} + {slope:.4f}·x (Lasso, α={alpha})"
    
    return {
        'success': True,
        'model_type': 'lasso',
        'model_name': f"{AVAILABLE_MODELS['lasso']} (α={alpha})",
        'forecast': forecast_values,
        'metrics': metrics,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': formula,
        'intercept': float(intercept),
        'slope': float(slope),
        'alpha': alpha
    }


def auto_regression_forecast(series: List[float], steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """Авторегрессионный прогноз с выбором модели"""
    degree = kwargs.get('degree', 2)
    alpha = kwargs.get('alpha', 1.0)
    
    if model_type == 'linear':
        return linear_trend(series, steps)
    elif model_type == 'polynomial':
        return polynomial_trend(series, steps, degree)
    elif model_type == 'exponential':
        return exponential_trend(series, steps)
    elif model_type == 'ridge':
        return ridge_trend(series, steps, alpha)
    elif model_type == 'lasso':
        return lasso_trend(series, steps, alpha)
    else:
        return linear_trend(series, steps)


def compare_auto_regression_models(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Сравнение всех моделей авторегрессии"""
    results = {}
    
    # Линейная модель
    linear_result = linear_trend(series, steps)
    if linear_result.get('success'):
        results['linear'] = linear_result
    
    # Полиномиальная модель (степень 2)
    if len(series) >= 3:
        poly2_result = polynomial_trend(series, steps, 2)
        if poly2_result.get('success'):
            results['polynomial_2'] = poly2_result
    
    # Полиномиальная модель (степень 3)
    if len(series) >= 4:
        poly3_result = polynomial_trend(series, steps, 3)
        if poly3_result.get('success'):
            results['polynomial_3'] = poly3_result
    
    # Экспоненциальная модель
    exp_result = exponential_trend(series, steps)
    if exp_result.get('success'):
        results['exponential'] = exp_result
    
    # Ridge модель
    ridge_result = ridge_trend(series, steps)
    if ridge_result.get('success'):
        results['ridge'] = ridge_result
    
    # Lasso модель
    lasso_result = lasso_trend(series, steps)
    if lasso_result.get('success'):
        results['lasso'] = lasso_result
    
    # Находим лучшую модель по R²
    best_model = None
    best_r2 = -float('inf')
    
    for name, result in results.items():
        r2 = result.get('metrics', {}).get('r2', -1)
        if r2 > best_r2:
            best_r2 = r2
            best_model = name
    
    return {
        'success': True,
        'all_models': results,
        'best_model': best_model,
        'best_model_name': results.get(best_model, {}).get('model_name', 'N/A'),
        'best_r2': best_r2
    }

def irwin_criterion(series: List[float], threshold: float = 3.0) -> Dict[str, Any]:
    """
    Поиск аномальных наблюдений во временном ряду по критерию Ирвина.
    
    Критерий Ирвина проверяет гипотезу об отсутствии грубых ошибок (выбросов).
    Вычисляется λ_t = |x_t - x_{t-1}| / σ_Δ, где σ_Δ — СКО разностей соседних уровней.
    Если λ_t > threshold, то наблюдение считается аномальным.
    
    Args:
        series: список исторических значений
        threshold: пороговое значение (обычно 3 для уровня значимости 0.05)
    
    Returns:
        словарь с результатами: аномальные индексы, значения, λ-статистики
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для критерия Ирвина (нужно минимум 3 точки)'}
    
    y = np.array([float(x) for x in series])
    n = len(y)
    
    # Разности между соседними уровнями
    diffs = np.diff(y)
    sigma_diff = np.std(diffs, ddof=1)  # несмещённое СКО
    
    if sigma_diff == 0:
        return {'error': 'Нулевое СКО разностей, все разности одинаковы'}
    
    # Расчёт λ для каждой точки (начиная со 2-й)
    lambda_vals = np.abs(diffs) / sigma_diff
    is_outlier = lambda_vals > threshold
    
    outliers = []
    for i in range(1, n):
        if is_outlier[i-1]:
            outliers.append({
                'index': i,  # 0-based индекс в series
                'value': float(y[i]),
                'lambda': float(lambda_vals[i-1]),
                'prev_value': float(y[i-1])
            })
    
    return {
        'success': True,
        'threshold': threshold,
        'sigma_diff': float(sigma_diff),
        'outliers': outliers,
        'outlier_count': len(outliers),
        'all_lambda': lambda_vals.tolist()
    }

def t_test_slope(series: List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """
    Проверка значимости наклона линейного тренда по критерию Стьюдента.
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных'}
    
    y = np.array([float(x) for x in series])
    x = np.arange(1, len(y) + 1)
    n = len(x)
    
    slope, intercept = linear_regression_ols(x, y)
    y_pred = intercept + slope * x
    residuals = y - y_pred
    residual_var = np.sum(residuals ** 2) / (n - 2)
    se_slope = np.sqrt(residual_var / np.sum((x - np.mean(x)) ** 2))
    
    t_stat = slope / se_slope
    # Двусторонний тест
    from scipy import stats
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-2))
    significant = p_value < alpha
    
    return {
        'slope': slope,
        'std_error': se_slope,
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': significant,
        'alpha': alpha
    }