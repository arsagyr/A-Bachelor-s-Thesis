"""
Сервис для кластеризации стран (API слой)
"""

import pandas as pd
from typing import Dict, Any, Optional
from decimal import Decimal
from database import with_db_connection
from calculations.clustering_calc import ClusteringCalc


class ClusteringService:
    """Сервис для кластеризации стран"""
    
    @staticmethod
    @with_db_connection
    def analyze_country_clusters(conn, year: Optional[int] = None) -> Dict[str, Any]:
        """Анализ кластеризации стран"""
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
            cur.close()
            
            if not data:
                return {'success': False, 'error': 'Нет данных для кластеризации'}
            
            if len(data) < 3:
                return {'success': False, 'error': f'Недостаточно стран для кластеризации: {len(data)}'}
            
            # Преобразуем данные в DataFrame с float значениями
            rows = []
            for row in data:
                rows.append({
                    'country_id': row['country_id'],
                    'country_name': row['country_name'],
                    'year': row['year'],
                    'export_value': float(row['export_value']) if row['export_value'] else 0.0,
                    'import_value': float(row['import_value']) if row['import_value'] else 0.0,
                    'gdp_value': float(row['gdp_value']) if row['gdp_value'] else 0.0
                })
            
            df = pd.DataFrame(rows)
            df = df[(df['export_value'] > 0) | (df['gdp_value'] > 0)]
            
            if len(df) < 3:
                return {'success': False, 'error': f'Недостаточно стран после фильтрации: {len(df)}'}
            
            features, feature_names = ClusteringCalc.prepare_features(df)
            
            if len(features) == 0:
                return {'success': False, 'error': 'Ошибка подготовки признаков'}
            
            elbow_result = ClusteringCalc.find_optimal_clusters(features)
            optimal_k = elbow_result.get('optimal_k', 3)
            
            clustering_result = ClusteringCalc.perform_clustering(features, optimal_k)
            
            if not clustering_result.get('success'):
                return {'success': False, 'error': clustering_result.get('error')}
            
            countries = []
            for i, row in df.iterrows():
                label = clustering_result['labels'][i]
                cluster_type = None
                for info in clustering_result['cluster_info']:
                    if info['cluster_id'] == label:
                        cluster_type = info['type']
                        break
                
                countries.append({
                    'country_id': int(row['country_id']),
                    'country_name': row['country_name'],
                    'cluster_id': label,
                    'cluster_type': cluster_type,
                    'export_value': float(row['export_value']),
                    'import_value': float(row['import_value']),
                    'gdp_value': float(row['gdp_value'])
                })
            
            type_order = {'Передовые': 0, 'Средние': 1, 'Отстающие': 2}
            countries.sort(key=lambda x: type_order.get(x['cluster_type'], 3))
            
            for cluster in clustering_result['cluster_info']:
                cluster_countries = [c for c in countries if c['cluster_type'] == cluster['type']]
                if cluster_countries:
                    cluster['avg_gdp'] = sum(c['gdp_value'] for c in cluster_countries) / len(cluster_countries)
                    cluster['avg_export'] = sum(c['export_value'] for c in cluster_countries) / len(cluster_countries)
                    cluster['avg_import'] = sum(c['import_value'] for c in cluster_countries) / len(cluster_countries)
            
            return {
                'success': True,
                'year': year if year else 'последний доступный',
                'n_countries': len(countries),
                'n_clusters': optimal_k,
                'elbow_analysis': {
                    'optimal_k': optimal_k,
                    'inertias': elbow_result.get('inertias', []),
                    'silhouette_scores': elbow_result.get('silhouette_scores', []),
                    'k_values': elbow_result.get('k_values', [])
                },
                'clusters': clustering_result['cluster_info'],
                'countries': countries,
                'feature_names': feature_names
            }
            
        except Exception as e:
            print(f"Error in analyze_country_clusters: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}