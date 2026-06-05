#!/usr/bin/env python3
"""
Консольная программа для регрессионного и авторегрессионного анализа экономических данных
Адаптирована под существующие функции пакета calculations
"""

import sys
import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from database import Database, init_database
from services.indicator_service import IndicatorService
from services.country_service import CountryService

# Импортируем реально существующие функции из calculations
from calculations import (
    prepare_regression_features,   # принимает DataFrame, а не списки
    auto_regression_forecast,
    compare_auto_regression_models,
    calculate_metrics,
    linear_trend,
)
from calculations.regression_calc import train_regression_model
from calculations.auto_regression import (
    polynomial_trend,
    exponential_trend,
    ridge_trend,
    lasso_trend,
)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def convert_data_to_float(data_list):
    """Преобразует числовые значения (в т.ч. Decimal) в float."""
    for row in data_list:
        for key in ['export_value', 'import_value', 'gdp_value']:
            if key in row:
                row[key] = float(row[key])
    return data_list


def prepare_dataframe_from_records(data_list):
    """Создаёт DataFrame с колонками export, import, gdp из списка записей."""
    df = pd.DataFrame([
        {
            'export': row['export_value'],
            'import': row['import_value'],
            'gdp': row['gdp_value']
        }
        for row in data_list
    ])
    return df


def linear_regression_analysis(X, y, feature_names):
    """Линейная регрессия через train_regression_model."""
    result = train_regression_model(X, y, model_type='linear')
    if 'error' in result:
        return None
    return {
        'name': 'Линейная регрессия',
        'model': None,  # модель не сохраняем, нужны только коэффициенты
        'coefficients': result['coefficients'],
        'intercept': result['intercept'],
        'metrics': result['metrics'],
        'statistics': result.get('statistics'),
    }


def ridge_regression_analysis(X, y, feature_names, alpha=1.0):
    """Ridge регрессия."""
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
    """Lasso регрессия."""
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
    """Полиномиальная регрессия (степень degree) с использованием PolynomialFeatures."""
    poly = PolynomialFeatures(degree=degree, include_bias=False)
    X_poly = poly.fit_transform(X)
    # Получаем новые имена признаков
    poly_feature_names = [f"{name}^{i}" if i > 1 else name for name in feature_names for i in range(1, degree+1)]
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
    """Сравнивает все доступные регрессионные модели и возвращает лучшую по R²."""
    models = []
    # Линейная
    m1 = linear_regression_analysis(X, y, feature_names)
    if m1:
        models.append(m1)
    # Ridge
    m2 = ridge_regression_analysis(X, y, feature_names, alpha=1.0)
    if m2:
        models.append(m2)
    # Lasso
    m3 = lasso_regression_analysis(X, y, feature_names, alpha=1.0)
    if m3:
        models.append(m3)
    # Полиномиальная 2 степени
    m4 = polynomial_regression_analysis(X, y, feature_names, degree=2)
    if m4:
        models.append(m4)
    # Полиномиальная 3 степени (если данных достаточно)
    if len(X) >= 5:
        m5 = polynomial_regression_analysis(X, y, feature_names, degree=3)
        if m5:
            models.append(m5)
    if not models:
        return [], None
    best = max(models, key=lambda m: m['metrics']['r2'])
    return models, best


def forecast_gdp(model_coefs, intercept, export_val, import_val):
    """
    Прогноз ВВП по одному наблюдению для линейной модели (без полиномов).
    Принимает коэффициенты и intercept, а не объект модели.
    """
    features = np.array([export_val, import_val, export_val*import_val, export_val**2, import_val**2])
    pred = intercept + np.sum(model_coefs * features)
    return pred


