"""Regras de negócio do EstuLanches.

As funções "puras" (validação, cálculo, transição de status) não dependem
de banco e são cobertas pelos testes unitários. As funções que acessam o
banco são cobertas pelos testes de integração.
"""
import secrets
from decimal import Decimal, ROUND_HALF_UP

from .models import ItemPedido, Pedido, Produto, db

CATEGORIAS = {"LANCHE", "BEBIDA", "DOCE", "SAUDAVEL"}
MAX_ITENS_POR_PEDIDO = 10
MAX_QTD_POR_ITEM = 5

# Máquina de estados do pedido
TRANSICOES = {
    "RECEBIDO": {"EM_PREPARO", "CANCELADO"},
    "EM_PREPARO": {"PRONTO", "CANCELADO"},
    "PRONTO": {"ENTREGUE"},
    "ENTREGUE": set(),
    "CANCELADO": set(),
}


class RegraNegocioErro(ValueError):
    """Erro de validação de regra de negócio (vira HTTP 400/409)."""

    def __init__(self, mensagem, status_http=400):
        super().__init__(mensagem)
        self.status_http = status_http


# ---------------------------------------------------------------- puras
def validar_produto(dados: dict) -> dict:
    nome = str(dados.get("nome", "")).strip()
    if not 2 <= len(nome) <= 80:
        raise RegraNegocioErro("Nome do produto deve ter entre 2 e 80 caracteres")
    categoria = str(dados.get("categoria", "")).upper()
    if categoria not in CATEGORIAS:
        raise RegraNegocioErro(f"Categoria inválida. Use: {', '.join(sorted(CATEGORIAS))}")
    try:
        preco = Decimal(str(dados.get("preco"))).quantize(Decimal("0.01"), ROUND_HALF_UP)
    except Exception:
        raise RegraNegocioErro("Preço inválido")
    if preco <= 0 or preco > Decimal("200"):
        raise RegraNegocioErro("Preço deve ser maior que 0 e no máximo R$ 200,00")
    try:
        estoque = int(dados.get("estoque", 0))
    except (TypeError, ValueError):
        raise RegraNegocioErro("Estoque inválido")
    if estoque < 0:
        raise RegraNegocioErro("Estoque não pode ser negativo")
    return {
        "nome": nome,
        "descricao": str(dados.get("descricao", "")).strip()[:255],
        "categoria": categoria,
        "preco": preco,
        "estoque": estoque,
        "disponivel": bool(dados.get("disponivel", True)),
    }


def validar_itens(itens) -> list:
    if not isinstance(itens, list) or not itens:
        raise RegraNegocioErro("O pedido precisa de pelo menos um item")
    if len(itens) > MAX_ITENS_POR_PEDIDO:
        raise RegraNegocioErro(f"Máximo de {MAX_ITENS_POR_PEDIDO} itens por pedido")
    normalizados = {}
    for item in itens:
        try:
            pid = int(item["produto_id"])
            qtd = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            raise RegraNegocioErro("Item inválido: informe produto_id e quantidade")
        if not 1 <= qtd <= MAX_QTD_POR_ITEM:
            raise RegraNegocioErro(f"Quantidade por item deve ser de 1 a {MAX_QTD_POR_ITEM}")
        normalizados[pid] = normalizados.get(pid, 0) + qtd
    return [{"produto_id": p, "quantidade": q} for p, q in normalizados.items()]


def calcular_total(linhas) -> Decimal:
    """linhas: iterável de (preco_unitario, quantidade)."""
    total = sum((Decimal(str(p)) * q for p, q in linhas), Decimal("0"))
    return total.quantize(Decimal("0.01"), ROUND_HALF_UP)


def pode_transicionar(atual: str, novo: str) -> bool:
    return novo in TRANSICOES.get(atual, set())


def gerar_codigo() -> str:
    return "EL-" + secrets.token_hex(3).upper()


# ---------------------------------------------------------- com banco
def criar_pedido(nome_aluno: str, turma: str, itens) -> Pedido:
    nome_aluno = (nome_aluno or "").strip()
    turma = (turma or "").strip()
    if not 2 <= len(nome_aluno) <= 80:
        raise RegraNegocioErro("Informe o nome do aluno (2 a 80 caracteres)")
    if not 1 <= len(turma) <= 20:
        raise RegraNegocioErro("Informe a turma")
    itens = validar_itens(itens)

    pedido = Pedido(codigo=gerar_codigo(), nome_aluno=nome_aluno, turma=turma)
    linhas = []
    for item in itens:
        # with_for_update evita vender o mesmo estoque duas vezes em pedidos simultâneos
        produto = db.session.execute(
            db.select(Produto).filter_by(id=item["produto_id"]).with_for_update()
        ).scalar_one_or_none()
        if produto is None or not produto.disponivel:
            db.session.rollback()
            raise RegraNegocioErro(f"Produto {item['produto_id']} indisponível", 409)
        if produto.estoque < item["quantidade"]:
            db.session.rollback()
            raise RegraNegocioErro(f"Estoque insuficiente para {produto.nome}", 409)
        produto.estoque -= item["quantidade"]
        pedido.itens.append(
            ItemPedido(produto=produto, quantidade=item["quantidade"], preco_unitario=produto.preco)
        )
        linhas.append((produto.preco, item["quantidade"]))

    pedido.total = calcular_total(linhas)
    db.session.add(pedido)
    db.session.commit()
    return pedido


def atualizar_status(pedido: Pedido, novo_status: str) -> Pedido:
    novo_status = (novo_status or "").upper()
    if novo_status not in TRANSICOES:
        raise RegraNegocioErro("Status inválido")
    if not pode_transicionar(pedido.status, novo_status):
        raise RegraNegocioErro(f"Não é possível mudar de {pedido.status} para {novo_status}", 409)
    if novo_status == "CANCELADO":  # devolve o estoque
        for item in pedido.itens:
            item.produto.estoque += item.quantidade
    pedido.status = novo_status
    db.session.commit()
    return pedido
