from datetime import datetime, timezone
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def agora():
    return datetime.now(timezone.utc)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)


class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    descricao = db.Column(db.String(255), default="")
    categoria = db.Column(db.String(30), nullable=False)
    preco = db.Column(db.Numeric(8, 2), nullable=False)
    estoque = db.Column(db.Integer, nullable=False, default=0)
    disponivel = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "categoria": self.categoria,
            "preco": float(self.preco),
            "estoque": self.estoque,
            "disponivel": self.disponivel,
        }


class Pedido(db.Model):
    __tablename__ = "pedidos"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(12), unique=True, nullable=False, index=True)
    nome_aluno = db.Column(db.String(80), nullable=False)
    turma = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="RECEBIDO", index=True)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0"))
    criado_em = db.Column(db.DateTime(timezone=True), default=agora)
    itens = db.relationship("ItemPedido", backref="pedido", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nome_aluno": self.nome_aluno,
            "turma": self.turma,
            "status": self.status,
            "total": float(self.total),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "itens": [i.to_dict() for i in self.itens],
        }


class ItemPedido(db.Model):
    __tablename__ = "itens_pedido"
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(8, 2), nullable=False)
    produto = db.relationship("Produto")

    def to_dict(self):
        return {
            "produto_id": self.produto_id,
            "nome": self.produto.nome if self.produto else None,
            "quantidade": self.quantidade,
            "preco_unitario": float(self.preco_unitario),
        }
