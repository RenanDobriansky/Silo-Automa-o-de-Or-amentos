"""Testes das validacoes do processamento e do TXT Syscomp."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validar_txt import (
    validar_linhas_txt,
    validar_processamento,
    validar_produtos_convertidos,
    validar_total_oc,
)


def test_validar_produtos_convertidos_bloqueia_status_invalidos() -> None:
    relatorio = pd.DataFrame(
        [
            {"status": "encontrado_exato"},
            {"status": "revisar"},
            {"status": "nao_encontrado"},
            {"status": "nao_atendido"},
        ]
    )

    erros = validar_produtos_convertidos(relatorio)

    assert len(erros) == 3
    assert "nao_encontrado" in erros[0]
    assert "revisar" in erros[1]
    assert "nao_atendido" in erros[2]


def test_validar_total_oc_respeita_tolerancia() -> None:
    dados_ok = {
        "itens": [
            {"valor_total": 10.00},
            {"valor_total": 5.00},
        ],
        "totais": {"total_fornecedor": 15.01},
    }
    dados_erro = {
        "itens": [
            {"valor_total": 10.00},
            {"valor_total": 5.00},
        ],
        "totais": {"total_fornecedor": 15.02},
    }

    assert validar_total_oc(dados_ok) == []
    assert len(validar_total_oc(dados_erro)) == 1


def test_validar_linhas_txt_confere_registros_e_tamanhos_syscomp(tmp_path: Path) -> None:
    caminho_ok = tmp_path / "ok.txt"
    caminho_ok.write_text(
        "\n".join(
            [
                "019" + ("A" * 301),
                "024" + ("B" * 42),
                "040" + ("C" * 347),
                "090" + ("D" * 119),
            ]
        )
        + "\n",
        encoding="ascii",
    )

    caminho_erro = tmp_path / "erro.txt"
    caminho_erro.write_text("019AAAA\n777BBBB\n090DDDD\n", encoding="ascii")

    assert validar_linhas_txt(caminho_ok) == []

    erros = validar_linhas_txt(caminho_erro)
    assert any("registro invalido" in erro for erro in erros)
    assert any("ao menos um registro 040" in erro for erro in erros)


def test_validar_linhas_txt_detecta_tamanho_invalido(tmp_path: Path) -> None:
    caminho = tmp_path / "tamanho.txt"
    caminho.write_text(
        "\n".join(
            [
                "019" + ("A" * 10),
                "040" + ("B" * 347),
                "090" + ("C" * 119),
            ]
        )
        + "\n",
        encoding="ascii",
    )

    erros = validar_linhas_txt(caminho)

    assert any("tamanho" in erro for erro in erros)


def test_validar_processamento_retorna_status_consolidado(tmp_path: Path) -> None:
    dados_oc = {
        "itens": [
            {"valor_total": 10.0},
            {"valor_total": 15.0},
        ],
        "totais": {"total_fornecedor": 25.0},
    }
    relatorio = pd.DataFrame(
        [
            {"status": "encontrado_exato"},
            {"status": "encontrado_aproximado"},
        ]
    )
    caminho_txt = tmp_path / "oc.txt"
    caminho_txt.write_text(
        "\n".join(
            [
                "019" + ("A" * 301),
                "040" + ("B" * 347),
                "090" + ("C" * 119),
            ]
        )
        + "\n",
        encoding="ascii",
    )

    resultado = validar_processamento(dados_oc, relatorio, caminho_txt)

    assert resultado == {
        "status": "ok",
        "erros": [],
    }
