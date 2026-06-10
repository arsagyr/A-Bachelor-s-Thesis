#!/usr/bin/env python3
"""
Консольная программа для регрессионного и авторегрессионного анализа экономических данных
Добавлены критерии Ирвина, Стьюдента, Фишера для оценки качества.
"""

import sys
import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from database import Database, init_database
from services.indicator_service import IndicatorService
from services.country_service import CountryService

# Реальные импорты из calculations
from calculations import (
    prepare_regression_features,
    auto_regression_forecast,
    compare_auto_regression_models,
    calculate_metrics,
)
from calculations.regression_calc import train_regression_model
from calculations.auto_regression import (
    polynomial_trend,
    exponential_trend,
    ridge_trend,
    lasso_trend,
    irwin_criterion,
    t_test_slope,
)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def convert_data_to_float(data_list):
    """Преобразует числовые значения в float, пропуская None."""
    for row in data_list:
        for key in ['export_value', 'import_value', 'gdp_value']:
            if key in row and row[key] is not None:
                try:
                    row[key] = float(row[key])
                except (ValueError, TypeError):
                    row[key] = None
    return data_list

def filter_valid_records(data_list):
    """Удаляет записи, содержащие None в ключевых полях."""
    valid = []
    for row in data_list:
        if (row.get('export_value') is not None and 
            row.get('import_value') is not None and 
            row.get('gdp_value') is not None):
            valid.append(row)
    return valid

def prepare_dataframe_from_records(data_list):
    df = pd.DataFrame([
        {'export': row['export_value'],
         'import': row['import_value'],
         'gdp': row['gdp_value']}
        for row in data_list
    ])
    return df

def linear_regression_analysis(X, y, feature_names):
    result = train_regression_model(X, y, model_type='linear')
    if 'error' in result:
        return None
    return {
        'name': 'Линейная регрессия',
        'model': None,
        'coefficients': result['coefficients'],
        'intercept': result['intercept'],
        'metrics': result['metrics'],
        'statistics': result.get('statistics'),
    }

def ridge_regression_analysis(X, y, feature_names, alpha=1.0):
    result = train_regression_model(X, y, model_type='ridge', alpha=alpha)
    if 'error' in result:
        return None
    return {
        'name': f'Ridge регрессия (α={alpha})',
        'model': None,
        'coefficients': result['coefficients'],
        'intercept': result['intercept'],
        'metrics': result['metrics'],
    }

def lasso_regression_analysis(X, y, feature_names, alpha=1.0):
    result = train_regression_model(X, y, model_type='lasso', alpha=alpha)
    if 'error' in result:
        return None
    return {
        'name': f'Lasso регрессия (α={alpha})',
        'model': None,
        'coefficients': result['coefficients'],
        'intercept': result['intercept'],
        'metrics': result['metrics'],
    }

def polynomial_regression_analysis(X, y, feature_names, degree=2):
    poly = PolynomialFeatures(degree=degree, include_bias=False)
    X_poly = poly.fit_transform(X)
    result = train_regression_model(X_poly, y, model_type='linear')
    if 'error' in result:
        return None
    return {
        'name': f'Полиномиальная регрессия (степень {degree})',
        'model': None,
        'coefficients': result['coefficients'],
        'intercept': result['intercept'],
        'metrics': result['metrics'],
        'poly': True,
        'degree': degree,
        'poly_features': poly,
    }

def compare_all_models(X, y, feature_names):
    models = []
    m1 = linear_regression_analysis(X, y, feature_names)
    if m1: models.append(m1)
    m2 = ridge_regression_analysis(X, y, feature_names, alpha=1.0)
    if m2: models.append(m2)
    m3 = lasso_regression_analysis(X, y, feature_names, alpha=1.0)
    if m3: models.append(m3)
    m4 = polynomial_regression_analysis(X, y, feature_names, degree=2)
    if m4: models.append(m4)
    if len(X) >= 5:
        m5 = polynomial_regression_analysis(X, y, feature_names, degree=3)
        if m5: models.append(m5)
    if not models:
        return [], None
    best = max(models, key=lambda m: m['metrics']['r2'])
    return models, best

