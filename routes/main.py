from flask import Blueprint, render_template, jsonify
from database import Database

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})