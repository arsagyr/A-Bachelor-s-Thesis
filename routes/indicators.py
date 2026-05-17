from flask import Blueprint, request, jsonify, send_file
from services.indicator_service import IndicatorService
from services.csv_import_service import CSVImportService
from services.forecast_service import ForecastService
from services.regression_service import RegressionService
import pandas as pd
import io
import json
import traceback

indicators_bp = Blueprint('indicators', __name__)


# ==================== ОСНОВНЫЕ ЭНДПОИНТЫ ====================

@indicators_bp.route('/api/indicators/<int:country_id>', methods=['GET'])
def get_indicators_by_country(country_id):
    """Получение показателей для страны"""
    try:
        indicators = IndicatorService.get_indicators_by_country(country_id)
        return jsonify(indicators)
    except Exception as e:
        print(f"Error in get_indicators_by_country: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/filter', methods=['GET'])
def filter_indicators():
    """Фильтрация показателей"""
    try:
        country_id = request.args.get('country_id', type=int)
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        indicator_type = request.args.get('indicator_type', 'all')
        
        data = IndicatorService.filter_indicators(
            country_id=country_id,
            start_year=start_year,
            end_year=end_year,
            indicator_type=indicator_type
        )
        
        return jsonify(data)
    except Exception as e:
        print(f"Error in filter_indicators: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/stats/<int:country_id>', methods=['GET'])
def get_stats(country_id):
    """Получение статистики по стране"""
    try:
        stats = IndicatorService.get_country_stats(country_id)
        if stats:
            return jsonify(stats)
        return jsonify({'error': 'Статистика не найдена'}), 404
    except Exception as e:
        print(f"Error in get_stats: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/years', methods=['GET'])
def get_available_years():
    """Получение доступных годов"""
    try:
        years = IndicatorService.get_available_years()
        return jsonify(years)
    except Exception as e:
        print(f"Error in get_available_years: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/add_indicator', methods=['POST'])
def add_indicator():
    """Добавление показателя"""
    try:
        data = request.json
        country_id = data.get('country_id')
        year = data.get('year')
        export_value = data.get('export_value')
        import_value = data.get('import_value')
        gdp_value = data.get('gdp_value')
        
        if not all([country_id, year]):
            return jsonify({'error': 'Страна и год обязательны'}), 400
        
        success, message = IndicatorService.add_or_update_indicator(
            country_id=country_id,
            year=year,
            export_value=export_value,
            import_value=import_value,
            gdp_value=gdp_value
        )
        
        if success:
            return jsonify({'message': message})
        
        return jsonify({'error': message}), 400
    except Exception as e:
        print(f"Error in add_indicator: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
def delete_indicator(indicator_id):
    """Удаление показателя"""
    try:
        success, message = IndicatorService.delete_indicator(indicator_id)
        if success:
            return jsonify({'message': message})
        return jsonify({'error': message}), 404
    except Exception as e:
        print(f"Error in delete_indicator: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== CSV ИМПОРТ ====================

@indicators_bp.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    """Предпросмотр CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        return jsonify({'error': 'Поддерживаются только CSV и Excel файлы'}), 400
    
    try:
        file_content = file.read()
        preview_result = CSVImportService.preview_csv(file_content, file.filename)
        
        if preview_result['success']:
            return jsonify(preview_result)
        else:
            return jsonify({'error': preview_result['error']}), 400
            
    except Exception as e:
        print(f"Error in preview_csv: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ошибка при обработке файла: {str(e)}'}), 500


@indicators_bp.route('/api/csv/import', methods=['POST'])
def import_csv():
    """Импорт CSV файла в базу данных"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        return jsonify({'error': 'Поддерживаются только CSV и Excel файлы'}), 400
    
    custom_mapping = request.form.get('mapping')
    if custom_mapping:
        try:
            custom_mapping = json.loads(custom_mapping)
        except:
            pass
    
    try:
        file_content = file.read()
        import_result = CSVImportService.import_csv(
            file_content, 
            file.filename, 
            custom_mapping
        )
        
        return jsonify(import_result)
        
    except Exception as e:
        print(f"Error in import_csv: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ошибка при импорте: {str(e)}'}), 500


@indicators_bp.route('/api/csv/template', methods=['GET'])
def download_template():
    """Скачивание шаблона CSV файла"""
    try:
        template_content = CSVImportService.generate_template()
        
        return send_file(
            io.BytesIO(template_content),
            mimetype='text/csv',
            as_attachment=True,
            download_name='import_template.csv'
        )
    except Exception as e:
        print(f"Error in download_template: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ошибка при создании шаблона: {str(e)}'}), 500


@indicators_bp.route('/api/csv/mapping-options', methods=['GET'])
def get_mapping_options():
    """Получение вариантов маппинга колонок"""
    return jsonify({
        'available_mappings': list(CSVImportService.COLUMN_MAPPING.keys()),
        'column_keywords': CSVImportService.COLUMN_MAPPING
    })


# ==================== ПРОГНОЗИРОВАНИЕ ВРЕМЕННЫХ РЯДОВ ====================

@indicators_bp.route('/api/forecast/<int:country_id>/<indicator>', methods=['GET'])
def get_forecast_for_country(country_id, indicator):
    """
    Получение прогноза для страны и показателя с выбором модели
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        model_type = request.args.get('model', 'auto')
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя. Доступные: export, import, gdp'}), 400
        
        indicator_field = f'{indicator}_value'
        
        forecast = ForecastService.get_forecast_for_country(
            country_id=country_id,
            indicator_type=indicator_field,
            steps=steps,
            model_type=model_type
        )
        
        if forecast.get('success', False):
            return jsonify(forecast)
        else:
            error_msg = forecast.get('error', 'Ошибка прогнозирования')
            return jsonify({'error': error_msg}), 400
            
    except Exception as e:
        print(f"Error in get_forecast_for_country: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@indicators_bp.route('/api/forecast/<int:country_id>/all', methods=['GET'])
def get_all_forecasts_for_country(country_id):
    """
    Получение прогнозов для всех показателей страны
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        model_type = request.args.get('model', 'auto')
        
        forecasts = ForecastService.get_all_forecasts_for_country(
            country_id=country_id,
            steps=steps,
            model_type=model_type
        )
        return jsonify(forecasts)
        
    except Exception as e:
        print(f"Error in get_all_forecasts_for_country: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@indicators_bp.route('/api/forecast/models', methods=['GET'])
def get_available_forecast_models():
    """
    Получение списка доступных моделей прогнозирования
    """
    return jsonify({
        'models': ForecastService.AVAILABLE_MODELS,
        'default': 'auto',
        'description': {
            'auto': 'Автоматический выбор лучшей модели на основе RMSE',
            'arima': 'ARIMA - классическая модель авторегрессии',
            'holt_winters': 'Хольта-Винтерса - учитывает тренд и сезонность',
            'linear': 'Линейная регрессия - простой линейный тренд',
            'exponential': 'Экспоненциальное сглаживание - взвешенное среднее'
        }
    })


# ==================== РЕГРЕССИОННЫЙ АНАЛИЗ ====================

@indicators_bp.route('/api/regression/country/<int:country_id>', methods=['GET'])
def regression_analysis_for_country(country_id):
    """
    Регрессионный анализ зависимости ВВП от экспорта и импорта для страны
    """
    try:
        model_type = request.args.get('model', 'linear')
        
        if model_type not in ['linear', 'ridge', 'lasso', 'polynomial']:
            model_type = 'linear'
        
        print(f"Starting regression analysis for country {country_id} with model {model_type}")
        
        result = RegressionService.analyze_country(country_id, model_type)
        
        if result.get('success'):
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Ошибка анализа')
            print(f"Regression analysis error: {error_msg}")
            return jsonify({'error': error_msg}), 400
            
    except Exception as e:
        print(f"Exception in regression_analysis_for_country: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@indicators_bp.route('/api/regression/predict', methods=['POST'])
def predict_gdp():
    """
    Прогнозирование ВВП на основе экспорта и импорта
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных в запросе'}), 400
        
        country_id = data.get('country_id')
        export_value = data.get('export_value')
        import_value = data.get('import_value')
        model_type = data.get('model_type', 'linear')
        
        if not country_id:
            return jsonify({'error': 'Необходимо указать country_id'}), 400
        
        if export_value is None or import_value is None:
            return jsonify({'error': 'Необходимо указать export_value и import_value'}), 400
        
        try:
            export_value = float(export_value)
            import_value = float(import_value)
        except ValueError:
            return jsonify({'error': 'export_value и import_value должны быть числами'}), 400
        
        if export_value <= 0 or import_value <= 0:
            return jsonify({'error': 'Экспорт и импорт должны быть положительными числами'}), 400
        
        result = RegressionService.predict_gdp(country_id, export_value, import_value, model_type)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
            
    except Exception as e:
        print(f"Exception in predict_gdp: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@indicators_bp.route('/api/regression/models', methods=['GET'])
def get_regression_models():
    """
    Получение списка доступных регрессионных моделей
    """
    return jsonify({
        'models': RegressionService.AVAILABLE_MODELS,
        'default': 'linear',
        'description': {
            'linear': 'Линейная регрессия - простая линейная зависимость',
            'ridge': 'Ridge регрессия - с L2 регуляризацией для предотвращения переобучения',
            'lasso': 'Lasso регрессия - с L1 регуляризацией, автоматический отбор признаков',
            'polynomial': 'Полиномиальная регрессия - учитывает нелинейные зависимости'
        }
    })


# ==================== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ====================

@indicators_bp.route('/api/indicators/compare', methods=['GET'])
def compare_countries():
    """
    Сравнение показателей нескольких стран
    """
    try:
        country_ids = request.args.get('country_ids', type=str)
        if country_ids:
            country_ids = [int(x) for x in country_ids.split(',')]
        else:
            return jsonify({'error': 'Не указаны страны для сравнения'}), 400
        
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        indicator_type = request.args.get('indicator_type', 'all')
        
        results = {}
        for country_id in country_ids:
            data = IndicatorService.filter_indicators(
                country_id=country_id,
                start_year=start_year,
                end_year=end_year,
                indicator_type=indicator_type
            )
            results[country_id] = data
        
        return jsonify({
            'countries': results,
            'comparison': True
        })
    except Exception as e:
        print(f"Error in compare_countries: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/export/csv', methods=['GET'])
def export_to_csv():
    """
    Экспорт данных в CSV
    """
    try:
        country_id = request.args.get('country_id', type=int)
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        
        data = IndicatorService.filter_indicators(
            country_id=country_id,
            start_year=start_year,
            end_year=end_year,
            indicator_type='all'
        )
        
        if not data:
            return jsonify({'error': 'Нет данных для экспорта'}), 404
        
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='economic_data_export.csv'
        )
    except Exception as e:
        print(f"Error in export_to_csv: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    # ==================== ИНТЕГРИРОВАННЫЙ ПРОГНОЗ ====================

@indicators_bp.route('/api/integrated-forecast/<int:country_id>', methods=['GET'])
def get_integrated_forecast(country_id):
    """
    Интегрированный прогноз: прогноз экспорта и импорта через временные ряды,
    затем прогноз ВВП на их основе через регрессию
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        regression_model = request.args.get('regression_model', 'linear')
        
        if regression_model not in ['linear', 'ridge', 'lasso']:
            regression_model = 'linear'
        
        result = IntegratedForecastService.integrated_forecast_with_confidence(
            country_id=country_id,
            steps=steps,
            regression_model=regression_model
        )
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
            
    except Exception as e:
        print(f"Error in get_integrated_forecast: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/integrated-forecast/<int:country_id>/compare', methods=['GET'])
def compare_integrated_forecast(country_id):
    """
    Сравнение различных методов прогнозирования ВВП
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        # Получаем прогнозы разными методами
        results = {}
        
        # 1. Интегрированный прогноз
        integrated = IntegratedForecastService.integrated_forecast_with_confidence(
            country_id, steps, regression_model='linear'
        )
        results['integrated'] = integrated
        
        # 2. Прямой прогноз ВВП через временные ряды
        direct = ForecastService.get_forecast_for_country(
            country_id, 'gdp_value', steps, 'auto'
        )
        results['direct_ts'] = direct
        
        # 3. Регрессионный прогноз с текущими данными
        regression = RegressionService.analyze_country(country_id, 'linear')
        results['regression'] = regression
        
        return jsonify({
            'success': True,
            'country_id': country_id,
            'steps': steps,
            'comparison': results
        })
        
    except Exception as e:
        print(f"Error in compare_integrated_forecast: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500