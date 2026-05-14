"""Testes do relatorio de conversao antes da geracao do TXT final."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from produtos_depara import (
    CODE_COLUMN,
    DESCRIPTION_COLUMN,
    ITEM_COLUMN,
    NORMALIZED_ITEM_COLUMN,
)
from relatorio_processamento import (
    gerar_relatorio_conversao,
    pode_gerar_txt,
    salvar_relatorio_conversao,
    status_geracao_txt,
)


def test_gerar_relatorio_conversao_retorna_dataframe_com_colunas_esperadas() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "623986"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "623986",
                "item_pdf": "Bobina Plástica Picotada 39x59 com 500un",
                "qtde": 1.0,
                "unidade": "UN",
                "valor_unitario": 51.2,
                "valor_total": 51.2,
            },
            {
                "sequencia": 2,
                "numero_oc": "623986",
                "item_pdf": "Produto Sem Match",
                "qtde": 3.0,
                "unidade": "UN",
                "valor_unitario": 10.0,
                "valor_total": 30.0,
            },
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Bobina Plástica Picotada 39x59 com 500un",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Bobina Plastica ERP",
                NORMALIZED_ITEM_COLUMN: "Bobina Plástica Picotada 39x59 com 500un",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert list(df.columns) == [
        "numero_oc",
        "sequencia",
        "item_pdf",
        "item_encontrado_tabela",
        "codigo_silo",
        "descricao_erp",
        "quantidade",
        "unidade",
        "valor_unitario",
        "valor_total",
        "score",
        "status",
    ]
    assert len(df) == 2
    assert df.loc[0, "numero_oc"] == "623986"
    assert df.loc[0, "codigo_silo"] == "100"
    assert df.loc[0, "status"] == "encontrado_exato"
    assert df.loc[1, "status"] == "nao_encontrado"
    assert df.attrs["pode_gerar_txt"] is False
    assert df.attrs["status_geracao_txt"] == "bloqueado_nao_encontrado"


def test_pode_gerar_txt_so_libera_status_validos() -> None:
    df_liberado = pd.DataFrame(
        [
            {"status": "encontrado_exato"},
            {"status": "encontrado_aproximado"},
        ]
    )
    df_revisar = pd.DataFrame([{"status": "revisar"}])
    df_nao_encontrado = pd.DataFrame([{"status": "nao_encontrado"}])

    assert pode_gerar_txt(df_liberado) is True
    assert status_geracao_txt(df_liberado) == "liberado"
    assert pode_gerar_txt(df_revisar) is False
    assert status_geracao_txt(df_revisar) == "bloqueado_revisao_manual"
    assert pode_gerar_txt(df_nao_encontrado) is False
    assert status_geracao_txt(df_nao_encontrado) == "bloqueado_nao_encontrado"


def test_salvar_relatorio_conversao_grava_excel(tmp_path: Path) -> None:
    df = pd.DataFrame(
        [
            {
                "numero_oc": "623986",
                "sequencia": 1,
                "item_pdf": "Item A",
                "item_encontrado_tabela": "Item A",
                "codigo_silo": "100",
                "descricao_erp": "Item ERP",
                "quantidade": 1.0,
                "unidade": "UN",
                "valor_unitario": 5.0,
                "valor_total": 5.0,
                "score": 100,
                "status": "encontrado_exato",
            }
        ]
    )

    caminho = salvar_relatorio_conversao(df, str(tmp_path), "623986")

    assert caminho.exists()
    assert caminho.name == "relatorio_conversao_OC_623986.xlsx"
