import os
from datetime import timedelta

class Config:
    """Konfiguracja aplikacji Flask"""
    
    # Klucz sekretny aplikacji (zmień w produkcji!)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-zmien-w-produkcji-123'
    
    # Baza danych SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Ustaw na True żeby widzieć SQL queries w konsoli
    
    # Email (opcjonalne - dla wysyłania prawdziwych emaili)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@requestsystem.local'
    
    # Ustawienia sesji
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Ustawienia aplikacji
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16MB upload
    
    # Języki i lokalizacja
    LANGUAGES = ['pl', 'en']
    BABEL_DEFAULT_LOCALE = 'pl'
    BABEL_DEFAULT_TIMEZONE = 'Europe/Warsaw'


class DevelopmentConfig(Config):
    """Konfiguracja dla środowiska deweloperskiego"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Pokazuj SQL queries


class ProductionConfig(Config):
    """Konfiguracja dla środowiska produkcyjnego"""
    DEBUG = False
    TESTING = False
    
    # W produkcji SECRET_KEY jest dziedziczony z Config
    # Tam już jest zabezpieczenie przez os.environ.get


class TestingConfig(Config):
    """Konfiguracja dla testów"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Wybór konfiguracji na podstawie zmiennej środowiskowej
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}