"""Testes unitários de segurança: hash de senha e token JWT."""
from datetime import datetime, timedelta, timezone

import jwt
from flask import Flask

from app.models import Usuario
from app.security import gerar_token


def test_senha_nunca_e_guardada_em_texto_puro():
    u = Usuario(username="cantina")
    u.definir_senha("minha-senha")
    assert "minha-senha" not in u.senha_hash
    assert u.verificar_senha("minha-senha")
    assert not u.verificar_senha("senha-errada")


def _app():
    app = Flask(__name__)
    app.config.update(SECRET_KEY="k" * 32, JWT_EXPIRES_MINUTES=60)
    return app


def test_token_contem_usuario_e_expiracao():
    with _app().app_context():
        dados = jwt.decode(gerar_token("cantina"), "k" * 32, algorithms=["HS256"])
    assert dados["sub"] == "cantina"
    assert dados["exp"] > datetime.now(timezone.utc).timestamp()


def test_token_assinado_com_outra_chave_e_rejeitado():
    falso = jwt.encode({"sub": "cantina", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       "chave-do-invasor", algorithm="HS256")
    try:
        jwt.decode(falso, "k" * 32, algorithms=["HS256"])
        assert False, "token forjado foi aceito"
    except jwt.InvalidSignatureError:
        pass
