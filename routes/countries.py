from flask import Blueprint, jsonify
from services.country_service import CountryService

countries_bp = Blueprint('countries', __name__)


@countries_bp.route('/api/countries', methods=['GET'])
def get_countries():
    countries = CountryService.get_all_countries()
    return jsonify(countries)


@countries_bp.route('/api/countries/<int:country_id>', methods=['DELETE'])
def delete_country(country_id):
    """Удаление страны"""
    try:
        success, message = CountryService.delete_country(country_id)
        if success:
            return jsonify({'message': message})
        return jsonify({'error': message}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500