def auto_regression_with_confidence(series, steps, model_type='linear',
                                    confidence_level=0.95, degree=2, alpha=1.0):
    """
    Авторегрессия с доверительными интервалами.
    Использует стандартную ошибку прогноза на основе остатков.
    """
    # Получаем прогноз и исторические предсказания
    forecast_result = auto_regression_forecast(
        series, steps=steps, model_type=model_type,
        degree=degree, alpha=alpha
    )
    if not forecast_result.get('success'):
        return forecast_result

    y_true = np.array(series)
    # Для расчёта предсказаний на истории используем ту же модель
    # Придётся пересчитать, т.к. auto_regression_forecast возвращает только будущие прогнозы
    if model_type == 'linear':
        hist_pred = linear_trend(series, steps=0)  # получим предсказания на истории
        if hist_pred.get('success'):
            y_pred = np.array(hist_pred.get('predicted', []))
        else:
            y_pred = np.array([np.nan]*len(series))
    elif model_type == 'polynomial':
        poly_res = polynomial_trend(series, steps=0, degree=degree)
        if poly_res.get('success'):
            y_pred = np.array(poly_res.get('predicted', []))
        else:
            y_pred = np.array([np.nan]*len(series))
    elif model_type == 'exponential':
        exp_res = exponential_trend(series, steps=0)
        if exp_res.get('success'):
            y_pred = np.array(exp_res.get('predicted', []))
        else:
            y_pred = np.array([np.nan]*len(series))
    elif model_type == 'ridge':
        ridge_res = ridge_trend(series, steps=0, alpha=alpha)
        if ridge_res.get('success'):
            y_pred = np.array(ridge_res.get('predicted', []))
        else:
            y_pred = np.array([np.nan]*len(series))
    elif model_type == 'lasso':
        lasso_res = lasso_trend(series, steps=0, alpha=alpha)
        if lasso_res.get('success'):
            y_pred = np.array(lasso_res.get('predicted', []))
        else:
            y_pred = np.array([np.nan]*len(series))
    else:
        y_pred = np.array([np.nan]*len(series))

    # Вычисляем стандартную ошибку остатков
    residuals = y_true - y_pred
    valid = ~np.isnan(residuals)
    if np.sum(valid) < 2:
        return {**forecast_result, 'error': 'Недостаточно данных для расчёта доверительных интервалов'}

    resid_std = np.std(residuals[valid], ddof=1)
    n = len(y_true)
    # Коэффициент Стьюдента
    t_val = stats.t.ppf((1 + confidence_level) / 2, df=n-2)

    forecast_vals = np.array(forecast_result['forecast'])
    margin = t_val * resid_std * np.sqrt(1 + 1/n + (np.arange(1, steps+1) - np.mean(np.arange(1, n+1)))**2 / np.sum((np.arange(1, n+1) - np.mean(np.arange(1, n+1)))**2))

    lower_bounds = (forecast_vals - margin).tolist()
    upper_bounds = (forecast_vals + margin).tolist()

    forecast_result['lower_bounds'] = lower_bounds
    forecast_result['upper_bounds'] = upper_bounds
    forecast_result['confidence_level'] = confidence_level
    return forecast_result


# ==================== ВЫВОД РЕЗУЛЬТАТОВ ====================

def print_header(text, char='='):
    """Вывод заголовка"""
    print("\n" + char * 80)
    print(f" {text}")
    print(char * 80)


def print_subheader(text, char='-'):
    """Вывод подзаголовка"""
    print(f"\n{char * 60}")
    print(f" {text}")
    print(char * 60)


def print_section(text):
    """Вывод секции"""
    print(f"\n▶ {text}")


def print_country_list(countries):
    """Вывод списка стран"""
    print_header("СПИСОК СТРАН")
    print(f"{'ID':<6} {'Название'}")
    print("-" * 40)
    for c in countries:
        print(f"{c['id']:<6} {c['name']}")
    print()


def print_data_table(data, title="ИСТОРИЧЕСКИЕ ДАННЫЕ"):
    """Вывод таблицы данных"""
    print_header(title)
    print(f"{'Год':<8} {'Экспорт':<18} {'Импорт':<18} {'ВВП':<18}")
    print("-" * 65)
    for row in data:
        print(f"{row['year']:<8} {row['export_value']:<18.2f} {row['import_value']:<18.2f} {row['gdp_value']:<18.2f}")
    print()