def forecast_gdp(coefs, intercept, export_val, import_val):
    features = np.array([export_val, import_val,
                         export_val*import_val,
                         export_val**2, import_val**2])
    return intercept + np.sum(coefs * features)

def auto_regression_with_confidence(series, steps, model_type='linear',
                                    confidence_level=0.95, degree=2, alpha=1.0):
    forecast_result = auto_regression_forecast(
        series, steps=steps, model_type=model_type,
        degree=degree, alpha=alpha
    )
    if not forecast_result.get('success'):
        return forecast_result
    # Получить предсказания на истории для расчёта остатков
    if model_type == 'linear':
        from calculations.auto_regression import linear_trend
        hist = linear_trend(series, steps=0)
        y_pred = np.array(hist.get('predicted', [np.nan]*len(series))) if hist.get('success') else np.array([np.nan]*len(series))
    elif model_type == 'polynomial':
        hist = polynomial_trend(series, steps=0, degree=degree)
        y_pred = np.array(hist.get('predicted', [np.nan]*len(series))) if hist.get('success') else np.array([np.nan]*len(series))
    elif model_type == 'exponential':
        hist = exponential_trend(series, steps=0)
        y_pred = np.array(hist.get('predicted', [np.nan]*len(series))) if hist.get('success') else np.array([np.nan]*len(series))
    elif model_type == 'ridge':
        hist = ridge_trend(series, steps=0, alpha=alpha)
        y_pred = np.array(hist.get('predicted', [np.nan]*len(series))) if hist.get('success') else np.array([np.nan]*len(series))
    elif model_type == 'lasso':
        hist = lasso_trend(series, steps=0, alpha=alpha)
        y_pred = np.array(hist.get('predicted', [np.nan]*len(series))) if hist.get('success') else np.array([np.nan]*len(series))
    else:
        y_pred = np.array([np.nan]*len(series))

    residuals = np.array(series) - y_pred
    valid = ~np.isnan(residuals)
    if np.sum(valid) < 2:
        return {**forecast_result, 'error': 'Недостаточно данных для доверительных интервалов'}
    resid_std = np.std(residuals[valid], ddof=1)
    n = len(series)
    t_val = stats.t.ppf((1+confidence_level)/2, df=n-2)
    future_steps = np.arange(1, steps+1)
    x_hist = np.arange(1, n+1)
    mean_x = np.mean(x_hist)
    se_forecast = resid_std * np.sqrt(1 + 1/n + (future_steps - mean_x)**2 / np.sum((x_hist - mean_x)**2))
    margin = t_val * se_forecast
    forecast_vals = np.array(forecast_result['forecast'])
    forecast_result['lower_bounds'] = (forecast_vals - margin).tolist()
    forecast_result['upper_bounds'] = (forecast_vals + margin).tolist()
    forecast_result['confidence_level'] = confidence_level
    return forecast_result


# ==================== ФУНКЦИИ ВЫВОДА ====================

def print_header(text, char='='):
    print("\n" + char * 80)
    print(f" {text}")
    print(char * 80)

def print_subheader(text, char='-'):
    print(f"\n{char * 60}")
    print(f" {text}")
    print(char * 60)

def print_section(text):
    print(f"\n▶ {text}")

def print_country_list(countries):
    print_header("СПИСОК СТРАН")
    print(f"{'ID':<6} {'Название'}")
    print("-" * 40)
    for c in countries:
        print(f"{c['id']:<6} {c['name']}")
    print()

def print_data_table(data, title="ИСТОРИЧЕСКИЕ ДАННЫЕ"):
    print_header(title)
    print(f"{'Год':<8} {'Экспорт':<18} {'Импорт':<18} {'ВВП':<18}")
    print("-" * 65)
    for row in data:
        print(f"{row['year']:<8} {row['export_value']:<18.2f} {row['import_value']:<18.2f} {row['gdp_value']:<18.2f}")
    print()

def print_series_stats(series, name):
    print_section(f"Статистика ряда {name}")
    print(f"   Количество точек: {len(series)}")
    print(f"   Минимум: {min(series):.2f}")
    print(f"   Максимум: {max(series):.2f}")
    print(f"   Среднее: {np.mean(series):.2f}")
    print(f"   Медиана: {np.median(series):.2f}")
    print(f"   Стандартное отклонение: {np.std(series):.2f}")

