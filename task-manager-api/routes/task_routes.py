from flask import Blueprint, jsonify, request

from controllers.task_controller import TaskController

task_bp = Blueprint('tasks', __name__)


@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(TaskController.list_tasks()), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    return jsonify(TaskController.get_task(task_id)), 200


@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400
    return jsonify(TaskController.create_task(data)), 201


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    return jsonify(TaskController.update_task(task_id, request.get_json())), 200


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    return jsonify(TaskController.delete_task(task_id)), 200


@task_bp.route('/tasks/search', methods=['GET'])
def search_tasks():
    results = TaskController.search_tasks(
        text=request.args.get('q', ''),
        status=request.args.get('status', ''),
        priority=request.args.get('priority', ''),
        user_id=request.args.get('user_id', ''),
    )
    return jsonify(results), 200


@task_bp.route('/tasks/stats', methods=['GET'])
def task_stats():
    return jsonify(TaskController.stats()), 200
