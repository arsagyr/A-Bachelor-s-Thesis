#!/usr/bin/env python3
"""
Консольная программа для регрессионного и авторегрессионного анализа экономических данных
"""

import sys
import argparse
import numpy as np
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

from database import Database, init_database
from services.indicator_service import IndicatorService
from services.country_service import CountryService
from calculations import (
    prepare_regression_features,
    convert_data_to_float,
    linear_regression_analysis,
    ridge_regression_analysis,
    lasso_regression_analysis,
    polynomial_regression_analysis,
    compare_all_models,
    forecast_gdp,
    auto_regression_forecast,
    auto_regression_with_confidence,
    compare_auto_regression_models,
    AUTO_AVAILABLE_MODELS
)


# ==================== ВЫВОД РЕЗУЛЬТАТОВ ====================

def print_header(text, char='='):
    """Вывод заголовка"""
    print("\n" + char * 70)
    print(f" {text}")
    print(char * 70)


def print_subheader(text):
    """Вывод подзаголовка"""
    print(f"\n--- {text} ---")


def print_country_list(countries):
    """Вывод списка стран"""
    print_header("СПИСОК СТРАН")
    print(f"{'ID':<6} {'Название'}")
    print("-" * 40)
    for c in countries:
        print(f"{c['id']:<6} {c['name']}")
    print()


def print_data_table(data):
    """Вывод таблицы данных"""
    print_header("ИСТОРИЧЕСКИЕ ДАННЫЕ")
    print(f"{'Год':<8} {'Экспорт':<18} {'Импорт':<18} {'ВВП':<18}")
    print("-" * 65)
    for row in data:
        print(f"{row['year']:<8} {row['export_value']:<18.2f} {row['import_value']:<18.2f} {row['gdp_value']:<18.2f}")
    print()


def print_auto_regression_results(data, indicator_name, forecast_result):
    """Вывод результатов авторегрессионного прогноза"""
    print_subheader(f"АВТОРЕГРЕССИОННЫЙ ПРОГНОЗ {indicator_name}")
    
    if not forecast_result.get('success'):
        print(f"   ❌ Ошибка: {forecast_result.get('error')}")
        return
    
    print(f"\n   Модель: {forecast_result.get('model_name', forecast_result.get('model_type', 'N/A'))}")
    
    print("\n📊 МЕТРИКИ КАЧЕСТВА МОДЕЛИ:")
    print(f"   RMSE = {forecast_result.get('rmse', 0):.2f} млрд USD")
    print(f"   MAE  = {forecast_result.get('mae', 0):.2f} млрд USD")
    print(f"   R²   = {forecast_result.get('r2', 0):.4f}")
    
    print(f"\n📐 ФОРМУЛА ТРЕНДА:")
    print(f"   {forecast_result.get('formula', 'N/A')}")
    
    print(f"\n🔮 ПРОГНОЗ НА {len(forecast_result['forecast'])} ЛЕТ:")
    last_year = data[-1]['year']
    for i, val in enumerate(forecast_result['forecast']):
        year = last_year + i + 1
        print(f"   {year}: {val:.2f} млрд USD")
    
    if 'lower_bounds' in forecast_result and 'upper_bounds' in forecast_result:
        print(f"\n📊 ДОВЕРИТЕЛЬНЫЕ ИНТЕРВАЛЫ ({int(forecast_result.get('confidence_level', 0.95)*100)}%):")
        for i, val in enumerate(forecast_result['forecast']):
            year = last_year + i + 1
            print(f"   {year}: [{forecast_result['lower_bounds'][i]:.2f} ; {forecast_result['upper_bounds'][i]:.2f}]")


def print_auto_regression_comparison(comparison, data):
    """Вывод сравнения всех моделей авторегрессии"""
    print_header("СРАВНЕНИЕ МОДЕЛЕЙ АВТОРЕГРЕССИИ")
    
    print(f"\n{'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12}")
    print("-" * 75)
    
    for name, result in comparison['all_models'].items():
        if result.get('success'):
            model_display = result.get('model_name', name)
            print(f"{model_display:<35} {result['r2']:<12.4f} {result['rmse']:<12.2f} {result['mae']:<12.2f}")
    
    print(f"\n🏆 ЛУЧШАЯ МОДЕЛЬ: {comparison['best_model_name']}")
    print(f"   R² = {comparison['best_r2']:.4f}")
    
    # Вывод прогноза лучшей модели
    best_result = comparison['all_models'].get(comparison['best_model'])
    if best_result and best_result.get('success'):
        print(f"\n🔮 ПРОГНОЗ ЛУЧШЕЙ МОДЕЛИ НА {comparison['steps']} ЛЕТ:")
        last_year = data[-1]['year']
        for i, val in enumerate(best_result['forecast']):
            year = last_year + i + 1
            print(f"   {year}: {val:.2f} млрд USD")


