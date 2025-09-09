import pandas as pd
import mysql.connector
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from config import Config

DB_CONFIG = {
    "host": Config.MYSQL_HOST,
    "user": Config.MYSQL_USER,
    "password": Config.MYSQL_PASSWORD,
    "database": Config.MYSQL_DB
}

CSV_FOLDER = 'csv_files' # Pasta onde seus arquivos CSV estão
FILENAME_DATE_REGEX = r'(\d{2})-(\d{4})\.csv$' # Ex: 01_2024.csv

MONTH_NAMES = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def ensure_user_exists(cursor, user_name="Admin", user_email="admin@example.com", password_hash="hashed_password"):
    """Garante que um usuário padrão exista e retorna seu ID."""
    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    user_id = cursor.fetchone()
    if user_id:
        return user_id[0]
    else:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (user_name, user_email, password_hash)
        )
        return cursor.lastrowid # Retorna o ID do usuário recém-inserido

def ensure_category_exists(cursor, user_id, category_name, budget_amount=None):
    normalized_category_name = category_name.strip().upper()
    cursor.execute(
        "SELECT id FROM categories WHERE user_id = %s AND name = %s",
        (user_id, normalized_category_name)
    )
    category_id = cursor.fetchone()
    if category_id:
        return category_id[0]
    else:
        cursor.execute(
            "INSERT INTO categories (user_id, name, budget_amount) VALUES (%s, %s, %s)",
            (user_id, normalized_category_name, budget_amount)
        )
        return cursor.lastrowid

def clean_amount(amount_str):
    if pd.isna(amount_str):
        return Decimal(0)
    
    amount_str = str(amount_str).replace('R$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()
    try:
        return Decimal(amount_str)
    except InvalidOperation:
        print(f"Aviso: Não foi possível converter o valor '{amount_str}' para Decimal. Usando 0.")
        return Decimal(0)

def import_csv_to_db():
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = 1

        csv_files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
        if not csv_files:
            print(f"Nenhum arquivo CSV encontrado na pasta: {CSV_FOLDER}")
            return

        for csv_file in csv_files:
            file_path = os.path.join(CSV_FOLDER, csv_file)
            print(f"\nProcessando arquivo: {csv_file}")

            match = re.search(r'(\d{2})[-_](\d{4})\.csv$', csv_file)
            if not match:
                print(f"Ignorando '{csv_file}': Nome do arquivo não corresponde ao padrão de data (ex: '07-2025.csv').")
                continue

            month, year = int(match.group(1)), int(match.group(2))
            transaction_date = datetime(year, month, 1).date()

            try:
                df = pd.read_csv(file_path, skiprows=1, header=None, names=['description', 'amount_str', 'category_name'])
            except Exception as e:
                print(f"Erro ao ler CSV '{csv_file}': {e}")
                continue

            for row, _ in df.iterrows():
                description = str(row[0]) if row[0] else "Sem descrição"
                amount = clean_amount(row[1])
                category_id = ensure_category_exists(cursor, 1, row[2]) if row[2] else 1

                cursor.execute(
                    """INSERT INTO bills (user_id, category_id, description, amount, transaction_date)
                    VALUES (%s, %s, %s, %s, %s)""", (user_id, category_id, description, amount, transaction_date)
                )

            conn.commit()
            print(f"Importação de '{csv_file}' concluída. {len(df)} transações inseridas.")

    except mysql.connector.Error as err:
        print(f"Erro no MySQL: {err}")
        if conn:
            conn.rollback() # Desfaz as mudanças em caso de erro
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    # Crie a pasta CSV_FOLDER se ela não existir
    if not os.path.exists(CSV_FOLDER):
        os.makedirs(CSV_FOLDER)
        print(f"Pasta '{CSV_FOLDER}' criada. Coloque seus arquivos CSV aqui.")
    else:
        import_csv_to_db()