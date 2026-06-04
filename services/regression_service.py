import numpy as np
import pandas as pd
from typing import Dict, Any
from database import with_db_connection
from repositories.country_repository import CountryRepository
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository
from calculations.regression_calc import (
    predict_gdp_by_regression,
    prepare_regression_features,
    train_regression_model,
    calculate_regression_statistics,
)


class RegressionService:

    # ------------------------------------------------------------------
    # Вспомогательный метод: загрузка данных из БД → DataFrame
    # ------------------------------------------------------------------

    @staticmethod
    def _load_dataframe(conn, country_id: int) -> tuple:
        """
        Возвращает (df, country_name) или (None, error_message).
        df содержит колонки year, export, import, gdp — только полные строки.
        """
        ind_repo = IndicatorRepository(conn)
        ind_ids = {}
        for name in ('export_value', 'import_value', 'gdp_value'):
            ind = ind_repo.get_by_name(name)
            if not ind:
                return None, f'Индикатор {name} не найден'
            ind_ids[name] = ind.id

        stats_repo = StatisticsRepository(conn)
        all_stats = stats_repo.get_by_country(country_id)

        data_by_year: Dict[int, Dict] = {}
        for s in all_stats:
            year = s.year
            row = data_by_year.setdefault(year, {})
            if s.indicator_id == ind_ids['export_value']:
                row['export'] = s.value
            elif s.indicator_id == ind_ids['import_value']:
                row['import'] = s.value
            elif s.indicator_id == ind_ids['gdp_value']:
                row['gdp'] = s.value

        rows = [
            {'year': year, **vals}
            for year, vals in sorted(data_by_year.items())
            if all(k in vals for k in ('export', 'import', 'gdp'))
        ]

        country_repo = CountryRepository(conn)
        country = country_repo.get_by_id(country_id)
        country_name = country.name if country else 'Unknown'

        if not rows:
            return None, 'Нет данных'

        return pd.DataFrame(rows), country_name

    # ------------------------------------------------------------------
    # Прогноз ВВП
    # ------------------------------------------------------------------

    @staticmethod
    @with_db_connection
    def get_gdp_forecast(
        conn,
        country_id: int,
        steps: int = 5,
        model_type: str = 'linear',
        **kwargs,
    ) -> Dict[str, Any]:

        df, country_name_or_err = RegressionService._load_dataframe(conn, country_id)
        if df is None:
            return {'success': False, 'error': country_name_or_err}

        if len(df) < 4:
            return {'success': False, 'error': f'Недостаточно данных: {len(df)} точек'}

        country_name = country_name_or_err
        historical_years = df['year'].tolist()
        historical_export = df['export'].tolist()
        historical_import = df['import'].tolist()
        historical_gdp = df['gdp'].tolist()
        last_year = historical_years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]

        result = predict_gdp_by_regression(df, steps, model_type, **kwargs)

        # Статистики значимости для линейной модели
        if result.get('success') and model_type == 'linear':
            X, y, _ = prepare_regression_features(df)
            coeffs = np.array(result.get('coefficients', []))
            intercept = result.get('intercept', 0.0)
            result['statistics'] = calculate_regression_statistics(X, y, coeffs, intercept)

        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Ошибка регрессии')}

        metrics = result.get('metrics', {})
        coefficients = result.get('coefficients', [])
        intercept = result.get('intercept', 0.0)
        export_forecast = result.get('export_forecast', [])
        import_forecast = result.get('import_forecast', [])
        gdp_forecast = result.get('forecast', [])

        # Модельные предсказания (исторические + прогнозные точки)
        coeffs_arr = np.array(coefficients, dtype=float)
        model_predictions = []
        for i in range(len(historical_years) + steps):
            if i < len(historical_years):
                pred_export = float(historical_export[i])
                pred_import = float(historical_import[i])
            else:
                idx = i - len(historical_years)
                pred_export = float(export_forecast[idx]) if idx < len(export_forecast) else float(historical_export[-1])
                pred_import = float(import_forecast[idx]) if idx < len(import_forecast) else float(historical_import[-1])

            features = np.array([
                pred_export, pred_import,
                pred_export * pred_import,
                pred_export ** 2,
                pred_import ** 2,
            ], dtype=float)
            model_predictions.append(float(intercept + np.dot(coeffs_arr, features)))

        # Формула
        names = ['Э', 'И', 'Э×И', 'Э²', 'И²']
        parts = [f"{intercept:.4f}"]
        for coef, name in zip(coefficients[:5], names):
            if abs(coef) > 1e-10:
                sign = '+' if coef > 0 else '-'
                parts.append(f" {sign} {abs(coef):.4f}·{name}")
        formula = "ВВП = " + ''.join(parts)

        return {
            'success': True,
            'country_name': country_name,
            'model_type': model_type,
            'historical': {
                'years': historical_years,
                'export': historical_export,
                'import': historical_import,
                'gdp': historical_gdp,
            },
            'forecast_years': forecast_years,
            'forecast': {
                'export': export_forecast,
                'import': import_forecast,
                'gdp': gdp_forecast,
            },
            'model_predictions': model_predictions,
            'metrics': {
                'r2': metrics.get('r2', 0),
                'rmse': metrics.get('rmse', 0),
                'mae': metrics.get('mae', 0),
                'mape': metrics.get('mape', 0),
            },
            'coefficients': coefficients,
            'intercept': intercept,
            'formula': formula,
        }

    # ------------------------------------------------------------------
    # Статистики значимости
    # ------------------------------------------------------------------

    @staticmethod
    @with_db_connection
    def get_regression_statistics(
        conn,
        country_id: int,
        model_type: str = 'linear',
    ) -> Dict[str, Any]:
        """
        Расчёт t-критерия Стьюдента для коэффициентов, F-критерия Фишера
        для модели, скорректированного R² и p-значений.
        """
        df, country_name_or_err = RegressionService._load_dataframe(conn, country_id)
        if df is None:
            return {'success': False, 'error': country_name_or_err}

        if len(df) < 4:
            return {'success': False, 'error': f'Недостаточно данных: {len(df)} точек'}

        country_name = country_name_or_err
        X, y, _ = prepare_regression_features(df)

        model_result = train_regression_model(X, y, model_type=model_type)
        if not model_result.get('success'):
            return {'success': False, 'error': model_result.get('error')}

        # train_regression_model уже вкладывает statistics для linear;
        # для ridge/lasso считаем отдельно (смещённые оценки — информационно)
        if 'statistics' in model_result:
            stats_data = model_result['statistics']
        else:
            coeffs = np.array(model_result['coefficients'])
            intercept = model_result['intercept']
            stats_data = calculate_regression_statistics(X, y, coeffs, intercept)

        return {
            'success': True,
            'country_name': country_name,
            'model_type': model_type,
            'statistics': stats_data,
            'metrics': model_result.get('metrics', {}),
        }