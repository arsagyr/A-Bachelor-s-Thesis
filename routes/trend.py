from flask import Blueprint, request, jsonify
from services.forecast_service import ForecastService
import traceback

trend_bp = Blueprint('trend', __name__)


@trend_bp.route('/api/trend/<int:country_id>/<indicator>', methods=['GET'])
def check_trend_significance(country_id, indicator):
    """Проверка значимости тренда по t-критерию Стьюдента"""
    try:
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя. Допустимые: export, import, gdp'}), 400
        
        indicator_field = f'{indicator}_value'
        alpha = request.args.get('alpha', 0.05, type=float)
        
        result = ForecastService.check_trend_significance(country_id, indicator_field, alpha)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка проверки тренда')}), 400
    except Exception as e:
        print(f"Error in trend: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@trend_bp.route('/api/trend/compare/<int:country_id>', methods=['GET'])
def compare_trends(country_id):
    """Сравнение трендов экспорта, импорта и ВВП"""
    try:
        result = ForecastService.compare_trends(country_id)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка сравнения трендов')}), 400
    except Exception as e:
        print(f"Error in compare trends: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500