"""Gera relatorios de conversao e resumo de processamento das ordens."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from parser_oc import PurchaseOrder
from produtos_depara import (
    CONVERSION_COLUMN,
    NORMALIZED_ITEM_COLUMN,
    aplicar_regra_conversao,
    buscar_produto,
    normalizar_texto_match,
)

REPORT_COLUMNS = [
    "numero_oc",
    "sequencia",
    "item_pdf",
    "item_encontrado_tabela",
    "status_item",
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

ALLOWED_AUTOMATIC_STATUSES = {"encontrado_exato", "encontrado_aproximado"}


def gerar_relatorio_conversao(
    dados_oc: dict[str, Any],
    df_depara: pd.DataFrame,
) -> pd.DataFrame:
    """Gera um DataFrame item a item com o resultado da busca no de-para."""

    cabecalho = dados_oc.get("cabecalho", {})
    numero_oc = str(cabecalho.get("numero_oc", ""))
    itens = dados_oc.get("itens", [])

    rows: list[dict[str, Any]] = []
    for item in itens:
        resultado_busca = buscar_produto(str(item.get("item_pdf", "")), df_depara)
        regra_conversao = _obter_regra_conversao(resultado_busca, df_depara)
        resultado_conversao = aplicar_regra_conversao(
            quantidade=float(item.get("qtde", 0) or 0),
            unidade=str(item.get("unidade", "") or ""),
            regra_conversao=regra_conversao,
            item_pdf=str(item.get("item_pdf", "") or ""),
            descricao_erp=str(resultado_busca.get("descricao_erp", "") or ""),
            valor_unitario=float(item.get("valor_unitario", 0) or 0),
            valor_total=float(item.get("valor_total", 0) or 0),
        )
        rows.append(
            {
                "numero_oc": item.get("numero_oc") or numero_oc,
                "sequencia": item.get("sequencia", 0),
                "item_pdf": item.get("item_pdf", ""),
                "item_encontrado_tabela": resultado_busca["item_encontrado_tabela"],
                "status_item": resultado_busca.get("status_item", ""),
                "codigo_silo": resultado_busca["codigo_silo"],
                "descricao_erp": resultado_busca["descricao_erp"],
                "quantidade_original": item.get("qtde", 0),
                "quantidade": resultado_conversao["quantidade_convertida"],
                "unidade": resultado_conversao["unidade_convertida"],
                "valor_unitario": resultado_conversao["valor_unitario_convertido"],
                "valor_total": resultado_conversao["valor_total_convertido"],
                "regra_conversao": resultado_conversao["regra_conversao_aplicada"],
                "criterio_conversao": resultado_conversao["criterio_conversao"],
                "score": resultado_busca["score"],
                "status": resultado_busca["status"],
            }
        )

    dataframe = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    dataframe.attrs["numero_oc"] = numero_oc
    dataframe.attrs["pode_gerar_txt"] = pode_gerar_txt(dataframe)
    dataframe.attrs["status_geracao_txt"] = status_geracao_txt(dataframe)
    return dataframe


def _obter_regra_conversao(
    resultado_busca: dict[str, Any],
    df_depara: pd.DataFrame,
) -> str:
    """Busca a regra de conversao na linha do produto encontrado."""

    if CONVERSION_COLUMN not in df_depara.columns:
        return ""

    item_tabela = str(resultado_busca.get("item_encontrado_tabela", "") or "")
    if not item_tabela:
        return ""

    item_normalizado = normalizar_texto_match(item_tabela)
    match = df_depara.loc[
        df_depara[NORMALIZED_ITEM_COLUMN].map(normalizar_texto_match) == item_normalizado
    ]
    if match.empty:
        return ""

    return str(match.iloc[0].get(CONVERSION_COLUMN, "") or "")


def salvar_relatorio_conversao(
    df: pd.DataFrame,
    pasta_saida: str,
    numero_oc: str,
) -> Path:
    """Salva o relatorio de conversao em Excel com o nome padrao da OC."""

    output_dir = Path(pasta_saida)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"relatorio_conversao_OC_{numero_oc}.xlsx"
    df.to_excel(output_path, index=False)
    return output_path


def pode_gerar_txt(df: pd.DataFrame) -> bool:
    """Informa se o TXT pode ser gerado automaticamente a partir do relatorio."""

    if df.empty:
        return False

    statuses = set(df["status"].dropna().astype(str))
    return statuses.issubset(ALLOWED_AUTOMATIC_STATUSES)


def status_geracao_txt(df: pd.DataFrame) -> str:
    """Resume o motivo pelo qual o TXT pode ou nao pode ser gerado."""

    if df.empty:
        return "sem_itens"

    statuses = set(df["status"].dropna().astype(str))
    if "nao_atendido" in statuses:
        return "bloqueado_nao_atendido"
    if "nao_encontrado" in statuses:
        return "bloqueado_nao_encontrado"
    if "revisar" in statuses:
        return "bloqueado_revisao_manual"
    if statuses.issubset(ALLOWED_AUTOMATIC_STATUSES):
        return "liberado"
    return "bloqueado_status_desconhecido"


def build_processing_report(
    source_file: str,
    output_file: str,
    order: PurchaseOrder,
    status: str,
    validation_errors: list[str],
) -> dict[str, object]:
    """Monta um dicionario serializavel com o resumo do processamento."""

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source_file": source_file,
        "output_file": output_file,
        "status": status,
        "pedido": order.pedido,
        "fornecedor": order.fornecedor,
        "total_itens": len(order.itens),
        "validation_errors": validation_errors,
    }


def save_processing_report(report: dict[str, object], report_path: str | Path) -> Path:
    """Salva o relatorio de processamento em JSON."""

    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return path
