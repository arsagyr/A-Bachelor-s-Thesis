import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculations.auto_regression import (
    linear_trend, polynomial_trend, exponential_trend,
    ridge_trend, lasso_trend, irwin_criterion, t_test_slope,
    auto_regression_forecast, compare_auto_regression_models
)

class TestAutoRegression(unittest.TestCase):
    """Тестирование трендов и критериев"""

    def setUp(self):
        # Линейный ряд: y = 2 + 0.5*t
        self.linear_series = [2 + 0.5*i for i in range(1, 11)]
        # Экспоненциальный ряд: y = exp(0.5 + 0.2*t)
        self.exp_series = [np.exp(0.5 + 0.2*i) for i in range(1, 11)]

    def test_linear_trend_success(self):
        result = linear_trend(self.linear_series, steps=3)
        self.assertTrue(result['success'])
        self.assertEqual(result['model_type'], 'linear')
        self.assertEqual(len(result['forecast']), 3)
        self.assertAlmostEqual(result['slope'], 0.5, places=1)
        self.assertAlmostEqual(result['intercept'], 2.0, places=1)

    def test_linear_trend_insufficient_data(self):
        result = linear_trend([1, 2], steps=2)
        self.assertIn('error', result)
        self.assertEqual(result['forecast'], [])

    def test_polynomial_trend(self):
        result = polynomial_trend(self.linear_series, steps=2, degree=2)
        self.assertTrue(result['success'])
        self.assertEqual(result['degree'], 2)
        self.assertEqual(len(result['coefficients']), 2)

    def test_polynomial_degree_too_high(self):
        result = polynomial_trend([1, 2, 3], steps=1, degree=3)
        self.assertIn('error', result)

    def test_exponential_trend_success(self):
        result = exponential_trend(self.exp_series, steps=2)
        self.assertTrue(result['success'])
        self.assertEqual(result['model_type'], 'exponential')
        self.assertEqual(len(result['forecast']), 2)
        self.assertGreater(result['forecast'][0], 0)

    def test_exponential_trend_non_positive(self):
        result = exponential_trend([-1, 0, 2], steps=2)
        self.assertIn('error', result)

    def test_ridge_trend(self):
        result = ridge_trend(self.linear_series, steps=2, alpha=0.5)
        self.assertTrue(result['success'])
        self.assertEqual(result['model_type'], 'ridge')
        self.assertEqual(result['alpha'], 0.5)

    def test_lasso_trend(self):
        result = lasso_trend(self.linear_series, steps=2, alpha=0.1)
        self.assertTrue(result['success'])
        self.assertEqual(result['model_type'], 'lasso')

    def test_irwin_criterion(self):
        series = [1, 2, 3, 100, 5]
        result = irwin_criterion(series, threshold=3.0)
        self.assertTrue(result['success'])
        self.assertEqual(result['outlier_count'], 0)   

    def test_irwin_criterion_insufficient_data(self):
        result = irwin_criterion([1, 2], threshold=3)
        self.assertIn('error', result)

    def test_t_test_slope_significant(self):
        result = t_test_slope(self.linear_series, alpha=0.05)
        self.assertTrue(result['significant'])
        self.assertLess(result['p_value'], 0.05)

    def test_t_test_slope_insufficient_data(self):
        result = t_test_slope([1, 2], alpha=0.05)
        self.assertIn('error', result)

    def test_auto_regression_forecast_linear_default(self):
        result = auto_regression_forecast(self.linear_series, steps=2)
        self.assertTrue(result['success'])
        self.assertEqual(result['model_type'], 'linear')

    def test_auto_regression_forecast_polynomial(self):
        result = auto_regression_forecast(self.linear_series, steps=2, model_type='polynomial', degree=2)
        self.assertEqual(result['model_type'], 'polynomial')

    def test_compare_models(self):
        result = compare_auto_regression_models(self.linear_series, steps=2)
        self.assertTrue(result['success'])
        self.assertIn('best_model', result)
        self.assertGreater(result['best_r2'], 0.9)  # линейный ряд хорошо описывается

if __name__ == '__main__':
    unittest.main()