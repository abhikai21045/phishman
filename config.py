import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-change-me-123456789'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(BASE_DIR / 'phishsim.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email settings
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USER = 'abhishekgore890@gmail.com'
    SMTP_PASSWORD = 'frin ltld kasr ntql'           # use app password 
    FROM_EMAIL = 'abhishekgore890@gmail.com'
