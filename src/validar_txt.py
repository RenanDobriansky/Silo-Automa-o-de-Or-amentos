"""Valida a conversao da OC antes e depois da geracao do TXT Syscomp."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

VALID_RECORD_PREFIXES = {"019", "024", "040", "090"}
RECORD_LENGTHS = {
    "019": 304,
    "024": 45,
    "040": 350,
    "090": 122,
}
BLOCKING_STATUSES = {"nao_encontrado", "revisar", "nao_atendido"}
TOTAL_TOLERANCE = Decimal("0.01")
TXT_ENCODING = os.getenv("AUTOMACAO_OC_TXT_ENCODING", "ascii")


def validar_produtos_convertidos(relatorio_conversao: pd.DataFrame) -> list[str]:
    """Retorna erros quando houver itens bloqueando a geracao automatica do TXT."""

    if relatorio_conversao.empty:
        return ["Relatorio de conversao vazio."]

    erros: list[str] = []
    statuses = set(relatorio_conversao["status"].dropna().astype(str))

    if "nao_encontrado" in statuses:
        erros.append(
            "Existem itens com status 'nao_encontrado'. O TXT nao pode ser gerado."
        )
    if "revisar" in statuses:
        erros.append("Existem itens com status 'revisar'. O TXT nao pode ser gerado automaticamente.")
    if "nao_atendido" in statuses:
        erros.append(
            "Existem itens com status 'nao_atendido'. O TXT nao pode ser gerado porque a empresa nao atende esses itens."
        )

    return erros


def validar_total_oc(dados_oc: dict[str, Any]) -> list[str]:
    """Compara o total dos itens com o total do fornecedor informado no PDF."""

    itens = dados_oc.get("itens", [])
    totais = dados_oc.get("totais", {})
    total_informado = Decimal(str(totais.get("total_fornecedor", 0) or 0))
    total_itens = sum(Decimal(str(item.get("valor_total", 0) or 0)) for item in itens)

    if abs(total_itens - total_informado) > TOTAL_TOLERANCE:
        return [
            "Total da OC divergente: soma dos itens "
            f"({float(total_itens):.2f}) diferente do total fornecedor "
            f"({float(total_informado):.2f})."
        ]

    return []


def validar_linhas_txt(caminho_txt: str | Path) -> list[str]:
    """Valida a estrutura posicional do TXT aceito pela Syscomp."""

    path = Path(caminho_txt)
    if not path.exists():
        return [f"Arquivo TXT nao encontrado: {path}"]

    linhas = [
        linha.rstrip("\n\r")
        for linha in path.read_text(encoding=TXT_ENCODING).splitlines()
        if linha.strip()
    ]
    if not linhas:
        return ["Arquivo TXT vazio."]

    erros: list[str] = []
    prefixos = [linha[:3] for linha in linhas]

    for index, linha in enumerate(linhas, start=1):
        prefixo = linha[:3]
        if prefixo not in VALID_RECORD_PREFIXES:
            erros.append(f"Linha {index} possui registro invalido: {prefixo}.")
            continue

        tamanho_esperado = RECORD_LENGTHS[prefixo]
        if len(linha) != tamanho_esperado:
            erros.append(
                f"Linha {index} do registro {prefixo} possui tamanho {len(linha)} "
                f"mas o esperado e {tamanho_esperado}."
            )

    if prefixos.count("019") != 1:
        erros.append("O arquivo deve conter exatamente um registro 019.")
    if prefixos.count("090") != 1:
        erros.append("O arquivo deve conter exatamente um registro 090.")
    if prefixos.count("040") < 1:
        erros.append("O arquivo deve conter ao menos um registro 040.")

    return erros


def validar_processamento(
    dados_oc: dict[str, Any],
    relatorio_conversao: pd.DataFrame,
    caminho_txt: str | Path | None = None,
) -> dict[str, Any]:
    """Executa as validacoes do processamento e devolve status consolidado."""

    erros: list[str] = []
    erros.extend(validar_produtos_convertidos(relatorio_conversao))
    erros.extend(validar_total_oc(dados_oc))

    if caminho_txt is not None:
        erros.extend(validar_linhas_txt(caminho_txt))

    return {
        "status": "ok" if not erros else "erro",
        "erros": erros,
    }


def validate_neogrid_txt(content: str) -> list[str]:
    """Wrapper legado para validacao em memoria do formato simples antigo."""

    errors: list[str] = []
    lines = [line for line in content.splitlines() if line.strip()]

    if not lines:
        return ["Arquivo TXT vazio."]

    header = lines[0].split("|")
    if not lines[0].startswith("H|") or len(header) != 5:
        errors.append("Cabecalho invalido. Esperado: H|pedido|fornecedor|cnpj|data_entrega")

    detail_lines = lines[1:]
    if not detail_lines:
        errors.append("O arquivo precisa conter ao menos uma linha de detalhe.")

    for index, line in enumerate(detail_lines, start=2):
        parts = line.split("|")
        if not line.startswith("D|") or len(parts) != 7:
            errors.append(
                f"Linha {index} invalida. Esperado: "
                "D|sequencia|codigo|descricao|quantidade|unidade|preco"
            )

    return errors
