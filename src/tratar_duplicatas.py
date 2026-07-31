"""Centraliza o tratamento de duplicatas de produtos e de itens processados."""

from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

from config import get_config
from parser_oc import PurchaseOrderItem

ITEM_COLUMN = "Item"
CODE_COLUMN = "COD. SILO"
DESCRIPTION_COLUMN = "DESCRI\u00c7\u00c3O"
NORMALIZED_ITEM_COLUMN = "item_normalizado"
NORMALIZED_DESCRIPTION_COLUMN = "descricao_normalizada"
MATCH_SCORE_COLUMN = "score_correspondencia"
MATCH_REVIEW_COLUMN = "requer_revisao"
MATCH_REASON_COLUMN = "criterio_escolha"
ACTIVE_COLUMN = "Ativo"
ITEM_STATUS_COLUMN = "Status Item"
PRIORITY_COLUMN = "Prioridade"
START_DATE_COLUMN = "Data início"
END_DATE_COLUMN = "Data fim"
NOTES_COLUMN = "Observação"

REQUIRED_PRODUCT_COLUMNS = [ITEM_COLUMN, CODE_COLUMN, DESCRIPTION_COLUMN]
REVIEW_MARGIN_THRESHOLD = 3.0
LOW_CONFIDENCE_THRESHOLD = 80.0


def tratar_duplicatas_produtos(caminho_excel: str) -> dict[str, int]:
    """Limpa a tabela de produtos, resolve duplicatas e gera uma tabela utilizavel.

    A limpeza garante um unico registro por `item_normalizado`, escolhendo o
    `COD. SILO` e a `DESCRIÇÃO` com melhor correspondencia textual para o Item.
    """

    dataframe = _read_products_workbook(caminho_excel)
    _validate_required_columns(dataframe)

    qtd_linhas_original = len(dataframe)
    dataframe = _padronizar_colunas_texto(dataframe)
    dataframe = dataframe.loc[dataframe[NORMALIZED_ITEM_COLUMN] != ""].reset_index(drop=True)
    dataframe["_ativo"] = dataframe.apply(_is_row_operational, axis=1)
    dataframe["_prioridade"] = dataframe.apply(_parse_priority, axis=1)
    dataframe["_has_code"] = dataframe[CODE_COLUMN].map(_has_value)
    dataframe["_has_description"] = dataframe[DESCRIPTION_COLUMN].map(_has_value)
    dataframe["_completeness_rank"] = (
        dataframe["_has_code"].astype(int) + dataframe["_has_description"].astype(int)
    )
    dataframe[MATCH_SCORE_COLUMN] = dataframe.apply(
        lambda row: _calculate_match_score(
            row[NORMALIZED_ITEM_COLUMN],
            row[NORMALIZED_DESCRIPTION_COLUMN],
        ),
        axis=1,
    )

    dedup_subset = [
        NORMALIZED_ITEM_COLUMN,
        CODE_COLUMN,
        NORMALIZED_DESCRIPTION_COLUMN,
    ]
    dataframe_sem_duplicatas_exatas = dataframe.drop_duplicates(
        subset=dedup_subset,
        keep="first",
    ).reset_index(drop=True)

    qtd_duplicatas_exatas_removidas = (
        qtd_linhas_original - len(dataframe_sem_duplicatas_exatas)
    )

    produtos_unicos, produtos_revisao = _resolver_grupos_duplicados(
        dataframe_sem_duplicatas_exatas
    )

    report_dir = _get_report_output_dir()
    report_dir.mkdir(parents=True, exist_ok=True)
    produtos_unicos.to_excel(report_dir / "produtos_unicos.xlsx", index=False)
    produtos_revisao.to_excel(
        report_dir / "produtos_duplicados_para_revisao.xlsx",
        index=False,
    )

    return {
        "qtd_linhas_original": qtd_linhas_original,
        "qtd_produtos_unicos": len(produtos_unicos),
        "qtd_duplicatas_exatas_removidas": qtd_duplicatas_exatas_removidas,
        "qtd_duplicatas_para_revisao": len(produtos_revisao),
        "qtd_itens_requerendo_revisao": int(produtos_unicos[MATCH_REVIEW_COLUMN].sum()),
    }