def print_series_stats(series, name):
    """Вывод статистики временного ряда"""
    print_section(f"Статистика ряда {name}")
    print(f"   Количество точек: {len(series)}")
    print(f"   Минимум: {min(series):.2f}")
    print(f"   Максимум: {max(series):.2f}")
    print(f"   Среднее: {np.mean(series):.2f}")
    print(f"   Медиана: {np.median(series):.2f}")
    print(f"   Стандартное отклонение: {np.std(series):.2f}")
    print(f"   Диапазон: {max(series) - min(series):.2f}")


def print_auto_regression_details(series, steps, model_type, result, data):
    """Детальный вывод авторегрессионного прогноза"""
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
    if r2 >= 0.9:
        quality = "Отличное качество"
    elif r2 >= 0.7:
        quality = "Хорошее качество"
    elif r2 >= 0.5:
        quality = "Удовлетворительное качество"
    else:
        quality = "Низкое качество"
    print(f"   Оценка качества: {quality}")
    
    last_year = data[-1]['year'] if data else 2023
    print_section("Пошаговый расчёт прогноза")
    print(f"   Формула: {result.get('formula', 'N/A')}")
    print()
    print(f"   {'Шаг':<6} {'Год':<8} {'Прогноз':<15}")
    print(f"   {'-' * 35}")
    for i, val in enumerate(result['forecast']):
        year = last_year + i + 1
        print(f"   {i+1:<6} {year:<8} {val:<15.2f}")
    
    print_section("Итоговая таблица прогноза")
    print(f"{'Год':<10} {'Прогноз':<15}", end='')
    if 'lower_bounds' in result:
        print(f" {'Нижняя граница (95%)':<20} {'Верхняя граница (95%)':<20}")
    else:
        print()
    print("-" * 70)
    for i, val in enumerate(result['forecast']):
        year = last_year + i + 1
        print(f"{year:<10} {val:<15.2f}", end='')
        if 'lower_bounds' in result:
            print(f" {result['lower_bounds'][i]:<20.2f} {result['upper_bounds'][i]:<20.2f}")
        else:
            print()


def print_auto_regression_comparison_details(comparison, data):
    """Детальный вывод сравнения моделей авторегрессии"""
    print_header("СРАВНЕНИЕ ВСЕХ МОДЕЛЕЙ АВТОРЕГРЕССИИ")
    
    print_section("Информация о данных")
    series = comparison.get('historical', [])
    print(f"   Количество точек: {len(series)}")
    print(f"   Диапазон значений: {min(series):.2f} - {max(series):.2f}")
    
    print_section("Сравнение метрик качества")
    print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10} {'Качество':<12}")
    print("-" * 95)
    for name, res in comparison['all_models'].items():
        if res.get('success'):
            r2 = res.get('r2', 0)
            if r2 >= 0.9:
                quality = "Отличное"
            elif r2 >= 0.7:
                quality = "Хорошее"
            elif r2 >= 0.5:
                quality = "Среднее"
            else:
                quality = "Низкое"
            model_display = res.get('model_name', name)
            print(f"{model_display:<35} {res.get('r2', 0):<12.4f} {res.get('rmse', 0):<12.2f} "
                  f"{res.get('mae', 0):<12.2f} {res.get('mape', 0):<10.2f} {quality:<12}")
    
    print_header(f"🏆 ЛУЧШАЯ МОДЕЛЬ: {comparison['best_model_name']}")
    print(f"   R² = {comparison['best_r2']:.6f}")
    best_result = comparison['all_models'].get(comparison['best_model'])
    if best_result and best_result.get('success'):
        print(f"   Формула: {best_result.get('formula', 'N/A')}")
        last_year = data[-1]['year'] if data else 2023
        print_section("Прогноз лучшей модели")
        print(f"{'Год':<10} {'Прогноз':<15}")
        print("-" * 30)
        for i, val in enumerate(best_result['forecast']):
            year = last_year + i + 1
            print(f"{year:<10} {val:<15.2f}")


