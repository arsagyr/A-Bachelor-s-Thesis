from flask import Blueprint, request, jsonify
from services.regression_service import RegressionService
import traceback

regression_bp = Blueprint('regression', __name__)


@regression_bp.route('/api/regression/gdp-forecast/<int:country_id>', methods=['GET'])
def get_gdp_regression_forecast(country_id):
    """Прогноз ВВП на основе регрессии экспорта и импорта"""
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        model_type = request.args.get('model', 'linear')
        
        if model_type not in ['linear', 'ridge', 'lasso']:
            model_type = 'linear'
        
        alpha = request.args.get('alpha', 1.0, type=float)
        
        result = RegressionService.get_gdp_forecast(country_id, steps, model_type, alpha=alpha)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка прогнозирования')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@regression_bp.route('/api/regression/stats/<int:country_id>', methods=['GET'])
def get_regression_statistics(country_id):
    """Расчёт статистик значимости для регрессионной модели"""
    try:
        model_type = request.args.get('model', 'linear')
        if model_type not in ['linear', 'ridge', 'lasso']:
            model_type = 'linear'
        
        result = RegressionService.get_regression_statistics(country_id, model_type)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка расчёта статистик')}), 400
    except Exception as e:
        print(f"Error in regression stats: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@regression_bp.route('/api/regression/models', methods=['GET'])
def get_regression_models():
    """Получение списка доступных регрессионных моделей"""
    return jsonify({
        'models': {
            'linear': 'Линейная регрессия',
            'ridge': 'Ridge регрессия (L2)',
            'lasso': 'Lasso регрессия (L1)'
        },
        'default': 'linear'
    })