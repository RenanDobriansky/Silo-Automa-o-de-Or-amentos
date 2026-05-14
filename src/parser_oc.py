"""Interpreta texto extraido de ordens de compra em estruturas reutilizaveis."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Iterable


@dataclass(frozen=True)
class PurchaseOrderItem:
    """Representa um item individual da ordem de compra."""

    line_number: int
    codigo: str
    descricao: str
    quantidade: Decimal
    unidade: str
    preco_unitario: Decimal
    codigo_neogrid: str | None = None
    data_entrega: str | None = None


@dataclass(frozen=True)
class PurchaseOrder:
    """Representa o cabecalho e os itens extraidos de uma ordem de compra."""

    pedido: str
    fornecedor: str
    cnpj: str
    data_entrega: str
    itens: list[PurchaseOrderItem]


HEADER_ALIASES = {
    "pedido": "pedido",
    "ordem": "pedido",
    "ordem_compra": "pedido",
    "fornecedor": "fornecedor",
    "cnpj": "cnpj",
    "data_entrega": "data_entrega",
    "entrega": "data_entrega",
}

REAL_ITEM_PATTERN = re.compile(
    r"^(?P<data>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<sequencia>\d+)\s+"
    r"(?P<numero_oc>\d+)\s+"
    r"(?P<descricao_base>.+?)\s+"
    r"(?P<qtde_emb>\d[\d ]*,\d{2})\s+"
    r"(?P<qtde>\d[\d ]*,\d{2}[A-Z]{2,3})\s+"
    r"(?P<valor_unitario>\d[\d ]*,\d{2})\s+"
    r"(?P<valor_total>\d[\d ]*,\d{2})$"
)

SECTION_HEADER_PATTERN = re.compile(r"^Dt\.\s*Entrega\b", re.IGNORECASE)
ORDER_START_PATTERN = re.compile(r"^Fornecedor:", re.IGNORECASE)
ORDER_END_PATTERN = re.compile(r"^Total Fornecedor:", re.IGNORECASE)
SUPPLIER_PATTERN = re.compile(r"^Fornecedor:\s*(?P<fornecedor>.+?)\s+N\S*\s*OC\s*$")
CNPJ_PATTERN = re.compile(r"CNPJ:\s*([\d./-]+)")
ORDER_NUMBER_PATTERN = re.compile(r"(\d{5,})\s*$")
BUYER_PATTERN = re.compile(r"Comprador:\s*(.+)$")
PAYMENT_PATTERN = re.compile(r"Cond\.\s*Pag\.\s*:\s*(.+)$")
UNIT_DELIVERY_PATTERN = re.compile(r"^Unidade:\s*(.+?)(?:\s+Cep:.*)?$")
DELIVERY_ADDRESS_PATTERN = re.compile(r"^Endere[cç]o Ent:\s*(.+)$", re.IGNORECASE)
DELIVERY_CITY_PATTERN = re.compile(r"^Cidade:\s*(.+?)\s+UF:\s*([A-Za-z]{2})$", re.IGNORECASE)
INVOICE_CNPJ_PATTERN = re.compile(r"^Faturamento:.*?CNPJ:\s*([\d./-]+)")
TOTAL_UNIDADE_PATTERN = re.compile(r"^Total Unidade:\s*(.+)$", re.IGNORECASE)
TOTAL_FORNECEDOR_PATTERN = re.compile(r"^Total Fornecedor:\s*(.+)$", re.IGNORECASE)

PACKAGING_LABELS = {
    "UNIDADE",
    "QUILOGRAMA",
    "LITRO",
    "LITROS",
    "PACOTE",
    "CAIXA",
    "FARDO",
    "BANDEJA",
    "SACO",
}


def parse_ordem_compra(texto: str) -> dict[str, Any]:
    """Interpreta o texto de uma OC e devolve a primeira ordem em formato de dicionario."""

    ordens = parse_ordens_compra(texto)
    if not ordens:
        raise ValueError("Nenhuma ordem de compra foi identificada no texto informado.")
    return ordens[0]


def parse_ordens_compra(texto: str) -> list[dict[str, Any]]:
    """Interpreta o texto de uma ou mais OCs e devolve a lista de ordens encontradas."""

    ordens = _parse_ordens_compra_internal(texto)
    return [_strip_private_fields(ordem) for ordem in ordens]


def _parse_ordens_compra_internal(texto: str) -> list[dict[str, Any]]:
    """Interpreta o texto de uma ou mais OCs e preserva metadados internos."""

    if "ITEM|" in texto.upper():
        return [_parse_simple_order_dict(texto)]

    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    blocos = _split_order_blocks(linhas)
    if not blocos:
        return []

    ordens: list[dict[str, Any]] = []
    for bloco in blocos:
        ordem = _parse_real_order_block(bloco)
        if ordem["itens"]:
            ordens.append(ordem)

    return ordens


def parse_purchase_order_text(raw_text: str) -> PurchaseOrder:
    """Wrapper de compatibilidade que devolve a primeira ordem como dataclass."""

    ordens = _parse_ordens_compra_internal(raw_text)
    if not ordens:
        raise ValueError("Nenhuma ordem de compra foi identificada no texto informado.")
    return _dict_to_purchase_order(ordens[0])


def parse_purchase_orders_text(raw_text: str) -> list[PurchaseOrder]:
    """Wrapper de compatibilidade que devolve todas as ordens como dataclasses."""

    return [_dict_to_purchase_order(ordem) for ordem in _parse_ordens_compra_internal(raw_text)]


def replace_items(order: PurchaseOrder, items: Iterable[PurchaseOrderItem]) -> PurchaseOrder:
    """Retorna uma nova ordem mantendo o cabecalho e substituindo os itens."""

    return replace(order, itens=list(items))


def _parse_real_order_block(linhas: list[str]) -> dict[str, Any]:
    """Converte um bloco do PDF real em dicionario estruturado."""

    cabecalho = {
        "fornecedor": _extract_supplier(linhas),
        "cnpj_fornecedor": _extract_main_cnpj(linhas),
        "numero_oc": _extract_order_number(linhas),
        "comprador": _extract_buyer(linhas),
        "condicao_pagamento": _extract_payment_condition(linhas),
        "cnpj_faturamento": _extract_invoice_cnpj(linhas),
        "unidade_entrega": _extract_delivery_unit(linhas),
        "endereco_entrega": _extract_delivery_address(linhas),
        "cidade_entrega": _extract_delivery_city(linhas),
        "uf_entrega": _extract_delivery_uf(linhas),
    }

    itens = _extract_items(linhas)
    totais = {
        "total_unidade": _extract_total(linhas, TOTAL_UNIDADE_PATTERN),
        "total_fornecedor": _extract_total(linhas, TOTAL_FORNECEDOR_PATTERN),
    }

    if not cabecalho["numero_oc"] and itens:
        cabecalho["numero_oc"] = itens[0]["numero_oc"]

    return {
        "cabecalho": cabecalho,
        "itens": itens,
        "totais": totais,
    }


def _parse_simple_order_dict(texto: str) -> dict[str, Any]:
    """Mantem compatibilidade com o formato simplificado usado nos testes iniciais."""

    cabecalho = {
        "fornecedor": "",
        "cnpj_fornecedor": "",
        "numero_oc": "",
        "comprador": "",
        "condicao_pagamento": "",
        "cnpj_faturamento": "",
        "unidade_entrega": "",
        "endereco_entrega": "",
        "cidade_entrega": "",
        "uf_entrega": "",
    }
    itens: list[dict[str, Any]] = []
    data_entrega = ""

    for line_number, raw_line in enumerate(texto.splitlines(), start=1):
        linha = raw_line.strip()
        if not linha:
            continue

        if ":" in linha and not linha.upper().startswith("ITEM|"):
            key, value = linha.split(":", maxsplit=1)
            normalized_key = key.strip().lower().replace(" ", "_")
            target_key = HEADER_ALIASES.get(normalized_key)
            if target_key == "pedido":
                cabecalho["numero_oc"] = value.strip()
            elif target_key == "fornecedor":
                cabecalho["fornecedor"] = value.strip()
            elif target_key == "cnpj":
                cabecalho["cnpj_fornecedor"] = value.strip()
            elif target_key == "data_entrega":
                data_entrega = value.strip()
            continue

        if linha.upper().startswith("ITEM|"):
            itens.append(
                _parse_simple_item_line(
                    line_number,
                    linha,
                    cabecalho["numero_oc"],
                    data_entrega,
                )
            )

    if data_entrega:
        for item in itens:
            item["data_entrega"] = item["data_entrega"] or data_entrega

    return {
        "cabecalho": cabecalho,
        "itens": itens,
        "totais": {
            "total_unidade": 0.0,
            "total_fornecedor": 0.0,
        },
    }


def _split_order_blocks(linhas: list[str]) -> list[list[str]]:
    """Separa o texto em blocos para suportar varias OCs dentro do mesmo PDF."""

    blocos: list[list[str]] = []
    bloco_atual: list[str] = []

    for linha in linhas:
        if ORDER_START_PATTERN.match(linha) and bloco_atual:
            blocos.append(bloco_atual)
            bloco_atual = [linha]
            continue

        if ORDER_START_PATTERN.match(linha):
            bloco_atual = [linha]
            continue

        if bloco_atual:
            bloco_atual.append(linha)
            if ORDER_END_PATTERN.match(linha):
                blocos.append(bloco_atual)
                bloco_atual = []

    if bloco_atual:
        blocos.append(bloco_atual)

    return blocos


def _extract_items(linhas: list[str]) -> list[dict[str, Any]]:
    """Extrai a lista de itens da secao tabular da OC."""

    linhas_itens = _extract_item_lines(linhas)
    itens: list[dict[str, Any]] = []
    linhas_quebradas: list[str] = []

    for line_number, linha in linhas_itens:
        match = REAL_ITEM_PATTERN.match(linha)
        if not match:
            linhas_quebradas.append(linha)
            continue

        descricao, embalagem = _build_item_description(
            linhas_quebradas,
            match.group("descricao_base"),
        )
        qtde_token = match.group("qtde")
        itens.append(
            {
                "data_entrega": match.group("data"),
                "sequencia": int(match.group("sequencia")),
                "numero_oc": match.group("numero_oc"),
                "item_pdf": descricao,
                "marca": "",
                "embalagem": embalagem,
                "qtde_emb": _to_float(match.group("qtde_emb")),
                "qtde": _to_float(_extract_quantity_number(qtde_token)),
                "unidade": _extract_quantity_unit(qtde_token),
                "valor_unitario": _to_float(match.group("valor_unitario")),
                "valor_total": _to_float(match.group("valor_total")),
                "_line_number": line_number,
            }
        )
        linhas_quebradas = []

    return itens


def _extract_item_lines(linhas: list[str]) -> list[tuple[int, str]]:
    """Retorna apenas as linhas da secao de itens da ordem."""

    collecting = False
    resultado: list[tuple[int, str]] = []

    for line_number, linha in enumerate(linhas, start=1):
        if SECTION_HEADER_PATTERN.search(linha):
            collecting = True
            continue

        if not collecting:
            continue

        if linha.startswith("Total Unidade:") or linha.startswith("OBS:") or linha.startswith("Total Fornecedor:"):
            break

        resultado.append((line_number, linha))

    return resultado


def _build_item_description(continuation_lines: list[str], descricao_base: str) -> tuple[str, str]:
    """Reconstroi descricoes quebradas e separa a embalagem quando possivel."""

    partes = [parte.strip() for parte in continuation_lines if parte.strip()]
    partes.append(descricao_base.strip())
    descricao_completa = " ".join(partes)
    descricao_completa = re.sub(r"\s+", " ", descricao_completa).strip()

    tokens = descricao_completa.split()
    embalagem = ""
    if tokens and tokens[-1].upper() in PACKAGING_LABELS:
        embalagem = tokens[-1]
        tokens = tokens[:-1]

    return " ".join(tokens).strip(), embalagem


def _extract_supplier(linhas: list[str]) -> str:
    """Extrai o nome do fornecedor do cabecalho."""

    for linha in linhas[:5]:
        match = SUPPLIER_PATTERN.match(linha)
        if match:
            return match.group("fornecedor").strip()

    primeira_linha = linhas[0] if linhas else ""
    if primeira_linha.startswith("Fornecedor:"):
        valor = primeira_linha.split("Fornecedor:", maxsplit=1)[1].strip()
        valor = re.sub(r"\s+N\S*\s*OC\s*$", "", valor).strip()
        return valor

    return ""


def _extract_main_cnpj(linhas: list[str]) -> str:
    """Extrai o CNPJ principal do fornecedor."""

    for linha in linhas[:10]:
        match = CNPJ_PATTERN.search(linha)
        if match:
            return match.group(1)
    return ""


def _extract_order_number(linhas: list[str]) -> str:
    """Extrai o numero da OC do cabecalho do bloco."""

    for linha in linhas[:6]:
        if "Vendedor:" in linha:
            match = ORDER_NUMBER_PATTERN.search(linha)
            if match:
                return match.group(1)
    return ""


def _extract_buyer(linhas: list[str]) -> str:
    """Extrai o nome do comprador."""

    for linha in linhas[:8]:
        match = BUYER_PATTERN.search(linha)
        if match:
            return match.group(1).strip()
    return ""


def _extract_payment_condition(linhas: list[str]) -> str:
    """Extrai a condicao de pagamento."""

    for linha in linhas[:10]:
        match = PAYMENT_PATTERN.search(linha)
        if match:
            return match.group(1).strip()
    return ""


def _extract_invoice_cnpj(linhas: list[str]) -> str:
    """Extrai o CNPJ do faturamento."""

    for linha in linhas:
        match = INVOICE_CNPJ_PATTERN.search(linha)
        if match:
            return match.group(1)
    return ""


def _extract_delivery_unit(linhas: list[str]) -> str:
    """Extrai a unidade de entrega."""

    for linha in linhas:
        match = UNIT_DELIVERY_PATTERN.match(linha)
        if match:
            return match.group(1).strip()
    return ""


def _extract_delivery_address(linhas: list[str]) -> str:
    """Extrai o endereco de entrega."""

    for linha in linhas:
        match = DELIVERY_ADDRESS_PATTERN.match(linha)
        if match:
            return match.group(1).strip()
    return ""


def _extract_delivery_city(linhas: list[str]) -> str:
    """Extrai a cidade de entrega."""

    for linha in linhas:
        match = DELIVERY_CITY_PATTERN.match(linha)
        if match:
            return match.group(1).strip()
    return ""


def _extract_delivery_uf(linhas: list[str]) -> str:
    """Extrai a UF de entrega."""

    for linha in linhas:
        match = DELIVERY_CITY_PATTERN.match(linha)
        if match:
            return match.group(2).strip()
    return ""


def _extract_total(linhas: list[str], pattern: re.Pattern[str]) -> float:
    """Extrai um total monetario do rodape da ordem."""

    for linha in linhas:
        match = pattern.match(linha)
        if match:
            return _to_float(match.group(1))
    return 0.0


def _parse_simple_item_line(
    line_number: int,
    linha: str,
    numero_oc: str,
    data_entrega: str,
) -> dict[str, Any]:
    """Converte uma linha `ITEM|...` para o payload padrao do parser."""

    partes = [parte.strip() for parte in linha.split("|")]
    if len(partes) != 6:
        raise ValueError(
            "Linha de item invalida. Formato esperado: "
            "ITEM|codigo|descricao|quantidade|unidade|preco"
        )

    _, codigo, descricao, quantidade, unidade, preco = partes
    return {
        "data_entrega": data_entrega,
        "sequencia": line_number,
        "numero_oc": numero_oc,
        "item_pdf": descricao,
        "marca": "",
        "embalagem": "",
        "qtde_emb": _to_float(quantidade),
        "qtde": _to_float(quantidade),
        "unidade": unidade,
        "valor_unitario": _to_float(preco),
        "valor_total": _to_float(preco) * _to_float(quantidade),
        "_codigo_original": codigo,
        "_line_number": line_number,
    }


def _strip_private_fields(ordem: dict[str, Any]) -> dict[str, Any]:
    """Remove metadados internos antes de expor o payload publico do parser."""

    itens_publicos: list[dict[str, Any]] = []
    for item in ordem["itens"]:
        itens_publicos.append(
            {
                key: value
                for key, value in item.items()
                if not key.startswith("_")
            }
        )

    return {
        "cabecalho": dict(ordem["cabecalho"]),
        "itens": itens_publicos,
        "totais": dict(ordem["totais"]),
    }


def _dict_to_purchase_order(ordem: dict[str, Any]) -> PurchaseOrder:
    """Converte o payload em dicionario para as dataclasses usadas pelo projeto."""

    cabecalho = ordem["cabecalho"]
    itens = ordem["itens"]

    order_items = [
        PurchaseOrderItem(
            line_number=int(item.get("_line_number", index)),
            codigo=str(item.get("_codigo_original", "")),
            descricao=str(item["item_pdf"]),
            quantidade=_to_decimal(str(item["qtde"])),
            unidade=str(item["unidade"]),
            preco_unitario=_to_decimal(str(item["valor_unitario"])),
            codigo_neogrid=None,
            data_entrega=str(item["data_entrega"]) or None,
        )
        for index, item in enumerate(itens, start=1)
    ]

    data_entrega = ""
    if itens:
        data_entrega = str(itens[0]["data_entrega"])

    return PurchaseOrder(
        pedido=str(cabecalho["numero_oc"]),
        fornecedor=str(cabecalho["fornecedor"]),
        cnpj=str(cabecalho["cnpj_fornecedor"]),
        data_entrega=data_entrega,
        itens=order_items,
    )


def _extract_quantity_number(value: str) -> str:
    """Extrai apenas a parte numerica de um token de quantidade com unidade."""

    match = re.match(r"(?P<number>\d[\d ]*,\d{2})", value)
    if not match:
        return value
    return match.group("number")


def _extract_quantity_unit(value: str) -> str:
    """Extrai a sigla da unidade de um token de quantidade."""

    match = re.search(r"([A-Z]{2,3})$", value)
    return match.group(1) if match else ""


def _to_decimal(value: str) -> Decimal:
    """Normaliza numeros com espacos, virgulas e pontos para Decimal."""

    normalized = str(value).replace(" ", "")
    normalized = normalized.replace(".", "").replace(",", ".") if "," in normalized else normalized
    return Decimal(normalized)


def _to_float(value: str) -> float:
    """Converte uma string numerica no formato local para float."""

    return float(_to_decimal(value))