def print_auto_regression_results(data, indicator_name, forecast_result):
    """Вывод результатов авторегрессионного прогноза (основной)"""
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
    if 'lower_bounds' in forecast_result and 'upper_bounds' in forecast_result:
        conf = int(forecast_result.get('confidence_level', 0.95)*100)
        print(f"\n📊 ДОВЕРИТЕЛЬНЫЕ ИНТЕРВАЛЫ ({conf}%):")
        for i, val in enumerate(forecast_result['forecast']):
            year = last_year + i + 1
            print(f"   {year}: [{forecast_result['lower_bounds'][i]:.2f} ; {forecast_result['upper_bounds'][i]:.2f}]")


def print_auto_regression_comparison(comparison, data):
    """Вывод сравнения всех моделей авторегрессии"""
    print_header("СРАВНЕНИЕ МОДЕЛЕЙ АВТОРЕГРЕССИИ")
    print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10}")
    print("-" * 85)
    for name, res in comparison['all_models'].items():
        if res.get('success'):
            model_display = res.get('model_name', name)
            print(f"{model_display:<35} {res.get('r2', 0):<12.4f} {res.get('rmse', 0):<12.2f} "
                  f"{res.get('mae', 0):<12.2f} {res.get('mape', 0):<10.2f}%")
    print(f"\n🏆 ЛУЧШАЯ МОДЕЛЬ: {comparison['best_model_name']}")
    print(f"   R² = {comparison['best_r2']:.4f}")
    best_result = comparison['all_models'].get(comparison['best_model'])
    if best_result and best_result.get('success'):
        print(f"\n🔮 ПРОГНОЗ ЛУЧШЕЙ МОДЕЛИ НА {comparison.get('steps', 5)} ЛЕТ:")
        last_year = data[-1]['year']
        for i, val in enumerate(best_result['forecast']):
            year = last_year + i + 1
            print(f"   {year}: {val:.2f} млрд USD")


def print_regression_analysis_details(X, y, feature_names, models, best_model, data):
    """Детальный вывод регрессионного анализа"""
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
    print_header("ДЕТАЛЬНЫЙ АНАЛИЗ МОДЕЛЕЙ")
    for m in models:
        print_subheader(m['name'])
        print(f"\n   R² = {m['metrics']['r2']:.6f}")
        print(f"   RMSE = {m['metrics']['rmse']:.2f} млрд USD")
        print(f"   MAE = {m['metrics']['mae']:.2f} млрд USD")
        print(f"   MAPE = {m['metrics']['mape']:.2f}%")
        if not m.get('poly'):
            print(f"\n   Формула:")
            formula = f"   ВВП = {m['intercept']:.6f}"
            for name, coef in zip(feature_names, m['coefficients']):
                if abs(coef) > 1e-10:
                    sign = '+' if coef >= 0 else '-'
                    abs_coef = abs(coef)
                    formula += f" {sign} {abs_coef:.6f}·{name}"
            print(formula)
        print("\n   " + "-" * 50)
    print_header("СРАВНЕНИЕ МОДЕЛЕЙ")
    print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10}")
    print("-" * 85)
    for m in models:
        print(f"{m['name']:<35} {m['metrics']['r2']:<12.6f} {m['metrics']['rmse']:<12.2f} "
              f"{m['metrics']['mae']:<12.2f} {m['metrics']['mape']:<10.2f}%")
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
                abs_coef = abs(coef)
                formula += f" {sign} {abs_coef:.6f}·{name}"
        print(formula)


