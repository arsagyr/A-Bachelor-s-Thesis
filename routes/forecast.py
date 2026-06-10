from flask import Blueprint, request, jsonify
from services.forecast_service import ForecastService
import traceback

forecast_bp = Blueprint('forecast', __name__)


@forecast_bp.route('/api/forecast/<int:country_id>/<indicator>', methods=['GET'])
def get_forecast(country_id, indicator):
    """Прогноз показателя с выбором модели"""
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'auto')
        degree = request.args.get('degree', 2, type=int)
        alpha = request.args.get('alpha', 1.0, type=float)
        
        # Проверка индикатора
        indicator_map = {
            'export': 'export_value',
            'import': 'import_value', 
            'gdp': 'gdp_value'
        }
        
        if indicator not in indicator_map:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        indicator_field = indicator_map[indicator]
        
        result = ForecastService.get_forecast(country_id, indicator_field, steps, model_type, degree, alpha)
        
        print(f"Forecast result: {result.get('success')}, error: {result.get('error')}")
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
    except Exception as e:
        print(f"Error in forecast: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@forecast_bp.route('/api/forecast/models', methods=['GET'])
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