def print_irwin_analysis(series, name, threshold=3.0):
    """Вывод аномалий по критерию Ирвина и t-теста наклона"""
    print_section(f"Критерий Ирвина для ряда {name}")
    irwin = irwin_criterion(series, threshold=threshold)
    if 'error' in irwin:
        print(f"   ⚠️ {irwin['error']}")
    else:
        print(f"   Порог: {threshold}")
        print(f"   СКО разностей: {irwin['sigma_diff']:.4f}")
        if irwin['outlier_count'] == 0:
            print(f"   ✅ Аномалий не обнаружено")
        else:
            print(f"   ⚠️ Найдено аномалий: {irwin['outlier_count']}")
            for o in irwin['outliers'][:5]:
                print(f"      Год {o['index']+1} (значение {o['value']:.2f}, λ={o['lambda']:.2f})")
            if irwin['outlier_count'] > 5:
                print(f"      ... и ещё {irwin['outlier_count']-5}")

    print_section(f"Проверка значимости тренда (t-критерий Стьюдента) для {name}")
    ttest = t_test_slope(series, alpha=0.05)
    if 'error' in ttest:
        print(f"   ⚠️ {ttest['error']}")
    else:
        print(f"   Наклон тренда: {ttest['slope']:.6f}")
        print(f"   t-статистика: {ttest['t_statistic']:.4f}")
        print(f"   p-значение: {ttest['p_value']:.6f}")
        if ttest['significant']:
            print(f"   ✅ Тренд статистически значим (p < {ttest['alpha']})")
        else:
            print(f"   ❌ Тренд не значим (p >= {ttest['alpha']})")

def print_regression_statistics(statistics):
    """Вывод t-статистик и F-теста из регрессии"""
    if not statistics:
        print("   Статистики недоступны (модель не линейная или ошибка)")
        return
    print_section("Статистическая значимость коэффициентов (критерий Стьюдента)")
    coefs = statistics['coefficients']
    print(f"   {'Переменная':<20} {'Коэфф.':<12} {'Ст.ошибка':<12} {'t-стат.':<12} {'p-знач.':<12} {'Значим?'}")
    print("   " + "-"*75)
    # Интерсепт
    i = coefs['intercept']
    pval = i['p_value']
    sig = "Да" if pval is not None and pval < 0.05 else "Нет"
    print(f"   {'Константа':<20} {i['value']:<12.4f} {i['std_error']:<12.4f} {i['t_statistic']:<12.4f} {pval:<12.6f} {sig}")
    for f in coefs['features']:
        pval = f['p_value']
        sig = "Да" if pval is not None and pval < 0.05 else "Нет"
        # Исправлено: без вложенной f-строки
        print(f"   Признак {f['index']:<13} {f['value']:<12.4f} {f['std_error']:<12.4f} {f['t_statistic']:<12.4f} {pval:<12.6f} {sig}")

    print_section("Общая значимость модели (критерий Фишера)")
    fstat = statistics['f_statistic']
    print(f"   F-статистика: {fstat['value']:.4f}")
    print(f"   p-значение: {fstat['p_value']:.6f}")
    print(f"   Число степеней свободы: модель={fstat['df_model']}, остаток={fstat['df_residual']}")
    if fstat['p_value'] is not None and fstat['p_value'] < 0.05:
        print("   ✅ Модель в целом значима (p < 0.05)")
    else:
        print("   ❌ Модель не значима (p >= 0.05)")

def print_auto_regression_details(series, steps, model_type, result, data):
    print_header(f"АВТОРЕГРЕССИОННЫЙ ПРОГНОЗ: {model_type.upper()}")
    print_series_stats(series, "исходных данных")
    print_section("Параметры прогноза")
    print(f"   Модель: {result.get('model_name', model_type)}")
    print(f"   Горизонт прогноза: {steps} лет")
    print(f"   Формула тренда: {result.get('formula', 'N/A')}")
    print_section("Метрики качества модели")
    print(f"   R²   : {result.get('r2', 0):.6f}")
    print(f"   RMSE : {result.get('rmse', 0):.2f}")
    print(f"   MAE  : {result.get('mae', 0):.2f}")
    print(f"   MAPE : {result.get('mape', 0):.2f}%")
    r2 = result.get('r2', 0)
    if r2 >= 0.9: quality = "Отличное качество"
    elif r2 >= 0.7: quality = "Хорошее качество"
    elif r2 >= 0.5: quality = "Удовлетворительное качество"
    else: quality = "Низкое качество"
    print(f"   Оценка качества: {quality}")

    last_year = data[-1]['year'] if data else 2023
    print_section("Пошаговый прогноз")
    for i, val in enumerate(result['forecast']):
        year = last_year + i + 1
        print(f"   {year}: {val:.2f} млрд USD")

