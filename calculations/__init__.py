"""
Пакет для математических вычислений и статистического анализа
"""

from calculations.metrics import calculate_metrics
from calculations.preprocessing import prepare_regression_features, decimal_to_float, convert_data_to_float
from calculations.regression import (
    linear_regression_analysis,
    ridge_regression_analysis,
    lasso_regression_analysis,
    polynomial_regression_analysis,
    compare_all_models,
    forecast_gdp
)
from calculations.auto_regression import (
    auto_regression_forecast,
    auto_regression_with_confidence,
    compare_auto_regression_models,
    linear_auto_regression,
    polynomial_auto_regression,
    exponential_auto_regression,
    ridge_auto_regression,
    lasso_auto_regression,
    AVAILABLE_MODELS as AUTO_AVAILABLE_MODELS
)

__all__ = [
    'calculate_metrics',
    'prepare_regression_features',
    'decimal_to_float',
    'convert_data_to_float',
    'linear_regression_analysis',
    'ridge_regression_analysis',
    'lasso_regression_analysis',
    'polynomial_regression_analysis',
    'compare_all_models',
    'forecast_gdp',
    'auto_regression_forecast',
    'auto_regression_with_confidence',
    'compare_auto_regression_models',
    'linear_auto_regression',
    'polynomial_auto_regression',
    'exponential_auto_regression',
    'ridge_auto_regression',
    'lasso_auto_regression',
    'AUTO_AVAILABLE_MODELS'
]