from flask import Blueprint, request, jsonify, send_file
from services.indicator_service import IndicatorService
from services.csv_import_service import CSVImportService
from services.forecast_service import ForecastService
from services.regression_service import RegressionService
from services.country_service import CountryService
from services.clustering_service import ClusteringService
import pandas as pd
import io
import json
import traceback

indicators_bp = Blueprint('indicators', __name__)


@indicators_bp.route('/api/indicators/filter', methods=['GET'])
def filter_indicators():
    try:
        country_id = request.args.get('country_id', type=int)
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        indicator_type = request.args.get('indicator_type', 'all')
        
        data = IndicatorService.filter_indicators(
            country_id=country_id, start_year=start_year, end_year=end_year, indicator_type=indicator_type
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/stats/<int:country_id>', methods=['GET'])
def get_stats(country_id):
    try:
        stats = IndicatorService.get_country_stats(country_id)
        return jsonify(stats or {})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    try:
        result = CSVImportService.preview_csv(file.read(), file.filename)
        return jsonify(result) if result['success'] else jsonify({'error': result['error']}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/csv/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    try:
        result = CSVImportService.import_csv(file.read(), file.filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/csv/template', methods=['GET'])
def download_template():
    try:
        content = CSVImportService.generate_template()
        return send_file(io.BytesIO(content), mimetype='text/csv', as_attachment=True, download_name='import_template.csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/forecast/<int:country_id>/<indicator>', methods=['GET'])
def get_forecast(country_id, indicator):
    """
    Получение прогноза для страны и показателя
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'auto')
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя. Доступные: export, import, gdp'}), 400
        
        indicator_field = f'{indicator}_value'
        
        result = ForecastService.get_forecast_for_country(country_id, indicator_field, steps, model_type)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
            
    except Exception as e:
        print(f"Error in get_forecast: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/forecast/models', methods=['GET'])
def get_forecast_models():
    return jsonify({'models': ForecastService.AVAILABLE_MODELS})


@indicators_bp.route('/api/regression/country/<int:country_id>', methods=['GET'])
def regression_analysis(country_id):
    try:
        model_type = request.args.get('model', 'linear')
        result = RegressionService.analyze_country(country_id, model_type)
        return jsonify(result) if result.get('success') else jsonify({'error': result.get('error')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/regression/predict', methods=['POST'])
def predict_gdp():
    try:
        data = request.json
        result = RegressionService.predict_gdp(
            data.get('country_id'), data.get('export_value'), data.get('import_value'), data.get('model_type', 'linear')
        )
        return jsonify(result) if result.get('success') else jsonify({'error': result.get('error')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/regression/models', methods=['GET'])
def get_regression_models():
    return jsonify({'models': RegressionService.AVAILABLE_MODELS})

@indicators_bp.route('/api/regression/forecast/<int:country_id>', methods=['GET'])
def regression_forecast(country_id):
    """
    Прогноз ВВП на основе ARIMA прогнозов экспорта и импорта
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        model_type = request.args.get('model', 'linear')
        
        if model_type not in ['linear', 'ridge', 'lasso', 'polynomial']:
            model_type = 'linear'
        
        result = RegressionService.predict_gdp(country_id, steps, model_type)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@indicators_bp.route('/api/forecast/gdp-from-trade/<int:country_id>', methods=['GET'])
def forecast_gdp_from_trade(country_id):
    """
    Прогнозирование ВВП на основе прогнозов экспорта и импорта
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        model_type = request.args.get('model', 'linear')
        
        if model_type not in ['linear', 'ridge', 'lasso', 'polynomial']:
            model_type = 'linear'
        
        result = RegressionService.forecast_gdp_from_trade(country_id, steps, model_type)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    

    # Добавьте эти эндпоинты в конец файла routes/indicators.py

# ==================== УДАЛЕНИЕ ДАННЫХ ====================

@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
def delete_indicator(indicator_id):
    """Удаление показателя по ID"""
    try:
        success, message = IndicatorService.delete_indicator(indicator_id)
        if success:
            return jsonify({'message': message})
        return jsonify({'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/country/<int:country_id>', methods=['DELETE'])
def delete_country_indicators(country_id):
    """Удаление всех показателей страны"""
    try:
        success, message = IndicatorService.delete_indicators_by_country(country_id)
        if success:
            return jsonify({'message': message})
        return jsonify({'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/countries/<int:country_id>', methods=['DELETE'])
def delete_country(country_id):
    """Удаление страны (вместе со всеми показателями)"""
    try:
        success, message = CountryService.delete_country(country_id)
        if success:
            return jsonify({'message': message})
        return jsonify({'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# ==================== КЛАСТЕРИЗАЦИЯ СТРАН ====================

@indicators_bp.route('/api/clustering/analyze', methods=['GET'])
def analyze_clusters():
    """
    Анализ кластеризации стран по экономическим показателям
    """
    try:
        year = request.args.get('year', type=int)
        
        result = ClusteringService.analyze_country_clusters(year)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка кластеризации')}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/clustering/statistics', methods=['GET'])
def get_cluster_statistics():
    """
    Получение статистики по кластерам
    """
    try:
        year = request.args.get('year', type=int)
        
        result = ClusteringService.get_cluster_statistics(year)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка получения статистики')}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/clustering/available-years', methods=['GET'])
def get_available_years_for_clustering():
    """
    Получение доступных годов для кластеризации
    """
    try:
        from services.indicator_service import IndicatorService
        years = IndicatorService.get_available_years()
        return jsonify({'years': years})
    except Exception as e:
        return jsonify({'error': str(e)}), 500