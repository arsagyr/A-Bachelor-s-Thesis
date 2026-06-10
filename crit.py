#!/usr/bin/env python3
"""
Программа для расчёта статистических критериев:
- Критерий Стьюдента (t-тест) для коэффициентов регрессии
- Критерий Фишера (F-тест) для значимости модели
- Критерий Ирвина для обнаружения аномалий во временных рядах
- t-тест значимости тренда для авторегрессии

Режимы работы:
- Анализ одной страны (подробный вывод)
- Анализ всех стран (сводная таблица)
"""

import sys
import numpy as np
import pandas as pd
from scipy import stats
from tabulate import tabulate

from database import Database, init_database
from services.indicator_service import IndicatorService
from services.country_service import CountryService
from calculations.regression_calc import train_regression_model
from calculations.auto_regression import irwin_criterion, t_test_slope


def prepare_regression_data(data_list):
    """Подготовка данных для регрессии."""
    clean_data = []
    for row in data_list:
        if (row.get('export_value') is not None and 
            row.get('import_value') is not None and 
            row.get('gdp_value') is not None):
            try:
                clean_data.append({
                    'export': float(row['export_value']),
                    'import': float(row['import_value']),
                    'gdp': float(row['gdp_value']),
                    'year': row.get('year')
                })
            except (ValueError, TypeError):
                continue
    if not clean_data:
        return None, None, None
    df = pd.DataFrame(clean_data)
    export = df['export'].values
    import_val = df['import'].values
    gdp = df['gdp'].values
    # Признаки: экспорт, импорт, произведение, квадраты
    X = np.column_stack([export, import_val, export * import_val, export ** 2, import_val ** 2])
    feature_names = ['Экспорт', 'Импорт', 'Экспорт×Импорт', 'Экспорт²', 'Импорт²']
    return X, gdp, feature_names


def calculate_regression_criteria_detailed(X, y, feature_names, country_name):
    """
    Расчёт критериев Стьюдента и Фишера для регрессионной модели (подробный вывод).
    """
    result = train_regression_model(X, y, model_type='linear')
    if 'error' in result:
        return None
    
    statistics = result.get('statistics')
    if not statistics:
        return None
    
    print(f"\n{'='*80}")
    print(f" РЕГРЕССИОННЫЙ АНАЛИЗ ДЛЯ СТРАНЫ: {country_name}")
    print(f"{'='*80}")
    
    # Метрики качества
    metrics = result['metrics']
    print(f"\n📊 МЕТРИКИ КАЧЕСТВА МОДЕЛИ:")
    print(f"   R²  = {metrics['r2']:.6f}")
    print(f"   R² скорректированный = {statistics['r2_adjusted']:.6f}")
    print(f"   RMSE = {metrics['rmse']:.2f} млрд USD")
    print(f"   MAE  = {metrics['mae']:.2f} млрд USD")
    print(f"   MAPE = {metrics['mape']:.2f}%")
    
    # ==================== КРИТЕРИЙ СТЬЮДЕНТА (t-тест) ====================
    print(f"\n{'─'*80}")
    print(" КРИТЕРИЙ СТЬЮДЕНТА (t-тест) – проверка значимости коэффициентов")
    print(f"{'─'*80}")
    
    coefs = statistics['coefficients']
    
    # Таблица для вывода
    t_table = []
    # Константа (intercept)
    i = coefs['intercept']
    significant = "✅ ДА" if (i['p_value'] is not None and i['p_value'] < 0.05) else "❌ НЕТ"
    t_table.append([
        'Константа', 
        f"{i['value']:.6f}", 
        f"{i['std_error']:.6f}" if i['std_error'] else "—",
        f"{i['t_statistic']:.4f}" if i['t_statistic'] else "—",
        f"{i['p_value']:.6f}" if i['p_value'] else "—",
        significant
    ])
    
    # Признаки
    for f in coefs['features']:
        name = feature_names[f['index']] if f['index'] < len(feature_names) else f"Признак {f['index']}"
        significant = "✅ ДА" if (f['p_value'] is not None and f['p_value'] < 0.05) else "❌ НЕТ"
        t_table.append([
            name,
            f"{f['value']:.6f}",
            f"{f['std_error']:.6f}" if f['std_error'] else "—",
            f"{f['t_statistic']:.4f}" if f['t_statistic'] else "—",
            f"{f['p_value']:.6f}" if f['p_value'] else "—",
            significant
        ])
    
    print(tabulate(t_table, 
                   headers=['Переменная', 'Коэффициент', 'Ст.ошибка', 't-статистика', 'p-значение', 'Значим (α=0.05)'],
                   tablefmt='grid'))
    
    # ==================== КРИТЕРИЙ ФИШЕРА (F-тест) ====================
    print(f"\n{'─'*80}")
    print(" КРИТЕРИЙ ФИШЕРА (F-тест) – проверка значимости модели в целом")
    print(f"{'─'*80}")
    
    fstat = statistics['f_statistic']
    f_value = fstat['value']
    f_pvalue = fstat['p_value']
    f_df_model = fstat['df_model']
    f_df_residual = fstat['df_residual']
    
    print(f"   F-статистика: {f_value:.4f}")
    print(f"   p-значение: {f_pvalue:.6f}")
    print(f"   Число степеней свободы модели: {f_df_model}")
    print(f"   Число степеней свободы остатков: {f_df_residual}")
    
    if f_pvalue is not None and f_pvalue < 0.05:
        print(f"\n   ✅ РЕЗУЛЬТАТ: Модель статистически значима (p = {f_pvalue:.6f} < 0.05)")
    else:
        print(f"\n   ❌ РЕЗУЛЬТАТ: Модель не значима (p = {f_pvalue:.6f} ≥ 0.05)")
    
    return {
        'country': country_name,
        'r2': metrics['r2'],
        'r2_adj': statistics['r2_adjusted'],
        'f_statistic': f_value,
        'f_pvalue': f_pvalue,
        'model_significant': f_pvalue < 0.05 if f_pvalue else False,
        'significant_coeffs': sum(1 for f in coefs['features'] if f.get('p_value') and f['p_value'] < 0.05),
        'data_points': len(y)
    }


