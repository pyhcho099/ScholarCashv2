import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///scholarcash_v2.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # For development
    DEBUG = True