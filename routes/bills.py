from flask import Blueprint, request, jsonify
import os
import tempfile
import asyncio
from audio_process.nlp import ProcessadorFrase
from db import get_db_connection, close_db_connection
from models import Bill
from utils.auth_helpers import token_required
import mysql.connector
from audio_process.speach_to_text import TranscritorGoogle

bills_bp = Blueprint('bills', __name__)

@bills_bp.route('/bills/audio', methods=['POST'])
@token_required
def create_bill_from_audio(current_user_id):
    if 'audio' not in request.files:
        return jsonify({'message': 'Arquivo de áudio não enviado!'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'message': 'Nome do arquivo de áudio inválido!'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, audio_file.filename)
        audio_file.save(audio_path)
        transcricao_path = os.path.join(tmpdir, 'transcricao.json')

        transcritor = TranscritorGoogle()
        transcritor.transcrever(audio_path, transcricao_path)

        pf = ProcessadorFrase()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        nlp_result = loop.run_until_complete(pf.processar_de_json(transcricao_path))

    category = nlp_result.get('categoria')
    description = nlp_result.get('local')
    amount = nlp_result.get('valor')
    transaction_date = nlp_result.get('data')
    if not all([category, description, amount, transaction_date]):
        return jsonify({'message': 'Não foi possível extrair todos os dados do áudio.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
                INSERT INTO bills (
                    user_id, 
                    category_id, 
                    description, 
                    amount, 
                    transaction_date
                ) VALUES (
                    %s,
                    (
                        SELECT id 
                          FROM categories 
                         WHERE name    = %s 
                           AND user_id = %s
                    ), 
                    %s, 
                    %s,
                    %s
                );""",
            (current_user_id, category, current_user_id, description, amount, transaction_date)
        )
        new_bill_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute("SELECT * FROM bills WHERE id = %s", (new_bill_id,))
        new_bill_data = {
            "id": new_bill_id, 
            "user_id": current_user_id,\
            "category_id": cursor.fetchone()[2],
            "description": description,
            "amount": amount,
            "transaction_date": transaction_date
        }
        
        if not new_bill_data:
            return jsonify({'message': 'Erro ao recuperar a conta recém-criada.'}), 500

        return jsonify(new_bill_data), 201
    
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        if conn and conn.is_connected():
            close_db_connection(conn)

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
        new_bill_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute("SELECT * FROM bills WHERE id = %s", (new_bill_id,))
        new_bill_data = {
            "id": new_bill_id, 
            "category_id": cursor.fetchone()[2],
            "description": description,
            "amount": amount,
            "transaction_date": transaction_date
        }
        
        if not new_bill_data:
            return jsonify({'message': 'Erro ao recuperar a conta recém-criada.'}), 500

        return jsonify(new_bill_data), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@bills_bp.route('/bills', methods=['GET'])
@token_required
def get_bills(current_user_id):
    start_date = request.args.get('start_date')
    final_date = request.args.get('final_date')
    query = "SELECT * FROM bills WHERE user_id = %s"
    params = [current_user_id]
    if start_date and final_date:
        query += " AND transaction_date BETWEEN %s AND %s"
        params.extend([start_date, final_date])
    elif start_date:
        query += " AND transaction_date >= %s"
        params.append(start_date)
    elif final_date:
        query += " AND transaction_date <= %s"
        params.append(final_date)
    query += " ORDER BY transaction_date DESC"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, tuple(params))
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
