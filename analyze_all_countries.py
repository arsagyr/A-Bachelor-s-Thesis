#!/usr/bin/env python3
"""
Анализ всех стран: лучшие авторегрессионные модели (ВВП) и регрессионные модели (ВВП ~ экспорт + импорт)
Вывод метрик и формул уравнений.
"""

import sys
import pandas as pd
import numpy as np
from tabulate import tabulate

from database import Database, init_database
from services.indicator_service import IndicatorService
from services.country_service import CountryService

# Импорт функций для авторегрессии
from calculations.auto_regression import compare_auto_regression_models

# Импорт функций для регрессии
from calculations.regression_calc import train_regression_model
from sklearn.preprocessing import PolynomialFeatures


def prepare_regression_dataframe(data_list):
    """
    Преобразует список записей из БД в DataFrame с колонками export, import, gdp.
    Пропускает записи, где хотя бы одно значение None.
    """
    clean_data = []
    for row in data_list:
        export = row.get('export_value')
        import_val = row.get('import_value')
        gdp = row.get('gdp_value')
        # Проверяем, что все значения не None и могут быть преобразованы в float
        if export is not None and import_val is not None and gdp is not None:
            try:
                clean_data.append({
                    'export': float(export),
                    'import': float(import_val),
                    'gdp': float(gdp),
                    'year': row.get('year')
                })
            except (ValueError, TypeError):
                continue
    if not clean_data:
        return pd.DataFrame(columns=['export', 'import', 'gdp'])
    df = pd.DataFrame(clean_data)
    return df[['export', 'import', 'gdp']]


def build_regression_features(df):
    """
    Строит матрицу признаков для регрессии ВВП от экспорта и импорта.
    Признаки: экспорт, импорт, произведение, квадраты.
    Возвращает X, y, feature_names.
    """
    if df.empty:
        return None, None, None
    export = df['export'].values
    import_val = df['import'].values
    gdp = df['gdp'].values

    X = np.column_stack([
        export,
        import_val,
        export * import_val,
        export ** 2,
        import_val ** 2
    ])
    feature_names = ['экспорт', 'импорт', 'экспорт×импорт', 'экспорт²', 'импорт²']
    return X, gdp, feature_names


def compare_regression_models(df):
    """
    Сравнивает регрессионные модели ВВП = f(экспорт, импорт).
    Возвращает список моделей и лучшую модель (по R²).
    """
    X, y, feature_names = build_regression_features(df)
    if X is None or len(X) < 5:
        return [], None

    models = []

    # 1. Линейная регрессия
    res_lin = train_regression_model(X, y, model_type='linear')
    if 'error' not in res_lin:
        models.append({
            'name': 'Линейная регрессия',
            'type': 'linear',
            'coefficients': res_lin['coefficients'],
            'intercept': res_lin['intercept'],
            'metrics': res_lin['metrics'],
            'poly': False
        })

    # 2. Ridge регрессия
    res_ridge = train_regression_model(X, y, model_type='ridge', alpha=1.0)
    if 'error' not in res_ridge:
        models.append({
            'name': f'Ridge (α=1.0)',
            'type': 'ridge',
            'coefficients': res_ridge['coefficients'],
            'intercept': res_ridge['intercept'],
            'metrics': res_ridge['metrics'],
            'poly': False
        })

    # 3. Lasso регрессия
    res_lasso = train_regression_model(X, y, model_type='lasso', alpha=1.0)
    if 'error' not in res_lasso:
        models.append({
            'name': f'Lasso (α=1.0)',
            'type': 'lasso',
            'coefficients': res_lasso['coefficients'],
            'intercept': res_lasso['intercept'],
            'metrics': res_lasso['metrics'],
            'poly': False
        })

    # 4. Полиномиальная регрессия 2-й степени
    try:
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_poly = poly.fit_transform(X)
        res_poly = train_regression_model(X_poly, y, model_type='linear')
        if 'error' not in res_poly:
            models.append({
                'name': f'Полиномиальная (степень 2)',
                'type': 'poly2',
                'coefficients': res_poly['coefficients'],
                'intercept': res_poly['intercept'],
                'metrics': res_poly['metrics'],
                'poly': True,
                'degree': 2,
                'poly_features': poly
            })
    except Exception:
        pass

    if not models:
        return [], None

    best = max(models, key=lambda m: m['metrics']['r2'])
    return models, best


