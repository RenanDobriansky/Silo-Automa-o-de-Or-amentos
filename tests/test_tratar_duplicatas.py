"""Testes do tratamento de duplicatas na tabela de produtos."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tratar_duplicatas import (
    DESCRIPTION_COLUMN,
    MATCH_REVIEW_COLUMN,
    MATCH_SCORE_COLUMN,
    NORMALIZED_ITEM_COLUMN,
    tratar_duplicatas_produtos,
)


def test_tratar_duplicatas_remove_duplicatas_exatas(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entrada = tmp_path / "tabela_produtos.xlsx"
    saida = tmp_path / "relatorios"
    dataframe = pd.DataFrame(
        [
            {"Item": "Milho  Premium", "COD. SILO": "100", DESCRIPTION_COLUMN: "Milho\nPremium"},
            {"Item": "  Milho Premium ", "COD. SILO": "100", DESCRIPTION_COLUMN: "Milho Premium"},
            {"Item": "Soja", "COD. SILO": "200", DESCRIPTION_COLUMN: "Farelo   de soja"},
        ]
    )
    dataframe.to_excel(entrada, index=False)

    monkeypatch.setattr("tratar_duplicatas._get_report_output_dir", lambda: saida)

    resultado = tratar_duplicatas_produtos(str(entrada))

    produtos_unicos = pd.read_excel(saida / "produtos_unicos.xlsx")
    produtos_duplicados = pd.read_excel(saida / "produtos_duplicados_para_revisao.xlsx")

    assert resultado["qtd_linhas_original"] == 3
    assert resultado["qtd_produtos_unicos"] == 2
    assert resultado["qtd_duplicatas_exatas_removidas"] == 1
    assert resultado["qtd_duplicatas_para_revisao"] == 0
    assert len(produtos_unicos) == 2
    assert len(produtos_duplicados) == 0
    assert NORMALIZED_ITEM_COLUMN in produtos_unicos.columns
    assert MATCH_SCORE_COLUMN in produtos_unicos.columns
    assert MATCH_REVIEW_COLUMN in produtos_unicos.columns
    assert produtos_unicos.loc[0, NORMALIZED_ITEM_COLUMN] == "milho premium"
    assert bool(produtos_unicos.loc[0, MATCH_REVIEW_COLUMN]) is False


def test_tratar_duplicatas_escolhe_melhor_correspondencia_por_item(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entrada = tmp_path / "tabela_produtos.xlsx"
    saida = tmp_path / "relatorios"
    dataframe = pd.DataFrame(
        [
            {"Item": "Esponja Dupla Face", "COD. SILO": "100", DESCRIPTION_COLUMN: "ESPONJA DUPLA FACE AMARELO/VERDE"},
            {"Item": " Esponja  Dupla Face ", "COD. SILO": "101", DESCRIPTION_COLUMN: "FARINHA DE MILHO BIJU"},
            {"Item": "Soja", "COD. SILO": "200", DESCRIPTION_COLUMN: "Farelo de soja"},
        ]
    )
    dataframe.to_excel(entrada, index=False)

    monkeypatch.setattr("tratar_duplicatas._get_report_output_dir", lambda: saida)

    resultado = tratar_duplicatas_produtos(str(entrada))

    produtos_unicos = pd.read_excel(saida / "produtos_unicos.xlsx")
    produtos_duplicados = pd.read_excel(saida / "produtos_duplicados_para_revisao.xlsx")

    assert resultado["qtd_linhas_original"] == 3
    assert resultado["qtd_produtos_unicos"] == 2
    assert resultado["qtd_duplicatas_exatas_removidas"] == 0
    assert resultado["qtd_duplicatas_para_revisao"] == 1
    assert len(produtos_unicos) == 2
    assert len(produtos_duplicados) == 1
    escolhido = produtos_unicos.loc[produtos_unicos["Item"] == "Esponja Dupla Face"].iloc[0]
    assert str(escolhido["COD. SILO"]) == "100"
    assert bool(escolhido[MATCH_REVIEW_COLUMN]) is False


def test_tratar_duplicatas_marca_revisao_quando_correspondencia_e_ambigua(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entrada = tmp_path / "tabela_produtos.xlsx"
    saida = tmp_path / "relatorios"
    dataframe = pd.DataFrame(
        [
            {"Item": "Doce de Leite Em Pasta", "COD. SILO": "100", DESCRIPTION_COLUMN: "DOCE DE GOIABA EM PASTA"},
            {"Item": "Doce de Leite Em Pasta", "COD. SILO": "101", DESCRIPTION_COLUMN: "DOCE DE MACA EM PASTA"},
        ]
    )
    dataframe.to_excel(entrada, index=False)

    monkeypatch.setattr("tratar_duplicatas._get_report_output_dir", lambda: saida)

    resultado = tratar_duplicatas_produtos(str(entrada))
    produtos_unicos = pd.read_excel(saida / "produtos_unicos.xlsx")

    assert resultado["qtd_produtos_unicos"] == 1
    assert resultado["qtd_duplicatas_para_revisao"] == 1
    assert resultado["qtd_itens_requerendo_revisao"] == 1
    assert bool(produtos_unicos.loc[0, MATCH_REVIEW_COLUMN]) is True


def test_tratar_duplicatas_prefere_item_ativo_com_maior_prioridade(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entrada = tmp_path / "tabela_produtos.xlsx"
    saida = tmp_path / "relatorios"
    dataframe = pd.DataFrame(
        [
            {
                "Item": "Doce de Goiaba",
                "COD. SILO": "100",
                DESCRIPTION_COLUMN: "DOCE DE GOIABA ANTIGO",
                "Ativo": "Nao",
                "Prioridade": 1,
            },
            {
                "Item": "Doce de Goiaba",
                "COD. SILO": "999",
                DESCRIPTION_COLUMN: "DOCE DE GOIABA NOVO",
                "Ativo": "Sim",
                "Prioridade": 10,
            },
        ]
    )
    dataframe.to_excel(entrada, index=False)

    monkeypatch.setattr("tratar_duplicatas._get_report_output_dir", lambda: saida)

    resultado = tratar_duplicatas_produtos(str(entrada))
    produtos_unicos = pd.read_excel(saida / "produtos_unicos.xlsx")

    assert resultado["qtd_produtos_unicos"] == 1
    assert str(produtos_unicos.loc[0, "COD. SILO"]) == "999"
    assert str(produtos_unicos.loc[0, "Ativo"]).lower() == "sim"


def test_tratar_duplicatas_le_planilha_operacional_com_cabecalho_deslocado(
    tmp_path: Path,
    monkeypatch,
) -> None:
    entrada = tmp_path / "Tabela de produtos.xlsx"
    saida = tmp_path / "relatorios"

    dataframe = pd.DataFrame(
        [
            {
                "Ativo": "Sim",
                "Prioridade": 1,
                "Item": "Batata Palha",
                "COD. SILO": "2218",
                "DESCRIÇÃO": "BATATA PALHA 1KG (FD-12) - TAICO",
                "Código de Barras": "7898901982036",
                "Observação": "Carga inicial",
            }
        ]
    )

    with pd.ExcelWriter(entrada, engine="openpyxl") as writer:
        pd.DataFrame([["Modelo Operacional"], [""]]).to_excel(
            writer,
            sheet_name="cadastro_produtos",
            header=False,
            index=False,
        )
        dataframe.to_excel(
            writer,
            sheet_name="cadastro_produtos",
            startrow=3,
            index=False,
        )
        pd.DataFrame({"A": ["instrucao"]}).to_excel(
            writer,
            sheet_name="instrucoes",
            index=False,
        )

    monkeypatch.setattr("tratar_duplicatas._get_report_output_dir", lambda: saida)

    resultado = tratar_duplicatas_produtos(str(entrada))
    produtos_unicos = pd.read_excel(saida / "produtos_unicos.xlsx")

    assert resultado["qtd_produtos_unicos"] == 1
    assert produtos_unicos.loc[0, "Item"] == "Batata Palha"
    assert str(produtos_unicos.loc[0, "COD. SILO"]) == "2218"
