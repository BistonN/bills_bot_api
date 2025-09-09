from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from db import get_db_connection, close_db_connection
from utils.auth_helpers import create_jwt_token
import mysql.connector

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({'message': 'Nome, email e senha são obrigatórios!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s",(email,))
        if cursor.fetchone():
            return jsonify({'message': 'Email já cadastrado.'}), 409

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        conn.commit()
        return jsonify({'message': 'Usuário registrado com sucesso!'}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)

@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({'message': 'Email e senha são obrigatórios!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or not bcrypt.check_password_hash(user['password_hash'], password):
            return jsonify({'message': 'Email ou senha inválidos.'}), 401

        token = create_jwt_token(user['id'])
        return jsonify({'message': 'Login bem-sucedido!', 'token': token}), 200
    except mysql.connector.Error as err:
        return jsonify({'message': f'Erro no banco de dados: {err}'}), 500
    finally:
        close_db_connection(conn)