from flask import Blueprint, request, jsonify, send_file
from services.indicator_service import IndicatorService
from services.csv_import_service import CSVImportService
from services.country_service import CountryService
from services.forecast_service import ForecastService
from services.clustering_service import ClusteringService
import io

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
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'auto')
        degree = request.args.get('degree', 2, type=int)
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        indicator_field = f'{indicator}_value'
        result = ForecastService.get_forecast(country_id, indicator_field, steps, model_type, degree)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/countries/<int:country_id>', methods=['DELETE'])
def delete_country(country_id):
    try:
        success, message = CountryService.delete_country(country_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
def delete_indicator(indicator_id):
    try:
        success, message = IndicatorService.delete_indicator(indicator_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/country/<int:country_id>', methods=['DELETE'])
def delete_country_indicators(country_id):
    try:
        success, message = IndicatorService.delete_indicators_by_country(country_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@indicators_bp.route('/api/clustering/analyze', methods=['GET'])
def analyze_clusters():
    """Анализ кластеризации стран"""
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


@indicators_bp.route('/api/clustering/available-years', methods=['GET'])
def get_clustering_available_years():
    """Получение доступных годов для кластеризации"""
    try:
        years = IndicatorService.get_available_years()
        return jsonify({'years': years})
    except Exception as e:
        return jsonify({'error': str(e)}), 500