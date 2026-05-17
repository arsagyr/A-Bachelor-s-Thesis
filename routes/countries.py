from flask import Blueprint, jsonify
from services.country_service import CountryService

countries_bp = Blueprint('countries', __name__)


@countries_bp.route('/api/countries', methods=['GET'])
def get_countries():
    countries = CountryService.get_all_countries()
    return jsonify(countries)