def print_auto_regression_results(data, indicator_name, forecast_result):
    print_subheader(f"АВТОРЕГРЕССИОННЫЙ ПРОГНОЗ {indicator_name}")
    if not forecast_result.get('success'):
        print(f"   ❌ Ошибка: {forecast_result.get('error')}")
        return
    print(f"\n   Модель: {forecast_result.get('model_name', forecast_result.get('model_type', 'N/A'))}")
    print("\n📊 МЕТРИКИ КАЧЕСТВА МОДЕЛИ:")
    print(f"   RMSE = {forecast_result.get('rmse', 0):.2f} млрд USD")
    print(f"   MAE  = {forecast_result.get('mae', 0):.2f} млрд USD")
    print(f"   R²   = {forecast_result.get('r2', 0):.4f}")
    print(f"   MAPE = {forecast_result.get('mape', 0):.2f}%")
    print(f"\n📐 ФОРМУЛА ТРЕНДА:")
    print(f"   {forecast_result.get('formula', 'N/A')}")
    print(f"\n🔮 ПРОГНОЗ НА {len(forecast_result['forecast'])} ЛЕТ:")
    last_year = data[-1]['year']
    for i, val in enumerate(forecast_result['forecast']):
        year = last_year + i + 1
        print(f"   {year}: {val:.2f} млрд USD")
    if 'lower_bounds' in forecast_result:
        conf = int(forecast_result.get('confidence_level', 0.95)*100)
        print(f"\n📊 ДОВЕРИТЕЛЬНЫЕ ИНТЕРВАЛЫ ({conf}%):")
        for i, val in enumerate(forecast_result['forecast']):
            year = last_year + i + 1
            print(f"   {year}: [{forecast_result['lower_bounds'][i]:.2f} ; {forecast_result['upper_bounds'][i]:.2f}]")

def print_regression_analysis_details(X, y, feature_names, models, best_model, data):
    print_header("РЕГРЕССИОННЫЙ АНАЛИЗ ВВП")
    print_section("Информация о данных")
    print(f"   Количество наблюдений: {len(y)}")
    print(f"   Диапазон ВВП: {min(y):.2f} - {max(y):.2f} млрд USD")
    exp_vals = [d['export_value'] for d in data]
    imp_vals = [d['import_value'] for d in data]
    print(f"   Диапазон экспорта: {min(exp_vals):.2f} - {max(exp_vals):.2f} млрд USD")
    print(f"   Диапазон импорта: {min(imp_vals):.2f} - {max(imp_vals):.2f} млрд USD")
    print_section("Матрица признаков")
    print(f"   Количество признаков: {X.shape[1]}")
    print(f"   Названия признаков: {', '.join(feature_names)}")
    print_header("СРАВНЕНИЕ МОДЕЛЕЙ")
    print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10}")
    print("-" * 85)
    for m in models:
        print(f"{m['name']:<35} {m['metrics']['r2']:<12.6f} {m['metrics']['rmse']:<12.2f} {m['metrics']['mae']:<12.2f} {m['metrics']['mape']:<10.2f}%")
    print_header(f"🏆 ЛУЧШАЯ МОДЕЛЬ: {best_model['name']}")
    print(f"   R² = {best_model['metrics']['r2']:.6f}")
    print(f"   RMSE = {best_model['metrics']['rmse']:.2f} млрд USD")
    print(f"   MAE = {best_model['metrics']['mae']:.2f} млрд USD")
    print(f"   MAPE = {best_model['metrics']['mape']:.2f}%")
    if not best_model.get('poly'):
        print(f"\n   Формула:")
        formula = f"   ВВП = {best_model['intercept']:.6f}"
        for name, coef in zip(feature_names, best_model['coefficients']):
            if abs(coef) > 1e-10:
                sign = '+' if coef >= 0 else '-'
                formula += f" {sign} {abs(coef):.6f}·{name}"
        print(formula)
    # Вывод статистической значимости (Стьюдент, Фишер)
    if 'statistics' in best_model and best_model['statistics']:
        print_regression_statistics(best_model['statistics'])
    else:
        print("\n   Статистическая значимость не доступна (модель не линейная или ошибка)")

