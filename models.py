from datetime import datetime
from decimal import Decimal

class User:
    def __init__(self, id, name, email, password_hash, created_at):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Category:
    def __init__(self, id, user_id, name, budget_amount, created_at):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.budget_amount = budget_amount
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'budget_amount': float(self.budget_amount) if self.budget_amount is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Bill:
    def __init__(self, id, user_id, category_id, description, amount, transaction_date, created_at):
        self.id = id
        self.user_id = user_id
        self.category_id = category_id
        self.description = description
        self.amount = amount
        self.transaction_date = transaction_date
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'description': self.description,
            'amount': float(self.amount),
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }