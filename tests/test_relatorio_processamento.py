"""Testes do relatorio de conversao antes da geracao do TXT final."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from produtos_depara import (
    CODE_COLUMN,
    CONVERSION_COLUMN,
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
                CONVERSION_COLUMN: "",
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
        "quantidade_original",
        "quantidade",
        "unidade",
        "valor_unitario",
        "valor_total",
        "regra_conversao",
        "criterio_conversao",
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


def test_gerar_relatorio_conversao_aplica_regra_de_conversao() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "623986"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "623986",
                "item_pdf": "Docinho Maria Mole",
                "qtde": 2249.0,
                "unidade": "UN",
                "valor_unitario": 0.74,
                "valor_total": 1664.26,
            }
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Docinho Maria Mole",
                CODE_COLUMN: "4715",
                DESCRIPTION_COLUMN: "DOCINHO MARIA MOLE CX C/50",
                NORMALIZED_ITEM_COLUMN: "docinho maria mole",
                CONVERSION_COLUMN: "50",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert df.loc[0, "quantidade_original"] == 2249.0
    assert df.loc[0, "quantidade"] == 45.0
    assert df.loc[0, "valor_unitario"] == 37.0
    assert df.loc[0, "valor_total"] == 1665.0
    assert df.loc[0, "regra_conversao"] == "50"
    assert df.loc[0, "criterio_conversao"] == "divisao_por_embalagem"


def test_gerar_relatorio_conversao_arredonda_guardanapo_para_proximo_fardo() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "624001"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "624001",
                "item_pdf": "Guardanapo 20x20 a 24x24 com 100un",
                "qtde": 90.0,
                "unidade": "UN",
                "valor_unitario": 0.1,
                "valor_total": 9.0,
            }
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Guardanapo 20x20 a 24x24 com 100un",
                CODE_COLUMN: "900",
                DESCRIPTION_COLUMN: "GUARDANAPO C/100 UN (FD 72)",
                NORMALIZED_ITEM_COLUMN: "guardanapo 20x20 a 24x24 com 100un",
                CONVERSION_COLUMN: "ARREDONDAR MULTIPLO DE 72",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert df.loc[0, "quantidade_original"] == 90.0
    assert df.loc[0, "quantidade"] == 144.0
    assert df.loc[0, "criterio_conversao"] == "arredondamento_para_multiplo"


def test_gerar_relatorio_conversao_arredonda_fibraco_para_multiplo_de_10() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "624010"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "624010",
                "item_pdf": "Fibraço Verde Grosso",
                "qtde": 13.0,
                "unidade": "UN",
                "valor_unitario": 2.5,
                "valor_total": 32.5,
            }
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Fibraço Verde Grosso",
                CODE_COLUMN: "2187",
                DESCRIPTION_COLUMN: "FIBRA LIMPEZA PESADA VERDE REF 9506 86,7MMX102MM (FARDO C/10)- BETTANIN",
                NORMALIZED_ITEM_COLUMN: "fibraco verde grosso",
                CONVERSION_COLUMN: "10",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert df.loc[0, "quantidade"] == 20.0
    assert df.loc[0, "valor_unitario"] == 2.5
    assert df.loc[0, "valor_total"] == 50.0
    assert df.loc[0, "criterio_conversao"] == "arredondamento_para_multiplo"


def test_gerar_relatorio_conversao_converte_farinha_rosca_de_kg_para_pacote() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "624050"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "624050",
                "item_pdf": "Farinha de Rosca",
                "qtde": 12.0,
                "unidade": "KG",
                "valor_unitario": 8.0,
                "valor_total": 96.0,
            }
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Farinha de Rosca",
                CODE_COLUMN: "4934",
                DESCRIPTION_COLUMN: "FARINHA DE ROSCA 5KG - CHARLOTTE",
                NORMALIZED_ITEM_COLUMN: "farinha de rosca",
                CONVERSION_COLUMN: "NA COTAÇÃO TEM UNIDADE DE MEDIDA KILO, CONVERTE POR 5 E DIRETO 5 KILOS",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert df.loc[0, "quantidade"] == 3.0
    assert df.loc[0, "valor_unitario"] == 40.0
    assert df.loc[0, "valor_total"] == 120.0
    assert df.loc[0, "criterio_conversao"] == "farinha_rosca_kg_para_pacote_5kg"


def test_gerar_relatorio_conversao_converte_moranguete_para_caixa() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "624060"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "624060",
                "item_pdf": "Docinho Chocolate Moranguete",
                "qtde": 130.0,
                "unidade": "UN",
                "valor_unitario": 0.25,
                "valor_total": 32.5,
            }
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Docinho Chocolate Moranguete",
                CODE_COLUMN: "4783",
                DESCRIPTION_COLUMN: "DOCINHO CHOCOLATE MORANGUETE 13 GR CX C/160 - BEL CHOCOLATES",
                NORMALIZED_ITEM_COLUMN: "docinho chocolate moranguete",
                CONVERSION_COLUMN: "160",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert df.loc[0, "quantidade"] == 1.0
    assert df.loc[0, "valor_unitario"] == 40.0
    assert df.loc[0, "valor_total"] == 40.0
    assert df.loc[0, "criterio_conversao"] == "divisao_por_embalagem"


def test_gerar_relatorio_conversao_converte_docinho_embalado_para_caixa_de_150() -> None:
    dados_oc = {
        "cabecalho": {"numero_oc": "624061"},
        "itens": [
            {
                "sequencia": 1,
                "numero_oc": "624061",
                "item_pdf": "Docinho Goiabada Embalado",
                "qtde": 151.0,
                "unidade": "UN",
                "valor_unitario": 0.37,
                "valor_total": 55.87,
            }
        ],
        "totais": {},
    }
    df_depara = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Docinho Goiabada Embalado",
                CODE_COLUMN: "4230",
                DESCRIPTION_COLUMN: "DOCINHO DE GOIABADA EMBALADO CX C/150 3,0 KG - COSSARI",
                NORMALIZED_ITEM_COLUMN: "docinho goiabada embalado",
                CONVERSION_COLUMN: "150",
            }
        ]
    )

    df = gerar_relatorio_conversao(dados_oc, df_depara)

    assert df.loc[0, "quantidade"] == 2.0
    assert df.loc[0, "valor_unitario"] == 55.5
    assert df.loc[0, "valor_total"] == 111.0
    assert df.loc[0, "criterio_conversao"] == "divisao_por_embalagem"


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
                "quantidade_original": 1.0,
                "quantidade": 1.0,
                "unidade": "UN",
                "valor_unitario": 5.0,
                "valor_total": 5.0,
                "regra_conversao": "",
                "criterio_conversao": "sem_conversao",
                "score": 100,
                "status": "encontrado_exato",
            }
        ]
    )

    caminho = salvar_relatorio_conversao(df, str(tmp_path), "623986")

    assert caminho.exists()
    assert caminho.name == "relatorio_conversao_OC_623986.xlsx"
