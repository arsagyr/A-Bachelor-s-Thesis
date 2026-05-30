import numpy as np
import pandas as pd
from typing import Dict, Any
from database import with_db_connection
from repositories.country_repository import CountryRepository
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository
from calculations.regression_calc import predict_gdp_by_regression


class RegressionService:

    @staticmethod
    @with_db_connection
    def get_gdp_forecast(conn, country_id: int, steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
        # Получаем id индикаторов
        ind_repo = IndicatorRepository(conn)
        ind_ids = {}
        for name in ['export_value', 'import_value', 'gdp_value']:
            ind = ind_repo.get_by_name(name)
            if not ind:
                return {'success': False, 'error': f'Индикатор {name} не найден'}
            ind_ids[name] = ind.id

        # Получаем статистику
        stats_repo = StatisticsRepository(conn)
        all_stats = stats_repo.get_by_country(country_id)

        # Собираем историю по годам
        data_by_year = {}
        for s in all_stats:
            year = s.year
            if year not in data_by_year:
                data_by_year[year] = {}
            if s.indicator_id == ind_ids['export_value']:
                data_by_year[year]['export'] = s.value
            elif s.indicator_id == ind_ids['import_value']:
                data_by_year[year]['import'] = s.value
            elif s.indicator_id == ind_ids['gdp_value']:
                data_by_year[year]['gdp'] = s.value

        # Преобразуем в список и сортируем
        rows = []
        for year, vals in sorted(data_by_year.items()):
            if all(k in vals for k in ['export', 'import', 'gdp']):
                rows.append({
                    'year': year,
                    'export': vals['export'],
                    'import': vals['import'],
                    'gdp': vals['gdp']
                })

        if len(rows) < 4:
            return {'success': False, 'error': f'Недостаточно данных: {len(rows)} точек'}

        df = pd.DataFrame(rows)

        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        historical_years = df['year'].tolist()
        historical_export = df['export'].tolist()
        historical_import = df['import'].tolist()
        historical_gdp = df['gdp'].tolist()
        last_year = historical_years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]

        result = predict_gdp_by_regression(df, steps, model_type, **kwargs)

        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Ошибка регрессии')}

        metrics = result.get('metrics', {})
        coefficients = result.get('coefficients', [])   # теперь 5 коэффициентов
        intercept = result.get('intercept', 0)
        export_forecast = result.get('export_forecast', [])
        import_forecast = result.get('import_forecast', [])
        gdp_forecast = result.get('forecast', [])

        # Модельные предсказания (на исторических + прогнозных)
        n = len(historical_years)
        total_points = n + steps
        model_predictions = []
        for i in range(total_points):
            if i < n:
                # исторические данные – используем фактические значения
                pred_export = historical_export[i]
                pred_import = historical_import[i]
            else:
                idx = i - n
                pred_export = export_forecast[idx] if idx < len(export_forecast) else historical_export[-1]
                pred_import = import_forecast[idx] if idx < len(import_forecast) else historical_import[-1]
            
            # Только 5 признаков: экспорт, импорт, произведение, квадраты
            features = np.array([
                pred_export, pred_import,
                pred_export * pred_import,
                pred_export ** 2,
                pred_import ** 2
            ], dtype=float)
            coeffs = np.array(coefficients, dtype=float)
            pred_gdp = intercept + np.sum(coeffs * features)
            model_predictions.append(float(pred_gdp))

        # Формула (только 5 слагаемых)
        formula_parts = [f"{intercept:.4f}"]
        names = ['Э', 'И', 'Э×И', 'Э²', 'И²']
        for i, (coef, name) in enumerate(zip(coefficients[:5], names[:5])):
            if abs(coef) > 1e-10:
                sign = '+' if coef > 0 else '-'
                formula_parts.append(f" {sign} {abs(coef):.4f}·{name}")
        formula = "ВВП = " + ''.join(formula_parts)

        return {
            'success': True,
            'country_name': country_name,
            'model_type': model_type,
            'historical': {
                'years': historical_years,
                'export': historical_export,
                'import': historical_import,
                'gdp': historical_gdp
            },
            'forecast_years': forecast_years,
            'forecast': {
                'export': export_forecast,
                'import': import_forecast,
                'gdp': gdp_forecast
            },
            'model_predictions': model_predictions,
            'metrics': {
                'r2': metrics.get('r2', 0),
                'rmse': metrics.get('rmse', 0),
                'mae': metrics.get('mae', 0),
                'mape': metrics.get('mape', 0)
            },
            'coefficients': coefficients,
            'intercept': intercept,
            'formula': formula
        }