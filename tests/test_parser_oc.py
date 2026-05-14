"""Testes do parser de texto para estrutura de ordem de compra."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parser_oc import parse_ordem_compra, parse_purchase_order_text


def test_parse_ordem_compra_retorna_estrutura_completa() -> None:
    texto = """
    Fornecedor: SILO MIOTTO DISTRIBUIDORA LTDA Nº OC
    Vendedor: Renan - Silo Miotto Email: comercial@silomiotto.com.br 623986
    CNPJ: 16.897.607/0001-56
    Telefone: (41) 3376-6606 Comprador: Fabricio Pedro
    Cond. Pag. : <a vista>
    ENDEREÇO DE ENTREGA:
    Unidade: 4009 - AlimentaSesi Sao Lourenco Cep: 89.990-000
    Endereço Ent: Rod. SC 473, km 1,5 Nro.:685 Hora: 7:30 às 10:30h
    Cidade: São Lourenço do Oeste UF: SC
    ENDEREÇO DE FATURAMENTO:
    Faturamento: 4009 - SERVIÇO SOCIAL DA INDUSTRIA CNPJ: 03.777.341/0397-04
    Dt. Entrega Seq. OC .Nro. Produto Marca Emb. Qtde.Emb. Qtde.Un.Med. Un.Med. Vlr. Unitario Vlr. Total
    Bobina Plástica
    Picotada 39x59 com
    23/04/2026 1 623986 500un Unidade 1,00 1,00UN 51,20 51,20
    23/04/2026 2 623986 Docinho Geléia Unidade 150,00 150,00UN 0,37 55,50
    Total Unidade: 106,70
    OBS:
    Total Fornecedor: 106,70
    """

    ordem = parse_ordem_compra(texto)

    assert ordem["cabecalho"] == {
        "fornecedor": "SILO MIOTTO DISTRIBUIDORA LTDA",
        "cnpj_fornecedor": "16.897.607/0001-56",
        "numero_oc": "623986",
        "comprador": "Fabricio Pedro",
        "condicao_pagamento": "<a vista>",
        "cnpj_faturamento": "03.777.341/0397-04",
        "unidade_entrega": "4009 - AlimentaSesi Sao Lourenco",
        "endereco_entrega": "Rod. SC 473, km 1,5 Nro.:685 Hora: 7:30 às 10:30h",
        "cidade_entrega": "São Lourenço do Oeste",
        "uf_entrega": "SC",
    }
    assert len(ordem["itens"]) == 2
    assert ordem["itens"][0] == {
        "data_entrega": "23/04/2026",
        "sequencia": 1,
        "numero_oc": "623986",
        "item_pdf": "Bobina Plástica Picotada 39x59 com 500un",
        "marca": "",
        "embalagem": "Unidade",
        "qtde_emb": 1.0,
        "qtde": 1.0,
        "unidade": "UN",
        "valor_unitario": 51.2,
        "valor_total": 51.2,
    }
    assert ordem["itens"][1]["item_pdf"] == "Docinho Geléia"
    assert ordem["itens"][1]["qtde"] == 150.0
    assert ordem["totais"] == {
        "total_unidade": 106.7,
        "total_fornecedor": 106.7,
    }


def test_parse_purchase_order_text_mantem_compatibilidade_com_dataclass() -> None:
    texto = """
    PEDIDO: OC-12345
    FORNECEDOR: Silo Miotto
    CNPJ: 12.345.678/0001-90
    DATA_ENTREGA: 2026-05-20
    ITEM|789|Milho em graos|10|SC|25.50
    ITEM|456|Farelo de soja|5|SC|99.90
    """

    ordem = parse_purchase_order_text(texto)

    assert ordem.pedido == "OC-12345"
    assert ordem.fornecedor == "Silo Miotto"
    assert ordem.cnpj == "12.345.678/0001-90"
    assert ordem.data_entrega == "2026-05-20"
    assert len(ordem.itens) == 2
    assert ordem.itens[0].codigo == "789"
    assert ordem.itens[0].quantidade == Decimal("10")
