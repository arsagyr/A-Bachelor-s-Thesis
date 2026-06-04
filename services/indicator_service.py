from typing import Optional, List, Dict, Any, Tuple
from database import with_db_connection
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository


class IndicatorService:

    @staticmethod
    @with_db_connection
    def filter_indicators(conn,
                         country_id: Optional[int] = None,
                         start_year: Optional[int] = None,
                         end_year: Optional[int] = None,
                         indicator_type: str = 'all') -> List[Dict[str, Any]]:
        """
        Возвращает список показателей в старом формате:
        {id, year, export_value, import_value, gdp_value, country_name}
        id - составной, берём первое попавшееся значение (для совместимости)
        """
        stats_repo = StatisticsRepository(conn)
        ind_repo = IndicatorRepository(conn)

        # Получаем все записи с фильтрацией
        stats = stats_repo.filter(
            country_id=country_id,
            start_year=start_year,
            end_year=end_year
        )

        # Получаем mapping indicator_id -> indicator_name
        indicators = {ind.id: ind.name for ind in ind_repo.get_all()}

        # Группируем по (country_id, year) и создаём словарь
        from collections import defaultdict
        grouped = defaultdict(dict)
        for stat in stats:
            key = (stat.country_id, stat.year)
            ind_name = indicators.get(stat.indicator_id)
            if ind_name in ('export_value', 'import_value', 'gdp_value'):
                grouped[key][ind_name] = stat.value

        # Получаем названия стран
        from repositories.country_repository import CountryRepository
        country_repo = CountryRepository(conn)
        countries = {c.id: c.name for c in country_repo.get_all()}

        result = []
        # Генерируем искусственный id (для совместимости)
        fake_id = 1
        for (cid, year), values in grouped.items():
            row = {
                'id': fake_id,
                'year': year,
                'export_value': values.get('export_value'),
                'import_value': values.get('import_value'),
                'gdp_value': values.get('gdp_value'),
                'country_name': countries.get(cid, 'Unknown')
            }
            result.append(row)
            fake_id += 1

        # Сортировка по году
        result.sort(key=lambda x: x['year'])
        return result

    @staticmethod
    @with_db_connection
    def get_country_stats(conn, country_id: int) -> Optional[Dict[str, Any]]:
        stats_repo = StatisticsRepository(conn)
        ind_repo = IndicatorRepository(conn)

        # Получаем все записи для страны
        all_stats = stats_repo.get_by_country(country_id)
        if not all_stats:
            return None

        # Определим id нужных индикаторов
        indicators = {ind.name: ind.id for ind in ind_repo.get_all()}
        export_id = indicators.get('export_value')
        import_id = indicators.get('import_value')
        gdp_id = indicators.get('gdp_value')

        years = set(s.year for s in all_stats)

        # Фильтруем значения по индикаторам
        export_vals = [s.value for s in all_stats if s.indicator_id == export_id and s.value is not None]
        import_vals = [s.value for s in all_stats if s.indicator_id == import_id and s.value is not None]
        gdp_vals = [s.value for s in all_stats if s.indicator_id == gdp_id and s.value is not None]

        def safe_avg(lst):
            return sum(lst) / len(lst) if lst else None

        return {
            'years_count': len(years),
            'min_year': min(years) if years else None,
            'max_year': max(years) if years else None,
            'avg_export': float(safe_avg(export_vals)) if safe_avg(export_vals) is not None else None,
            'avg_import': float(safe_avg(import_vals)) if safe_avg(import_vals) is not None else None,
            'avg_gdp': float(safe_avg(gdp_vals)) if safe_avg(gdp_vals) is not None else None
        }

    @staticmethod
    @with_db_connection
    def get_available_years(conn) -> List[int]:
        stats_repo = StatisticsRepository(conn)
        return stats_repo.get_years()

    @staticmethod
    @with_db_connection
    def delete_indicator(conn, indicator_id: int) -> Tuple[bool, str]:
        """
        В новой схеме indicator_id - это id из справочника indicators.
        Удаляем сам индикатор и все связанные с ним значения (каскадно).
        """
        ind_repo = IndicatorRepository(conn)
        indicator = ind_repo.get_by_id(indicator_id)
        if not indicator:
            return False, "Индикатор не найден"

        try:
            # Удаляем все статистики для этого индикатора
            stats_repo = StatisticsRepository(conn)
            # В репозитории добавим метод delete_by_indicator
            stats_repo.delete_by_indicator(indicator_id)  # реализуем ниже
            # Удаляем справочную запись
            ind_repo.delete(indicator_id)
            conn.commit()
            return True, f"Индикатор '{indicator.name}' и его значения удалены"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {str(e)}"

    @staticmethod
    @with_db_connection
    def delete_indicators_by_country(conn, country_id: int) -> Tuple[bool, str]:
        stats_repo = StatisticsRepository(conn)
        try:
            deleted = stats_repo.delete_by_country(country_id)  # метод реализуем
            conn.commit()
            return True, f"Удалено {deleted} записей показателей для страны"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {str(e)}"