def deduplicate_items(items: list[PurchaseOrderItem]) -> list[PurchaseOrderItem]:
    """Agrupa itens com mesma chave comercial e soma suas quantidades."""

    grouped: OrderedDict[tuple[str, str, str, str], PurchaseOrderItem] = OrderedDict()

    for item in items:
        key = (
            item.codigo_neogrid or item.codigo,
            item.descricao,
            item.unidade,
            str(item.preco_unitario),
        )
        current = grouped.get(key)
        if current is None:
            grouped[key] = item
            continue

        grouped[key] = replace(
            current,
            quantidade=current.quantidade + item.quantidade,
            line_number=min(current.line_number, item.line_number),
        )

    return list(grouped.values())


def _resolver_grupos_duplicados(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Escolhe o melhor candidato por item e separa os descartados para revisao."""

    produtos_unicos_rows: list[dict[str, object]] = []
    produtos_revisao_frames: list[pd.DataFrame] = []

    for _, group in dataframe.groupby(NORMALIZED_ITEM_COLUMN, sort=True):
        candidatos_ativos = group.loc[group["_ativo"]].copy()
        candidate_pool = candidatos_ativos if not candidatos_ativos.empty else group.copy()

        ranked = candidate_pool.sort_values(
            by=[
                "_ativo",
                "_prioridade",
                "_completeness_rank",
                MATCH_SCORE_COLUMN,
                "_has_code",
                "_has_description",
                DESCRIPTION_COLUMN,
            ],
            ascending=[False, False, False, False, False, False, True],
        ).reset_index(drop=True)

        selected = ranked.iloc[0].copy()
        second_score = float(ranked.iloc[1][MATCH_SCORE_COLUMN]) if len(ranked) > 1 else -1.0
        margin = float(selected[MATCH_SCORE_COLUMN]) - second_score
        has_conflict = ranked[CODE_COLUMN].astype(str).nunique(dropna=False) > 1

        selected[MATCH_REVIEW_COLUMN] = bool(
            has_conflict
            and (
                float(selected[MATCH_SCORE_COLUMN]) < LOW_CONFIDENCE_THRESHOLD
                or margin < REVIEW_MARGIN_THRESHOLD
            )
        )
        selected[MATCH_REASON_COLUMN] = _build_selection_reason(
            selected_score=float(selected[MATCH_SCORE_COLUMN]),
            second_score=second_score,
            has_conflict=has_conflict,
            requires_review=bool(selected[MATCH_REVIEW_COLUMN]),
        )
        produtos_unicos_rows.append(selected.to_dict())

        if len(ranked) > 1:
            discarded = ranked.iloc[1:].copy()
            discarded["item_escolhido"] = selected[ITEM_COLUMN]
            discarded["codigo_escolhido"] = selected[CODE_COLUMN]
            discarded["score_escolhido"] = selected[MATCH_SCORE_COLUMN]
            discarded["requer_revisao_item"] = selected[MATCH_REVIEW_COLUMN]
            produtos_revisao_frames.append(discarded)

        historicos_inativos = group.loc[~group.index.isin(candidate_pool.index)].copy()
        if not historicos_inativos.empty:
            historicos_inativos["item_escolhido"] = selected[ITEM_COLUMN]
            historicos_inativos["codigo_escolhido"] = selected[CODE_COLUMN]
            historicos_inativos["score_escolhido"] = selected[MATCH_SCORE_COLUMN]
            historicos_inativos["requer_revisao_item"] = selected[MATCH_REVIEW_COLUMN]
            historicos_inativos["motivo_historico"] = "registro_inativo_ou_fora_da_vigencia"
            produtos_revisao_frames.append(historicos_inativos)

    produtos_unicos = pd.DataFrame(produtos_unicos_rows)
    produtos_revisao = (
        pd.concat(produtos_revisao_frames, ignore_index=True)
        if produtos_revisao_frames
        else pd.DataFrame(columns=list(produtos_unicos.columns) + [
            "item_escolhido",
            "codigo_escolhido",
            "score_escolhido",
            "requer_revisao_item",
        ])
    )

    drop_columns = [
        "_ativo",
        "_prioridade",
        "_has_code",
        "_has_description",
        "_completeness_rank",
    ]
    produtos_unicos = produtos_unicos.drop(columns=drop_columns, errors="ignore")
    produtos_revisao = produtos_revisao.drop(columns=drop_columns, errors="ignore")
    return produtos_unicos.reset_index(drop=True), produtos_revisao.reset_index(drop=True)


def _build_selection_reason(
    selected_score: float,
    second_score: float,
    has_conflict: bool,
    requires_review: bool,
) -> str:
    """Explica resumidamente o criterio usado para selecionar o item vencedor."""

    if not has_conflict:
        return "item_unico_ou_sem_conflito"
    if requires_review:
        return (
            f"melhor_correspondencia_com_revisao(score={selected_score:.2f},"
            f"margem={selected_score - second_score:.2f})"
        )
    return (
        f"melhor_correspondencia_automatica(score={selected_score:.2f},"
        f"margem={selected_score - second_score:.2f})"
    )


def _padronizar_colunas_texto(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normaliza textos e cria colunas auxiliares para comparacao."""

    dataframe = dataframe.copy()

    for column in REQUIRED_PRODUCT_COLUMNS:
        dataframe[column] = dataframe[column].map(_normalize_text_cell)

    for column in [ACTIVE_COLUMN, ITEM_STATUS_COLUMN, PRIORITY_COLUMN, NOTES_COLUMN]:
        if column in dataframe.columns:
            dataframe[column] = dataframe[column].map(_normalize_text_cell)

    dataframe[NORMALIZED_ITEM_COLUMN] = dataframe[ITEM_COLUMN].map(_normalize_match_text)
    dataframe[NORMALIZED_DESCRIPTION_COLUMN] = dataframe[DESCRIPTION_COLUMN].map(
        _normalize_match_text
    )
    return dataframe


def _calculate_match_score(item_text: str, description_text: str) -> float:
    """Calcula um score de correspondencia entre Item e DESCRIÇÃO."""

    if not item_text or not description_text:
        return 0.0

    token_set = fuzz.token_set_ratio(item_text, description_text)
    token_sort = fuzz.token_sort_ratio(item_text, description_text)
    wratio = fuzz.WRatio(item_text, description_text)
    return max(token_set, token_sort, wratio)


def _normalize_text_cell(value: object) -> str:
    """Remove espacos excedentes e quebras de linha de valores textuais."""

    if pd.isna(value):
        return ""

    text = str(value).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_match_text(value: object) -> str:
    """Normaliza texto para comparacao tolerante a acento, caixa e pontuacao."""

    text = _normalize_text_cell(value)
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _has_value(value: object) -> bool:
    """Indica se um campo textual ou numerico possui valor util."""

    if pd.isna(value):
        return False
    return str(value).strip() != ""


def _is_row_operational(row: pd.Series) -> bool:
    """Indica se a linha esta operacionalmente vigente para uso automatico."""

    ativo = _parse_active_flag(row.get(ACTIVE_COLUMN, ""))
    inicio = _parse_date_value(row.get(START_DATE_COLUMN))
    fim = _parse_date_value(row.get(END_DATE_COLUMN))
    hoje = date.today()

    if inicio is not None and inicio > hoje:
        return False
    if fim is not None and fim < hoje:
        return False
    return ativo


def _parse_active_flag(value: object) -> bool:
    """Interpreta a coluna Ativo da planilha de apoio."""

    texto = _normalize_match_text(value)
    if not texto:
        return True

    if texto in {"sim", "s", "ativo", "true", "1", "ok"}:
        return True
    if texto in {"nao", "n", "inativo", "false", "0"}:
        return False
    return True


def _parse_priority(row: pd.Series) -> int:
    """Converte a prioridade operacional para inteiro, com fallback seguro."""

    value = row.get(PRIORITY_COLUMN, "")
    if pd.isna(value):
        return 0

    texto = _normalize_text_cell(value).replace(",", ".")
    if not texto:
        return 0

    try:
        return int(float(texto))
    except ValueError:
        return 0


def _parse_date_value(value: object) -> date | None:
    """Interpreta uma data opcional da planilha operacional."""

    if pd.isna(value):
        return None

    texto = _normalize_text_cell(value)
    if not texto:
        return None

    parsed = pd.to_datetime(texto, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _validate_required_columns(dataframe: pd.DataFrame) -> None:
    """Garante que a planilha contenha as colunas obrigatorias."""

    missing_columns = [
        column for column in REQUIRED_PRODUCT_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(
            "A planilha de produtos deve conter as colunas obrigatorias: "
            f"{missing}."
        )


def _read_products_workbook(caminho_excel: str) -> pd.DataFrame:
    """Le a planilha de produtos suportando abas operacionais e cabecalhos deslocados."""

    workbook = pd.ExcelFile(caminho_excel)
    required = {_normalize_header_name(column) for column in REQUIRED_PRODUCT_COLUMNS}

    for sheet_name in workbook.sheet_names:
        preview = pd.read_excel(workbook, sheet_name=sheet_name, header=None, nrows=15)
        max_header_row = min(len(preview), 10)
        for header_row in range(max_header_row):
            header_values = preview.iloc[header_row].tolist()
            normalized_headers = {_normalize_header_name(value) for value in header_values}
            if not required.issubset(normalized_headers):
                continue

            dataframe = pd.read_excel(workbook, sheet_name=sheet_name, header=header_row)
            dataframe = dataframe.loc[
                :,
                [
                    column
                    for column in dataframe.columns
                    if not str(column).startswith("Unnamed:")
                ],
            ]
            return _rename_supported_columns(dataframe)

    return pd.read_excel(caminho_excel)


def _rename_supported_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Padroniza os nomes das colunas reconhecidas na planilha operacional."""

    known_columns = {
        _normalize_header_name(ITEM_COLUMN): ITEM_COLUMN,
        _normalize_header_name(CODE_COLUMN): CODE_COLUMN,
        _normalize_header_name(DESCRIPTION_COLUMN): DESCRIPTION_COLUMN,
        _normalize_header_name(ACTIVE_COLUMN): ACTIVE_COLUMN,
        _normalize_header_name(ITEM_STATUS_COLUMN): ITEM_STATUS_COLUMN,
        _normalize_header_name(PRIORITY_COLUMN): PRIORITY_COLUMN,
        _normalize_header_name(START_DATE_COLUMN): START_DATE_COLUMN,
        _normalize_header_name(END_DATE_COLUMN): END_DATE_COLUMN,
        _normalize_header_name(NOTES_COLUMN): NOTES_COLUMN,
        _normalize_header_name("Código de Barras"): "Código de Barras",
        _normalize_header_name("Codigo de Barras"): "Código de Barras",
        _normalize_header_name(MATCH_SCORE_COLUMN): MATCH_SCORE_COLUMN,
        _normalize_header_name(MATCH_REVIEW_COLUMN): MATCH_REVIEW_COLUMN,
        _normalize_header_name(MATCH_REASON_COLUMN): MATCH_REASON_COLUMN,
    }

    renamed_columns: dict[object, object] = {}
    for column in dataframe.columns:
        normalized = _normalize_header_name(column)
        if normalized in known_columns:
            renamed_columns[column] = known_columns[normalized]
    return dataframe.rename(columns=renamed_columns)


def _normalize_header_name(value: object) -> str:
    """Normaliza nomes de colunas para comparacao resiliente a acento e caixa."""

    text = _normalize_text_cell(value)
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.casefold()


def _get_report_output_dir() -> Path:
    """Resolve a pasta padrao de saida dos relatorios."""

    return get_config().output_reports_dir
