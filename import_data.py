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
FILENAME_DATE_REGEX = r'(\d{2})_(\d{4})\.csv$' # Ex: 01_2024.csv

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
    """Garante que uma categoria exista para o usuário e retorna seu ID."""
    normalized_category_name = category_name.strip().capitalize()
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
        return cursor.lastrowid # Retorna o ID da categoria recém-inserida

def clean_amount(amount_str):
    """Limpa e converte a string de valor monetário para Decimal."""
    if pd.isna(amount_str):
        return Decimal(0)
    
    amount_str = str(amount_str).replace('R$', '').replace('.', '').replace(',', '.').strip()
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

        # 1. Garante que o usuário padrão exista
        admin_user_id = ensure_user_exists(cursor)
        conn.commit()
        print(f"Usuário Admin (ID: {admin_user_id}) garantido no banco.")

        # 2. Processa arquivos CSV
        csv_files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
        if not csv_files:
            print(f"Nenhum arquivo CSV encontrado na pasta: {CSV_FOLDER}")
            return

        for csv_file in csv_files:
            file_path = os.path.join(CSV_FOLDER, csv_file)
            print(f"\nProcessando arquivo: {csv_file}")

            # Extrai mês e ano do nome do arquivo
            match = re.search(FILENAME_DATE_REGEX, csv_file)
            if not match:
                print(f"Ignorando '{csv_file}': Nome do arquivo não corresponde ao padrão de data (ex: '01_2024.csv').")
                continue
            
            month_str, year_str = match.groups()
            
            try:
                # Tenta converter o mês para número (se for nome, usa o mapeamento)
                month = MONTH_NAMES.get(month_str.lower(), int(month_str))
                year = int(year_str)
                # Criar uma data para a transação, assumindo o primeiro dia do mês do arquivo
                transaction_date_for_file = datetime(year, month, 1).date()
            except ValueError:
                print(f"Erro: Não foi possível determinar o mês/ano do arquivo '{csv_file}'. Verifique o nome do arquivo e a regex.")
                continue

            # Carrega o CSV
            # Assumimos que as colunas são: Descrição, Valor, Categoria
            # Adapte 'names' e 'header' se as colunas forem diferentes no seu CSV
            try:
                df = pd.read_csv(file_path, header=None, names=['description', 'amount_str', 'category_name'])
            except Exception as e:
                print(f"Erro ao ler CSV '{csv_file}': {e}")
                continue

            # Remove a linha de cabeçalho (se houver, e se você não usou 'header=None' e 'names')
            # Se você já usou 'header=None' e 'names', esta linha pode não ser necessária ou precisar de ajuste
            # Ex: Se a primeira linha são os cabeçalhos, e você quer pular: df = pd.read_csv(file_path, header=0, names=['description', 'amount_str', 'category_name'])
            # Por simplicidade, assumimos que 'header=None' e que a primeira linha de dados já é a real.
            
            # Itera sobre as linhas do DataFrame para inserir no banco de dados
            for index, row in df.iterrows():
                description = row['description'].strip() if pd.notna(row['description']) else "Sem descrição"
                amount = clean_amount(row['amount_str'])
                category_name = row['category_name'].strip() if pd.notna(row['category_name']) else "Outros"

                # Garante que a categoria exista e obtém seu ID
                category_id = ensure_category_exists(cursor, admin_user_id, category_name)
                
                # Insere a transação
                cursor.execute(
                    "INSERT INTO bills (user_id, category_id, description, amount, transaction_date) VALUES (%s, %s, %s, %s, %s)",
                    (admin_user_id, category_id, description, amount, transaction_date_for_file)
                )
                
            conn.commit() # Salva as mudanças no banco para este CSV
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