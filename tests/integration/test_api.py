"""Testes de integração: API HTTP + regras + banco de dados juntos.

No CI/produção rodam contra PostgreSQL (TEST_DATABASE_URL).
"""
import jwt

from app.models import Produto, db


def _produto(app, nome="Coxinha"):
    with app.app_context():
        return db.session.execute(db.select(Produto).filter_by(nome=nome)).scalar_one()


def _pedido(client, itens, nome="Ana Souza", turma="2B"):
    return client.post("/api/pedidos", json={"nome_aluno": nome, "turma": turma, "itens": itens})


# ------------------------------------------------------------ infraestrutura
def test_health_confirma_conexao_com_banco(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["banco"] == "ok"


def test_cabecalhos_de_seguranca(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]


def test_seed_cria_cardapio_inicial(client):
    produtos = client.get("/api/produtos").get_json()
    assert len(produtos) == 7
    assert {p["categoria"] for p in produtos} == {"LANCHE", "BEBIDA", "DOCE", "SAUDAVEL"}


# --------------------------------------------------------------- autenticação
def test_login_com_senha_errada(client):
    r = client.post("/api/auth/login", json={"username": "cantina", "senha": "errada"})
    assert r.status_code == 401


def test_rotas_da_cantina_exigem_token(client):
    assert client.get("/api/pedidos").status_code == 401
    assert client.post("/api/produtos", json={}).status_code == 401
    assert client.patch("/api/pedidos/1/status", json={}).status_code == 401


def test_token_invalido_e_rejeitado(client):
    falso = jwt.encode({"sub": "cantina"}, "outra-chave", algorithm="HS256")
    r = client.get("/api/pedidos", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401


# ---------------------------------------------------------------- cardápio
def test_cantina_cadastra_edita_e_remove_produto(client, auth):
    r = client.post("/api/produtos", headers=auth,
                    json={"nome": "Pão de Queijo", "categoria": "LANCHE", "preco": 4, "estoque": 30})
    assert r.status_code == 201
    pid = r.get_json()["id"]

    r = client.put(f"/api/produtos/{pid}", headers=auth,
                   json={"nome": "Pão de Queijo", "categoria": "LANCHE", "preco": 4.5, "estoque": 30})
    assert r.get_json()["preco"] == 4.5

    assert client.delete(f"/api/produtos/{pid}", headers=auth).status_code == 204
    assert pid not in [p["id"] for p in client.get("/api/produtos").get_json()]


def test_produto_invalido_retorna_400(client, auth):
    r = client.post("/api/produtos", headers=auth, json={"nome": "X", "categoria": "LANCHE", "preco": 1})
    assert r.status_code == 400
    assert "Nome" in r.get_json()["erro"]


# ----------------------------------------------------------------- pedidos
def test_fluxo_completo_do_pedido(app, client, auth):
    coxinha = _produto(app, "Coxinha")
    suco = _produto(app, "Suco de Laranja")

    r = _pedido(client, [{"produto_id": coxinha.id, "quantidade": 2}, {"produto_id": suco.id, "quantidade": 1}])
    assert r.status_code == 201
    pedido = r.get_json()
    assert pedido["total"] == 17.0  # 2 x 6,00 + 5,00
    assert pedido["status"] == "RECEBIDO"
    assert _produto(app, "Coxinha").estoque == coxinha.estoque - 2  # baixa de estoque

    # aluno acompanha pelo código
    assert client.get(f"/api/pedidos/{pedido['codigo']}").get_json()["status"] == "RECEBIDO"

    # cantina vê na fila e avança o status
    fila = client.get("/api/pedidos?status=RECEBIDO", headers=auth).get_json()
    assert pedido["codigo"] in [p["codigo"] for p in fila]
    for status in ["EM_PREPARO", "PRONTO", "ENTREGUE"]:
        r = client.patch(f"/api/pedidos/{pedido['id']}/status", headers=auth, json={"status": status})
        assert r.status_code == 200
    assert client.get(f"/api/pedidos/{pedido['codigo']}").get_json()["status"] == "ENTREGUE"


def test_transicao_invalida_retorna_409(app, client, auth):
    pid = _pedido(client, [{"produto_id": _produto(app).id, "quantidade": 1}]).get_json()["id"]
    r = client.patch(f"/api/pedidos/{pid}/status", headers=auth, json={"status": "ENTREGUE"})
    assert r.status_code == 409


def test_cancelamento_devolve_estoque(app, client, auth):
    antes = _produto(app).estoque
    pid = _pedido(client, [{"produto_id": _produto(app).id, "quantidade": 3}]).get_json()["id"]
    assert _produto(app).estoque == antes - 3
    client.patch(f"/api/pedidos/{pid}/status", headers=auth, json={"status": "CANCELADO"})
    assert _produto(app).estoque == antes


def test_estoque_insuficiente_retorna_409_e_nao_altera_nada(app, client, auth):
    p = _produto(app, "Salada de Frutas")
    client.put(f"/api/produtos/{p.id}", headers=auth,
               json={"nome": p.nome, "categoria": p.categoria, "preco": float(p.preco), "estoque": 1})
    r = _pedido(client, [{"produto_id": p.id, "quantidade": 2}])
    assert r.status_code == 409
    assert _produto(app, "Salada de Frutas").estoque == 1


def test_produto_inexistente_retorna_409(client):
    assert _pedido(client, [{"produto_id": 9999, "quantidade": 1}]).status_code == 409


def test_pedido_sem_nome_retorna_400(app, client):
    r = _pedido(client, [{"produto_id": _produto(app).id, "quantidade": 1}], nome="")
    assert r.status_code == 400


def test_pedido_inexistente_retorna_404(client):
    assert client.get("/api/pedidos/EL-000000").status_code == 404


def test_entrada_maliciosa_e_tratada_como_texto(app, client, auth):
    """Tentativa de SQL injection/XSS é gravada como texto comum, sem efeito."""
    nome = "Robert'); DROP TABLE pedidos;--<script>"
    r = _pedido(client, [{"produto_id": _produto(app).id, "quantidade": 1}], nome=nome)
    assert r.status_code == 201
    assert r.get_json()["nome_aluno"] == nome
    assert client.get("/api/pedidos", headers=auth).status_code == 200  # tabela intacta
