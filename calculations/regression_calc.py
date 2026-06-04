"""
Расчёты для регрессионного анализа ВВП от экспорта и импорта
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from sklearn.linear_model import Ridge, Lasso
from calculations.auto_regression import linear_trend
from calculations.metrics import calculate_metrics
from scipy import stats

def prepare_regression_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Подготовка признаков для регрессии ВВП от экспорта и импорта.
    Признаки: экспорт, импорт, произведение, квадраты (без сальдо и оборота).
    """
    if df.empty:
        return np.array([]), np.array([]), []
    
    # Преобразуем все значения в float
    export = df['export'].astype(float).values
    import_val = df['import'].astype(float).values
    gdp = df['gdp'].astype(float).values

    features = np.column_stack([
        export,
        import_val,
        export * import_val,
        export ** 2,
        import_val ** 2
    ])
    
    feature_names = [
        'экспорт', 'импорт', 'экспорт×импорт',
        'экспорт²', 'импорт²'
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
    Ridge регрессия (L2-регуляризация) с использованием sklearn
    """
    model = Ridge(alpha=alpha, fit_intercept=True, copy_X=True)
    model.fit(X, y)
    intercept = model.intercept_
    slopes = model.coef_
    return slopes, intercept


def lasso_regression_fit(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> tuple:
    """
    Lasso регрессия (L1-регуляризация) с использованием sklearn
    """
    model = Lasso(alpha=alpha, fit_intercept=True, copy_X=True, max_iter=10000)
    model.fit(X, y)
    intercept = model.intercept_
    slopes = model.coef_
    return slopes, intercept


def train_regression_model(X: np.ndarray, y: np.ndarray, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
    """
    Обучение регрессионной модели с расчётом статистик Стьюдента и Фишера.
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
        
        # Расчёт статистик (только для линейной модели, ridge/lasso дают смещённые оценки)
        statistics = None
        if model_type == 'linear':
            statistics = calculate_regression_statistics(X, y, np.array(slopes), intercept)
        
        result = {
            'success': True,
            'coefficients': slopes.tolist() if hasattr(slopes, 'tolist') else [float(slopes)],
            'intercept': float(intercept),
            'metrics': metrics
        }
        if statistics:
            result['statistics'] = statistics
        
        return result
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
        
        # 3. Подготовка признаков (уже без сальдо и оборота)
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
                pred_import ** 2
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
    
def calculate_regression_statistics(X: np.ndarray, y: np.ndarray, 
                                    coefficients: np.ndarray, intercept: float) -> Dict[str, Any]:
    """
    Расчёт статистик значимости для линейной регрессии:
    - t-статистики и p-значения для каждого коэффициента (Стьюдент)
    - F-статистики и p-значения для модели (Фишер)
    - скорректированный R-squared
    - стандартные ошибки коэффициентов
    
    Args:
        X: матрица признаков (n_samples, n_features)
        y: целевая переменная
        coefficients: вектор коэффициентов при признаках (без intercept)
        intercept: свободный член
    
    Returns:
        словарь со статистиками
    """
    n_samples, n_features = X.shape
    n_params = n_features + 1  # + intercept
    
    # Предсказания
    y_pred = intercept + X @ coefficients
    residuals = y - y_pred
    
    # Остаточная сумма квадратов
    rss = np.sum(residuals ** 2)
    # Общая сумма квадратов
    tss = np.sum((y - np.mean(y)) ** 2)
    # R-squared
    r2 = 1 - rss / tss if tss != 0 else 0
    # Скорректированный R-squared
    r2_adj = 1 - (1 - r2) * (n_samples - 1) / (n_samples - n_params - 1) if n_samples > n_params + 1 else r2
    
    # Оценка дисперсии ошибок
    if n_samples > n_params:
        residual_variance = rss / (n_samples - n_params)
    else:
        residual_variance = np.nan
    
    # Стандартные ошибки коэффициентов
    # Добавляем столбец единиц для intercept
    X_design = np.column_stack([np.ones(n_samples), X])
    try:
        XTX_inv = np.linalg.inv(X_design.T @ X_design)
        std_errors = np.sqrt(np.diag(XTX_inv) * residual_variance) if not np.isnan(residual_variance) else np.full(n_params, np.nan)
    except np.linalg.LinAlgError:
        # Если матрица вырождена, используем псевдообратную
        XTX_pinv = np.linalg.pinv(X_design.T @ X_design)
        std_errors = np.sqrt(np.diag(XTX_pinv) * residual_variance) if not np.isnan(residual_variance) else np.full(n_params, np.nan)
    
    # t-статистики и p-значения для каждого коэффициента
    t_stats = coefficients / std_errors[1:] if not np.isnan(residual_variance) else np.full(n_features, np.nan)
    t_stats_intercept = intercept / std_errors[0] if not np.isnan(residual_variance) else np.nan
    
    p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=n_samples - n_params)) if not np.isnan(residual_variance) else np.full(n_features, np.nan)
    p_value_intercept = 2 * (1 - stats.t.cdf(np.abs(t_stats_intercept), df=n_samples - n_params)) if not np.isnan(residual_variance) else np.nan
    
    # F-статистика для модели
    # F = (RSS_reduced - RSS_full) / (p_full - p_reduced) / (RSS_full / (n - p_full))
    # Для проверки общей значимости: RSS_reduced = TSS (модель только с intercept)
    if n_samples > n_params and rss > 0:
        f_stat = (tss - rss) / n_features / (rss / (n_samples - n_params))
        f_p_value = 1 - stats.f.cdf(f_stat, n_features, n_samples - n_params)
    else:
        f_stat = np.nan
        f_p_value = np.nan
    
    return {
        'r2': float(r2),
        'r2_adjusted': float(r2_adj),
        'residual_std_error': float(np.sqrt(residual_variance)) if not np.isnan(residual_variance) else None,
        'coefficients': {
            'intercept': {
                'value': float(intercept),
                'std_error': float(std_errors[0]) if not np.isnan(std_errors[0]) else None,
                't_statistic': float(t_stats_intercept) if not np.isnan(t_stats_intercept) else None,
                'p_value': float(p_value_intercept) if not np.isnan(p_value_intercept) else None
            },
            'features': [
                {
                    'index': i,
                    'value': float(coefficients[i]),
                    'std_error': float(std_errors[i+1]) if not np.isnan(std_errors[i+1]) else None,
                    't_statistic': float(t_stats[i]) if not np.isnan(t_stats[i]) else None,
                    'p_value': float(p_values[i]) if not np.isnan(p_values[i]) else None
                }
                for i in range(n_features)
            ]
        },
        'f_statistic': {
            'value': float(f_stat) if not np.isnan(f_stat) else None,
            'p_value': float(f_p_value) if not np.isnan(f_p_value) else None,
            'df_model': n_features,
            'df_residual': n_samples - n_params
        }
    }