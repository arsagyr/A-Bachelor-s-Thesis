"""
Регрессионные модели для анализа экономических данных
"""

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from calculations.metrics import calculate_metrics
from calculations.preprocessing import prepare_regression_features


def linear_regression_analysis(X, y, feature_names):
    """
    Линейная регрессия
    
    Args:
        X: матрица признаков
        y: целевая переменная
        feature_names: названия признаков
    
    Returns:
        dict: результаты анализа
    """
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    metrics = calculate_metrics(y, y_pred)
    
    return {
        'name': 'Линейная регрессия',
        'model': model,
        'metrics': metrics,
        'coefficients': model.coef_,
        'intercept': model.intercept_
    }


def ridge_regression_analysis(X, y, feature_names, alpha=1.0):
    """
    Ridge регрессия (L2-регуляризация)
    
    Args:
        X: матрица признаков
        y: целевая переменная
        feature_names: названия признаков
        alpha: параметр регуляризации
    
    Returns:
        dict: результаты анализа
    """
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = Ridge(alpha=alpha)
    model.fit(X_scaled, y)
    y_pred = model.predict(X_scaled)
    metrics = calculate_metrics(y, y_pred)
    
    return {
        'name': f'Ridge регрессия (α={alpha})',
        'model': model,
        'metrics': metrics,
        'coefficients': model.coef_,
        'intercept': model.intercept_,
        'scaler': scaler
    }


def lasso_regression_analysis(X, y, feature_names, alpha=1.0):
    """
    Lasso регрессия (L1-регуляризация)
    
    Args:
        X: матрица признаков
        y: целевая переменная
        feature_names: названия признаков
        alpha: параметр регуляризации
    
    Returns:
        dict: результаты анализа
    """
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = Lasso(alpha=alpha)
    model.fit(X_scaled, y)
    y_pred = model.predict(X_scaled)
    metrics = calculate_metrics(y, y_pred)
    
    return {
        'name': f'Lasso регрессия (α={alpha})',
        'model': model,
        'metrics': metrics,
        'coefficients': model.coef_,
        'intercept': model.intercept_,
        'scaler': scaler
    }


def polynomial_regression_analysis(X, y, feature_names, degree=2):
    """
    Полиномиальная регрессия
    
    Args:
        X: матрица признаков
        y: целевая переменная
        feature_names: названия признаков
        degree: степень полинома
    
    Returns:
        dict: результаты анализа
    """
    poly = PolynomialFeatures(degree=degree, include_bias=False)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    y_pred = model.predict(X_poly)
    metrics = calculate_metrics(y, y_pred)
    
    return {
        'name': f'Полиномиальная регрессия (степень {degree})',
        'model': model,
        'metrics': metrics,
        'coefficients': model.coef_,
        'intercept': model.intercept_,
        'poly': poly
    }


def compare_all_models(X, y, feature_names):
    """
    Сравнение всех регрессионных моделей
    
    Args:
        X: матрица признаков
        y: целевая переменная
        feature_names: названия признаков
    
    Returns:
        tuple: (список всех моделей, лучшая модель)
    """
    models = []
    
    # Линейная регрессия
    models.append(linear_regression_analysis(X, y, feature_names))
    
    # Ridge регрессия
    models.append(ridge_regression_analysis(X, y, feature_names))
    
    # Lasso регрессия
    models.append(lasso_regression_analysis(X, y, feature_names))
    
    # Полиномиальная регрессия
    if len(X) >= 5:
        models.append(polynomial_regression_analysis(X, y, feature_names))
    
    # Находим лучшую модель по R²
    best_model = max(models, key=lambda m: m['metrics']['r2'])
    
    return models, best_model


def forecast_gdp(model, export_value, import_value):
    """
    Прогнозирование ВВП по заданным значениям экспорта и импорта
    
    Args:
        model: обученная модель
        export_value: значение экспорта
        import_value: значение импорта
    
    Returns:
        float: прогнозируемый ВВП
    """
    features = np.array([[
        export_value, import_value,
        export_value * import_value,
        export_value ** 2,
        import_value ** 2,
        export_value - import_value,
        export_value + import_value
    ]])
    
    predicted_gdp = model.predict(features)[0]
    return predicted_gdp


def forecast_gdp_with_features(features, model):
    """Прогнозирование ВВП по готовым признакам"""
    return model.predict(features)[0]