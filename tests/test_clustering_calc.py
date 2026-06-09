import unittest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculations.clustering_calc import ClusteringCalc

class TestClusteringCalc(unittest.TestCase):
    """Тестирование кластеризации"""

    def setUp(self):
        #  DataFrame для 5 стран с разными показателями
        self.df = pd.DataFrame({
            'country_id': [1, 2, 3, 4, 5],
            'country_name': ['A', 'B', 'C', 'D', 'E'],
            'export_value': [100, 200, 50, 300, 80],
            'import_value': [90, 210, 60, 280, 85],
            'gdp_value': [1000, 1500, 500, 2000, 600],
            'population_value': [10, 20, 5, 25, 8]
        })
        self.features, self.feature_names = ClusteringCalc.prepare_features(self.df.copy())

    def test_prepare_features_shape(self):
        self.assertEqual(self.features.shape[0], 5)
        self.assertEqual(self.features.shape[1], 7)
        self.assertIn('log_gdp', self.feature_names)
        self.assertIn('log_gdp_per_capita', self.feature_names)

    def test_prepare_features_no_nan_inf(self):
        self.assertFalse(np.any(np.isnan(self.features)))
        self.assertFalse(np.any(np.isinf(self.features)))

    def test_prepare_features_empty_df(self):
        empty_df = pd.DataFrame()
        feats, names = ClusteringCalc.prepare_features(empty_df)
        self.assertEqual(len(feats), 0)
        self.assertEqual(names, [])

    def test_find_optimal_clusters(self):
        result = ClusteringCalc.find_optimal_clusters(self.features, max_k=4)
        self.assertIn('optimal_k', result)
        self.assertGreaterEqual(result['optimal_k'], 1)
        self.assertEqual(len(result['k_values']), 4)  # от 1 до 4
        self.assertEqual(len(result['inertias']), 4)

    def test_find_optimal_clusters_small_data(self):
        small_feats = np.random.rand(2, 3)
        result = ClusteringCalc.find_optimal_clusters(small_feats, max_k=3)
        self.assertEqual(result['optimal_k'], 1)
        self.assertEqual(result['inertias'], [])
        self.assertEqual(result['k_values'], [])
        self.assertEqual(result['silhouette_scores'], [])

    def test_perform_clustering_success(self):
        result = ClusteringCalc.perform_clustering(self.features, n_clusters=3)
        self.assertTrue(result['success'])
        self.assertEqual(result['n_clusters'], 3)
        self.assertEqual(len(result['labels']), 5)
        self.assertEqual(len(result['cluster_info']), 3)
        # Типы кластеров: Передовые, Средние, Отстающие
        types = [info['type'] for info in result['cluster_info']]
        self.assertIn('Передовые', types)
        self.assertIn('Средние', types)
        self.assertIn('Отстающие', types)

    def test_perform_clustering_insufficient_data(self):
        small_feats = np.random.rand(2, 3)
        result = ClusteringCalc.perform_clustering(small_feats, n_clusters=3)
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()