def print_model_details(model_result, feature_names):
    """Детальный вывод одной модели с формулой и всеми метриками"""
    print_subheader(model_result['name'])
    
    print("\n📊 МЕТРИКИ КАЧЕСТВА:")
    print(f"   ┌─────────────────────────────────────────┐")
    print(f"   │ R²  (коэффициент детерминации) : {model_result['metrics']['r2']:>10.6f} │")
    print(f"   │ RMSE (среднеквадратичная ошибка): {model_result['metrics']['rmse']:>10.2f} │")
    print(f"   │ MAE  (средняя абсолютная ошибка): {model_result['metrics']['mae']:>10.2f} │")
    print(f"   │ MAPE (средняя % ошибка)         : {model_result['metrics']['mape']:>10.2f}% │")
    print(f"   └─────────────────────────────────────────┘")
    
    r2 = model_result['metrics']['r2']
    if r2 >= 0.9:
        quality = "Отличное качество"
    elif r2 >= 0.7:
        quality = "Хорошее качество"
    elif r2 >= 0.5:
        quality = "Удовлетворительное качество"
    elif r2 >= 0.3:
        quality = "Слабое качество"
    else:
        quality = "Неудовлетворительное качество"
    print(f"\n   📈 Оценка качества: {quality}")
    
    print("\n📐 КОЭФФИЦИЕНТЫ МОДЕЛИ:")
    print(f"   Константа (intercept): {model_result['intercept']:.6f}")
    
    if 'poly' in model_result:
        print(f"\n   Полиномиальных признаков: {len(model_result['coefficients'])}")
        print("   (первые 10 коэффициентов для наглядности):")
        for i, coef in enumerate(model_result['coefficients'][:10]):
            print(f"      признак_{i}: {coef:.6f}")
        if len(model_result['coefficients']) > 10:
            print(f"      ... и еще {len(model_result['coefficients']) - 10} коэффициентов")
    else:
        print("\n   Коэффициенты при признаках:")
        for name, coef in zip(feature_names, model_result['coefficients']):
            sign = '+' if coef >= 0 else '-'
            abs_coef = abs(coef)
            print(f"      {name:>20} : {sign} {abs_coef:.6f}")
    
    print("\n📝 ФОРМУЛА РЕГРЕССИИ:")
    if 'poly' in model_result:
        print(f"   ВВП = {model_result['intercept']:.6f} + полиномиальные члены (степень {model_result.get('degree', 2)})")
    else:
        formula = f"   ВВП = {model_result['intercept']:.6f}"
        for name, coef in zip(feature_names, model_result['coefficients']):
            if abs(coef) > 1e-10:
                sign = '+' if coef >= 0 else '-'
                abs_coef = abs(coef)
                formula += f" {sign} {abs_coef:.6f}·{name}"
        print(formula)
    
    print("\n" + "-" * 70)


def print_comparison_table(models):
    """Вывод таблицы сравнения моделей"""
    print_header("СРАВНЕНИЕ РЕГРЕССИОННЫХ МОДЕЛЕЙ")
    
    print(f"\n{'№':<3} {'Модель':<35} {'R²':<12} {'RMSE':<12} {'MAE':<12} {'MAPE':<10}")
    print("-" * 85)
    
    for i, m in enumerate(models, 1):
        print(f"{i:<3} {m['name']:<35} {m['metrics']['r2']:<12.6f} {m['metrics']['rmse']:<12.2f} {m['metrics']['mae']:<12.2f} {m['metrics']['mape']:<10.2f}%")
    
    print("\n" + "-" * 85)


def print_best_model_summary(best_model, feature_names):
    """Вывод сводки по лучшей модели"""
    print_header(f"🏆 ЛУЧШАЯ РЕГРЕССИОННАЯ МОДЕЛЬ: {best_model['name']}")
    
    print("\n📊 МЕТРИКИ КАЧЕСТВА:")
    print(f"   R²   = {best_model['metrics']['r2']:.6f}")
    print(f"   RMSE = {best_model['metrics']['rmse']:.2f} млрд USD")
    print(f"   MAE  = {best_model['metrics']['mae']:.2f} млрд USD")
    print(f"   MAPE = {best_model['metrics']['mape']:.2f}%")
    
    if 'poly' in best_model:
        print(f"\n   Степень полинома: {best_model.get('degree', 2)}")
        print(f"   Количество признаков после преобразования: {len(best_model['coefficients'])}")
    else:
        print("\n📐 ФОРМУЛА ЗАВИСИМОСТИ:")
        formula = f"   ВВП = {best_model['intercept']:.6f}"
        for name, coef in zip(feature_names, best_model['coefficients']):
            if abs(coef) > 1e-10:
                sign = '+' if coef >= 0 else '-'
                abs_coef = abs(coef)
                formula += f" {sign} {abs_coef:.6f}·{name}"
        print(formula)
        
        print("\n📖 ИНТЕРПРЕТАЦИЯ КОЭФФИЦИЕНТОВ:")
        for name, coef in zip(feature_names, best_model['coefficients']):
            if abs(coef) > 1e-10:
                impact = "положительно" if coef > 0 else "отрицательно"
                print(f"   • {name}: при увеличении на 1 млрд USD, ВВП изменяется на {abs(coef):.4f} млрд USD ({impact})")


