from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# --- 1. ORGANIZATIONAL STRUCTURE ---
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    hod_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    classes = db.relationship('ClassRoom', backref='branch', lazy=True)

class ClassRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    
    # The Tutor Link
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tutor = db.relationship('User', foreign_keys=[tutor_id], backref='tutor_of_class')

# --- 2. USERS & ROLES ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    # NEW: Link Teacher/HOD to a Branch
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    branch = db.relationship('Branch', foreign_keys=[branch_id], backref='staff_members')

    # Link Student to a Class
    class_id = db.Column(db.Integer, db.ForeignKey('class_room.id'), nullable=True)
    assigned_class = db.relationship('ClassRoom', foreign_keys=[class_id], backref=db.backref('students', lazy=True))
    
    balance = db.Column(db.Integer, default=0) 
    qr_code_secret = db.Column(db.String(100))

# --- 3. THE ECONOMY (Unchanged) ---
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_tx')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_tx')

class StoreItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    cost = db.Column(db.Integer)
    stock = db.Column(db.Integer)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('store_item.id'))
    unique_code = db.Column(db.String(20), unique=True)
    status = db.Column(db.String(20), default='PENDING')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item = db.relationship('StoreItem')
    student = db.relationship('User')
