"""
Авторегрессионный анализ временных рядов с выбором моделей
"""

import numpy as np
from typing import List, Dict, Any
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from calculations.metrics import calculate_metrics
from scipy import stats

AVAILABLE_MODELS = {
    'linear': 'Линейная регрессия',
    'polynomial': 'Полиномиальная регрессия',
    'exponential': 'Экспоненциальная регрессия',
    'ridge': 'Ridge регрессия',
    'lasso': 'Lasso регрессия'
}
 
def fit_linear_model(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str = 'linear',
    alpha: float = 1.0
) -> tuple:
    """
    Единая точка входа для подбора линейной / Ridge / Lasso модели через sklearn.

    Args:
        X: матрица признаков формы (n_samples, n_features)
        y: целевая переменная
        model_type: 'linear' | 'ridge' | 'lasso'
        alpha: коэффициент регуляризации (игнорируется для 'linear')

    Returns:
        (slopes, intercept) — коэффициенты при признаках и свободный член
    """
    if model_type == 'ridge':
        model = Ridge(alpha=alpha, fit_intercept=True)
    elif model_type == 'lasso':
        model = Lasso(alpha=alpha, fit_intercept=True, max_iter=10000)
    else:
        model = LinearRegression(fit_intercept=True)

    model.fit(X, y)
    slopes = model.coef_
    intercept = model.intercept_
    return slopes, intercept


  
# Тренды 

def linear_trend(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Линейный тренд y = a + b·t (через sklearn LinearRegression)."""
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}

    y = np.array([float(v) for v in series])
    x = np.arange(1, len(y) + 1).reshape(-1, 1)

    slopes, intercept = fit_linear_model(x, y, model_type='linear')
    slope = float(slopes[0])
    intercept = float(intercept)

    future_x = np.arange(len(y) + 1, len(y) + steps + 1).reshape(-1, 1)
    y_pred = (intercept + slopes * x).ravel()
    forecast_values = (intercept + slopes * future_x).ravel().tolist()
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
        'intercept': intercept,
        'slope': slope,
    }


def polynomial_trend(series: List[float], steps: int = 5, degree: int = 2) -> Dict[str, Any]:
    """Полиномиальный тренд степени degree."""
    if len(series) < degree + 1:
        return {'error': f'Недостаточно данных для полинома степени {degree}', 'forecast': []}

    y = np.array([float(v) for v in series])
    x = np.arange(1, len(y) + 1)

    X_poly = np.column_stack([x ** i for i in range(1, degree + 1)])
    X_with_intercept = np.column_stack([np.ones(len(x)), X_poly])

    XTX = X_with_intercept.T @ X_with_intercept
    XTy = X_with_intercept.T @ y
    try:
        coefficients = np.linalg.solve(XTX, XTy)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.pinv(XTX) @ XTy

    intercept = coefficients[0]
    poly_coeffs = coefficients[1:]

    def _predict(t_vals):
        result = []
        for t in t_vals:
            pred = intercept + sum(c * t ** p for p, c in enumerate(poly_coeffs, 1))
            result.append(float(pred))
        return result

    future_x = np.arange(len(y) + 1, len(y) + steps + 1)
    forecast_values = _predict(future_x)
    y_pred = np.array(_predict(x))
    metrics = calculate_metrics(y, y_pred)

    formula = f"y = {intercept:.4f}"
    for power, coeff in enumerate(poly_coeffs, 1):
        if abs(coeff) > 1e-10:
            sign = '+' if coeff > 0 else '-'
            suffix = 'x' if power == 1 else ('x²' if power == 2 else f'x^{power}')
            formula += f" {sign} {abs(coeff):.4f}·{suffix}"

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
        'degree': degree,
    }


def exponential_trend(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Экспоненциальный тренд y = e^(a + b·t)."""
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}
    if any(v <= 0 for v in series):
        return {'error': 'Экспоненциальная регрессия требует положительных значений', 'forecast': []}

    y = np.array([float(v) for v in series])
    log_y = np.log(y)
    x = np.arange(1, len(y) + 1).reshape(-1, 1)

    slopes, intercept = fit_linear_model(x, log_y, model_type='linear')
    slope = float(slopes[0])
    intercept = float(intercept)

    future_x = np.arange(len(y) + 1, len(y) + steps + 1)
    forecast_values = [float(np.exp(intercept + slope * t)) for t in future_x]
    y_pred = np.exp(intercept + slope * np.arange(1, len(y) + 1))
    metrics = calculate_metrics(y, y_pred)

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
        'formula': f"y = e^({intercept:.4f} + {slope:.4f}·x)",
        'intercept': intercept,
        'slope': slope,
    }


