from flask import Blueprint, request, jsonify, send_file
from services import IndicatorService
from services import CSVImportService
from services import CountryService
from services import ForecastService
from calculations.auto_regression import (
    auto_regression_forecast,
    auto_regression_with_confidence,
    compare_auto_regression_models,
    AVAILABLE_MODELS
)
import pandas as pd
import io
import json

indicators_bp = Blueprint('indicators', __name__)


# ==================== ЭНДПОИНТЫ ====================

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


@indicators_bp.route('/api/countries', methods=['GET'])
def get_countries():
    try:
        countries = CountryService.get_all_countries()
        return jsonify(countries)
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


# ==================== АВТОРЕГРЕССИЯ ====================


@indicators_bp.route('/api/auto-regression/<int:country_id>/<indicator>', methods=['GET'])
def get_auto_regression_forecast(country_id, indicator):
    """
    Авторегрессионный прогноз для показателя
    """
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        model_type = request.args.get('model', 'linear')
        degree = request.args.get('degree', 2, type=int)
        show_confidence = request.args.get('confidence', 'false').lower() == 'true'
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        # Вызываем сервис (он сам получит данные из БД)
        result = ForecastService.get_auto_regression_forecast(
            country_id, indicator, steps, model_type, degree, show_confidence
        )
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@indicators_bp.route('/api/auto-regression/models', methods=['GET'])
def get_auto_regression_models():
    """Получение списка доступных моделей авторегрессии"""
    return jsonify({
        'models': AVAILABLE_MODELS,
        'default': 'linear'
    })


@indicators_bp.route('/api/auto-regression/compare/<int:country_id>/<indicator>', methods=['GET'])
def compare_auto_regression(country_id, indicator):
    """Сравнение всех моделей авторегрессии для показателя"""
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        data = IndicatorService.filter_indicators(country_id=country_id)
        
        if len(data) < 3:
            return jsonify({'error': f'Недостаточно данных: {len(data)} точек'}), 400
        
        countries = CountryService.get_all_countries()
        country = next((c for c in countries if c['id'] == country_id), None)
        
        if not country:
            return jsonify({'error': 'Страна не найдена'}), 404
        
        series = []
        years = []
        for row in sorted(data, key=lambda x: x['year']):
            val = row.get(f'{indicator}_value')
            if val is not None:
                series.append(float(val))
                years.append(row['year'])
        
        result = compare_auto_regression_models(series, steps)
        result['country_name'] = country['name']
        result['indicator'] = indicator
        result['indicator_name'] = {'export': 'Экспорт', 'import': 'Импорт', 'gdp': 'ВВП'}.get(indicator, indicator)
        result['years'] = years
        result['historical'] = series
        result['forecast_years'] = [years[-1] + i + 1 for i in range(steps)]
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
