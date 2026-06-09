import unittest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculations.regression_calc import (
    prepare_regression_features, linear_regression_fit, ridge_regression_fit,
    lasso_regression_fit, train_regression_model, predict_gdp_by_regression,
    calculate_regression_statistics
)

class TestRegressionCalc(unittest.TestCase):
    """Тестирование регрессионных расчётов"""

    def setUp(self):
        # Данные для регрессии (экспорт, импорт, ВВП)
        self.df = pd.DataFrame({
            'export': [10, 12, 15, 18, 20, 22],
            'import': [8, 10, 13, 16, 19, 21],
            'gdp': [50, 60, 72, 85, 95, 105]
        })
        self.X, self.y, self.names = prepare_regression_features(self.df)

    def test_prepare_features(self):
        self.assertEqual(self.X.shape, (6, 5))
        self.assertEqual(len(self.y), 6)
        self.assertEqual(self.names, ['экспорт', 'импорт', 'экспорт×импорт', 'экспорт²', 'импорт²'])

    def test_linear_regression_fit(self):
        slopes, intercept = linear_regression_fit(self.X, self.y)
        self.assertEqual(len(slopes), 5)
        self.assertIsInstance(intercept, float)

    def test_ridge_regression_fit(self):
        slopes, intercept = ridge_regression_fit(self.X, self.y, alpha=0.5)
        self.assertEqual(len(slopes), 5)
        self.assertIsInstance(intercept, float)

    def test_lasso_regression_fit(self):
        slopes, intercept = lasso_regression_fit(self.X, self.y, alpha=0.1)
        self.assertEqual(len(slopes), 5)

    def test_train_regression_model_linear(self):
        result = train_regression_model(self.X, self.y, model_type='linear')
        self.assertTrue(result['success'])
        self.assertIn('metrics', result)
        self.assertIn('statistics', result)
        stats = result['statistics']
        self.assertIn('r2_adjusted', stats)
        self.assertIn('f_statistic', stats)

    def test_train_regression_model_ridge(self):
        result = train_regression_model(self.X, self.y, model_type='ridge', alpha=0.2)
        self.assertTrue(result['success'])
        self.assertNotIn('statistics', result)  # для ridge статистики не считаются

    def test_train_regression_model_insufficient_data(self):
        X_bad = np.random.rand(3, 5)
        y_bad = np.random.rand(3)
        result = train_regression_model(X_bad, y_bad)
        self.assertIn('error', result)

    def test_calculate_regression_statistics(self):
        # Данные с очень маленьким шумом, чтобы RSS > 0
        np.random.seed(42)
        X = np.array([[1, 2], [2, 3], [3, 4], [4, 5]])   # признаки
        y_true = 2 * X[:, 0] + 3 * X[:, 1]                # истинная зависимость
        noise = np.random.normal(0, 1e-8, size=len(y_true))  # микрошум
        y = y_true + noise
        
        # Обучаем модель (линейную) на этих данных, чтобы получить коэффициенты
        slopes, intercept = linear_regression_fit(X, y)
        stats = calculate_regression_statistics(X, y, slopes, intercept)
        
        # R² должен быть почти 1
        self.assertAlmostEqual(stats['r2'], 1.0, places=4)
        self.assertAlmostEqual(stats['r2_adjusted'], 1.0, places=4)
        
        # F-статистика теперь должна быть очень большой (не None)
        self.assertIsNotNone(stats['f_statistic']['value'])
        self.assertGreater(stats['f_statistic']['value'], 1000)
        self.assertLess(stats['f_statistic']['p_value'], 0.05)
        
        # Проверим, что коэффициенты значимы
        for coef_info in stats['coefficients']['features']:
            self.assertLess(coef_info['p_value'], 0.05)

    def test_predict_gdp_by_regression(self):
        result = predict_gdp_by_regression(self.df, steps=3, model_type='linear')
        self.assertTrue(result['success'])
        self.assertEqual(len(result['forecast']), 3)
        self.assertIn('export_forecast', result)
        self.assertIn('import_forecast', result)
        self.assertEqual(len(result['historical_predictions']), len(self.df))

    def test_predict_gdp_insufficient_data(self):
        small_df = pd.DataFrame({'export': [1], 'import': [2], 'gdp': [3]})
        result = predict_gdp_by_regression(small_df, steps=2)
        self.assertIn('error', result)
        self.assertEqual(result['forecast'], [])

if __name__ == '__main__':
    unittest.main()