def _regularized_trend(
    series: List[float],
    steps: int,
    model_type: str,   # 'ridge' | 'lasso'
    alpha: float,
) -> Dict[str, Any]:
    """
    Унифицированная реализация Ridge / Lasso тренда по одной переменной.
    Используется внутри ridge_trend и lasso_trend.
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}

    y = np.array([float(v) for v in series])
    x = np.arange(1, len(y) + 1).reshape(-1, 1)

    slopes, intercept = fit_linear_model(x, y, model_type=model_type, alpha=alpha)
    slope = float(slopes[0])
    intercept = float(intercept)

    future_x = np.arange(len(y) + 1, len(y) + steps + 1).reshape(-1, 1)

    # Используем ту же модель для предсказания, пересоздавать не нужно —
    # fit_linear_model возвращает коэффициенты, считаем вручную.
    y_pred = intercept + slope * np.arange(1, len(y) + 1)
    forecast_values = (intercept + slope * future_x.ravel()).tolist()
    metrics = calculate_metrics(y, y_pred)

    label = 'Ridge' if model_type == 'ridge' else 'Lasso'
    return {
        'success': True,
        'model_type': model_type,
        'model_name': f"{AVAILABLE_MODELS[model_type]} (α={alpha})",
        'forecast': forecast_values,
        'metrics': metrics,
        'r2': metrics['r2'],
        'rmse': metrics['rmse'],
        'mae': metrics['mae'],
        'mape': metrics['mape'],
        'formula': f"y = {intercept:.4f} + {slope:.4f}·x ({label}, α={alpha})",
        'intercept': intercept,
        'slope': slope,
        'alpha': alpha,
    }


def ridge_trend(series: List[float], steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
    """Ridge регрессия (L2) по одной переменной."""
    return _regularized_trend(series, steps, 'ridge', alpha)


def lasso_trend(series: List[float], steps: int = 5, alpha: float = 1.0) -> Dict[str, Any]:
    """Lasso регрессия (L1) по одной переменной."""
    return _regularized_trend(series, steps, 'lasso', alpha)


# ---------------------------------------------------------------------------
# Вспомогательные функции (критерий Ирвина, t-критерий наклона)
# ---------------------------------------------------------------------------

def irwin_criterion(series: List[float], threshold: float = 3.0) -> Dict[str, Any]:
    """
    Поиск аномальных наблюдений по критерию Ирвина.
    λ_t = |x_t - x_{t-1}| / σ_Δ; аномалия если λ_t > threshold.
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для критерия Ирвина (нужно минимум 3 точки)'}

    y = np.array([float(v) for v in series])
    diffs = np.diff(y)
    sigma_diff = np.std(diffs, ddof=1)

    if sigma_diff == 0:
        return {'error': 'Нулевое СКО разностей, все разности одинаковы'}

    lambda_vals = np.abs(diffs) / sigma_diff
    outliers = [
        {
            'index': i,
            'value': float(y[i]),
            'lambda': float(lambda_vals[i - 1]),
            'prev_value': float(y[i - 1]),
        }
        for i in range(1, len(y))
        if lambda_vals[i - 1] > threshold
    ]

    return {
        'success': True,
        'threshold': threshold,
        'sigma_diff': float(sigma_diff),
        'outliers': outliers,
        'outlier_count': len(outliers),
        'all_lambda': lambda_vals.tolist(),
    }


def t_test_slope(series: List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Проверка значимости наклона линейного тренда по критерию Стьюдента."""
    if len(series) < 3:
        return {'error': 'Недостаточно данных'}

    y = np.array([float(v) for v in series])
    x = np.arange(1, len(y) + 1).reshape(-1, 1)
    n = len(y)

    slopes, intercept = fit_linear_model(x, y, model_type='linear')
    slope = float(slopes[0])
    intercept = float(intercept)

    x_1d = x.ravel()
    y_pred = intercept + slope * x_1d
    residuals = y - y_pred
    residual_var = np.sum(residuals ** 2) / (n - 2)
    se_slope = np.sqrt(residual_var / np.sum((x_1d - np.mean(x_1d)) ** 2))

    t_stat = slope / se_slope
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 2))

    return {
        'slope': slope,
        'std_error': se_slope,
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': bool(p_value < alpha),
        'alpha': alpha,
    }


# ---------------------------------------------------------------------------
# Публичный API модуля
# ---------------------------------------------------------------------------

def auto_regression_forecast(
    series: List[float],
    steps: int = 5,
    model_type: str = 'linear',
    **kwargs,
) -> Dict[str, Any]:
    """Авторегрессионный прогноз с выбором модели."""
    degree = kwargs.get('degree', 2)
    alpha = kwargs.get('alpha', 1.0)

    dispatch = {
        'linear': lambda: linear_trend(series, steps),
        'polynomial': lambda: polynomial_trend(series, steps, degree),
        'exponential': lambda: exponential_trend(series, steps),
        'ridge': lambda: ridge_trend(series, steps, alpha),
        'lasso': lambda: lasso_trend(series, steps, alpha),
    }
    return dispatch.get(model_type, dispatch['linear'])()


def compare_auto_regression_models(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """Сравнение всех моделей авторегрессии; выбор лучшей по R²."""
    candidates = {
        'linear': lambda: linear_trend(series, steps),
        'exponential': lambda: exponential_trend(series, steps),
        'ridge': lambda: ridge_trend(series, steps),
        'lasso': lambda: lasso_trend(series, steps),
    }
    if len(series) >= 3:
        candidates['polynomial_2'] = lambda: polynomial_trend(series, steps, 2)
    if len(series) >= 4:
        candidates['polynomial_3'] = lambda: polynomial_trend(series, steps, 3)

    results = {name: fn() for name, fn in candidates.items() if candidates[name]().get('success')}

    best_model = max(results, key=lambda k: results[k].get('metrics', {}).get('r2', -1), default=None)

    return {
        'success': True,
        'all_models': results,
        'best_model': best_model,
        'best_model_name': results.get(best_model, {}).get('model_name', 'N/A'),
        'best_r2': results.get(best_model, {}).get('metrics', {}).get('r2', 0),
    }