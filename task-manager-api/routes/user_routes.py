from flask import Blueprint, jsonify, request

from controllers.user_controller import UserController
from middlewares.auth import current_user

user_bp = Blueprint('users', __name__)


@user_bp.route('/users', methods=['GET'])
def get_users():
    return jsonify(UserController.list_users()), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify(UserController.get_user(user_id)), 200


@user_bp.route('/users', methods=['POST'])
def create_user():
    return jsonify(UserController.create_user(request.get_json(), current_user())), 201


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    return jsonify(UserController.update_user(user_id, request.get_json(), current_user())), 200


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    return jsonify(UserController.delete_user(user_id, current_user())), 200


@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    return jsonify(UserController.list_user_tasks(user_id)), 200


@user_bp.route('/login', methods=['POST'])
def login():
    return jsonify(UserController.login(request.get_json())), 200
