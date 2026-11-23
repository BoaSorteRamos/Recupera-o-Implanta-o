"""Testes unitários: regras de negócio isoladas, sem banco e sem HTTP."""
from decimal import Decimal

import pytest

from app.services import (
    RegraNegocioErro,
    calcular_total,
    gerar_codigo,
    pode_transicionar,
    validar_itens,
    validar_produto,
)

PRODUTO_OK = {"nome": "X-Salada", "categoria": "lanche", "preco": "12.5", "estoque": 10}


class TestValidarProduto:
    def test_produto_valido_e_normalizado(self):
        p = validar_produto(PRODUTO_OK)
        assert p["categoria"] == "LANCHE"
        assert p["preco"] == Decimal("12.50")
        assert p["disponivel"] is True

    def test_arredonda_preco_para_centavos(self):
        assert validar_produto({**PRODUTO_OK, "preco": "3.005"})["preco"] == Decimal("3.01")

    @pytest.mark.parametrize("preco", ["0", "-1", "abc", None, "250"])
    def test_rejeita_preco_invalido(self, preco):
        with pytest.raises(RegraNegocioErro):
            validar_produto({**PRODUTO_OK, "preco": preco})

    def test_rejeita_categoria_inexistente(self):
        with pytest.raises(RegraNegocioErro, match="Categoria"):
            validar_produto({**PRODUTO_OK, "categoria": "PIZZA"})

    @pytest.mark.parametrize("nome", ["", "A", "x" * 81])
    def test_rejeita_nome_fora_do_tamanho(self, nome):
        with pytest.raises(RegraNegocioErro):
            validar_produto({**PRODUTO_OK, "nome": nome})

    def test_rejeita_estoque_negativo(self):
        with pytest.raises(RegraNegocioErro, match="Estoque"):
            validar_produto({**PRODUTO_OK, "estoque": -3})


class TestValidarItens:
    def test_agrupa_itens_repetidos(self):
        itens = validar_itens([{"produto_id": 1, "quantidade": 2}, {"produto_id": 1, "quantidade": 1}])
        assert itens == [{"produto_id": 1, "quantidade": 3}]

    @pytest.mark.parametrize("itens", [[], None, "x"])
    def test_pedido_sem_itens(self, itens):
        with pytest.raises(RegraNegocioErro):
            validar_itens(itens)

    @pytest.mark.parametrize("qtd", [0, -1, 6])
    def test_quantidade_fora_do_limite(self, qtd):
        with pytest.raises(RegraNegocioErro):
            validar_itens([{"produto_id": 1, "quantidade": qtd}])

    def test_limite_de_itens_por_pedido(self):
        with pytest.raises(RegraNegocioErro, match="Máximo"):
            validar_itens([{"produto_id": i, "quantidade": 1} for i in range(11)])

    def test_item_sem_campos(self):
        with pytest.raises(RegraNegocioErro):
            validar_itens([{"produto_id": 1}])


class TestCalcularTotal:
    def test_soma_precos_vezes_quantidade(self):
        assert calcular_total([(Decimal("12.00"), 2), (Decimal("5.00"), 1)]) == Decimal("29.00")

    def test_sem_erro_de_ponto_flutuante(self):
        # 0.1 + 0.2 em float daria 0.30000000000000004
        assert calcular_total([("0.10", 1), ("0.20", 1)]) == Decimal("0.30")

    def test_lista_vazia(self):
        assert calcular_total([]) == Decimal("0.00")


class TestStatusPedido:
    @pytest.mark.parametrize("atual,novo", [
        ("RECEBIDO", "EM_PREPARO"), ("EM_PREPARO", "PRONTO"),
        ("PRONTO", "ENTREGUE"), ("RECEBIDO", "CANCELADO"), ("EM_PREPARO", "CANCELADO"),
    ])
    def test_transicoes_permitidas(self, atual, novo):
        assert pode_transicionar(atual, novo)

    @pytest.mark.parametrize("atual,novo", [
        ("RECEBIDO", "ENTREGUE"), ("ENTREGUE", "RECEBIDO"),
        ("PRONTO", "CANCELADO"), ("CANCELADO", "EM_PREPARO"), ("XYZ", "PRONTO"),
    ])
    def test_transicoes_proibidas(self, atual, novo):
        assert not pode_transicionar(atual, novo)


def test_codigo_do_pedido_tem_formato_e_e_unico():
    codigos = {gerar_codigo() for _ in range(500)}
    assert len(codigos) == 500
    assert all(c.startswith("EL-") and len(c) == 9 for c in codigos)
