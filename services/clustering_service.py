import pandas as pd
from typing import Dict, Any, Optional
from database import with_db_connection
from repositories.country_repository import CountryRepository
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository
from calculations.clustering_calc import ClusteringCalc


class ClusteringService:

    @staticmethod
    @with_db_connection
    def analyze_country_clusters(conn, year: Optional[int] = None) -> Dict[str, Any]:
        try:
            # Получаем id нужных индикаторов
            ind_repo = IndicatorRepository(conn)
            ind_ids = {}
            for name in ['export_value', 'import_value', 'gdp_value', 'population_value']:
                ind = ind_repo.get_by_name(name)
                if not ind:
                    return {'success': False, 'error': f'Индикатор {name} не найден'}
                ind_ids[name] = ind.id

            # Получаем все статистики
            stats_repo = StatisticsRepository(conn)
            all_stats = stats_repo.filter()   # без фильтрации

            # Если указан год - фильтруем
            if year is not None:
                all_stats = [s for s in all_stats if s.year == year]
            else:
                # Берём последний доступный год для каждой страны
                from collections import defaultdict
                last_year_per_country = defaultdict(int)
                for s in all_stats:
                    if s.year > last_year_per_country[s.country_id]:
                        last_year_per_country[s.country_id] = s.year
                all_stats = [s for s in all_stats if s.year == last_year_per_country[s.country_id]]

            # Группируем по country_id и году, создаём словарь с тремя значениями
            data_by_country = {}
            for s in all_stats:
                if s.country_id not in data_by_country:
                    data_by_country[s.country_id] = {'year': s.year}
                if s.indicator_id == ind_ids['export_value']:
                    data_by_country[s.country_id]['export_value'] = s.value
                elif s.indicator_id == ind_ids['import_value']:
                    data_by_country[s.country_id]['import_value'] = s.value
                elif s.indicator_id == ind_ids['gdp_value']:
                    data_by_country[s.country_id]['gdp_value'] = s.value
                elif s.indicator_id == ind_ids['population_value']:
                    data_by_country[s.country_id]['population_value'] = s.value

            # Формируем список стран с полными данными
            rows = []
            for cid, vals in data_by_country.items():
                if all(k in vals for k in ['export_value', 'import_value', 'gdp_value', 'population_value']):
                    rows.append({
                        'country_id': cid,
                        'year': vals['year'],
                        'export_value': vals['export_value'],
                        'import_value': vals['import_value'],
                        'gdp_value': vals['gdp_value'],
                        'population_value': vals['population_value']
                    })

            if len(rows) < 3:
                return {'success': False, 'error': f'Недостаточно данных для кластеризации: {len(rows)} стран'}

            # Получаем названия стран
            country_repo = CountryRepository(conn)
            country_names = {c.id: c.name for c in country_repo.get_all()}

            # Создаём DataFrame
            df = pd.DataFrame(rows)
            df['country_name'] = df['country_id'].map(country_names)

            # Фильтр по положительным значениям
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