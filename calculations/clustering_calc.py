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
        if hasattr(value, 'to_eng_string'):   
            return float(value)
        return value
    
    @staticmethod
    def prepare_features(df) -> Tuple[np.ndarray, List[str]]:
        """
        Подготовка признаков для кластеризации
        
        Args:
            df: DataFrame с колонками country_id, country_name, export_value, import_value, gdp_value, population_value
                
        Returns:
            features: нормализованная матрица признаков
            feature_names: названия признаков
        """
        if df.empty:
            return np.array([]), []
        
        # Преобразуем Decimal в float для всех нужных колонок
        for col in ['export_value', 'import_value', 'gdp_value', 'population_value']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: float(x) if hasattr(x, 'to_eng_string') else x)
        
        # Вычисляем дополнительные показатели
        df['export_per_gdp'] = df['export_value'] / df['gdp_value'] * 100
        df['import_per_gdp'] = df['import_value'] / df['gdp_value'] * 100
        df['trade_balance'] = df['export_value'] - df['import_value']  # торговый баланс (млрд USD)
        
        # ВВП на душу населения (USD)
        # ВВП в млрд USD, население в млн человек → ВВП на душу = (gdp * 1e9) / (population * 1e6) = gdp / population * 1000
        df['gdp_per_capita'] = df['gdp_value'] / df['population_value'] * 1000
        
        # Логарифмирование для учёта масштаба (для положительных величин)
        df['log_gdp'] = np.log1p(df['gdp_value'].astype(float))
        df['log_export'] = np.log1p(df['export_value'].astype(float))
        df['log_import'] = np.log1p(df['import_value'].astype(float))
        df['log_population'] = np.log1p(df['population_value'].astype(float))
        
        # Торговый баланс может быть отрицательным, поэтому используем его как есть
        # ВВП на душу всегда положителен, можно прологарифмировать
        df['log_gdp_per_capita'] = np.log1p(df['gdp_per_capita'].astype(float))
        
        # Признаки для кластеризации (расширенный набор)
        feature_columns = [
            'log_gdp',               # логарифм ВВП (размер экономики)
            'log_export',            # логарифм экспорта
            'log_import',            # логарифм импорта
            'export_per_gdp',        # открытость экономики (экспорт)
            'import_per_gdp',        # открытость экономики (импорт)
            'trade_balance',         # торговый баланс (абсолютный)
            'log_gdp_per_capita'     # логарифм ВВП на душу (уровень развития)
        ]
        
        # Приводим к float и обрабатываем NaN/Inf
        features = df[feature_columns].values.astype(float)
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features, feature_columns
    
    @staticmethod
    def find_optimal_clusters(features: np.ndarray, max_k: int = 8) -> Dict[str, Any]:
        """
        Определение оптимального количества кластеров методом локтя
        """
        n_samples = len(features)
        if n_samples < 3:
            return {'optimal_k': 1, 'inertias': [], 'silhouette_scores': [], 'k_values': []}
        
        max_possible_k = min(max_k, n_samples - 1)
        
        inertias = []
        k_values = []
        silhouette_scores = []
        
        # Для k=1: инерция = сумма квадратов отклонений от среднего (TSS)
        tss = np.sum((features - np.mean(features, axis=0)) ** 2)
        inertias.append(float(tss))
        k_values.append(1)
        silhouette_scores.append(None)  # для k=1 силуэт не определён
        
        # Для k от 2 до max_possible_k
        for k in range(2, max_possible_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features)
            inertias.append(float(kmeans.inertia_))
            k_values.append(k)
            
            if len(np.unique(kmeans.labels_)) > 1:
                score = silhouette_score(features, kmeans.labels_)
                silhouette_scores.append(float(score))
            else:
                silhouette_scores.append(-1.0)
        
        # Определение оптимального k (по "локтю") – оставляем прежнюю логику, но сдвигаем индексы
        optimal_k = 3
        if len(inertias) >= 3:  # теперь в массиве есть k=1,2,3,...
            inertia_changes = []
            # изменение между последовательными k (начиная с k=2)
            for i in range(2, len(inertias)):
                prev_inertia = inertias[i-1]
                curr_inertia = inertias[i]
                change = (prev_inertia - curr_inertia) / prev_inertia * 100 if prev_inertia > 0 else 0
                inertia_changes.append(change)
            
            # Оптимальное k там, где изменение резко замедляется (< 10%)
            # индекс в inertia_changes соответствует k = i+2
            for idx, change in enumerate(inertia_changes):
                if change < 10:
                    optimal_k = idx + 2   # т.к. изменения начались с k=2, первое изменение соответствует k=2->3
                    break
        
        optimal_k = min(optimal_k, max_possible_k)
        
        return {
            'optimal_k': int(optimal_k),
            'k_values': k_values,               # [1,2,3,...,max_possible_k]
            'inertias': inertias,               # соответствующие инерции
            'silhouette_scores': silhouette_scores
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