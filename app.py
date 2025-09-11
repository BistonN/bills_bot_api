from flask import Flask, jsonify
from flask_bcrypt import Bcrypt
from config import Config
from routes.auth import auth_bp
from routes.categories import categories_bp
from routes.bills import bills_bp

app = Flask(__name__)
app.config.from_object(Config)

bcrypt = Bcrypt(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(categories_bp, url_prefix='/api')
app.register_blueprint(bills_bp, url_prefix='/api')

@app.route('/')
def hello_world():
    return jsonify({"message": "API de Contas Rodando!"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)