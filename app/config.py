"""Configuração da aplicação lida de variáveis de ambiente (12-factor).

Nenhum segredo fica no código: em produção os valores vêm do arquivo .env
carregado pelo docker-compose.
"""
import os

APP_VERSION = "1.0.0"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-inseguro-troque-em-producao")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///estulanches.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))
    ADMIN_USER = os.getenv("ADMIN_USER", "cantina")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "cantina123")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    SEED_DATA = os.getenv("SEED_DATA", "true").lower() == "true"
    APP_ENV = os.getenv("APP_ENV", "development")