def calculate_regression_criteria_summary(X, y, country_name):
    """
    Расчёт критериев для сводной таблицы (краткий вывод).
    """
    result = train_regression_model(X, y, model_type='linear')
    if 'error' in result:
        return None
    
    statistics = result.get('statistics')
    if not statistics:
        return None
    
    metrics = result['metrics']
    fstat = statistics['f_statistic']
    
    return {
        'country': country_name,
        'data_points': len(y),
        'r2': metrics['r2'],
        'r2_adj': statistics['r2_adjusted'],
        'f_statistic': fstat['value'] if fstat['value'] else np.nan,
        'f_pvalue': fstat['p_value'] if fstat['p_value'] else np.nan,
        'model_significant': fstat['p_value'] < 0.05 if fstat['p_value'] else False
    }


def calculate_autoregression_criteria_detailed(series, name, country_name):
    """
    Расчёт критериев для авторегрессии (подробный вывод).
    """
    print(f"\n{'─'*80}")
    print(f" АВТОРЕГРЕССИОННЫЙ АНАЛИЗ: {name} ({country_name})")
    print(f"{'─'*80}")
    
    # ==================== КРИТЕРИЙ ИРВИНА ====================
    print(f"\n🔍 КРИТЕРИЙ ИРВИНА – обнаружение аномалий (выбросов)")
    irwin = irwin_criterion(series, threshold=3.0)
    
    outliers_count = 0
    if 'error' in irwin:
        print(f"   ⚠️ {irwin['error']}")
    else:
        outliers_count = irwin['outlier_count']
        print(f"   Пороговое значение λ_крит = 3.0")
        print(f"   Среднеквадратическое отклонение разностей: {irwin['sigma_diff']:.4f}")
        
        if outliers_count == 0:
            print(f"\n   ✅ Аномалий не обнаружено")
        else:
            print(f"\n   ⚠️ Найдено аномалий: {outliers_count}")
            for o in irwin['outliers'][:5]:
                print(f"      • Точка {o['index']}: значение = {o['value']:.2f}, λ = {o['lambda']:.4f}")
            if outliers_count > 5:
                print(f"      ... и ещё {outliers_count - 5}")
    
    # ==================== t-ТЕСТ ЗНАЧИМОСТИ ТРЕНДА ====================
    print(f"\n📈 ПРОВЕРКА ЗНАЧИМОСТИ ТРЕНДА (t-критерий Стьюдента)")
    ttest = t_test_slope(series, alpha=0.05)
    
    trend_significant = False
    t_stat = None
    if 'error' in ttest:
        print(f"   ⚠️ {ttest['error']}")
    else:
        t_stat = ttest['t_statistic']
        trend_significant = ttest['significant']
        print(f"   Наклон тренда: {ttest['slope']:.6f}")
        print(f"   t-статистика: {ttest['t_statistic']:.4f}")
        print(f"   p-значение: {ttest['p_value']:.6f}")
        
        if trend_significant:
            print(f"\n   ✅ Тренд статистически значим (p < 0.05)")
        else:
            print(f"\n   ❌ Тренд не значим (p ≥ 0.05)")
    
    return {
        'series_name': name,
        'outliers_count': outliers_count,
        'trend_significant': trend_significant,
        't_statistic': t_stat
    }


