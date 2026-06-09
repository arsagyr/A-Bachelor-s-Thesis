import unittest
import numpy as np
import sys
import os

# Добавляем корень проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculations.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    """Тестирование метрик качества"""

    def test_perfect_prediction(self):
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])
        metrics = calculate_metrics(y_true, y_pred)
        self.assertAlmostEqual(metrics['r2'], 1.0)
        self.assertAlmostEqual(metrics['rmse'], 0.0)
        self.assertAlmostEqual(metrics['mae'], 0.0)
        self.assertAlmostEqual(metrics['mape'], 0.0)

    def test_constant_prediction(self):
        y_true = np.array([10, 20, 30, 40])
        y_pred = np.array([25, 25, 25, 25])
        metrics = calculate_metrics(y_true, y_pred)
        self.assertEqual(metrics['r2'], 0.0)
        self.assertGreater(metrics['rmse'], 0)
        self.assertGreater(metrics['mae'], 0)
        self.assertGreater(metrics['mape'], 0)

    def test_zero_true_values(self):
        y_true = np.array([0, 0, 0, 1])
        y_pred = np.array([0, 0, 0, 1])
        metrics = calculate_metrics(y_true, y_pred)
        # MAPE для нулевых значений не считается (пропускаются)
        self.assertAlmostEqual(metrics['mape'], 0.0)

    def test_mape_division_by_zero_handling(self):
        y_true = np.array([0, 2, 0, 4])
        y_pred = np.array([0, 2, 0, 4])
        metrics = calculate_metrics(y_true, y_pred)
        self.assertAlmostEqual(metrics['mape'], 0.0)

if __name__ == '__main__':
    unittest.main()