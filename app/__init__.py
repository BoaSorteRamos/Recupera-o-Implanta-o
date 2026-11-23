import logging
from decimal import Decimal

from flask import Flask, jsonify

from .config import APP_VERSION, Config
from .models import Produto, Usuario, db
from .routes import bp
from .security import aplicar_cabecalhos_seguranca, limiter

CARDAPIO_INICIAL = [
    ("X-Salada", "Pão, hambúrguer, queijo, alface e tomate", "LANCHE", "12.00", 30),
    ("Misto Quente", "Pão de forma, presunto e queijo", "LANCHE", "7.50", 40),
    ("Coxinha", "Coxinha de frango assada", "LANCHE", "6.00", 50),
    ("Suco de Laranja", "Natural, 300 ml", "BEBIDA", "5.00", 40),
    ("Água Mineral", "500 ml", "BEBIDA", "3.00", 60),
    ("Salada de Frutas", "Frutas da estação", "SAUDAVEL", "6.50", 20),
    ("Brigadeiro", "Unidade", "DOCE", "2.50", 80),
]


def seed(app):
    """Cria o usuário da cantina e o cardápio inicial (idempotente)."""
    if db.session.execute(db.select(Usuario).filter_by(username=app.config["ADMIN_USER"])).first() is None:
        u = Usuario(username=app.config["ADMIN_USER"])
        u.definir_senha(app.config["ADMIN_PASSWORD"])
        db.session.add(u)
    if db.session.execute(db.select(Produto)).first() is None:
        for nome, desc, cat, preco, est in CARDAPIO_INICIAL:
            db.session.add(Produto(nome=nome, descricao=desc, categoria=cat, preco=Decimal(preco), estoque=est))
    db.session.commit()


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    if app.config["APP_ENV"] == "production" and app.config["SECRET_KEY"].startswith("dev-"):
        raise RuntimeError("SECRET_KEY padrão não é permitida em produção")

    db.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(bp)
    app.after_request(aplicar_cabecalhos_seguranca)

    @app.errorhandler(404)
    def nao_encontrado(_):
        return jsonify(erro="Recurso não encontrado"), 404

    @app.errorhandler(429)
    def muitas_requisicoes(_):
        return jsonify(erro="Muitas requisições, tente novamente em instantes"), 429

    @app.errorhandler(500)
    def erro_interno(_):
        return jsonify(erro="Erro interno"), 500  # não vaza stack trace

    with app.app_context():
        db.create_all()
        if app.config["SEED_DATA"]:
            seed(app)
        app.logger.info("EstuLanches v%s iniciado (ambiente=%s)", APP_VERSION, app.config["APP_ENV"])
        # com gunicorn --preload, cada worker abre suas próprias conexões após o fork
        db.engine.dispose()
    return app