def calculate_autoregression_criteria_summary(series, name):
    """
    Расчёт критериев для сводной таблицы (краткий вывод).
    """
    irwin = irwin_criterion(series, threshold=3.0)
    ttest = t_test_slope(series, alpha=0.05)
    
    return {
        'series': name,
        'outliers_count': irwin.get('outlier_count', 0) if 'error' not in irwin else None,
        'trend_significant': ttest.get('significant') if 'error' not in ttest else None,
        't_statistic': ttest.get('t_statistic') if 'error' not in ttest else None,
        'p_value': ttest.get('p_value') if 'error' not in ttest else None
    }


def analyze_single_country(country_id, country_name):
    """Анализ одной страны (подробный вывод)."""
    print(f"\n✅ Анализ для страны: {country_name}")
    
    # Получаем данные
    data = IndicatorService.filter_indicators(country_id=country_id)
    if len(data) < 5:
        print(f"❌ Недостаточно данных для анализа (нужно минимум 5 лет)")
        return None, None, None
    
    # Очистка данных
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
        print(f"❌ Недостаточно корректных данных (нужно минимум 5 лет)")
        return None, None, None
    
    # Сортируем по году
    clean_data.sort(key=lambda x: x['year'])
    
    # Извлекаем ряды
    years = [row['year'] for row in clean_data]
    export_series = [row['export_value'] for row in clean_data]
    import_series = [row['import_value'] for row in clean_data]
    gdp_series = [row['gdp_value'] for row in clean_data]
    
    print(f"\n📅 Период: {min(years)} – {max(years)} (всего {len(clean_data)} лет)")
    
    # ==================== 1. АВТОРЕГРЕССИЯ ====================
    print("\n" + "=" * 90)
    print(" ЧАСТЬ 1: АНАЛИЗ ВРЕМЕННЫХ РЯДОВ (АВТОРЕГРЕССИЯ)")
    print("=" * 90)
    
    auto_results = []
    auto_results.append(calculate_autoregression_criteria_detailed(export_series, "ЭКСПОРТ", country_name))
    auto_results.append(calculate_autoregression_criteria_detailed(import_series, "ИМПОРТ", country_name))
    auto_results.append(calculate_autoregression_criteria_detailed(gdp_series, "ВВП", country_name))
    
    # ==================== 2. РЕГРЕССИЯ ====================
    print("\n" + "=" * 90)
    print(" ЧАСТЬ 2: РЕГРЕССИОННЫЙ АНАЛИЗ ВВП (ВВП = f(экспорт, импорт))")
    print("=" * 90)
    
    X, y, feature_names = prepare_regression_data(clean_data)
    reg_result = None
    if X is not None and len(X) >= 5:
        reg_result = calculate_regression_criteria_detailed(X, y, feature_names, country_name)
    else:
        print("❌ Недостаточно данных для регрессионного анализа")
    
    # ==================== 3. СОХРАНЕНИЕ ====================
    print("\n" + "=" * 90)
    print(" СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
    print("=" * 90)
    
    df_data = pd.DataFrame(clean_data)
    safe_name = country_name.replace(' ', '_').replace('/', '_')
    df_data.to_csv(f"{safe_name}_data.csv", index=False, encoding='utf-8-sig')
    print(f"✅ Данные сохранены: {safe_name}_data.csv")
    
    return auto_results, reg_result, clean_data


def analyze_all_countries():
    """Анализ всех стран (сводная таблица)."""
    print("\n" + "=" * 90)
    print(" АНАЛИЗ ВСЕХ СТРАН – СВОДНЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 90)
    
    countries = CountryService.get_all_countries()
    if not countries:
        print("❌ Нет стран в базе данных")
        return
    
    # Списки для сбора результатов
    regression_results = []
    autoregression_export = []
    autoregression_import = []
    autoregression_gdp = []
    
    print(f"\n📊 Обработка {len(countries)} стран...")
    
    for country in countries:
        country_id = country['id']
        country_name = country['name']
        print(f"   → Анализ: {country_name}...")
        
        # Получаем данные
        data = IndicatorService.filter_indicators(country_id=country_id)
        if len(data) < 5:
            continue
        
        # Очистка данных
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
            continue
        
        clean_data.sort(key=lambda x: x['year'])
        
        # Извлекаем ряды
        export_series = [row['export_value'] for row in clean_data]
        import_series = [row['import_value'] for row in clean_data]
        gdp_series = [row['gdp_value'] for row in clean_data]
        
        # Авторегрессия (краткие результаты)
        auto_exp = calculate_autoregression_criteria_summary(export_series, 'Экспорт')
        auto_imp = calculate_autoregression_criteria_summary(import_series, 'Импорт')
        auto_gdp = calculate_autoregression_criteria_summary(gdp_series, 'ВВП')
        
        auto_exp['country'] = country_name
        auto_imp['country'] = country_name
        auto_gdp['country'] = country_name
        
        autoregression_export.append(auto_exp)
        autoregression_import.append(auto_imp)
        autoregression_gdp.append(auto_gdp)
        
        # Регрессия
        X, y, _ = prepare_regression_data(clean_data)
        if X is not None and len(X) >= 5:
            reg_summary = calculate_regression_criteria_summary(X, y, country_name)
            if reg_summary:
                regression_results.append(reg_summary)
    
    # ==================== ВЫВОД СВОДНЫХ ТАБЛИЦ ====================
    
    # 1. Регрессионный анализ
    print("\n" + "=" * 90)
    print(" СВОДНАЯ ТАБЛИЦА: РЕГРЕССИОННЫЙ АНАЛИЗ ВВП")
    print("=" * 90)
    
    if regression_results:
        df_reg = pd.DataFrame(regression_results)
        df_reg = df_reg.sort_values('r2', ascending=False)
        
        # Форматирование для вывода
        display_df = df_reg.copy()
        display_df['r2'] = display_df['r2'].apply(lambda x: f"{x:.4f}")
        display_df['r2_adj'] = display_df['r2_adj'].apply(lambda x: f"{x:.4f}")
        display_df['f_statistic'] = display_df['f_statistic'].apply(lambda x: f"{x:.2f}")
        display_df['f_pvalue'] = display_df['f_pvalue'].apply(lambda x: f"{x:.6f}" if pd.notna(x) else "—")
        display_df['model_significant'] = display_df['model_significant'].apply(lambda x: "✅ Да" if x else "❌ Нет")
        
        print(tabulate(display_df[['country', 'data_points', 'r2', 'r2_adj', 'f_statistic', 'f_pvalue', 'model_significant']],
                       headers=['Страна', 'Лет', 'R²', 'R² скорр.', 'F-статистика', 'p-значение', 'Модель значима'],
                       tablefmt='grid'))
    else:
        print("Нет данных для регрессионного анализа")
    
    # 2. Авторегрессия экспорта
    print("\n" + "=" * 90)
    print(" СВОДНАЯ ТАБЛИЦА: АВТОРЕГРЕССИЯ ЭКСПОРТА")
    print("=" * 90)
    
    if autoregression_export:
        df_exp = pd.DataFrame(autoregression_export)
        df_exp['trend_significant'] = df_exp['trend_significant'].apply(lambda x: "✅ Да" if x else "❌ Нет")
        df_exp['t_statistic'] = df_exp['t_statistic'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        print(tabulate(df_exp[['country', 'outliers_count', 'trend_significant', 't_statistic']],
                       headers=['Страна', 'Аномалии', 'Тренд значим', 't-статистика'],
                       tablefmt='grid'))
    
    # 3. Авторегрессия импорта
    print("\n" + "=" * 90)
    print(" СВОДНАЯ ТАБЛИЦА: АВТОРЕГРЕССИЯ ИМПОРТА")
    print("=" * 90)
    
    if autoregression_import:
        df_imp = pd.DataFrame(autoregression_import)
        df_imp['trend_significant'] = df_imp['trend_significant'].apply(lambda x: "✅ Да" if x else "❌ Нет")
        df_imp['t_statistic'] = df_imp['t_statistic'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        print(tabulate(df_imp[['country', 'outliers_count', 'trend_significant', 't_statistic']],
                       headers=['Страна', 'Аномалии', 'Тренд значим', 't-статистика'],
                       tablefmt='grid'))
    
    # 4. Авторегрессия ВВП
    print("\n" + "=" * 90)
    print(" СВОДНАЯ ТАБЛИЦА: АВТОРЕГРЕССИЯ ВВП")
    print("=" * 90)
    
    if autoregression_gdp:
        df_gdp = pd.DataFrame(autoregression_gdp)
        df_gdp['trend_significant'] = df_gdp['trend_significant'].apply(lambda x: "✅ Да" if x else "❌ Нет")
        df_gdp['t_statistic'] = df_gdp['t_statistic'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
        print(tabulate(df_gdp[['country', 'outliers_count', 'trend_significant', 't_statistic']],
                       headers=['Страна', 'Аномалии', 'Тренд значим', 't-статистика'],
                       tablefmt='grid'))
    
    # ==================== СОХРАНЕНИЕ В CSV ====================
    print("\n" + "=" * 90)
    print(" СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
    print("=" * 90)
    
    if regression_results:
        pd.DataFrame(regression_results).to_csv('all_countries_regression_criteria.csv', index=False, encoding='utf-8-sig')
        print("✅ all_countries_regression_criteria.csv")
    
    if autoregression_export:
        pd.DataFrame(autoregression_export).to_csv('all_countries_export_autoregression.csv', index=False, encoding='utf-8-sig')
        print("✅ all_countries_export_autoregression.csv")
    
    if autoregression_import:
        pd.DataFrame(autoregression_import).to_csv('all_countries_import_autoregression.csv', index=False, encoding='utf-8-sig')
        print("✅ all_countries_import_autoregression.csv")
    
    if autoregression_gdp:
        pd.DataFrame(autoregression_gdp).to_csv('all_countries_gdp_autoregression.csv', index=False, encoding='utf-8-sig')
        print("✅ all_countries_gdp_autoregression.csv")


def main():
    print("=" * 90)
    print(" СТАТИСТИЧЕСКИЕ КРИТЕРИИ ДЛЯ РЕГРЕССИИ И АВТОРЕГРЕССИИ")
    print("=" * 90)
    print("   • Критерий Стьюдента (t-тест) – значимость коэффициентов")
    print("   • Критерий Фишера (F-тест) – значимость модели в целом")
    print("   • Критерий Ирвина – обнаружение аномалий в рядах")
    print("   • t-тест значимости тренда для авторегрессии")
    print("=" * 90)
    
    # Инициализация БД
    print("\n🔌 Инициализация базы данных...")
    init_database()
    Database.init_pool()
    print("✅ База данных готова\n")
    
    # Выбор режима
    print("Выберите режим работы:")
    print("   1 – Анализ одной страны (подробный вывод)")
    print("   2 – Анализ всех стран (сводная таблица)")
    
    choice = input("\n👉 Ваш выбор (1 или 2): ").strip()
    
    if choice == '1':
        # Режим одной страны
        countries = CountryService.get_all_countries()
        if not countries:
            print("❌ Нет стран в базе данных")
            return
        
        print("\nСписок стран:")
        for c in countries:
            print(f"   {c['id']}: {c['name']}")
        
        try:
            country_id = int(input("\n👉 Введите ID страны для анализа: "))
            country = next((c for c in countries if c['id'] == country_id), None)
            if not country:
                print(f"❌ Страна с ID {country_id} не найдена")
                return
            analyze_single_country(country_id, country['name'])
        except ValueError:
            print("❌ Неверный ID страны")
    
    elif choice == '2':
        # Режим всех стран
        analyze_all_countries()
    
    else:
        print("❌ Неверный выбор. Запустите программу заново.")
    
    # Закрытие соединения
    if hasattr(Database, 'close_pool'):
        Database.close_pool()
    
    print("\n" + "=" * 90)
    print(" РАБОТА ЗАВЕРШЕНА")
    print("=" * 90)


if __name__ == '__main__':
    main()