def print_prediction_analysis(model_coefs, intercept, data, best_model_result):
    """Анализ прогноза на последнем году с учётом типа модели"""
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
    if best_model_result.get('poly'):
        # Полиномиальная модель
        poly = best_model_result['poly_features']

        X_pred, _, _ = prepare_regression_features(pd.DataFrame([{'export': last_export, 'import': last_import, 'gdp': 0}]))
        X_pred_poly = poly.transform(X_pred)
        predicted_gdp = best_model_result['intercept'] + np.sum(best_model_result['coefficients'] * X_pred_poly[0])
        print(f"   Применено полиномиальное преобразование (степень {best_model_result.get('degree', 2)})")
    else:
        predicted_gdp = forecast_gdp(np.array(best_model_result['coefficients']),
                                     best_model_result['intercept'],
                                     last_export, last_import)
        print(f"   Использована линейная регрессия")
    print(f"\n📊 РЕЗУЛЬТАТ:")
    print(f"   Предсказанный ВВП: {predicted_gdp:.2f} млрд USD")
    print(f"   Абсолютная ошибка: {predicted_gdp - last_gdp:+.2f} млрд USD")
    rel_err = (predicted_gdp - last_gdp) / last_gdp * 100
    print(f"   Относительная ошибка: {rel_err:+.2f}%")
    if abs(rel_err) < 5:
        print(f"\n   ✅ Оценка: Отличное предсказание (ошибка менее 5%)")
    elif abs(rel_err) < 10:
        print(f"\n   ✅ Оценка: Хорошее предсказание (ошибка менее 10%)")
    elif abs(rel_err) < 20:
        print(f"\n   ⚠️ Оценка: Удовлетворительное предсказание (ошибка менее 20%)")
    else:
        print(f"\n   ❌ Оценка: Плохое предсказание (ошибка более 20%)")


