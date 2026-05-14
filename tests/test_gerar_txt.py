"""Testes da geracao do TXT NeoGrid."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gerar_txt_neogrid import (
    RECORD_SIZE,
    formatar_data,
    formatar_numero,
    formatar_texto,
    gerar_registro_019,
    gerar_registro_024,
    gerar_registro_040,
    gerar_registro_090,
    gerar_txt_neogrid,
    somente_numeros,
)


def test_funcoes_auxiliares_formatam_valores() -> None:
    assert formatar_texto("ABC", 5) == "ABC  "
    assert formatar_numero(12.34, 8, decimais=2) == "00001234"
    assert formatar_data("23/04/2026") == "20260423"
    assert somente_numeros("12.345.678/0001-90") == "12345678000190"


def test_gerar_registros_retorna_tamanho_fixo() -> None:
    cabecalho = {
        "numero_oc": "623986",
        "fornecedor": "SILO MIOTTO DISTRIBUIDORA LTDA",
        "cnpj_fornecedor": "16.897.607/0001-56",
        "data_entrega": "23/04/2026",
        "unidade_entrega": "4009 - AlimentaSesi Sao Lourenco",
        "endereco_entrega": "Rod. SC 473, km 1,5",
        "cidade_entrega": "Sao Lourenco do Oeste",
        "uf_entrega": "SC",
        "condicao_pagamento": "<a vista>",
        "comprador": "Fabricio Pedro",
        "cnpj_faturamento": "03.777.341/0397-04",
    }
    item = {
        "sequencia": 1,
        "codigo_silo": "100",
        "descricao_erp": "Bobina Plastica ERP",
        "quantidade": 1.0,
        "unidade": "UN",
        "valor_unitario": 51.2,
        "valor_total": 51.2,
    }
    itens = [item]

    registro_019 = gerar_registro_019(cabecalho)
    registro_024 = gerar_registro_024(cabecalho)
    registro_040 = gerar_registro_040(item)
    registro_090 = gerar_registro_090(itens)

    assert registro_019.startswith("019")
    assert registro_024.startswith("024")
    assert registro_040.startswith("040")
    assert registro_090.startswith("090")
    assert len(registro_019) == RECORD_SIZE
    assert len(registro_024) == RECORD_SIZE
    assert len(registro_040) == RECORD_SIZE
    assert len(registro_090) == RECORD_SIZE


def test_gerar_txt_neogrid_salva_arquivo_quando_statuses_estao_liberados(
    tmp_path: Path,
) -> None:
    dados_oc = {
        "cabecalho": {
            "fornecedor": "SILO MIOTTO DISTRIBUIDORA LTDA",
            "cnpj_fornecedor": "16.897.607/0001-56",
            "numero_oc": "623986",
            "comprador": "Fabricio Pedro",
            "condicao_pagamento": "<a vista>",
            "cnpj_faturamento": "03.777.341/0397-04",
            "unidade_entrega": "4009 - AlimentaSesi Sao Lourenco",
            "endereco_entrega": "Rod. SC 473, km 1,5",
            "cidade_entrega": "Sao Lourenco do Oeste",
            "uf_entrega": "SC",
            "data_entrega": "23/04/2026",
        },
        "itens": [
            {
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
        ],
        "totais": {
            "total_unidade": 51.2,
            "total_fornecedor": 51.2,
        },
    }
    relatorio = pd.DataFrame(
        [
            {
                "numero_oc": "623986",
                "sequencia": 1,
                "item_pdf": "Bobina Plástica Picotada 39x59 com 500un",
                "item_encontrado_tabela": "Bobina Plástica Picotada 39x59 com 500un",
                "codigo_silo": "100",
                "descricao_erp": "Bobina Plastica ERP",
                "quantidade": 1.0,
                "unidade": "UN",
                "valor_unitario": 51.2,
                "valor_total": 51.2,
                "score": 100,
                "status": "encontrado_exato",
            }
        ]
    )

    caminho = gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    conteudo = caminho.read_text(encoding="utf-8").splitlines()

    assert caminho.exists()
    assert caminho.name == "OC_623986.txt"
    assert len(conteudo) == 4
    assert conteudo[0].startswith("019")
    assert conteudo[1].startswith("024")
    assert conteudo[2].startswith("040")
    assert conteudo[3].startswith("090")
    assert "100" in conteudo[2]


def test_gerar_txt_neogrid_bloqueia_status_revisar(tmp_path: Path) -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "623986", "data_entrega": "23/04/2026"},
        "itens": [],
        "totais": {},
    }
    relatorio = pd.DataFrame(
        [
            {
                "numero_oc": "623986",
                "sequencia": 1,
                "item_pdf": "Produto Incerto",
                "item_encontrado_tabela": "Produto Parecido",
                "codigo_silo": "100",
                "descricao_erp": "Produto ERP",
                "quantidade": 1.0,
                "unidade": "UN",
                "valor_unitario": 10.0,
                "valor_total": 10.0,
                "score": 82,
                "status": "revisar",
            }
        ]
    )

    try:
        gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    except ValueError as exc:
        assert "encontrado_exato" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado bloqueio para status revisar.")
