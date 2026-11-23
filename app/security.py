"""Autenticação JWT, limitação de requisições e cabeçalhos de segurança."""
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["300 per minute"])


def gerar_token(username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"])
    return jwt.encode({"sub": username, "exp": exp}, current_app.config["SECRET_KEY"], algorithm="HS256")


def login_obrigatorio(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cabecalho = request.headers.get("Authorization", "")
        if not cabecalho.startswith("Bearer "):
            return jsonify(erro="Autenticação necessária"), 401
        try:
            dados = jwt.decode(cabecalho[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify(erro="Sessão expirada"), 401
        except jwt.InvalidTokenError:
            return jsonify(erro="Token inválido"), 401
        g.usuario = dados["sub"]
        return func(*args, **kwargs)

    return wrapper


def aplicar_cabecalhos_seguranca(resposta):
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    )
    return resposta
