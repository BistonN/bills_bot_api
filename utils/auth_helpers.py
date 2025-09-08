import jwt
from flask import request, jsonify
from functools import wraps
from config import Config
import datetime

def create_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=365),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def decode_jwt_token(token):
    try:
        return jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expirado.'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido.'}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Token de autenticação está faltando!'}), 401

        try:
            data = decode_jwt_token(token)
            if 'error' in data:
                return jsonify({'message': data['error']}), 401
            current_user_id = data['user_id']
        except Exception as e:
            return jsonify({'message': f'Token inválido: {str(e)}'}), 401

        return f(current_user_id, *args, **kwargs)
    return decorated