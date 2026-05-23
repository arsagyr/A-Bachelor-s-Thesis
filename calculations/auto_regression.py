"""
Авторегрессионный анализ временных рядов с выбором моделей
"""

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
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


def linear_auto_regression(series: List[float], steps: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Линейная авторегрессия (тренд)
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
    
    Returns:
        dict: прогноз и метрики качества
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза (минимум 3 точки)', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    X = np.arange(len(y)).reshape(-1, 1)
    
    model = LinearRegression()
    model.fit(X, y)
    
    future_X = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    forecast = model.predict(future_X)
    forecast_values = [float(x) for x in forecast.tolist()]
    
    y_pred = model.predict(X)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t"
    
    return {
        'success': True,
        'model_type': 'linear',
        'model_name': AVAILABLE_MODELS['linear'],
        'forecast': forecast_values,
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'formula': formula,
        'intercept': float(model.intercept_),
        'slope': float(model.coef_[0]),
        'model': model
    }


def polynomial_auto_regression(series: List[float], steps: int = 5, degree: int = 2, **kwargs) -> Dict[str, Any]:
    """
    Полиномиальная авторегрессия
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        degree: степень полинома (2 или 3)
    """
    if len(series) < degree + 1:
        return {'error': f'Недостаточно данных для полинома степени {degree} (нужно минимум {degree+1} точек)', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    X = np.arange(len(y)).reshape(-1, 1)
    
    poly = PolynomialFeatures(degree=degree, include_bias=False)
    X_poly = poly.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_poly, y)
    
    future_X = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    future_X_poly = poly.transform(future_X)
    forecast = model.predict(future_X_poly)
    forecast_values = [float(x) for x in forecast.tolist()]
    
    y_pred = model.predict(X_poly)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    # Формируем формулу
    formula = f"y = {model.intercept_:.4f}"
    for i, coef in enumerate(model.coef_):
        if i == 0:
            formula += f" + {coef:.4f}·t"
        elif i == 1:
            formula += f" + {coef:.4f}·t²"
        else:
            formula += f" + {coef:.4f}·t^{i+1}"
    
    return {
        'success': True,
        'model_type': 'polynomial',
        'model_name': f"{AVAILABLE_MODELS['polynomial']} (степень {degree})",
        'forecast': forecast_values,
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'formula': formula,
        'intercept': float(model.intercept_),
        'coefficients': model.coef_.tolist(),
        'degree': degree,
        'model': model,
        'poly': poly
    }


def exponential_auto_regression(series: List[float], steps: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Экспоненциальная авторегрессия (для данных с экспоненциальным ростом)
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза', 'forecast': []}
    
    # Проверяем, что все значения положительные (для логарифма)
    if any(x <= 0 for x in series):
        return {'error': 'Экспоненциальная регрессия требует положительных значений', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    log_y = np.log(y)
    X = np.arange(len(y)).reshape(-1, 1)
    
    model = LinearRegression()
    model.fit(X, log_y)
    
    future_X = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    log_forecast = model.predict(future_X)
    forecast_values = [float(np.exp(x)) for x in log_forecast.tolist()]
    
    log_y_pred = model.predict(X)
    y_pred = np.exp(log_y_pred)
    
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    formula = f"y = e^({model.intercept_:.4f} + {model.coef_[0]:.4f}·t)"
    
    return {
        'success': True,
        'model_type': 'exponential',
        'model_name': AVAILABLE_MODELS['exponential'],
        'forecast': forecast_values,
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'formula': formula,
        'intercept': float(model.intercept_),
        'slope': float(model.coef_[0]),
        'model': model
    }


def ridge_auto_regression(series: List[float], steps: int = 5, alpha: float = 1.0, **kwargs) -> Dict[str, Any]:
    """
    Ridge авторегрессия (L2-регуляризация)
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        alpha: параметр регуляризации
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза', 'forecast': []}
    
    from sklearn.preprocessing import StandardScaler
    
    y = np.array([float(x) for x in series])
    X = np.arange(len(y)).reshape(-1, 1)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = Ridge(alpha=alpha)
    model.fit(X_scaled, y)
    
    future_X = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    future_X_scaled = scaler.transform(future_X)
    forecast = model.predict(future_X_scaled)
    forecast_values = [float(x) for x in forecast.tolist()]
    
    y_pred = model.predict(X_scaled)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t (Ridge, α={alpha})"
    
    return {
        'success': True,
        'model_type': 'ridge',
        'model_name': f"{AVAILABLE_MODELS['ridge']} (α={alpha})",
        'forecast': forecast_values,
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'formula': formula,
        'intercept': float(model.intercept_),
        'slope': float(model.coef_[0]),
        'alpha': alpha,
        'model': model,
        'scaler': scaler
    }


def lasso_auto_regression(series: List[float], steps: int = 5, alpha: float = 1.0, **kwargs) -> Dict[str, Any]:
    """
    Lasso авторегрессия (L1-регуляризация)
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        alpha: параметр регуляризации
    """
    if len(series) < 3:
        return {'error': 'Недостаточно данных для прогноза', 'forecast': []}
    
    from sklearn.preprocessing import StandardScaler
    
    y = np.array([float(x) for x in series])
    X = np.arange(len(y)).reshape(-1, 1)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = Lasso(alpha=alpha)
    model.fit(X_scaled, y)
    
    future_X = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    future_X_scaled = scaler.transform(future_X)
    forecast = model.predict(future_X_scaled)
    forecast_values = [float(x) for x in forecast.tolist()]
    
    y_pred = model.predict(X_scaled)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t (Lasso, α={alpha})"
    
    return {
        'success': True,
        'model_type': 'lasso',
        'model_name': f"{AVAILABLE_MODELS['lasso']} (α={alpha})",
        'forecast': forecast_values,
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'formula': formula,
        'intercept': float(model.intercept_),
        'slope': float(model.coef_[0]),
        'alpha': alpha,
        'model': model,
        'scaler': scaler
    }


def auto_regression_forecast(series: List[float], steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """Авторегрессионный прогноз с выбором модели (возвращает объекты моделей)"""
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
    else:
        return linear_auto_regression(series, steps)


def linear_auto_regression(series: List[float], steps: int = 5, **kwargs) -> Dict[str, Any]:
    """Линейная авторегрессия (возвращает объект модели)"""
    if len(series) < 3:
        return {'error': 'Недостаточно данных', 'forecast': []}
    
    y = np.array([float(x) for x in series])
    X = np.arange(len(y)).reshape(-1, 1)
    
    model = LinearRegression()  # Объект модели остаётся
    model.fit(X, y)
    
    future_X = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    forecast = model.predict(future_X)
    forecast_values = [float(x) for x in forecast.tolist()]
    
    y_pred = model.predict(X)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    formula = f"y = {model.intercept_:.4f} + {model.coef_[0]:.4f}·t"
    
    return {
        'success': True,
        'model_type': 'linear',
        'model_name': AVAILABLE_MODELS['linear'],
        'forecast': forecast_values,
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'formula': formula,
        'intercept': float(model.intercept_),
        'slope': float(model.coef_[0]),
        'model': model  # Объект модели остаётся для возможного использования
    }

def compare_auto_regression_models(series: List[float], steps: int = 5) -> Dict[str, Any]:
    """
    Сравнение всех моделей авторегрессии
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
    
    Returns:
        dict: результаты всех моделей и лучшая модель
    """
    results = {}
    models_to_try = ['linear', 'exponential', 'ridge', 'lasso']
    
    # Добавляем полиномиальные модели
    if len(series) >= 3:
        models_to_try.append('polynomial_2')
    if len(series) >= 4:
        models_to_try.append('polynomial_3')
    
    for model in models_to_try:
        if model == 'polynomial_2':
            result = polynomial_auto_regression(series, steps, degree=2)
            results['polynomial_2'] = result
        elif model == 'polynomial_3':
            result = polynomial_auto_regression(series, steps, degree=3)
            results['polynomial_3'] = result
        else:
            result = auto_regression_forecast(series, steps, model_type=model)
            results[model] = result
    
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
        'best_r2': best_r2,
        'steps': steps
    }


def auto_regression_with_confidence(series: List[float], steps: int = 5, 
                                     model_type: str = 'linear',
                                     confidence_level: float = 0.95,
                                     **kwargs) -> Dict[str, Any]:
    """
    Авторегрессионный прогноз с доверительными интервалами
    
    Args:
        series: список исторических значений
        steps: количество шагов прогноза
        model_type: тип модели
        confidence_level: уровень доверия (0.95 = 95%)
    """
    result = auto_regression_forecast(series, steps, model_type, **kwargs)
    
    if not result.get('success'):
        return result
    
    # Расчет доверительных интервалов
    y = np.array([float(x) for x in series])
    
    if model_type == 'polynomial':
        X = np.arange(len(y)).reshape(-1, 1)
        poly = PolynomialFeatures(degree=result.get('degree', 2), include_bias=False)
        X_poly = poly.fit_transform(X)
        y_pred = result['model'].predict(X_poly)
    elif model_type in ['ridge', 'lasso']:
        X = np.arange(len(y)).reshape(-1, 1)
        X_scaled = result['scaler'].transform(X)
        y_pred = result['model'].predict(X_scaled)
    else:
        X = np.arange(len(y)).reshape(-1, 1)
        y_pred = result['model'].predict(X)
    
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