def print_prediction_analysis(model, data, best_model_result):
    """Анализ прогноза на последнем году с учётом типа модели"""
    last_export = float(data[-1]['export_value'])
    last_import = float(data[-1]['import_value'])
    last_gdp = float(data[-1]['gdp_value'])
    
    if 'poly' in best_model_result:
        from sklearn.preprocessing import PolynomialFeatures
        X_pred, _ = prepare_regression_features([last_export], [last_import])
        poly = PolynomialFeatures(degree=best_model_result.get('degree', 2), include_bias=False)
        X_pred_poly = poly.fit_transform(X_pred)
        predicted_gdp = model.predict(X_pred_poly)[0]
    else:
        predicted_gdp = forecast_gdp(model, last_export, last_import)
    
    error = predicted_gdp - last_gdp
    error_percent = (error / last_gdp) * 100 if last_gdp != 0 else 0
    
    print_header("ПРОВЕРКА ПРОГНОЗА НА ПОСЛЕДНЕМ ГОДЕ")
    
    print("\n📋 ИСХОДНЫЕ ДАННЫЕ:")
    print(f"   Год: {data[-1]['year']}")
    print(f"   Экспорт: {last_export:.2f} млрд USD")
    print(f"   Импорт: {last_import:.2f} млрд USD")
    print(f"   Фактический ВВП: {last_gdp:.2f} млрд USD")
    
    print("\n🔮 РЕЗУЛЬТАТ ПРОГНОЗА:")
    print(f"   Предсказанный ВВП: {predicted_gdp:.2f} млрд USD")
    print(f"   Абсолютная ошибка: {error:+.2f} млрд USD")
    print(f"   Относительная ошибка: {error_percent:+.2f}%")
    
    if abs(error_percent) < 5:
        print("\n   ✅ Отлично! Ошибка менее 5%")
    elif abs(error_percent) < 10:
        print("\n   ✅ Хорошо! Ошибка менее 10%")
    elif abs(error_percent) < 20:
        print("\n   ⚠️ Удовлетворительно. Ошибка менее 20%")
    else:
        print("\n   ❌ Плохо. Ошибка более 20%")