def print_forecast_result(country_name, export_val, import_val, predicted_gdp, actual_gdp_last, last_year):
    """Вывод результата прогноза по заданным значениям"""
    print_header("ПРОГНОЗ ВВП ПО ЗАДАННЫМ ЗНАЧЕНИЯМ")
    print(f"\n📋 ВХОДНЫЕ ДАННЫЕ:")
    print(f"   Страна: {country_name}")
    print(f"   Экспорт: {export_val:.2f} млрд USD")
    print(f"   Импорт: {import_val:.2f} млрд USD")
    print(f"\n🔮 РЕЗУЛЬТАТ ПРОГНОЗА:")
    print(f"   📊 Прогнозируемый ВВП: {predicted_gdp:.2f} млрд USD")
    print(f"\n📊 ДЛЯ СПРАВКИ:")
    print(f"   ВВП в последнем году ({last_year}) = {actual_gdp_last:.2f} млрд USD")
    print(f"   Разница с последним годом: {predicted_gdp - actual_gdp_last:+.2f} млрд USD")
    print(f"   Относительное изменение: {((predicted_gdp - actual_gdp_last) / actual_gdp_last * 100):+.2f}%")


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
            if len(data) >= 4:
                data = convert_data_to_float(data)
                df = prepare_dataframe_from_records(data)
                X, y, feature_names = prepare_regression_features(df)
                if len(X) == 0:
                    continue
                models, best_model = compare_all_models(X, y, feature_names)
                if best_model:
                    all_results.append({
                        'country_name': country['name'],
                        'best_model': best_model['name'],
                        'r2': best_model['metrics']['r2'],
                        'rmse': best_model['metrics']['rmse'],
                        'data_points': len(data)
                    })
        print(f"\n{'Страна':<25} {'Лучшая модель':<35} {'R²':<12} {'RMSE':<12} {'Точек':<8}")
        print("-" * 95)
        for r in sorted(all_results, key=lambda x: x['r2'], reverse=True):
            print(f"{r['country_name']:<25} {r['best_model']:<35} {r['r2']:<12.4f} {r['rmse']:<12.2f} {r['data_points']:<8}")
        return

    if args.forecast and args.country:
        data = IndicatorService.filter_indicators(country_id=args.country)
        if len(data) < 3:
            print(f"❌ Недостаточно данных для прогноза (найдено {len(data)} точек, нужно минимум 3)")
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
                print_auto_regression_comparison_details(comparison, data)
            else:
                if args.confidence:
                    result = auto_regression_with_confidence(export_series, args.steps, args.model,
                                                              confidence_level=0.95, degree=args.degree)
                else:
                    result = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                if result.get('success'):
                    print_auto_regression_details(export_series, args.steps, args.model, result, data)
                else:
                    print(f"❌ Ошибка: {result.get('error')}")
        else:
            if args.model == 'compare':
                export_comparison = compare_auto_regression_models(export_series, args.steps)
                print_auto_regression_comparison(export_comparison, data)
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
                print_auto_regression_comparison_details(comparison, data)
            else:
                if args.confidence:
                    result = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                              confidence_level=0.95, degree=args.degree)
                else:
                    result = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
                if result.get('success'):
                    print_auto_regression_details(import_series, args.steps, args.model, result, data)
                else:
                    print(f"❌ Ошибка: {result.get('error')}")
        else:
            if args.model == 'compare':
                import_comparison = compare_auto_regression_models(import_series, args.steps)
                print_auto_regression_comparison(import_comparison, data)
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
            print(f"❌ Недостаточно данных для анализа (найдено {len(data)} точек, нужно минимум 4)")
            return
        data = convert_data_to_float(data)
        countries = CountryService.get_all_countries()
        country = next((c for c in countries if c['id'] == args.country), None)
        if not country:
            print(f"❌ Страна с ID {args.country} не найдена")
            return
        print_header(f"ПОЛНЫЙ АНАЛИЗ ДЛЯ СТРАНЫ: {country['name']}")
        print_data_table(data, "ИСХОДНЫЕ ДАННЫЕ")

        # 1. Авторегрессионный анализ
        print_header("1. АВТОРЕГРЕССИОННЫЙ АНАЛИЗ")
        export_series = [d['export_value'] for d in data]
        import_series = [d['import_value'] for d in data]

        print_header("ЭКСПОРТ")
        if args.details:
            if args.model == 'compare':
                export_comparison = compare_auto_regression_models(export_series, args.steps)
                print_auto_regression_comparison_details(export_comparison, data)
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
                print_auto_regression_comparison(export_comparison, data)
            else:
                if args.confidence:
                    export_forecast = auto_regression_with_confidence(export_series, args.steps, args.model,
                                                                        degree=args.degree)
                else:
                    export_forecast = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                print_auto_regression_results(data, "ЭКСПОРТА", export_forecast)
        print("\n" + "=" * 80)

        print_header("ИМПОРТ")
        if args.details:
            if args.model == 'compare':
                import_comparison = compare_auto_regression_models(import_series, args.steps)
                print_auto_regression_comparison_details(import_comparison, data)
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
                print_auto_regression_comparison(import_comparison, data)
            else:
                if args.confidence:
                    import_forecast = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                                        degree=args.degree)
                else:
                    import_forecast = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
                print_auto_regression_results(data, "ИМПОРТА", import_forecast)

        # 2. Регрессионный анализ ВВП
        print_header("2. РЕГРЕССИОННЫЙ АНАЛИЗ ВВП")
        df = prepare_dataframe_from_records(data)
        X, y, feature_names = prepare_regression_features(df)
        models, best_model = compare_all_models(X, y, feature_names)

        if args.details:
            print_regression_analysis_details(X, y, feature_names, models, best_model, data)
        else:
            print_data_table(data, "ДАННЫЕ ДЛЯ РЕГРЕССИИ")
            print_header("СРАВНЕНИЕ РЕГРЕССИОННЫХ МОДЕЛЕЙ")
            print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10}")
            print("-" * 85)
            for m in models:
                print(f"{m['name']:<35} {m['metrics']['r2']:<12.6f} {m['metrics']['rmse']:<12.2f} "
                      f"{m['metrics']['mae']:<12.2f} {m['metrics']['mape']:<10.2f}%")
            print_header(f"🏆 ЛУЧШАЯ РЕГРЕССИОННАЯ МОДЕЛЬ: {best_model['name']}")
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
                        abs_coef = abs(coef)
                        formula += f" {sign} {abs_coef:.6f}·{name}"
                print(formula)
        print_prediction_analysis(best_model['coefficients'] if not best_model.get('poly') else None,
                                  best_model['intercept'], data, best_model)
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
                print(f"❌ Недостаточно данных для прогноза (найдено {len(data)} точек)")
                return
            data = convert_data_to_float(data)
            df = prepare_dataframe_from_records(data)
            X, y, feature_names = prepare_regression_features(df)
            # Обучаем линейную модель
            result = train_regression_model(X, y, model_type='linear')
            if 'error' in result:
                print(f"❌ Ошибка обучения: {result['error']}")
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