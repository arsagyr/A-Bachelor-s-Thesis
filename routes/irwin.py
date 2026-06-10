from flask import Blueprint, request, jsonify
from services.forecast_service import ForecastService
import traceback

irwin_bp = Blueprint('irwin', __name__)


@irwin_bp.route('/api/irwin/<int:country_id>/<indicator>', methods=['GET'])
def check_irwin_criterion(country_id, indicator):
    """Проверка временного ряда на аномалии по критерию Ирвина"""
    try:
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя. Допустимые: export, import, gdp'}), 400
        
        indicator_field = f'{indicator}_value'
        threshold = request.args.get('threshold', 3.0, type=float)
        
        result = ForecastService.check_irwin(country_id, indicator_field, threshold)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка проверки по Ирвину')}), 400
    except Exception as e:
        print(f"Error in irwin: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500