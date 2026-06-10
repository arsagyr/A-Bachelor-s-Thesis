from flask import Blueprint, request, jsonify
from services.indicator_service import IndicatorService
import traceback

indicators_bp = Blueprint('indicators', __name__)


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
    """Удаление всех показателей страны"""
    try:
        success, message = IndicatorService.delete_indicators_by_country(country_id)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 404
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@indicators_bp.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API"""
    return jsonify({'status': 'ok', 'message': 'API работает'})