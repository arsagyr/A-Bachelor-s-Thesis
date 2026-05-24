from flask import Blueprint, request, jsonify, send_file
from services.indicator_service import IndicatorService
from services.csv_import_service import CSVImportService
from services.country_service import CountryService
from services.forecast_service import ForecastService
from services.regression_service import RegressionService
from services.clustering_service import ClusteringService
import io
import traceback

indicators_bp = Blueprint('indicators', __name__)


# ==================== ОСНОВНЫЕ ЭНДПОИНТЫ ====================

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
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/stats/<int:country_id>', methods=['GET'])
def get_stats(country_id):
    """Получение статистики по стране"""
    try:
        stats = IndicatorService.get_country_stats(country_id)
        return jsonify(stats or {})
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== CSV ИМПОРТ/ЭКСПОРТ ====================

@indicators_bp.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    """Предпросмотр CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    try:
        result = CSVImportService.preview_csv(file.read(), file.filename)
        return jsonify(result) if result.get('success') else jsonify({'error': result.get('error')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/csv/import', methods=['POST'])
def import_csv():
    """Импорт CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    try:
        result = CSVImportService.import_csv(file.read(), file.filename)
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/csv/template', methods=['GET'])
def download_template():
    """Скачивание шаблона CSV"""
    try:
        content = CSVImportService.generate_template()
        return send_file(
            io.BytesIO(content),
            mimetype='text/csv',
            as_attachment=True,
            download_name='import_template.csv'
        )
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== ПРОГНОЗИРОВАНИЕ ВРЕМЕННЫХ РЯДОВ ====================

@indicators_bp.route('/api/forecast/<int:country_id>/<indicator>', methods=['GET'])
def get_forecast(country_id, indicator):
    """Прогноз показателя с выбором модели"""
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'auto')
        degree = request.args.get('degree', 2, type=int)
        alpha = request.args.get('alpha', 1.0, type=float)
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        indicator_field = f'{indicator}_value'
        result = ForecastService.get_forecast(country_id, indicator_field, steps, model_type, degree, alpha)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/forecast/models', methods=['GET'])
def get_forecast_models():
    """Получение списка доступных моделей прогнозирования"""
    return jsonify({
        'models': ForecastService.AVAILABLE_MODELS,
        'default': 'auto',
        'description': {
            'auto': 'Автоматический выбор лучшей модели по R²',
            'linear': 'Линейная регрессия - y = a + b·x',
            'polynomial': 'Полиномиальная регрессия - y = a + b·x + c·x²',
            'exponential': 'Экспоненциальная регрессия - y = e^(a + b·x)',
            'ridge': 'Ridge регрессия - L2-регуляризация',
            'lasso': 'Lasso регрессия - L1-регуляризация'
        }
    })


# ==================== РЕГРЕССИЯ ВВП ====================

@indicators_bp.route('/api/regression/gdp-forecast/<int:country_id>', methods=['GET'])
def get_gdp_regression_forecast(country_id):
    """Прогноз ВВП на основе регрессии экспорта и импорта"""
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'linear')
        
        if model_type not in ['linear', 'ridge', 'lasso', 'polynomial']:
            model_type = 'linear'
        
        degree = request.args.get('degree', 2, type=int)
        alpha = request.args.get('alpha', 1.0, type=float)
        
        result = RegressionService.get_gdp_forecast(country_id, steps, model_type, degree=degree, alpha=alpha)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/regression/models', methods=['GET'])
def get_regression_models():
    """Получение списка доступных регрессионных моделей"""
    return jsonify({
        'models': {
            'linear': 'Линейная регрессия',
            'ridge': 'Ridge регрессия (L2)',
            'lasso': 'Lasso регрессия (L1)',
            'polynomial': 'Полиномиальная регрессия (степень 2)'
        },
        'default': 'linear'
    })


# ==================== КЛАСТЕРИЗАЦИЯ ====================

@indicators_bp.route('/api/clustering/analyze', methods=['GET'])
def analyze_clusters():
    """Анализ кластеризации стран"""
    try:
        year = request.args.get('year', type=int)
        
        result = ClusteringService.analyze_country_clusters(year)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка кластеризации')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/clustering/available-years', methods=['GET'])
def get_clustering_available_years():
    """Получение доступных годов для кластеризации"""
    try:
        years = IndicatorService.get_available_years()
        return jsonify({'years': years})
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== УПРАВЛЕНИЕ ДАННЫМИ ====================

@indicators_bp.route('/api/countries', methods=['GET'])
def get_countries():
    """Получение списка стран"""
    try:
        countries = CountryService.get_all_countries()
        return jsonify(countries)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/countries/<int:country_id>', methods=['DELETE'])
def delete_country(country_id):
    """Удаление страны вместе со всеми показателями"""
    try:
        success, message = CountryService.delete_country(country_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
def delete_indicator(indicator_id):
    """Удаление одного показателя"""
    try:
        success, message = IndicatorService.delete_indicator(indicator_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@indicators_bp.route('/api/indicators/country/<int:country_id>', methods=['DELETE'])
def delete_country_indicators(country_id):
    """Удаление всех показателей страны (страна остаётся)"""
    try:
        success, message = IndicatorService.delete_indicators_by_country(country_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500