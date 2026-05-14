"""Testes do carregamento e busca de produtos no de-para tratado."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from produtos_depara import (
    CODE_COLUMN,
    DESCRIPTION_COLUMN,
    ITEM_COLUMN,
    MATCH_REVIEW_COLUMN,
    NORMALIZED_ITEM_COLUMN,
    buscar_produto,
    carregar_depara_produtos,
    normalizar_texto,
    normalizar_texto_match,
)


def test_carregar_depara_produtos_valida_colunas_e_normaliza(tmp_path: Path) -> None:
    arquivo = tmp_path / "produtos_tratados.xlsx"
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Milho Premium",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Milho ERP",
                NORMALIZED_ITEM_COLUMN: "  Milho\nPremium  ",
            }
        ]
    )
    dataframe.to_excel(arquivo, index=False)

    resultado = carregar_depara_produtos(str(arquivo))

    assert ITEM_COLUMN in resultado.columns
    assert CODE_COLUMN in resultado.columns
    assert DESCRIPTION_COLUMN in resultado.columns
    assert NORMALIZED_ITEM_COLUMN in resultado.columns
    assert resultado.loc[0, NORMALIZED_ITEM_COLUMN] == "milho premium"


def test_carregar_depara_produtos_bloqueia_conflitos_de_codigo(tmp_path: Path) -> None:
    arquivo = tmp_path / "produtos_tratados.xlsx"
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Milho Premium",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Milho ERP A",
                NORMALIZED_ITEM_COLUMN: "Milho Premium",
            },
            {
                ITEM_COLUMN: "Milho Premium",
                CODE_COLUMN: "200",
                DESCRIPTION_COLUMN: "Milho ERP B",
                NORMALIZED_ITEM_COLUMN: "Milho Premium",
            },
        ]
    )
    dataframe.to_excel(arquivo, index=False)

    try:
        carregar_depara_produtos(str(arquivo))
    except ValueError as exc:
        assert "COD. SILO diferentes" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado erro para duplicidade com codigos diferentes.")


def test_buscar_produto_retorna_correspondencia_exata() -> None:
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Milho Premium",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Milho ERP",
                NORMALIZED_ITEM_COLUMN: "Milho Premium",
            }
        ]
    )

    resultado = buscar_produto(" Milho   Premium ", dataframe)

    assert resultado == {
        "item_original_pdf": " Milho   Premium ",
        "item_encontrado_tabela": "Milho Premium",
        "codigo_silo": "100",
        "descricao_erp": "Milho ERP",
        "score": 100,
        "status": "encontrado_exato",
    }


def test_buscar_produto_retorna_correspondencia_aproximada() -> None:
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Milho Premium",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Milho ERP",
                NORMALIZED_ITEM_COLUMN: "Milho Premium",
            }
        ]
    )

    resultado = buscar_produto("Milho Premiu", dataframe)

    assert resultado["status"] == "encontrado_aproximado"
    assert resultado["codigo_silo"] == "100"
    assert resultado["score"] >= 90


def test_buscar_produto_retorna_revisar_para_item_exato_marcado_com_revisao() -> None:
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Doce de Leite Em Pasta",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Doce ERP",
                NORMALIZED_ITEM_COLUMN: "doce de leite em pasta",
                MATCH_REVIEW_COLUMN: True,
                "score_correspondencia": 85,
            }
        ]
    )

    resultado = buscar_produto("Doce de Leite Em Pasta", dataframe)

    assert resultado["status"] == "revisar"
    assert resultado["score"] == 85


def test_buscar_produto_retorna_revisar_para_score_intermediario() -> None:
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Milho Premium Especial",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Milho ERP",
                NORMALIZED_ITEM_COLUMN: "Milho Premium Especial",
            }
        ]
    )

    resultado = buscar_produto("Milho Especial", dataframe)

    assert resultado["status"] == "revisar"
    assert 75 <= resultado["score"] <= 89


def test_buscar_produto_retorna_nao_encontrado_para_score_baixo() -> None:
    dataframe = pd.DataFrame(
        [
            {
                ITEM_COLUMN: "Milho Premium",
                CODE_COLUMN: "100",
                DESCRIPTION_COLUMN: "Milho ERP",
                NORMALIZED_ITEM_COLUMN: "Milho Premium",
            }
        ]
    )

    resultado = buscar_produto("Parafuso Sextavado", dataframe)

    assert resultado["status"] == "nao_encontrado"
    assert resultado["codigo_silo"] == ""
    assert resultado["descricao_erp"] == ""
    assert resultado["score"] < 75


def test_normalizar_texto_remove_quebras_e_espacos() -> None:
    assert normalizar_texto("  Milho \n  Premium \r\n ") == "Milho Premium"


def test_normalizar_texto_match_remove_acento_e_pontuacao() -> None:
    assert normalizar_texto_match("  Soja em Grão!  ") == "soja em grao"
