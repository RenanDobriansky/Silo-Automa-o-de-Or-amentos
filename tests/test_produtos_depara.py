"""Testes do carregamento, busca e conversao de produtos no de-para tratado."""

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
    MATCH_REVIEW_COLUMN,
    NORMALIZED_ITEM_COLUMN,
    aplicar_regra_conversao,
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


def test_aplicar_regra_conversao_numerica_divide_e_arredonda() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=2249,
        unidade="UN",
        regra_conversao="50",
        item_pdf="Docinho Maria Mole",
        descricao_erp="DOCINHO MARIA MOLE CX C/50",
        valor_unitario=0.74,
        valor_total=1664.26,
    )

    assert resultado["quantidade_convertida"] == 45.0
    assert resultado["valor_unitario_convertido"] == 37.0
    assert resultado["valor_total_convertido"] == 1665.0
    assert resultado["criterio_conversao"] == "divisao_por_embalagem"


def test_aplicar_regra_conversao_numerica_arredonda_sempre_para_cima() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=130,
        unidade="UN",
        regra_conversao="50",
        item_pdf="Docinho Maria Mole",
        descricao_erp="DOCINHO MARIA MOLE CX C/50",
        valor_unitario=0.74,
        valor_total=96.2,
    )

    assert resultado["quantidade_convertida"] == 3.0
    assert resultado["valor_unitario_convertido"] == 37.0
    assert resultado["valor_total_convertido"] == 111.0
    assert resultado["criterio_conversao"] == "divisao_por_embalagem"


def test_aplicar_regra_conversao_multiplo_de_72() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=90,
        unidade="UN",
        regra_conversao="ARREDONDAR MULTIPLO DE 72",
        item_pdf="Guardanapo 20x20 a 24x24 com 100un",
        descricao_erp="GUARDANAPO C/100 UN (FD 72)",
    )

    assert resultado["quantidade_convertida"] == 144.0
    assert resultado["criterio_conversao"] == "arredondamento_para_multiplo"


def test_aplicar_regra_conversao_fibraco_verde_grosso_para_multiplo_de_10() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=13,
        unidade="UN",
        regra_conversao="10",
        item_pdf="Fibraço Verde Grosso",
        descricao_erp="FIBRA LIMPEZA PESADA VERDE REF 9506 86,7MMX102MM (FARDO C/10)- BETTANIN",
        valor_unitario=2.5,
        valor_total=32.5,
    )

    assert resultado["quantidade_convertida"] == 20.0
    assert resultado["valor_unitario_convertido"] == 2.5
    assert resultado["valor_total_convertido"] == 50.0
    assert resultado["criterio_conversao"] == "arredondamento_para_multiplo"


def test_aplicar_regra_conversao_filme_500_para_1000() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=3,
        unidade="UN",
        regra_conversao="CONVERTER A CADA DUAS DE 500, MANDAMOS UMA DE 1.000",
        item_pdf="Filme PVC Largura 40cm rolo 500mt",
        descricao_erp="FILME PVC ESTICAVEL 38X1000M",
        valor_unitario=25.0,
        valor_total=75.0,
    )

    assert resultado["quantidade_convertida"] == 2.0
    assert resultado["valor_unitario_convertido"] == 50.0
    assert resultado["valor_total_convertido"] == 100.0
    assert resultado["criterio_conversao"] == "duas_unidades_de_500_para_uma_de_1000"


def test_aplicar_regra_conversao_moranguete_160_unidades_por_caixa() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=130,
        unidade="UN",
        regra_conversao="160",
        item_pdf="Docinho Chocolate Moranguete",
        descricao_erp="DOCINHO CHOCOLATE MORANGUETE 13 GR CX C/160 - BEL CHOCOLATES",
        valor_unitario=0.25,
        valor_total=32.5,
    )

    assert resultado["quantidade_convertida"] == 1.0
    assert resultado["valor_unitario_convertido"] == 40.0
    assert resultado["valor_total_convertido"] == 40.0
    assert resultado["criterio_conversao"] == "divisao_por_embalagem"


def test_aplicar_regra_conversao_docinho_embalado_150_unidades_por_caixa() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=151,
        unidade="UN",
        regra_conversao="150",
        item_pdf="Docinho Goiabada Embalado",
        descricao_erp="DOCINHO DE GOIABADA EMBALADO CX C/150 3,0 KG - COSSARI",
        valor_unitario=0.37,
        valor_total=55.87,
    )

    assert resultado["quantidade_convertida"] == 2.0
    assert resultado["valor_unitario_convertido"] == 55.5
    assert resultado["valor_total_convertido"] == 111.0
    assert resultado["criterio_conversao"] == "divisao_por_embalagem"


def test_aplicar_regra_conversao_farinha_rosca_em_kg() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=12,
        unidade="KG",
        regra_conversao="NA COTAÇÃO TEM UNIDADE DE MEDIDA KILO, CONVERTE POR 5 E DIRETO 5 KILOS",
        item_pdf="Farinha de Rosca",
        descricao_erp="FARINHA DE ROSCA 5KG - CHARLOTTE",
        valor_unitario=8.0,
        valor_total=96.0,
    )

    assert resultado["quantidade_convertida"] == 3.0
    assert resultado["valor_unitario_convertido"] == 40.0
    assert resultado["valor_total_convertido"] == 120.0
    assert resultado["criterio_conversao"] == "farinha_rosca_kg_para_pacote_5kg"


def test_aplicar_regra_conversao_farinha_rosca_pacote_5kg_direto() -> None:
    resultado = aplicar_regra_conversao(
        quantidade=2,
        unidade="PCT",
        regra_conversao="NA COTAÇÃO TEM UNIDADE DE MEDIDA KILO, CONVERTE POR 5 E DIRETO 5 KILOS",
        item_pdf="Farinha de Rosca Pacote 5kg",
        descricao_erp="FARINHA DE ROSCA 5KG - CHARLOTTE",
        valor_unitario=40.0,
        valor_total=80.0,
    )

    assert resultado["quantidade_convertida"] == 2.0
    assert resultado["valor_unitario_convertido"] == 40.0
    assert resultado["valor_total_convertido"] == 80.0
    assert resultado["criterio_conversao"] == "farinha_rosca_pacote_5kg_direto"
