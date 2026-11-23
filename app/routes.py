from flask import Blueprint, current_app, jsonify, render_template, request
from sqlalchemy import text

from .config import APP_VERSION
from .models import Pedido, Produto, Usuario, db
from .security import gerar_token, limiter, login_obrigatorio
from .services import RegraNegocioErro, atualizar_status, criar_pedido, validar_produto

bp = Blueprint("api", __name__)


@bp.errorhandler(RegraNegocioErro)
def erro_negocio(e):
    return jsonify(erro=str(e)), e.status_http


# ------------------------------------------------------------- páginas
@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/health")
@limiter.exempt
def health():
    try:
        db.session.execute(text("SELECT 1"))
        banco = "ok"
    except Exception:
        current_app.logger.exception("Falha no health check do banco")
        return jsonify(status="erro", banco="indisponivel", versao=APP_VERSION), 503
    return jsonify(status="ok", banco=banco, versao=APP_VERSION)


# --------------------------------------------------------------- auth
@bp.post("/api/auth/login")
@limiter.limit("5 per minute")  # dificulta força bruta
def login():
    dados = request.get_json(silent=True) or {}
    usuario = db.session.execute(
        db.select(Usuario).filter_by(username=str(dados.get("username", "")))
    ).scalar_one_or_none()
    if usuario is None or not usuario.verificar_senha(str(dados.get("senha", ""))):
        return jsonify(erro="Usuário ou senha inválidos"), 401
    return jsonify(token=gerar_token(usuario.username))


# ----------------------------------------------------------- produtos
@bp.get("/api/produtos")
def listar_produtos():
    consulta = db.select(Produto).order_by(Produto.categoria, Produto.nome)
    if request.args.get("todos") != "1":
        consulta = consulta.filter(Produto.disponivel.is_(True), Produto.estoque > 0)
    return jsonify([p.to_dict() for p in db.session.execute(consulta).scalars()])


@bp.post("/api/produtos")
@login_obrigatorio
def criar_produto():
    produto = Produto(**validar_produto(request.get_json(silent=True) or {}))
    db.session.add(produto)
    db.session.commit()
    return jsonify(produto.to_dict()), 201


@bp.put("/api/produtos/<int:pid>")
@login_obrigatorio
def editar_produto(pid):
    produto = db.get_or_404(Produto, pid)
    for campo, valor in validar_produto(request.get_json(silent=True) or {}).items():
        setattr(produto, campo, valor)
    db.session.commit()
    return jsonify(produto.to_dict())


@bp.delete("/api/produtos/<int:pid>")
@login_obrigatorio
def remover_produto(pid):
    produto = db.get_or_404(Produto, pid)
    produto.disponivel = False  # exclusão lógica preserva o histórico de pedidos
    db.session.commit()
    return "", 204


# ------------------------------------------------------------ pedidos
@bp.post("/api/pedidos")
@limiter.limit("20 per minute")
def novo_pedido():
    dados = request.get_json(silent=True) or {}
    pedido = criar_pedido(dados.get("nome_aluno"), dados.get("turma"), dados.get("itens"))
    current_app.logger.info("Pedido %s criado (total %s)", pedido.codigo, pedido.total)
    return jsonify(pedido.to_dict()), 201


@bp.get("/api/pedidos/<codigo>")
def consultar_pedido(codigo):
    pedido = db.session.execute(db.select(Pedido).filter_by(codigo=codigo.upper())).scalar_one_or_none()
    if pedido is None:
        return jsonify(erro="Pedido não encontrado"), 404
    return jsonify(pedido.to_dict())


@bp.get("/api/pedidos")
@login_obrigatorio
def listar_pedidos():
    consulta = db.select(Pedido).order_by(Pedido.criado_em.desc()).limit(200)
    if status := request.args.get("status"):
        consulta = consulta.filter_by(status=status.upper())
    return jsonify([p.to_dict() for p in db.session.execute(consulta).scalars()])


@bp.patch("/api/pedidos/<int:pid>/status")
@login_obrigatorio
def mudar_status(pid):
    pedido = db.get_or_404(Pedido, pid)
    novo = (request.get_json(silent=True) or {}).get("status")
    atualizar_status(pedido, novo)
    current_app.logger.info("Pedido %s -> %s", pedido.codigo, pedido.status)
    return jsonify(pedido.to_dict())
