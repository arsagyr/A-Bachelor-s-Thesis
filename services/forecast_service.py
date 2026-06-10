import numpy as np
from typing import Dict, Any, Optional, List
from database import with_db_connection
from repositories.country_repository import CountryRepository
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository
from calculations.auto_regression import auto_regression_forecast, compare_auto_regression_models, irwin_criterion, t_test_slope


class ForecastService:

    AVAILABLE_MODELS = {
        'auto': 'Автоматический выбор',
        'linear': 'Линейная регрессия',
        'polynomial': 'Полиномиальная регрессия',
        'exponential': 'Экспоненциальная регрессия',
        'ridge': 'Ridge регрессия',
        'lasso': 'Lasso регрессия',
    }

    @staticmethod
    def _get_trend_strength(t_statistic: float, n: int) -> str:
        """Оценка силы тренда на основе t-статистики."""
        if t_statistic > 10:
            return "Очень сильный"
        elif t_statistic > 5:
            return "Сильный"
        elif t_statistic > 3:
            return "Умеренный"
        elif t_statistic > 2:
            return "Слабый"
        else:
            return "Очень слабый или отсутствует"

    @staticmethod
    @with_db_connection
    def check_irwin(conn, country_id: int, indicator: str, threshold: float = 3.0) -> Dict[str, Any]:
        """
        Проверка временного ряда на аномалии по критерию Ирвина.
        Дополнительно выводит t-статистику и p-значение для тренда.
        """
        ind_repo = IndicatorRepository(conn)
        indicator_obj = ind_repo.get_by_name(indicator)
        if not indicator_obj:
            return {'success': False, 'error': f'Неизвестный индикатор: {indicator}'}

        stats_repo = StatisticsRepository(conn)
        all_stats = stats_repo.get_by_country(country_id)
        hist = sorted(
            [(s.year, s.value) for s in all_stats
             if s.indicator_id == indicator_obj.id and s.value is not None],
            key=lambda x: x[0],
        )

        if len(hist) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(hist)} точек'}

        years = [y for y, _ in hist]
        values = [v for _, v in hist]

        # Критерий Ирвина
        irwin_result = irwin_criterion(values, threshold)

        if irwin_result.get('error'):
            return {'success': False, 'error': irwin_result['error']}

        # t-тест значимости тренда (Стьюдент)
        ttest_result = t_test_slope(values, alpha=0.05)

        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        indicator_names = {
            'export_value': 'Экспорт',
            'import_value': 'Импорт',
            'gdp_value': 'ВВП',
        }

        outliers_with_years = [
            {
                'year': years[o['index']],
                'value': o['value'],
                'lambda': o['lambda'],
                'prev_value': o['prev_value'],
                'prev_year': years[o['index'] - 1],
            }
            for o in irwin_result.get('outliers', [])
        ]

        # Формируем ответ
        response = {
            'success': True,
            'country_name': country_name,
            'indicator_name': indicator_names.get(indicator, indicator),
            'threshold': threshold,
            'sigma_diff': irwin_result['sigma_diff'],
            'outliers': outliers_with_years,
            'outlier_count': irwin_result['outlier_count'],
            'all_lambda': irwin_result['all_lambda'],
        }

        # Добавляем t-тест, если он успешен
        if 'error' not in ttest_result:
            response['trend_test'] = {
                'slope': ttest_result['slope'],
                'std_error': ttest_result['std_error'],
                't_statistic': ttest_result['t_statistic'],
                'p_value': ttest_result['p_value'],
                'significant': ttest_result['significant'],
                'alpha': ttest_result['alpha'],
                'interpretation': 'Тренд статистически значим' if ttest_result['significant'] else 'Тренд не значим'
            }
        else:
            response['trend_test'] = {'error': ttest_result['error']}

        return response

    @staticmethod
    @with_db_connection
    def check_trend_significance(conn, country_id: int, indicator: str, alpha: float = 0.05) -> Dict[str, Any]:
        """
        Отдельный метод для проверки значимости тренда по t-критерию Стьюдента.
        """
        ind_repo = IndicatorRepository(conn)
        indicator_obj = ind_repo.get_by_name(indicator)
        if not indicator_obj:
            return {'success': False, 'error': f'Неизвестный индикатор: {indicator}'}

        stats_repo = StatisticsRepository(conn)
        all_stats = stats_repo.get_by_country(country_id)
        hist = sorted(
            [(s.year, s.value) for s in all_stats
             if s.indicator_id == indicator_obj.id and s.value is not None],
            key=lambda x: x[0],
        )

        if len(hist) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(hist)} точек'}

        years = [y for y, _ in hist]
        values = [v for _, v in hist]

        ttest_result = t_test_slope(values, alpha=alpha)

        if 'error' in ttest_result:
            return {'success': False, 'error': ttest_result['error']}

        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        indicator_names = {
            'export_value': 'Экспорт',
            'import_value': 'Импорт',
            'gdp_value': 'ВВП',
        }

        # Расчёт дополнительных метрик
        n = len(values)
        mean_value = np.mean(values)
        std_value = np.std(values, ddof=1)
        cv = std_value / mean_value * 100 if mean_value != 0 else None

        # Годовой темп роста (средний)
        if n > 1:
            growth_rates = [(values[i] - values[i-1]) / values[i-1] * 100 for i in range(1, n) if values[i-1] != 0]
            avg_growth_rate = np.mean(growth_rates) if growth_rates else None
        else:
            avg_growth_rate = None

        return {
            'success': True,
            'country_name': country_name,
            'indicator_name': indicator_names.get(indicator, indicator),
            'years': years,
            'values': values,
            'statistics': {
                'n': n,
                'mean': float(mean_value),
                'std': float(std_value),
                'cv_percent': float(cv) if cv is not None else None,
                'avg_growth_rate_percent': float(avg_growth_rate) if avg_growth_rate is not None else None,
            },
            'trend_test': {
                'slope': float(ttest_result['slope']),
                'std_error': float(ttest_result['std_error']),
                't_statistic': float(ttest_result['t_statistic']),
                'p_value': float(ttest_result['p_value']),
                'alpha': ttest_result['alpha'],
                'significant': ttest_result['significant'],
                'critical_value': round(ttest_result['t_statistic'], 4) if abs(ttest_result['t_statistic']) > 0 else None,
            },
            'interpretation': {
                'trend': 'Тренд статистически значим' if ttest_result['significant'] else 'Тренд не значим',
                'direction': 'Положительный (рост)' if ttest_result['slope'] > 0 else 'Отрицательный (снижение)',
                'strength': ForecastService._get_trend_strength(abs(ttest_result['t_statistic']), n)
            }
        }

    @staticmethod
    @with_db_connection
    def get_forecast(
        conn,
        country_id: int,
        indicator: str,
        steps: int = 5,
        model_type: str = 'auto',
        degree: int = 2,
        alpha: float = 1.0,
    ) -> Dict[str, Any]:

        ind_repo = IndicatorRepository(conn)
        indicator_obj = ind_repo.get_by_name(indicator)
        if not indicator_obj:
            return {'success': False, 'error': f'Неизвестный индикатор: {indicator}'}

        stats_repo = StatisticsRepository(conn)
        all_stats = stats_repo.get_by_country(country_id)
        hist = sorted(
            [(s.year, s.value) for s in all_stats
             if s.indicator_id == indicator_obj.id and s.value is not None],
            key=lambda x: x[0],
        )

        if len(hist) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(hist)} точек'}

        historical_years = [h[0] for h in hist]
        historical_values = [h[1] for h in hist]

        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        if model_type == 'auto':
            result = compare_auto_regression_models(historical_values, steps)
            best_model_name = result.get('best_model')
            if best_model_name and best_model_name in result.get('all_models', {}):
                best_result = result['all_models'][best_model_name]
                result.update(best_result)
                result['model_type'] = best_model_name
                result['model_name'] = best_result.get('model_name', best_model_name)
                result['best_model'] = best_model_name
        else:
            result = auto_regression_forecast(
                historical_values, steps, model_type, degree=degree, alpha=alpha
            )

        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Ошибка прогнозирования')}

        last_year = historical_years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]

        indicator_names = {
            'export_value': 'Экспорт',
            'import_value': 'Импорт',
            'gdp_value': 'ВВП',
        }

        metrics = result.get('metrics', {})
        r2 = metrics.get('r2', result.get('r2', 0))
        rmse = metrics.get('rmse', result.get('rmse', 0))
        mae = metrics.get('mae', result.get('mae', 0))
        mape = metrics.get('mape', result.get('mape', 0))

        slope = result.get('slope')
        intercept = result.get('intercept')
        coefficients = result.get('coefficients')
        actual_model_type = result.get('model_type', model_type)

        response = {
            'success': True,
            'country_name': country_name,
            'indicator_name': indicator_names.get(indicator, indicator),
            'historical_years': historical_years,
            'historical_values': historical_values,
            'forecast_years': forecast_years,
            'forecast': result.get('forecast', []),
            'model_type': actual_model_type,
            'model_name': result.get('model_name', ForecastService.AVAILABLE_MODELS.get(model_type, model_type)),
            'metrics': {
                'r2': float(r2),
                'rmse': float(rmse),
                'mae': float(mae),
                'mape': float(mape),
            },
            'formula': result.get('formula', ''),
            'unit': 'млрд USD',
            'r2': float(r2),
            'rmse': float(rmse),
            'mae': float(mae),
            'slope': slope,
            'intercept': intercept,
            'coefficients': coefficients,
            'degree': result.get('degree', degree),
        }

        # Добавляем t-тест значимости тренда для полученной модели
        ttest_result = t_test_slope(historical_values, alpha=0.05)
        if 'error' not in ttest_result:
            response['trend_significance'] = {
                't_statistic': ttest_result['t_statistic'],
                'p_value': ttest_result['p_value'],
                'significant': ttest_result['significant'],
                'interpretation': 'Тренд статистически значим' if ttest_result['significant'] else 'Тренд не значим'
            }

        # Модельные предсказания по всей оси t (исторические + прогнозные)
        n = len(historical_values)
        model_predictions = []
        for i in range(n + steps):
            x = i + 1
            if actual_model_type == 'linear' and slope is not None and intercept is not None:
                pred = intercept + slope * x
            elif actual_model_type == 'polynomial' and coefficients:
                pred = intercept if intercept else 0
                for power, coeff in enumerate(coefficients, 1):
                    pred += coeff * (x ** power)
            elif actual_model_type == 'exponential' and slope is not None and intercept is not None:
                pred = np.exp(intercept + slope * x)
            elif actual_model_type in ('ridge', 'lasso') and slope is not None:
                pred = (intercept or 0) + slope * x
            else:
                forecast_list = result.get('forecast', [])
                pred = historical_values[i] if i < n else (forecast_list[i - n] if i - n < len(forecast_list) else 0)
            model_predictions.append(pred)
        response['model_predictions'] = model_predictions

        if model_type == 'auto' and 'all_models' in result:
            response['all_models'] = result['all_models']
            response['best_model'] = result.get('best_model')
            response['best_model_name'] = result.get('best_model_name')
            response['best_r2'] = result.get('best_r2')

        return response

    @staticmethod
    @with_db_connection
    def compare_trends(conn, country_id: int) -> Dict[str, Any]:
        """
        Сравнение трендов для экспорта, импорта и ВВП одной страны.
        """
        indicators = ['export_value', 'import_value', 'gdp_value']
        results = {}

        for indicator in indicators:
            result = ForecastService.check_trend_significance(conn, country_id, indicator)
            if result.get('success'):
                # Извлекаем название индикатора для отображения
                ind_name = result['indicator_name']
                results[ind_name] = {
                    'indicator_name': ind_name,
                    'trend_significant': result['trend_test']['significant'],
                    't_statistic': result['trend_test']['t_statistic'],
                    'p_value': result['trend_test']['p_value'],
                    'slope': result['trend_test']['slope'],
                    'direction': result['interpretation']['direction'],
                    'strength': result['interpretation']['strength'],
                    'mean_value': result['statistics']['mean'],
                    'avg_growth_rate': result['statistics'].get('avg_growth_rate_percent'),
                }
            else:
                results[indicator] = {'error': result.get('error')}

        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        return {
            'success': True,
            'country_name': country_name,
            'results': results
        }