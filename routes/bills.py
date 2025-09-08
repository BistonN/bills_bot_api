from flask import Blueprint, request, jsonify
from db import get_db_connection, close_db_connection
from models import Bill
from utils.auth_helpers import token_required
import mysql.connector

bills_bp = Blueprint('bills', __name__)

@bills_bp.route('/bills', methods=['POST'])
@token_required
def create_bill(current_user_id):
    data = request.get_json()
    category_name = data.get('category_name')
    description = data.get('description')
    amount = data.get('amount')
    transaction_date = data.get('transaction_date')

    if not all([category_name, description, amount, transaction_date]):
        return jsonify({'message': 'Todos os campos são obrigatórios!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """ INSERT INTO bills (
                    user_id, 
                    category_id, 
                    description, 
                    amount, 
                    transaction_date) 
                VALUES (%s,
                        (SELECT id FROM categories WHERE name = %s AND user_id = %s) , 
                        %s, 
                        %s,
                        %s);""",
            (current_user_id, category_name, current_user_id, description, amount, transaction_date)
        )
        conn.commit()
        return jsonify({'message': 'Conta criada com sucesso!', 'id': cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@bills_bp.route('/bills', methods=['GET'])
@token_required
def get_bills(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM bills WHERE user_id = %s", (current_user_id,))
        bills_data = cursor.fetchall()
        bills = [Bill(**data).to_dict() for data in bills_data]
        return jsonify(bills), 200
    except mysql.connector.Error as err:
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@bills_bp.route('/bills/<int:bill_id>', methods=['PUT'])
@token_required
def update_bill(current_user_id, bill_id):
    data = request.get_json()
    category_id = data.get('category_id')
    description = data.get('description')
    amount = data.get('amount')
    transaction_date = data.get('transaction_date')

    if not any([category_id, description, amount, transaction_date]):
        return jsonify({'message': 'Nenhum dado fornecido para atualização.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM bills WHERE id = %s AND user_id = %s", (bill_id, current_user_id))
        if not cursor.fetchone():
            return jsonify({'message': 'Conta não encontrada ou não pertence a este usuário.'}), 404

        updates = []
        params = []
        if category_id:
            updates.append("category_id = %s")
            params.append(category_id)
        if description:
            updates.append("description = %s")
            params.append(description)
        if amount is not None:
            updates.append("amount = %s")
            params.append(amount)
        if transaction_date:
            updates.append("transaction_date = %s")
            params.append(transaction_date)
        if not updates:
            return jsonify({'message': 'Nenhum campo válido para atualização.'}), 400
        query = f"UPDATE bills SET {', '.join(updates)} WHERE id = %s AND user_id = %s"
        params.extend([bill_id, current_user_id])
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Conta não encontrada ou nenhum dado alterado.'}), 404
        return jsonify({'message': 'Conta atualizada com sucesso!'}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@bills_bp.route('/bills/<int:bill_id>', methods=['DELETE'])
@token_required
def delete_bill(current_user_id, bill_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM bills WHERE id = %s AND user_id = %s", (bill_id, current_user_id))
        if not cursor.fetchone():
            return jsonify({'message': 'Conta não encontrada ou não pertence a este usuário.'}), 404
        cursor.execute("DELETE FROM bills WHERE id = %s AND user_id = %s", (bill_id, current_user_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Conta não encontrada ou já foi deletada.'}), 404
        return jsonify({'message': 'Conta deletada com sucesso!'}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)
