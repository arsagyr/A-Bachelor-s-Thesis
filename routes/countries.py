from flask import Blueprint, request, jsonify
from services.country_service import CountryService

countries_bp = Blueprint('countries', __name__)


@countries_bp.route('/api/countries')
def get_countries():
    return jsonify(CountryService.get_all_countries())


@countries_bp.route('/api/add_country', methods=['POST'])
def add_country():
    data = request.json
    country, error = CountryService.add_country(data.get('name'))
    if error:
        return jsonify({'error': error}), 400
    return jsonify(country), 201