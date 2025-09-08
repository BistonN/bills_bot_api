from flask import Blueprint, request, jsonify
from db import get_db_connection, close_db_connection
from models import Category
from utils.auth_helpers import token_required
import mysql.connector

categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/categories', methods=['POST'])
@token_required
def create_category(current_user_id):
    data = request.get_json()
    name = data.get('name')
    budget_amount = data.get('budget_amount')

    if not name:
        return jsonify({'message': 'Nome da categoria é obrigatório!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM categories WHERE user_id = %s AND name = %s",
            (current_user_id, name)
        )
        if cursor.fetchone():
            return jsonify({'message': 'Categoria já existe para este usuário.'}), 409

        cursor.execute(
            "INSERT INTO categories (user_id, name, budget_amount) VALUES (%s, %s, %s)",
            (current_user_id, name, budget_amount)
        )
        conn.commit()
        return jsonify({'message': 'Categoria criada com sucesso!', 'id': cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@categories_bp.route('/categories', methods=['GET'])
@token_required
def get_categories(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM categories WHERE user_id = %s", (current_user_id,))
        categories_data = cursor.fetchall()
        
        categories = [Category(**data).to_dict() for data in categories_data]
        return jsonify(categories), 200
    except mysql.connector.Error as err:
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@categories_bp.route('/categories/<int:category_id>', methods=['PUT'])
@token_required
def update_category(current_user_id, category_id):
    data = request.get_json()
    name = data.get('name')
    budget_amount = data.get('budget_amount')

    if not name and budget_amount is None:
        return jsonify({'message': 'Nenhum dado fornecido para atualização.'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM categories WHERE id = %s AND user_id = %s", (category_id, current_user_id))
        if not cursor.fetchone():
            return jsonify({'message': 'Categoria não encontrada ou não pertence a este usuário.'}), 404

        updates = []
        params = []

        if name:
            updates.append("name = %s")
            params.append(name)
        if budget_amount is not None:
            updates.append("budget_amount = %s")
            params.append(budget_amount)
        
        if not updates:
            return jsonify({'message': 'Nenhum campo válido para atualização.'}), 400

        query = f"UPDATE categories SET {', '.join(updates)} WHERE id = %s AND user_id = %s"
        params.extend([category_id, current_user_id])
        
        cursor.execute(query, tuple(params))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'message': 'Categoria não encontrada ou nenhum dado alterado.'}), 404
        
        return jsonify({'message': 'Categoria atualizada com sucesso!'}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@token_required
def delete_category(current_user_id, category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM categories WHERE id = %s AND user_id = %s", (category_id, current_user_id))
        if not cursor.fetchone():
            return jsonify({'message': 'Categoria não encontrada ou não pertence a este usuário.'}), 404
        
        cursor.execute("DELETE FROM categories WHERE id = %s AND user_id = %s", (category_id, current_user_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'message': 'Categoria não encontrada ou já foi deletada.'}), 404
        
        return jsonify({'message': 'Categoria deletada com sucesso!'}), 200
    except mysql.connector.errors.IntegrityError as err:
        conn.rollback()
        if "Cannot delete or update a parent row: a foreign key constraint fails" in str(err):
            return jsonify({'message': 'Não foi possível deletar a categoria. Existem contas associadas a ela. Por favor, remova ou redefina as contas primeiro.'}), 409 # Conflict
        return jsonify({'message': f'Erro de integridade do banco de dados: {err}'}), 500
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)