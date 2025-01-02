from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_transaction_user'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

class InitialBalance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_initial_balance_user'), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    
    user = db.relationship('User', backref=db.backref('initial_balance', lazy=True))

class UserPreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    modules = db.Column(db.JSON, default=list)
    email_notifications = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref=db.backref('preferences', lazy=True))