def print_forecast_result(country_name, export_val, import_val, predicted_gdp, actual_gdp_last, last_year):
    """Вывод результата прогноза по заданным значениям"""
    print_header("ПРОГНОЗ ВВП ПО ЗАДАННЫМ ЗНАЧЕНИЯМ")
    
    print("\n📋 ВХОДНЫЕ ДАННЫЕ:")
    print(f"   Страна: {country_name}")
    print(f"   Экспорт: {export_val:.2f} млрд USD")
    print(f"   Импорт: {import_val:.2f} млрд USD")
    
    print("\n🔮 РЕЗУЛЬТАТ ПРОГНОЗА:")
    print(f"   📊 Прогнозируемый ВВП: {predicted_gdp:.2f} млрд USD")
    
    print("\n📊 ДЛЯ СПРАВКИ:")
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
    parser.add_argument('-m', '--model', type=str, default='linear', 
                        choices=['linear', 'polynomial', 'exponential', 'ridge', 'lasso', 'compare'],
                        help='Модель для авторегрессии (по умолчанию linear)')
    parser.add_argument('-d', '--degree', type=int, default=2, help='Степень полинома (для polynomial)')
    parser.add_argument('--steps', type=int, default=5, help='Горизонт прогноза (по умолчанию 5 лет)')
    args = parser.parse_args()
    
    # Инициализация БД
    print("🔌 Инициализация базы данных...")
    init_database()
    Database.init_pool()
    print("✅ База данных готова\n")
    
    # Показываем список стран
    if args.list:
        countries = CountryService.get_all_countries()
        print_country_list(countries)
        return
    
    # Анализ всех стран
    if args.all:
        countries = CountryService.get_all_countries()
        print_header("РЕГРЕССИОННЫЙ АНАЛИЗ ДЛЯ ВСЕХ СТРАН")
        
        all_results = []
        for country in countries:
            data = IndicatorService.filter_indicators(country_id=country['id'])
            
            if len(data) >= 4:
                data = convert_data_to_float(data)
                
                export = [d['export_value'] for d in data]
                import_val = [d['import_value'] for d in data]
                gdp = [d['gdp_value'] for d in data]
                
                X, feature_names = prepare_regression_features(export, import_val)
                y = np.array(gdp)
                
                models, best_model = compare_all_models(X, y, feature_names)
                
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
    
    # Авторегрессионный прогноз экспорта и импорта
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
        
        export_series = [d['export_value'] for d in data]
        import_series = [d['import_value'] for d in data]
        
        # Сравнение всех моделей
        if args.model == 'compare':
            print_header("СРАВНЕНИЕ МОДЕЛЕЙ ДЛЯ ЭКСПОРТА")
            export_comparison = compare_auto_regression_models(export_series, args.steps)
            print_auto_regression_comparison(export_comparison, data)
            
            print_header("СРАВНЕНИЕ МОДЕЛЕЙ ДЛЯ ИМПОРТА")
            import_comparison = compare_auto_regression_models(import_series, args.steps)
            print_auto_regression_comparison(import_comparison, data)
        else:
            # Прогноз выбранной моделью
            if args.confidence:
                export_forecast = auto_regression_with_confidence(export_series, args.steps, args.model, 
                                                                   degree=args.degree)
                import_forecast = auto_regression_with_confidence(import_series, args.steps, args.model,
                                                                   degree=args.degree)
            else:
                export_forecast = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
                import_forecast = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
            
            print_auto_regression_results(data, "ЭКСПОРТА", export_forecast)
            print("\n" + "-" * 70)
            print_auto_regression_results(data, "ИМПОРТА", import_forecast)
        
        return
    
    # Полный анализ конкретной страны (включая регрессию ВВП)
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
        
        # 1. Авторегрессионный прогноз экспорта и импорта
        print_header("1. АВТОРЕГРЕССИОННЫЙ АНАЛИЗ")
        
        export_series = [d['export_value'] for d in data]
        import_series = [d['import_value'] for d in data]
        
        if args.model == 'compare':
            export_comparison = compare_auto_regression_models(export_series, args.steps)
            print_auto_regression_comparison(export_comparison, data)
            print("\n" + "-" * 70)
            import_comparison = compare_auto_regression_models(import_series, args.steps)
            print_auto_regression_comparison(import_comparison, data)
        else:
            export_forecast = auto_regression_forecast(export_series, args.steps, args.model, degree=args.degree)
            import_forecast = auto_regression_forecast(import_series, args.steps, args.model, degree=args.degree)
            
            print_auto_regression_results(data, "ЭКСПОРТА", export_forecast)
            print("\n" + "-" * 70)
            print_auto_regression_results(data, "ИМПОРТА", import_forecast)
        
        # 2. Регрессионный анализ ВВП
        print_header("2. РЕГРЕССИОННЫЙ АНАЛИЗ ВВП")
        
        export = [d['export_value'] for d in data]
        import_val = [d['import_value'] for d in data]
        gdp = [d['gdp_value'] for d in data]
        
        X, feature_names = prepare_regression_features(export, import_val)
        y = np.array(gdp)
        
        print_data_table(data)
        
        models, best_model = compare_all_models(X, y, feature_names)
        
        print_header("ДЕТАЛЬНЫЙ АНАЛИЗ РЕГРЕССИОННЫХ МОДЕЛЕЙ")
        for m in models:
            print_model_details(m, feature_names)
        
        print_comparison_table(models)
        
        print_best_model_summary(best_model, feature_names)
        
        print_prediction_analysis(best_model['model'], data, best_model)
        
        return
    
    # Прогноз ВВП по заданным значениям
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
            
            export_hist = [d['export_value'] for d in data]
            import_hist = [d['import_value'] for d in data]
            gdp_hist = [d['gdp_value'] for d in data]
            
            X, feature_names = prepare_regression_features(export_hist, import_hist)
            y = np.array(gdp_hist)
            
            model = LinearRegression()
            model.fit(X, y)
            
            predicted = forecast_gdp(model, export_val, import_val)
            
            actual_gdp_last = data[-1]['gdp_value']
            last_year = data[-1]['year']
            
            print_forecast_result(country['name'], export_val, import_val, predicted, actual_gdp_last, last_year)
            
        except ValueError:
            print("❌ Неверный ID страны")
        
        return
    
    parser.print_help()


if __name__ == '__main__':
    main()