def print_prediction_analysis(best_model, data):
    last_export = float(data[-1]['export_value'])
    last_import = float(data[-1]['import_value'])
    last_gdp = float(data[-1]['gdp_value'])
    print_header("ПРОВЕРКА ПРОГНОЗА НА ПОСЛЕДНЕМ ГОДЕ")
    print(f"\n📋 ИСХОДНЫЕ ДАННЫЕ:")
    print(f"   Год: {data[-1]['year']}")
    print(f"   Экспорт: {last_export:.2f} млрд USD")
    print(f"   Импорт: {last_import:.2f} млрд USD")
    print(f"   Фактический ВВП: {last_gdp:.2f} млрд USD")
    print(f"\n🔮 РАСЧЁТ ПРОГНОЗА:")
    if best_model.get('poly'):
        poly = best_model['poly_features']
        X_pred, _, _ = prepare_regression_features(pd.DataFrame([{'export': last_export, 'import': last_import, 'gdp': 0}]))
        X_pred_poly = poly.transform(X_pred)
        predicted_gdp = best_model['intercept'] + np.sum(best_model['coefficients'] * X_pred_poly[0])
        print(f"   Применено полиномиальное преобразование (степень {best_model.get('degree', 2)})")
    else:
        predicted_gdp = forecast_gdp(np.array(best_model['coefficients']),
                                     best_model['intercept'],
                                     last_export, last_import)
        print(f"   Использована линейная регрессия")
    print(f"\n📊 РЕЗУЛЬТАТ:")
    print(f"   Предсказанный ВВП: {predicted_gdp:.2f} млрд USD")
    print(f"   Абсолютная ошибка: {predicted_gdp - last_gdp:+.2f} млрд USD")
    rel_err = (predicted_gdp - last_gdp) / last_gdp * 100
    print(f"   Относительная ошибка: {rel_err:+.2f}%")
    if abs(rel_err) < 5: print(f"\n   ✅ Оценка: Отличное предсказание (ошибка <5%)")
    elif abs(rel_err) < 10: print(f"\n   ✅ Оценка: Хорошее предсказание (ошибка <10%)")
    elif abs(rel_err) < 20: print(f"\n   ⚠️ Оценка: Удовлетворительное предсказание (ошибка <20%)")
    else: print(f"\n   ❌ Оценка: Плохое предсказание (ошибка >20%)")

def print_forecast_result(country_name, export_val, import_val, predicted_gdp, actual_gdp_last, last_year):
    print_header("ПРОГНОЗ ВВП ПО ЗАДАННЫМ ЗНАЧЕНИЯМ")
    print(f"\n📋 ВХОДНЫЕ ДАННЫЕ:")
    print(f"   Страна: {country_name}")
    print(f"   Экспорт: {export_val:.2f} млрд USD")
    print(f"   Импорт: {import_val:.2f} млрд USD")
    print(f"\n🔮 РЕЗУЛЬТАТ ПРОГНОЗА:")
    print(f"   📊 Прогнозируемый ВВП: {predicted_gdp:.2f} млрд USD")
    print(f"\n📊 ДЛЯ СПРАВКИ:")
    print(f"   ВВП в последнем году ({last_year}) = {actual_gdp_last:.2f} млрд USD")
    print(f"   Разница: {predicted_gdp - actual_gdp_last:+.2f} млрд USD")
    print(f"   Изменение: {((predicted_gdp - actual_gdp_last) / actual_gdp_last * 100):+.2f}%")


# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

