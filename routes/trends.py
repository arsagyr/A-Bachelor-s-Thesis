from flask import Blueprint, render_template, request, jsonify
from services.trend_service import TrendService

trends_bp = Blueprint('trends', __name__)


@trends_bp.route('/trends')
def trends_page():
    return render_template('trends.html')


@trends_bp.route('/api/trends/forecast/<int:country_id>', methods=['GET'])
def get_trends_forecast(country_id):
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'linear')
        
        result = TrendService.get_country_trends(country_id, steps, model_type)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500