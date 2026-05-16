from flask import Blueprint, request, jsonify
from services.country_service import CountryService

countries_bp = Blueprint('countries', __name__)


@countries_bp.route('/api/countries', methods=['GET'])
def get_countries():
    """Получение списка стран"""
    countries = CountryService.get_all_countries()
    return jsonify(countries)


@countries_bp.route('/api/countries/<int:country_id>', methods=['GET'])
def get_country(country_id):
    """Получение страны по ID"""
    country = CountryService.get_country_by_id(country_id)
    if country:
        return jsonify(country)
    return jsonify({'error': 'Страна не найдена'}), 404


@countries_bp.route('/api/add_country', methods=['POST'])
def add_country():
    """Добавление новой страны"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Название страны обязательно'}), 400
    
    country, error = CountryService.add_country(name)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify(country), 201


@countries_bp.route('/api/countries/<int:country_id>', methods=['DELETE'])
def delete_country(country_id):
    """Удаление страны"""
    deleted, error = CountryService.delete_country(country_id)
    if error:
        return jsonify({'error': error}), 400
    
    if deleted:
        return jsonify({'message': 'Страна успешно удалена'})
    
    return jsonify({'error': 'Страна не найдена'}), 404