def main():
    parser = argparse.ArgumentParser(description='Регрессионный и авторегрессионный анализ экономических данных')
    parser.add_argument('-c', '--country', type=int, help='ID страны для анализа')
    parser.add_argument('-l', '--list', action='store_true', help='Показать список стран')
    parser.add_argument('-a', '--all', action='store_true', help='Анализировать все страны')
    parser.add_argument('-f', '--forecast', action='store_true', help='Выполнить авторегрессионный прогноз экспорта и импорта')
    parser.add_argument('-p', '--predict', nargs=2, type=float, metavar=('EXPORT', 'IMPORT'),
                        help='Прогноз ВВП по экспорту и импорту')
    parser.add_argument('-ci', '--confidence', action='store_true', help='Показать доверительные интервалы для прогноза')
    parser.add_argument('-d', '--details', action='store_true', help='Показать детальный вывод (пошаговый расчёт)')
    parser.add_argument('-m', '--model', type=str, default='linear',
                        choices=['linear', 'polynomial', 'exponential', 'ridge', 'lasso', 'compare'],
                        help='Модель для авторегрессии (по умолчанию linear)')
    parser.add_argument('--degree', type=int, default=2, help='Степень полинома (для polynomial)')
    parser.add_argument('--steps', type=int, default=5, help='Горизонт прогноза (по умолчанию 5 лет)')
    args = parser.parse_args()

    print("🔌 Инициализация базы данных...")
    init_database()
    Database.init_pool()
    print("✅ База данных готова\n")

    if args.list:
        countries = CountryService.get_all_countries()
        print_country_list(countries)
        return

    if args.all:
        countries = CountryService.get_all_countries()
        print_header("РЕГРЕССИОННЫЙ АНАЛИЗ ДЛЯ ВСЕХ СТРАН")
        all_results = []
        for country in countries:
            data = IndicatorService.filter_indicators(country_id=country['id'])
            # Фильтруем: оставляем только записи с полными данными
            filtered = []
            for row in data:
                if (row.get('export_value') is not None and 
                    row.get('import_value') is not None and 
                    row.get('gdp_value') is not None):
                    filtered.append(row)
            if len(filtered) < 4:
                continue
            filtered = convert_data_to_float(filtered)
            # Дополнительная проверка после преобразования
            if any(row.get(key) is None for row in filtered for key in ['export_value', 'import_value', 'gdp_value']):
                continue
            df = prepare_dataframe_from_records(filtered)
            X, y, feature_names = prepare_regression_features(df)
            if len(X) == 0 or len(y) == 0:
                continue
            models, best_model = compare_all_models(X, y, feature_names)
            if best_model:
                all_results.append({
                    'country_name': country['name'],
                    'best_model': best_model['name'],
                    'r2': best_model['metrics']['r2'],
                    'rmse': best_model['metrics']['rmse'],
                    'data_points': len(filtered)
                })
        if all_results:
            print(f"\n{'Страна':<25} {'Лучшая модель':<35} {'R²':<12} {'RMSE':<12} {'Точек':<8}")
            print("-" * 95)
            for r in sorted(all_results, key=lambda x: x['r2'], reverse=True):
                print(f"{r['country_name']:<25} {r['best_model']:<35} {r['r2']:<12.4f} {r['rmse']:<12.2f} {r['data_points']:<8}")
        else:
            print("Нет стран с достаточным количеством корректных данных.")
        return

    if args.forecast and args.country:
        data = IndicatorService.filter_indicators(country_id=args.country)
        if len(data) < 3:
            print(f"❌ Недостаточно данных для прогноза (нужно минимум 3)")
            return
        data = convert_data_to_float(data)
        countries = CountryService.get_all_countries()
        country = next((c for c in countries if c['id'] == args.country), None)
        if not country:
            print(f"❌ Страна с ID {args.country} не найдена")
            return
        print_header(f"АВТОРЕГРЕССИОННЫЙ АНАЛИЗ ДЛЯ СТРАНЫ: {country['name']}")
        print_data_table(data, "ИСХОДНЫЕ ДАННЫЕ")

        export_series = [d['export_value'] for d in data]
        import_series = [d['import_value'] for d in data]

        # Экспорт
        print_header("ЭКСПОРТ")
        if args.details:
            if args.model == 'compare':
                comparison = compare_auto_regression_models(export_series, args.steps)
                print_auto_regression_details(export_series, args.steps, 'compare', comparison, data)
            else:
                if args.confidence:
                    result = auto_regression_with_confidence(export_series, args.steps, args.model,
                                                              degree=args.degree)
                else:
                    result = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                if result.get('success'):
                    print_auto_regression_details(export_series, args.steps, args.model, result, data)
                else:
                    print(f"❌ Ошибка: {result.get('error')}")
        else:
            if args.model == 'compare':
                export_comparison = compare_auto_regression_models(export_series, args.steps)
                print_auto_regression_results(data, "ЭКСПОРТА", export_comparison)
            else:
                if args.confidence:
                    export_forecast = auto_regression_with_confidence(export_series, args.steps, args.model,
                                                                        degree=args.degree)
                else:
                    export_forecast = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                print_auto_regression_results(data, "ЭКСПОРТА", export_forecast)
        print("\n" + "=" * 80)

        # Импорт
        print_header("ИМПОРТ")
        if args.details:
            if args.model == 'compare':
                comparison = compare_auto_regression_models(import_series, args.steps)
                print_auto_regression_details(import_series, args.steps, 'compare', comparison, data)
            else:
                if args.confidence:
                    result = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                              degree=args.degree)
                else:
                    result = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
                if result.get('success'):
                    print_auto_regression_details(import_series, args.steps, args.model, result, data)
                else:
                    print(f"❌ Ошибка: {result.get('error')}")
        else:
            if args.model == 'compare':
                import_comparison = compare_auto_regression_models(import_series, args.steps)
                print_auto_regression_results(data, "ИМПОРТА", import_comparison)
            else:
                if args.confidence:
                    import_forecast = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                                        degree=args.degree)
                else:
                    import_forecast = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
                print_auto_regression_results(data, "ИМПОРТА", import_forecast)
        return

    if args.country:
        data = IndicatorService.filter_indicators(country_id=args.country)
        if len(data) < 4:
            print(f"❌ Недостаточно данных для анализа (нужно минимум 4)")
            return
        data = convert_data_to_float(data)
        countries = CountryService.get_all_countries()
        country = next((c for c in countries if c['id'] == args.country), None)
        if not country:
            print(f"❌ Страна с ID {args.country} не найдена")
            return
        print_header(f"ПОЛНЫЙ АНАЛИЗ ДЛЯ СТРАНЫ: {country['name']}")
        print_data_table(data, "ИСХОДНЫЕ ДАННЫЕ")

        # --- Добавлено: критерий Ирвина и t-тест для рядов ---
        print_header("СТАТИСТИЧЕСКАЯ ОЦЕНКА ВРЕМЕННЫХ РЯДОВ")
        gdp_series = [d['gdp_value'] for d in data]
        export_series = [d['export_value'] for d in data]
        import_series = [d['import_value'] for d in data]
        print_irwin_analysis(export_series, "ЭКСПОРТА")
        print_irwin_analysis(import_series, "ИМПОРТА")
        print_irwin_analysis(gdp_series, "ВВП")

        # --- 1. Авторегрессионный анализ ---
        print_header("1. АВТОРЕГРЕССИОННЫЙ АНАЛИЗ")
        # Экспорт
        print_header("ЭКСПОРТ")
        if args.details:
            if args.model == 'compare':
                export_comparison = compare_auto_regression_models(export_series, args.steps)
                print_auto_regression_details(export_series, args.steps, 'compare', export_comparison, data)
            else:
                if args.confidence:
                    export_result = auto_regression_with_confidence(export_series, args.steps, args.model,
                                                                      degree=args.degree)
                else:
                    export_result = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                if export_result.get('success'):
                    print_auto_regression_details(export_series, args.steps, args.model, export_result, data)
                else:
                    print(f"❌ Ошибка: {export_result.get('error')}")
        else:
            if args.model == 'compare':
                export_comparison = compare_auto_regression_models(export_series, args.steps)
                print_auto_regression_results(data, "ЭКСПОРТА", export_comparison)
            else:
                if args.confidence:
                    export_forecast = auto_regression_with_confidence(export_series, args.steps, args.model,
                                                                        degree=args.degree)
                else:
                    export_forecast = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                print_auto_regression_results(data, "ЭКСПОРТА", export_forecast)
        print("\n" + "=" * 80)

        # Импорт
        print_header("ИМПОРТ")
        if args.details:
            if args.model == 'compare':
                import_comparison = compare_auto_regression_models(import_series, args.steps)
                print_auto_regression_details(import_series, args.steps, 'compare', import_comparison, data)
            else:
                if args.confidence:
                    import_result = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                                      degree=args.degree)
                else:
                    import_result = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
                if import_result.get('success'):
                    print_auto_regression_details(import_series, args.steps, args.model, import_result, data)
                else:
                    print(f"❌ Ошибка: {import_result.get('error')}")
        else:
            if args.model == 'compare':
                import_comparison = compare_auto_regression_models(import_series, args.steps)
                print_auto_regression_results(data, "ИМПОРТА", import_comparison)
            else:
                if args.confidence:
                    import_forecast = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                                        degree=args.degree)
                else:
                    import_forecast = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
                print_auto_regression_results(data, "ИМПОРТА", import_forecast)

        # --- 2. Регрессионный анализ ВВП ---
        print_header("2. РЕГРЕССИОННЫЙ АНАЛИЗ ВВП")
        df = prepare_dataframe_from_records(data)
        X, y, feature_names = prepare_regression_features(df)
        models, best_model = compare_all_models(X, y, feature_names)

        if args.details:
            print_regression_analysis_details(X, y, feature_names, models, best_model, data)
        else:
            print_header("СРАВНЕНИЕ РЕГРЕССИОННЫХ МОДЕЛЕЙ")
            print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10}")
            print("-" * 85)
            for m in models:
                print(f"{m['name']:<35} {m['metrics']['r2']:<12.6f} {m['metrics']['rmse']:<12.2f} {m['metrics']['mae']:<12.2f} {m['metrics']['mape']:<10.2f}%")
            print_header(f"🏆 ЛУЧШАЯ РЕГРЕССИОННАЯ МОДЕЛЬ: {best_model['name']}")
            print(f"   R² = {best_model['metrics']['r2']:.6f}")
            print(f"   RMSE = {best_model['metrics']['rmse']:.2f} млрд USD")
            print(f"   MAE = {best_model['metrics']['mae']:.2f} млрд USD")
            print(f"   MAPE = {best_model['metrics']['mape']:.2f}%")
            if not best_model.get('poly'):
                formula = f"   ВВП = {best_model['intercept']:.6f}"
                for name, coef in zip(feature_names, best_model['coefficients']):
                    if abs(coef) > 1e-10:
                        sign = '+' if coef >= 0 else '-'
                        formula += f" {sign} {abs(coef):.6f}·{name}"
                print(f"\n   Формула: {formula}")
            # Вывод статистической значимости
            if 'statistics' in best_model and best_model['statistics']:
                print_regression_statistics(best_model['statistics'])
            else:
                print("\n   Статистическая значимость не доступна (модель не линейная)")

        print_prediction_analysis(best_model, data)
        return

    if args.predict:
        export_val, import_val = args.predict
        countries = CountryService.get_all_countries()
        print_country_list(countries)
        try:
            country_id = int(input("\n👉 Введите ID страны для прогноза: "))
            country = next((c for c in countries if c['id'] == country_id), None)
            if not country:
                print(f"❌ Страна с ID {country_id} не найдена")
                return
            data = IndicatorService.filter_indicators(country_id=country_id)
            if len(data) < 4:
                print(f"❌ Недостаточно данных для прогноза")
                return
            data = convert_data_to_float(data)
            df = prepare_dataframe_from_records(data)
            X, y, feature_names = prepare_regression_features(df)
            result = train_regression_model(X, y, model_type='linear')
            if 'error' in result:
                print(f"❌ Ошибка: {result['error']}")
                return
            predicted = forecast_gdp(np.array(result['coefficients']), result['intercept'],
                                     export_val, import_val)
            actual_gdp_last = data[-1]['gdp_value']
            last_year = data[-1]['year']
            print_forecast_result(country['name'], export_val, import_val, predicted, actual_gdp_last, last_year)
        except ValueError:
            print("❌ Неверный ID страны")
        return

    parser.print_help()


if __name__ == '__main__':
    main()