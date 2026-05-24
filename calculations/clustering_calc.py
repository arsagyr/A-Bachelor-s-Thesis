"""
Расчёты для кластеризации стран по экономическим показателям
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from typing import Dict, List, Any, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class ClusteringCalc:
    """Класс для расчётов кластеризации"""
    
    @staticmethod
    def decimal_to_float(value):
        """Преобразование Decimal в float"""
        if hasattr(value, 'to_eng_string'):  # это Decimal
            return float(value)
        return value
    
    @staticmethod
    def prepare_features(df) -> Tuple[np.ndarray, List[str]]:
        """
        Подготовка признаков для кластеризации
        
        Args:
            df: DataFrame с колонками country_id, country_name, export_value, import_value, gdp_value
            
        Returns:
            features: нормализованная матрица признаков
            feature_names: названия признаков
        """
        if df.empty:
            return np.array([]), []
        
        # Преобразуем Decimal в float для всех нужных колонок
        df['export_value'] = df['export_value'].apply(lambda x: float(x) if hasattr(x, 'to_eng_string') else x)
        df['import_value'] = df['import_value'].apply(lambda x: float(x) if hasattr(x, 'to_eng_string') else x)
        df['gdp_value'] = df['gdp_value'].apply(lambda x: float(x) if hasattr(x, 'to_eng_string') else x)
        
        # Вычисляем дополнительные показатели
        df['export_per_gdp'] = df['export_value'] / df['gdp_value'] * 100
        df['import_per_gdp'] = df['import_value'] / df['gdp_value'] * 100
        df['trade_balance'] = df['export_value'] - df['import_value']
        df['trade_balance_per_gdp'] = df['trade_balance'] / df['gdp_value'] * 100
        df['trade_turnover'] = df['export_value'] + df['import_value']
        df['trade_turnover_per_gdp'] = df['trade_turnover'] / df['gdp_value'] * 100
        
        # Логарифмирование для учета масштаба (теперь значения уже float)
        df['log_export'] = np.log1p(df['export_value'].astype(float))
        df['log_import'] = np.log1p(df['import_value'].astype(float))
        df['log_gdp'] = np.log1p(df['gdp_value'].astype(float))
        
        # Признаки для кластеризации
        feature_columns = [
            'log_gdp',           # Логарифм ВВП (размер экономики)
            'log_export',        # Логарифм экспорта
            'log_import',        # Логарифм импорта
            'export_per_gdp',    # Открытость экономики (экспорт)
            'import_per_gdp',    # Открытость экономики (импорт)
            'trade_balance_per_gdp'  # Торговое сальдо относительно ВВП
        ]
        
        # Приводим к float и обрабатываем NaN/Inf
        features = df[feature_columns].values.astype(float)
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features, feature_columns
    
    @staticmethod
    def find_optimal_clusters(features: np.ndarray, max_k: int = 6) -> Dict[str, Any]:
        """
        Определение оптимального количества кластеров методом локтя
        """
        n_samples = len(features)
        if n_samples < 3:
            return {'optimal_k': 1, 'inertias': [], 'silhouette_scores': [], 'k_values': []}
        
        max_possible_k = min(max_k, n_samples - 1)
        
        inertias = []
        silhouette_scores = []
        
        for k in range(2, max_possible_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features)
            inertias.append(kmeans.inertia_)
            
            if len(np.unique(kmeans.labels_)) > 1:
                score = silhouette_score(features, kmeans.labels_)
                silhouette_scores.append(score)
            else:
                silhouette_scores.append(-1)
        
        # Находим точку "локтя" (максимальное изменение инерции)
        optimal_k = 3  # значение по умолчанию
        if len(inertias) >= 2:
            inertia_changes = []
            for i in range(1, len(inertias)):
                change = (inertias[i-1] - inertias[i]) / inertias[i-1] * 100 if inertias[i-1] > 0 else 0
                inertia_changes.append(change)
            
            # Оптимальное k там, где изменение резко замедляется (< 10%)
            for i, change in enumerate(inertia_changes):
                if change < 10:
                    optimal_k = i + 2
                    break
        
        optimal_k = min(optimal_k, max_possible_k)
        
        return {
            'optimal_k': int(optimal_k),
            'inertias': [float(x) for x in inertias],
            'silhouette_scores': [float(x) for x in silhouette_scores],
            'k_values': list(range(2, max_possible_k + 1))
        }
    
    @staticmethod
    def perform_clustering(features: np.ndarray, n_clusters: int = 3) -> Dict[str, Any]:
        """
        Выполнение кластеризации методом K-Means
        """
        if len(features) < n_clusters:
            return {'error': f'Недостаточно данных для {n_clusters} кластеров'}
        
        # Стандартизация признаков
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Кластеризация
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features_scaled)
        
        # Анализ кластеров (оценка по log_gdp - первый признак)
        cluster_ranking = []
        for i in range(n_clusters):
            cluster_mask = labels == i
            if np.sum(cluster_mask) > 0:
                avg_log_gdp = np.mean(features[cluster_mask, 0])
                cluster_ranking.append((i, avg_log_gdp, np.sum(cluster_mask)))
        
        # Сортируем по убыванию log_gdp
        cluster_ranking.sort(key=lambda x: x[1], reverse=True)
        
        # Назначаем названия
        type_names = ['Передовые', 'Средние', 'Отстающие']
        type_mapping = {}
        for idx, (old_id, _, _) in enumerate(cluster_ranking):
            if idx < len(type_names):
                type_mapping[old_id] = type_names[idx]
            else:
                type_mapping[old_id] = f'Кластер {idx+1}'
        
        # Создаем маппинг старых ID кластеров на новые
        old_to_new = {old_id: new_id for new_id, (old_id, _, _) in enumerate(cluster_ranking)}
        
        # Преобразуем метки
        new_labels = [old_to_new[label] for label in labels]
        
        # Информация о кластерах
        cluster_info = []
        for new_id, (old_id, _, size) in enumerate(cluster_ranking):
            cluster_info.append({
                'cluster_id': new_id,
                'type': type_mapping[old_id],
                'size': int(size)
            })
        
        return {
            'success': True,
            'n_clusters': n_clusters,
            'labels': [int(x) for x in new_labels],
            'cluster_info': cluster_info,
            'scaler': scaler,
            'model': kmeans
        }