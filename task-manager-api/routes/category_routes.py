from flask import Blueprint, jsonify, request

from controllers.category_controller import CategoryController

category_bp = Blueprint('categories', __name__)


@category_bp.route('/categories', methods=['GET'])
def get_categories():
    return jsonify(CategoryController.list_categories()), 200


@category_bp.route('/categories', methods=['POST'])
def create_category():
    return jsonify(CategoryController.create_category(request.get_json())), 201


@category_bp.route('/categories/<int:cat_id>', methods=['PUT'])
def update_category(cat_id):
    return jsonify(CategoryController.update_category(cat_id, request.get_json())), 200


@category_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    return jsonify(CategoryController.delete_category(cat_id)), 200
