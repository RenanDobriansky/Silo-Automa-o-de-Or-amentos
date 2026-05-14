"""Carrega e consulta a tabela de de-para de produtos para itens vindos do PDF."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz, process

from parser_oc import PurchaseOrder, PurchaseOrderItem, replace_items

ITEM_COLUMN = "Item"
CODE_COLUMN = "COD. SILO"
DESCRIPTION_COLUMN = "DESCRI\u00c7\u00c3O"
NORMALIZED_ITEM_COLUMN = "item_normalizado"
MATCH_SCORE_COLUMN = "score_correspondencia"
MATCH_REVIEW_COLUMN = "requer_revisao"
MATCH_REASON_COLUMN = "criterio_escolha"

REQUIRED_COLUMNS = [
    ITEM_COLUMN,
    CODE_COLUMN,
    DESCRIPTION_COLUMN,
    NORMALIZED_ITEM_COLUMN,
]


def carregar_depara_produtos(caminho_excel: str) -> pd.DataFrame:
    """Carrega a tabela tratada de produtos e valida conflitos de mapeamento."""

    dataframe = pd.read_excel(caminho_excel)
    _validar_colunas_obrigatorias(dataframe)

    dataframe = dataframe.copy()
    dataframe[ITEM_COLUMN] = dataframe[ITEM_COLUMN].map(normalizar_texto)
    dataframe[CODE_COLUMN] = dataframe[CODE_COLUMN].map(normalizar_texto)
    dataframe[DESCRIPTION_COLUMN] = dataframe[DESCRIPTION_COLUMN].map(normalizar_texto)
    dataframe[NORMALIZED_ITEM_COLUMN] = dataframe[NORMALIZED_ITEM_COLUMN].map(normalizar_texto_match)
    dataframe = dataframe.drop_duplicates().reset_index(drop=True)

    conflitos = _identificar_conflitos(dataframe)
    if not conflitos.empty:
        itens = ", ".join(sorted(conflitos[NORMALIZED_ITEM_COLUMN].astype(str).unique()))
        raise ValueError(
            "Existem duplicatas em item_normalizado apontando para COD. SILO diferentes: "
            f"{itens}."
        )

    return dataframe


def normalizar_texto(texto: str) -> str:
    """Padroniza textos removendo quebras de linha e espacos excedentes."""

    if pd.isna(texto):
        return ""

    valor = str(texto).replace("\r", " ").replace("\n", " ")
    valor = re.sub(r"\s+", " ", valor)
    return valor.strip()


def normalizar_texto_match(texto: str) -> str:
    """Padroniza texto para comparacao tolerante a acento e pontuacao."""

    valor = normalizar_texto(texto)
    if not valor:
        return ""

    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(char for char in valor if not unicodedata.combining(char))
    valor = valor.lower()
    valor = re.sub(r"[^a-z0-9]+", " ", valor)
    valor = re.sub(r"\s+", " ", valor).strip()
    return valor


def buscar_produto(item_pdf: str, df_depara: pd.DataFrame) -> dict[str, Any]:
    """Busca um produto por correspondencia exata ou aproximada na tabela tratada."""

    item_normalizado = normalizar_texto_match(item_pdf)
    if df_depara.empty or not item_normalizado:
        return _build_result(item_pdf, "", "", "", 0, "nao_encontrado")

    dataframe = df_depara.copy()
    dataframe[NORMALIZED_ITEM_COLUMN] = dataframe[NORMALIZED_ITEM_COLUMN].map(normalizar_texto_match)

    match_exato = dataframe.loc[dataframe[NORMALIZED_ITEM_COLUMN] == item_normalizado]
    if not match_exato.empty:
        row = match_exato.iloc[0]
        if bool(row.get(MATCH_REVIEW_COLUMN, False)):
            return _build_result(
                item_pdf,
                row[ITEM_COLUMN],
                row[CODE_COLUMN],
                row[DESCRIPTION_COLUMN],
                int(float(row.get(MATCH_SCORE_COLUMN, 0) or 0)),
                "revisar",
            )
        return _build_result(
            item_pdf,
            row[ITEM_COLUMN],
            row[CODE_COLUMN],
            row[DESCRIPTION_COLUMN],
            100,
            "encontrado_exato",
        )

    escolhas = dataframe[NORMALIZED_ITEM_COLUMN].dropna().astype(str).tolist()
    resultado = process.extractOne(
        item_normalizado,
        escolhas,
        scorer=fuzz.WRatio,
    )
    if resultado is None:
        return _build_result(item_pdf, "", "", "", 0, "nao_encontrado")

    item_encontrado, score, _ = resultado
    row = dataframe.loc[dataframe[NORMALIZED_ITEM_COLUMN] == item_encontrado].iloc[0]

    if score >= 90:
        status = "encontrado_aproximado"
    elif score >= 75:
        status = "revisar"
    else:
        return _build_result(item_pdf, "", "", "", int(score), "nao_encontrado")

    return _build_result(
        item_pdf,
        row[ITEM_COLUMN],
        row[CODE_COLUMN],
        row[DESCRIPTION_COLUMN],
        int(score),
        status,
    )


def load_product_mapping(xlsx_path: str | Path) -> dict[str, dict[str, str]]:
    """Wrapper de compatibilidade que monta um dicionario a partir do Excel tratado."""

    dataframe = carregar_depara_produtos(str(xlsx_path))
    mapping: dict[str, dict[str, str]] = {}

    for _, row in dataframe.iterrows():
        mapping[row[NORMALIZED_ITEM_COLUMN]] = {
            "codigo_neogrid": row[CODE_COLUMN],
            "descricao_neogrid": row[DESCRIPTION_COLUMN],
            "item_original": row[ITEM_COLUMN],
        }

    return mapping


def map_order_items(
    order: PurchaseOrder,
    mapping: Mapping[str, Mapping[str, str]] | pd.DataFrame,
) -> PurchaseOrder:
    """Aplica o de-para nos itens da ordem usando dicionario ou DataFrame."""

    mapped_items: list[PurchaseOrderItem] = []

    for item in order.itens:
        if isinstance(mapping, pd.DataFrame):
            resultado = buscar_produto(item.descricao, mapping)
            codigo = (
                resultado["codigo_silo"]
                if resultado["status"] in {"encontrado_exato", "encontrado_aproximado"}
                else item.codigo
            )
            descricao = (
                resultado["descricao_erp"]
                if resultado["status"] in {"encontrado_exato", "encontrado_aproximado"}
                else item.descricao
            )
        else:
            product_mapping = (
                mapping.get(normalizar_texto_match(item.descricao))
                or mapping.get(normalizar_texto_match(item.codigo))
                or {}
            )
            codigo = product_mapping.get("codigo_neogrid") or item.codigo
            descricao = product_mapping.get("descricao_neogrid") or item.descricao

        mapped_items.append(
            replace(
                item,
                codigo_neogrid=codigo,
                descricao=descricao,
            )
        )

    return replace_items(order, mapped_items)


def _validar_colunas_obrigatorias(dataframe: pd.DataFrame) -> None:
    """Valida a presenca das colunas minimas exigidas na tabela tratada."""

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(
            "A tabela de produtos tratada deve conter as colunas obrigatorias: "
            f"{missing}."
        )


def _identificar_conflitos(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Encontra itens normalizados que ainda apontam para mais de um codigo."""

    grouped = dataframe.groupby(NORMALIZED_ITEM_COLUMN)[CODE_COLUMN].nunique(dropna=False)
    itens_com_conflito = grouped[grouped > 1].index
    return dataframe.loc[dataframe[NORMALIZED_ITEM_COLUMN].isin(itens_com_conflito)].copy()


def _build_result(
    item_original_pdf: str,
    item_encontrado_tabela: str,
    codigo_silo: str,
    descricao_erp: str,
    score: int,
    status: str,
) -> dict[str, Any]:
    """Monta o payload padrao de retorno da busca de produto."""

    return {
        "item_original_pdf": item_original_pdf,
        "item_encontrado_tabela": item_encontrado_tabela,
        "codigo_silo": codigo_silo,
        "descricao_erp": descricao_erp,
        "score": score,
        "status": status,
    }