def format_regression_equation(model, feature_names):
    """Формирует строку уравнения регрессии."""
    if model.get('poly'):
        return "Полиномиальная модель (смотри коэффициенты в отдельном поле)"
    intercept = model['intercept']
    coeffs = model['coefficients']
    terms = [f"{intercept:.4f}"]
    for name, coef in zip(feature_names, coeffs):
        if abs(coef) > 1e-8:
            sign = '+' if coef >= 0 else '-'
            terms.append(f" {sign} {abs(coef):.4f}·{name}")
    return "ВВП = " + "".join(terms)


def analyze_all_countries(output_csv='country_analysis_results.csv'):
    """
    Основная функция: перебирает все страны, выполняет анализ и выводит результаты.
    """
    init_database()
    Database.init_pool()

    countries = CountryService.get_all_countries()
    if not countries:
        print("❌ Нет стран в базе данных.")
        return

    results_auto = []      # для авторегрессии ВВП
    results_reg = []       # для регрессии ВВП от экспорта/импорта

    print("\n" + "="*100)
    print(" АНАЛИЗ ВСЕХ СТРАН: АВТОРЕГРЕССИЯ ВВП И РЕГРЕССИЯ ВВП ~ ЭКСПОРТ + ИМПОРТ")
    print("="*100)

    for country in countries:
        country_id = country['id']
        country_name = country['name']

        # Получаем данные
        data = IndicatorService.filter_indicators(country_id=country_id)
        if len(data) < 5:
            print(f"\n⚠️ {country_name}: недостаточно данных ({len(data)} точек), пропускаем.")
            continue

        # Очищаем данные: убираем записи с None в любом из трёх показателей
        clean_data = []
        for row in data:
            if (row.get('export_value') is not None and 
                row.get('import_value') is not None and 
                row.get('gdp_value') is not None):
                try:
                    row['export_value'] = float(row['export_value'])
                    row['import_value'] = float(row['import_value'])
                    row['gdp_value'] = float(row['gdp_value'])
                    clean_data.append(row)
                except (ValueError, TypeError):
                    continue
        if len(clean_data) < 5:
            print(f"\n⚠️ {country_name}: недостаточно корректных данных ({len(clean_data)} точек), пропускаем.")
            continue

        # Извлекаем временной ряд ВВП
        gdp_series = [row['gdp_value'] for row in clean_data]

        # ------------------- 1. Авторегрессия ВВП -------------------
        ar_comparison = compare_auto_regression_models(gdp_series, steps=5)
        if ar_comparison.get('success') and ar_comparison.get('best_model'):
            best_ar = ar_comparison['all_models'][ar_comparison['best_model']]
            ar_metrics = best_ar.get('metrics', {})
            results_auto.append({
                'country': country_name,
                'best_model': best_ar.get('model_name', 'N/A'),
                'r2': ar_metrics.get('r2', np.nan),
                'rmse': ar_metrics.get('rmse', np.nan),
                'mae': ar_metrics.get('mae', np.nan),
                'mape': ar_metrics.get('mape', np.nan),
                'formula': best_ar.get('formula', 'N/A')
            })
        else:
            results_auto.append({
                'country': country_name,
                'best_model': 'Ошибка',
                'r2': np.nan,
                'rmse': np.nan,
                'mae': np.nan,
                'mape': np.nan,
                'formula': 'Не удалось построить модель'
            })

        # ------------------- 2. Регрессия ВВП от экспорта/импорта -------------------
        df = prepare_regression_dataframe(clean_data)
        if df.empty or len(df) < 5:
            results_reg.append({
                'country': country_name,
                'best_model': 'Ошибка',
                'r2': np.nan,
                'rmse': np.nan,
                'mae': np.nan,
                'mape': np.nan,
                'equation': 'Недостаточно данных',
                'intercept': None,
                'coeffs': None
            })
            continue

        reg_models, best_reg = compare_regression_models(df)
        if best_reg:
            reg_metrics = best_reg['metrics']
            _, _, feature_names = build_regression_features(df)
            equation = format_regression_equation(best_reg, feature_names)
            results_reg.append({
                'country': country_name,
                'best_model': best_reg['name'],
                'r2': reg_metrics.get('r2', np.nan),
                'rmse': reg_metrics.get('rmse', np.nan),
                'mae': reg_metrics.get('mae', np.nan),
                'mape': reg_metrics.get('mape', np.nan),
                'equation': equation,
                'intercept': best_reg['intercept'],
                'coeffs': str(best_reg['coefficients']) if not best_reg.get('poly') else 'полином'
            })
        else:
            results_reg.append({
                'country': country_name,
                'best_model': 'Ошибка',
                'r2': np.nan,
                'rmse': np.nan,
                'mae': np.nan,
                'mape': np.nan,
                'equation': 'Не удалось построить модель',
                'intercept': None,
                'coeffs': None
            })

    # Вывод результатов в консоль
    print("\n" + "="*100)
    print(" РЕЗУЛЬТАТЫ АВТОРЕГРЕССИОННОГО АНАЛИЗА ВВП (лучшая модель по R²)")
    print("="*100)
    df_auto = pd.DataFrame(results_auto)
    if not df_auto.empty:
        # Округляем метрики
        for col in ['r2', 'rmse', 'mae', 'mape']:
            if col in df_auto.columns:
                df_auto[col] = df_auto[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        print(tabulate(df_auto[['country', 'best_model', 'r2', 'rmse', 'mae', 'mape', 'formula']],
                       headers=['Страна', 'Лучшая AR-модель', 'R²', 'RMSE', 'MAE', 'MAPE(%)', 'Уравнение'],
                       tablefmt='grid', maxcolwidths=[20, 30, 8, 10, 10, 10, 50]))
    else:
        print("Нет данных.")

    print("\n" + "="*100)
    print(" РЕЗУЛЬТАТЫ РЕГРЕССИОННОГО АНАЛИЗА ВВП ОТ ЭКСПОРТА И ИМПОРТА")
    print("="*100)
    df_reg = pd.DataFrame(results_reg)
    if not df_reg.empty:
        for col in ['r2', 'rmse', 'mae', 'mape']:
            if col in df_reg.columns:
                df_reg[col] = df_reg[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        print(tabulate(df_reg[['country', 'best_model', 'r2', 'rmse', 'mae', 'mape', 'equation']],
                       headers=['Страна', 'Лучшая регрессия', 'R²', 'RMSE', 'MAE', 'MAPE(%)', 'Уравнение'],
                       tablefmt='grid', maxcolwidths=[20, 30, 8, 10, 10, 10, 60]))
    else:
        print("Нет данных.")

    # Сохраняем в CSV
    try:
        df_auto.to_csv(output_csv.replace('.csv', '_auto.csv'), index=False, encoding='utf-8-sig')
        df_reg.to_csv(output_csv.replace('.csv', '_reg.csv'), index=False, encoding='utf-8-sig')
        print(f"\n✅ Результаты сохранены в файлы: {output_csv.replace('.csv', '_auto.csv')} и {output_csv.replace('.csv', '_reg.csv')}")
    except Exception as e:
        print(f"\n⚠️ Не удалось сохранить CSV: {e}")

    Database.close_pool()


if __name__ == '__main__':
    analyze_all_countries()