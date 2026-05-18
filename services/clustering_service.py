"""
Сервис для кластеризации стран по экономическим показателям
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

from database import with_db_connection


class ClusteringService:
    """Сервис для кластеризации стран по экономическим показателям"""
    
    @staticmethod
    def convert_to_serializable(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    @staticmethod
    def convert_to_serializable_dict(obj):
        if isinstance(obj, dict):
            return {k: ClusteringService.convert_to_serializable_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ClusteringService.convert_to_serializable_dict(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    @staticmethod
    @with_db_connection
    def get_countries_data(conn, year: Optional[int] = None) -> pd.DataFrame:
        """
        Получение данных для кластеризации
        """
        cur = None
        try:
            cur = conn.cursor()
            
            if year:
                query = """
                    SELECT 
                        c.id as country_id,
                        c.name as country_name,
                        i.year,
                        i.export_value,
                        i.import_value,
                        i.gdp_value
                    FROM indicators i
                    JOIN countries c ON i.country_id = c.id
                    WHERE i.year = %s
                      AND i.export_value IS NOT NULL
                      AND i.import_value IS NOT NULL
                      AND i.gdp_value IS NOT NULL
                    ORDER BY c.name
                """
                cur.execute(query, (year,))
            else:
                # Берем последний доступный год для каждой страны
                query = """
                    SELECT DISTINCT ON (c.id)
                        c.id as country_id,
                        c.name as country_name,
                        i.year,
                        i.export_value,
                        i.import_value,
                        i.gdp_value
                    FROM indicators i
                    JOIN countries c ON i.country_id = c.id
                    WHERE i.export_value IS NOT NULL
                      AND i.import_value IS NOT NULL
                      AND i.gdp_value IS NOT NULL
                    ORDER BY c.id, i.year DESC
                """
                cur.execute(query)
            
            data = cur.fetchall()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            return df
            
        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()
        finally:
            if cur:
                cur.close()
    
    @staticmethod
    def prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Подготовка признаков для кластеризации
        """
        if df.empty:
            return np.array([]), np.array([]), []
        
        # Вычисляем дополнительные показатели
        df['export_per_gdp'] = df['export_value'] / df['gdp_value'] * 100
        df['import_per_gdp'] = df['import_value'] / df['gdp_value'] * 100
        df['trade_balance'] = df['export_value'] - df['import_value']
        df['trade_balance_per_gdp'] = df['trade_balance'] / df['gdp_value'] * 100
        df['trade_turnover'] = df['export_value'] + df['import_value']
        df['trade_turnover_per_gdp'] = df['trade_turnover'] / df['gdp_value'] * 100
        
        # Признаки для кластеризации
        feature_columns = [
            'export_value',
            'import_value', 
            'gdp_value',
            'export_per_gdp',
            'import_per_gdp',
            'trade_balance',
            'trade_balance_per_gdp',
            'trade_turnover',
            'trade_turnover_per_gdp'
        ]
        
        features = df[feature_columns].values.astype(float)
        feature_names = feature_columns
        
        # Обработка бесконечных значений
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features, df['country_id'].values, feature_names
    
    @staticmethod
    def find_optimal_clusters(features: np.ndarray, max_k: int = 10) -> Dict[str, Any]:
        """
        Определение оптимального количества кластеров методом локтя
        """
        if len(features) < 3:
            return {'error': 'Недостаточно данных для кластеризации', 'optimal_k': 1}
        
        inertias = []
        silhouette_scores = []
        
        for k in range(2, min(max_k + 1, len(features))):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features)
            inertias.append(kmeans.inertia_)
            
            if k >= 2:
                silhouette_scores.append(silhouette_score(features, kmeans.labels_))
        
        # Находим точку "локтя" (максимальное изменение инерции)
        if len(inertias) >= 2:
            deltas = np.diff(inertias)
            if len(deltas) >= 2:
                deltas2 = np.diff(deltas)
                optimal_k = np.argmax(np.abs(deltas2)) + 3 if len(deltas2) > 0 else 3
            else:
                optimal_k = 3
        else:
            optimal_k = 3
        
        optimal_k = min(optimal_k, len(features) - 1)
        
        return {
            'optimal_k': int(optimal_k),
            'inertias': [float(x) for x in inertias],
            'silhouette_scores': [float(x) for x in silhouette_scores],
            'k_values': list(range(2, min(max_k + 1, len(features))))
        }
    
    @staticmethod
    def perform_clustering(features: np.ndarray, n_clusters: int = 3) -> Dict[str, Any]:
        """
        Выполнение кластеризации
        """
        if len(features) < n_clusters:
            return {'error': f'Недостаточно данных для {n_clusters} кластеров'}
        
        # Стандартизация признаков
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Кластеризация
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features_scaled)
        
        # Анализ кластеров
        cluster_info = []
        for i in range(n_clusters):
            cluster_mask = labels == i
            cluster_data = features[cluster_mask]
            
            if len(cluster_data) > 0:
                avg_gdp = np.mean(cluster_data[:, 2])  # ВВП
                avg_export = np.mean(cluster_data[:, 0])  # Экспорт
                avg_import = np.mean(cluster_data[:, 1])  # Импорт
                
                cluster_info.append({
                    'cluster_id': int(i),
                    'size': int(np.sum(cluster_mask)),
                    'avg_gdp': float(avg_gdp),
                    'avg_export': float(avg_export),
                    'avg_import': float(avg_import)
                })
        
        # Сортируем кластеры по среднему ВВП
        cluster_info.sort(key=lambda x: x['avg_gdp'], reverse=True)
        
        # Назначаем названия
        names = ['Передовые', 'Средние', 'Отстающие']
        for i, info in enumerate(cluster_info):
            if i < len(names):
                info['type'] = names[i]
            else:
                info['type'] = f'Кластер {i+1}'
        
        # Создаем маппинг старых ID кластеров на новые
        old_to_new = {}
        for new_id, info in enumerate(cluster_info):
            old_to_new[info['cluster_id']] = new_id
        
        # Преобразуем метки
        new_labels = [old_to_new[label] for label in labels]
        
        return {
            'success': True,
            'n_clusters': n_clusters,
            'labels': [int(x) for x in new_labels],
            'cluster_info': cluster_info,
            'scaler': scaler,
            'model': kmeans
        }
    
    @staticmethod
    @with_db_connection
    def analyze_country_clusters(conn, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Анализ кластеризации стран
        """
        try:
            # Получаем данные
            df = ClusteringService.get_countries_data(year)
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'Нет данных для кластеризации'
                }
            
            if len(df) < 3:
                return {
                    'success': False,
                    'error': f'Недостаточно стран для кластеризации: {len(df)}'
                }
            
            # Подготовка признаков
            features, country_ids, feature_names = ClusteringService.prepare_features(df)
            
            if len(features) == 0:
                return {
                    'success': False,
                    'error': 'Ошибка подготовки признаков'
                }
            
            # Определение оптимального количества кластеров
            elbow_result = ClusteringService.find_optimal_clusters(features)
            optimal_k = elbow_result.get('optimal_k', 3)
            
            # Выполнение кластеризации
            clustering_result = ClusteringService.perform_clustering(features, optimal_k)
            
            if not clustering_result.get('success'):
                return clustering_result
            
            # Формирование результата
            countries = []
            for i, country_id in enumerate(country_ids):
                country_name = df[df['country_id'] == country_id]['country_name'].iloc[0]
                label = clustering_result['labels'][i]
                
                # Находим тип кластера
                cluster_type = None
                for info in clustering_result['cluster_info']:
                    if info['cluster_id'] == label:
                        cluster_type = info['type']
                        break
                
                countries.append({
                    'country_id': int(country_id),
                    'country_name': country_name,
                    'cluster_id': label,
                    'cluster_type': cluster_type,
                    'export_value': float(df.iloc[i]['export_value']) / 1000,  # в трлн
                    'import_value': float(df.iloc[i]['import_value']) / 1000,
                    'gdp_value': float(df.iloc[i]['gdp_value']) / 1000
                })
            
            # Сортируем страны по типу кластера
            type_order = {'Передовые': 0, 'Средние': 1, 'Отстающие': 2}
            countries.sort(key=lambda x: type_order.get(x['cluster_type'], 3))
            
            # Добавляем средние значения для кластеров (в трлн)
            for cluster in clustering_result['cluster_info']:
                cluster['avg_gdp'] = cluster['avg_gdp'] / 1000
                cluster['avg_export'] = cluster['avg_export'] / 1000
                cluster['avg_import'] = cluster['avg_import'] / 1000
            
            result = {
                'success': True,
                'year': year if year else 'последний доступный',
                'n_countries': len(countries),
                'n_clusters': optimal_k,
                'elbow_analysis': {
                    'optimal_k': optimal_k,
                    'inertias': elbow_result['inertias'],
                    'silhouette_scores': elbow_result['silhouette_scores'],
                    'k_values': elbow_result['k_values']
                },
                'clusters': clustering_result['cluster_info'],
                'countries': countries,
                'feature_names': feature_names
            }
            
            return ClusteringService.convert_to_serializable_dict(result)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    @with_db_connection
    def get_cluster_statistics(conn, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Получение статистики по кластерам
        """
        result = ClusteringService.analyze_country_clusters(year)
        
        if not result.get('success'):
            return result
        
        # Расчет дополнительной статистики
        stats = []
        for cluster in result['clusters']:
            cluster_countries = [c for c in result['countries'] if c['cluster_type'] == cluster['type']]
            
            if cluster_countries:
                avg_export = np.mean([c['export_value'] for c in cluster_countries])
                avg_import = np.mean([c['import_value'] for c in cluster_countries])
                avg_gdp = np.mean([c['gdp_value'] for c in cluster_countries])
                
                stats.append({
                    'type': cluster['type'],
                    'size': len(cluster_countries),
                    'avg_export': float(avg_export),
                    'avg_import': float(avg_import),
                    'avg_gdp': float(avg_gdp),
                    'countries': [c['country_name'] for c in cluster_countries]
                })
        
        result['cluster_statistics'] = stats
        
        return result