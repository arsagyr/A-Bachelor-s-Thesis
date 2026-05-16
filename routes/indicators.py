from flask import Blueprint, request, jsonify
from services.indicator_service import IndicatorService

indicators_bp = Blueprint('indicators', __name__)


@indicators_bp.route('/api/indicators/<int:country_id>', methods=['GET'])
def get_indicators(country_id):
    """Получение показателей для страны"""
    indicators = IndicatorService.get_indicators_by_country(country_id)
    return jsonify(indicators)


@indicators_bp.route('/api/indicators/filter', methods=['GET'])
def filter_indicators():
    """Фильтрация показателей"""
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


@indicators_bp.route('/api/stats/<int:country_id>', methods=['GET'])
def get_stats(country_id):
    """Получение статистики по стране"""
    stats = IndicatorService.get_country_stats(country_id)
    if stats:
        return jsonify(stats)
    return jsonify({'error': 'Статистика не найдена'}), 404


@indicators_bp.route('/api/indicators/years', methods=['GET'])
def get_available_years():
    """Получение доступных годов"""
    years = IndicatorService.get_available_years()
    return jsonify(years)


@indicators_bp.route('/api/add_indicator', methods=['POST'])
def add_indicator():
    """Добавление показателя"""
    data = request.json
    country_id = data.get('country_id')
    year = data.get('year')
    export_value = data.get('export_value')
    import_value = data.get('import_value')
    gdp_value = data.get('gdp_value')
    
    if not all([country_id, year]):
        return jsonify({'error': 'Страна и год обязательны'}), 400
    
    success, message = IndicatorService.add_or_update_indicator(
        country_id=country_id,
        year=year,
        export_value=export_value,
        import_value=import_value,
        gdp_value=gdp_value
    )
    
    if success:
        return jsonify({'message': message})
    
    return jsonify({'error': message}), 400


@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
def delete_indicator(indicator_id):
    """Удаление показателя"""
    success, message = IndicatorService.delete_indicator(indicator_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 404