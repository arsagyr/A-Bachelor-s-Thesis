import numpy as np
from typing import Dict, Any, Optional
from database import with_db_connection
from repositories.country_repository import CountryRepository
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository
from calculations.auto_regression import auto_regression_forecast, compare_auto_regression_models


class ForecastService:

    AVAILABLE_MODELS = {
        'auto': 'Автоматический выбор',
        'linear': 'Линейная регрессия',
        'polynomial': 'Полиномиальная регрессия',
        'exponential': 'Экспоненциальная регрессия',
        'ridge': 'Ridge регрессия',
        'lasso': 'Lasso регрессия'
    }

    @staticmethod
    @with_db_connection
    def get_forecast(conn, country_id: int, indicator: str, steps: int = 5,
                     model_type: str = 'auto', degree: int = 2, alpha: float = 1.0) -> Dict[str, Any]:
        # Получаем id индикатора
        ind_repo = IndicatorRepository(conn)
        indicator_obj = ind_repo.get_by_name(indicator)
        if not indicator_obj:
            return {'success': False, 'error': f'Неизвестный индикатор: {indicator}'}

        # Получаем исторические данные
        stats_repo = StatisticsRepository(conn)
        all_stats = stats_repo.get_by_country(country_id)
        # Фильтруем по нужному индикатору и сортируем по году
        hist = [(s.year, s.value) for s in all_stats if s.indicator_id == indicator_obj.id and s.value is not None]
        hist.sort(key=lambda x: x[0])

        if len(hist) < 3:
            return {'success': False, 'error': f'Недостаточно данных: {len(hist)} точек'}

        historical_years = [h[0] for h in hist]
        historical_values = [h[1] for h in hist]

        # Получаем название страны
        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        # Прогноз
        if model_type == 'auto':
            result = compare_auto_regression_models(historical_values, steps)
            best_model_name = result.get('best_model')
            if best_model_name and best_model_name in result.get('all_models', {}):
                best_result = result['all_models'][best_model_name]
                result.update(best_result)
                result['model_type'] = best_model_name
                result['model_name'] = best_result.get('model_name', best_model_name)
                result['best_model'] = best_model_name
                result['best_model_name'] = result.get('best_model_name', best_model_name)
                result['best_r2'] = result.get('best_r2', 0)
        else:
            result = auto_regression_forecast(historical_values, steps, model_type, degree=degree, alpha=alpha)

        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Ошибка прогнозирования')}

        last_year = historical_years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]

        indicator_names = {
            'export_value': 'Экспорт',
            'import_value': 'Импорт',
            'gdp_value': 'ВВП'
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
                'mape': float(mape)
            },
            'formula': result.get('formula', ''),
            'unit': 'млрд USD',
            'r2': float(r2),
            'rmse': float(rmse),
            'mae': float(mae),
            'slope': slope,
            'intercept': intercept,
            'coefficients': coefficients,
            'degree': result.get('degree', degree)
        }

        # Модельные предсказания
        n = len(historical_values)
        total_points = n + steps
        model_predictions = []
        for i in range(total_points):
            x = i + 1
            pred = 0
            if actual_model_type == 'linear' and slope is not None and intercept is not None:
                pred = intercept + slope * x
            elif actual_model_type == 'polynomial' and coefficients:
                pred = intercept if intercept else 0
                for power, coeff in enumerate(coefficients, 1):
                    pred += coeff * (x ** power)
            elif actual_model_type == 'exponential' and slope is not None and intercept is not None:
                pred = np.exp(intercept + slope * x)
            elif actual_model_type in ['ridge', 'lasso'] and slope is not None:
                pred = intercept + slope * x if intercept else slope * x
            else:
                if i < n:
                    pred = historical_values[i]
                else:
                    forecast_list = result.get('forecast', [])
                    pred = forecast_list[i - n] if i - n < len(forecast_list) else 0
            model_predictions.append(pred)
        response['model_predictions'] = model_predictions

        if model_type == 'auto' and 'all_models' in result:
            response['all_models'] = result['all_models']
            response['best_model'] = result.get('best_model')
            response['best_model_name'] = result.get('best_model_name')
            response['best_r2'] = result.get('best_r2')

        return response