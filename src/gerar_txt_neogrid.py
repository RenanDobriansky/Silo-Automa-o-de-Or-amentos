"""Gera arquivos TXT no layout aceito pela importacao Syscomp."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from parser_oc import PurchaseOrder

ALLOWED_STATUSES = {"encontrado_exato", "encontrado_aproximado"}
DEFAULT_OUTPUT_ENCODING = os.getenv("AUTOMACAO_OC_TXT_ENCODING", "ascii")
SYS_COMP_RECORD_LENGTHS = {
    "019": 304,
    "024": 45,
    "040": 350,
    "090": 122,
}
UNIT_CODE_MAP = {
    "UN": "EA",
    "UND": "EA",
    "EA": "EA",
    "PCT": "EA",
    "PC": "EA",
    "KG": "KG",
    "KGM": "KG",
    "L": "LT",
    "LTR": "LT",
    "ML": "ML",
    "CX": "CX",
    "FD": "FD",
}
PACKAGING_CODE_MAP = {
    "CAIXA": "BX",
    "CX": "BX",
    "BOX": "BX",
    "PACOTE": "PC",
    "PCT": "PC",
    "FARDO": "FD",
    "SACO": "SC",
    "UNIDADE": "UN",
    "UN": "UN",
}
DATE_INPUT_FORMATS = (
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%Y%m%d",
)
DATETIME_INPUT_FORMATS = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y%m%d%H%M",
)
MISSING = object()


class NeoGridError(ValueError):
    """Classe base para erros de geracao do layout de importacao."""


class NeoGridMappingError(NeoGridError):
    """Indica ausencia de dados essenciais para montar o TXT aceito pela Syscomp."""


class NeoGridConformityError(NeoGridError):
    """Indica violacao estrutural do layout de importacao."""


class NeoGridEncodingError(NeoGridConformityError):
    """Indica incompatibilidade de caracteres com a codificacao do arquivo."""


@dataclass(frozen=True)
class FieldSpec:
    """Define um campo posicional do layout de importacao."""

    name: str
    start: int
    end: int
    formatter: str
    required: bool = False
    decimals: int = 0
    align: str = "left"
    pad: str = " "

    @property
    def width(self) -> int:
        """Retorna a largura total do campo."""

        return self.end - self.start + 1


@dataclass(frozen=True)
class RecordSpec:
    """Agrupa os campos de um registro fixo."""

    code: str
    length: int
    fields: tuple[FieldSpec, ...]


REGISTRO_019 = RecordSpec(
    code="019",
    length=SYS_COMP_RECORD_LENGTHS["019"],
    fields=(
        FieldSpec("tipo_registro", 0, 2, "text", True),
        FieldSpec("tipo_pedido", 5, 7, "code", True, align="right", pad="0"),
        FieldSpec("pedido_cliente", 8, 27, "text", True),
        FieldSpec("pedido_sistema", 28, 47, "text"),
        FieldSpec("data_emissao", 48, 59, "datetime", True),
        FieldSpec("data_lancamento", 60, 71, "datetime", True),
        FieldSpec("data_entrega", 72, 83, "datetime", True),
        FieldSpec("numero_contrato", 84, 98, "text"),
        FieldSpec("lista_preco", 99, 113, "text"),
        FieldSpec("gln_fornecedor", 114, 126, "code", align="right", pad="0"),
        FieldSpec("gln_comprador", 127, 139, "code", align="right", pad="0"),
        FieldSpec("gln_faturamento", 140, 152, "code", align="right", pad="0"),
        FieldSpec("gln_entrega", 153, 165, "code", align="right", pad="0"),
        FieldSpec("cnpj_empresa", 166, 179, "digits14"),
        FieldSpec("cnpj_cliente", 180, 193, "digits14"),
        FieldSpec("cnpj_faturamento", 194, 207, "digits14"),
        FieldSpec("reserva_cnpj_entrega", 208, 210, "text"),
        FieldSpec("cnpj_entrega", 211, 224, "digits14_zero_optional", align="right"),
        FieldSpec("transportadora", 225, 254, "text"),
        FieldSpec("tipo_frete", 255, 257, "text", True),
        FieldSpec("secao_pedido", 258, 260, "code", True, align="right", pad="0"),
        FieldSpec("observacao", 261, 299, "text"),
        FieldSpec("vendedor_codigo", 300, 303, "code", align="right", pad=" "),
    ),
)

REGISTRO_024 = RecordSpec(
    code="024",
    length=SYS_COMP_RECORD_LENGTHS["024"],
    fields=(
        FieldSpec("tipo_registro", 0, 2, "text", True),
        FieldSpec("condicao_pagamento_codigo", 3, 5, "text", True, align="right"),
        FieldSpec("referencia_data_codigo", 6, 8, "text", True, align="right"),
        FieldSpec("tipo_periodo_codigo", 9, 11, "text", True, align="right"),
        FieldSpec("numero_periodos", 12, 16, "code3", True, align="right", pad=" "),
        FieldSpec("data_vencimento", 17, 24, "date", True),
        FieldSpec("valor_a_pagar", 25, 39, "number", True, 2),
        FieldSpec("percentual_a_pagar", 40, 44, "number", True, 2),
    ),
)

REGISTRO_040 = RecordSpec(
    code="040",
    length=SYS_COMP_RECORD_LENGTHS["040"],
    fields=(
        FieldSpec("tipo_registro", 0, 2, "text", True),
        FieldSpec("sequencia_linha", 3, 6, "code", True, align="right", pad="0"),
        FieldSpec("numero_item", 7, 10, "code", True, align="right", pad="0"),
        FieldSpec("tipo_codigo_produto", 14, 16, "text", True),
        FieldSpec("codigo_produto", 17, 30, "text", True),
        FieldSpec("descricao_produto", 31, 70, "text", True),
        FieldSpec("referencia_produto", 71, 90, "text"),
        FieldSpec("unidade", 91, 93, "text", True),
        FieldSpec("unidades_por_embalagem", 94, 99, "code", True, align="right", pad="0"),
        FieldSpec("quantidade_pedida", 100, 114, "number", True, 3),
        FieldSpec("quantidade_bonificada", 115, 129, "number", True, 3),
        FieldSpec("quantidade_troca", 130, 143, "number", False, 3),
        FieldSpec("tipo_embalagem", 144, 146, "text"),
        FieldSpec("numero_embalagens", 147, 152, "code", align="right", pad="0"),
        FieldSpec("valor_bruto", 153, 167, "number", True, 3),
        FieldSpec("valor_liquido", 168, 182, "number", True, 3),
        FieldSpec("preco_bruto", 183, 197, "number", True, 3),
        FieldSpec("preco_liquido", 198, 212, "number", True, 3),
        FieldSpec("base_preco", 213, 216, "code", align="right", pad="0"),
        FieldSpec("unidade_base_preco", 217, 218, "text"),
        FieldSpec("reserva_pos_unidade_base", 219, 219, "text"),
        FieldSpec("desconto_unitario", 220, 233, "number", False, 3),
        FieldSpec("percentual_desconto", 234, 238, "number", False, 2),
        FieldSpec("ipi_unitario", 239, 253, "number", False, 3),
        FieldSpec("aliquota_ipi", 254, 258, "number", False, 2),
        FieldSpec("despesa_tributada", 259, 273, "number", False, 3),
        FieldSpec("despesa_nao_tributada", 274, 288, "number", False, 3),
        FieldSpec("encargo_frete", 289, 303, "number", False, 3),
        FieldSpec("valor_pauta", 304, 310, "number", False, 2),
        FieldSpec("codigo_rms", 311, 319, "code", align="right", pad="0"),
        FieldSpec("codigo_ncm", 320, 329, "text", True),
        FieldSpec("vendedor_codigo", 330, 334, "code", align="right", pad="0"),
        FieldSpec("campo_final", 335, 349, "text"),
    ),
)

REGISTRO_090 = RecordSpec(
    code="090",
    length=SYS_COMP_RECORD_LENGTHS["090"],
    fields=(
        FieldSpec("tipo_registro", 0, 2, "text", True),
        FieldSpec("valor_produtos", 3, 17, "number", True, 3),
        FieldSpec("desconto_itens", 18, 32, "number", False, 3),
        FieldSpec("valor_icms", 33, 47, "number", False, 3),
        FieldSpec("valor_icms_st", 48, 62, "number", False, 3),
        FieldSpec("valor_fcp_st", 63, 77, "number", False, 3),
        FieldSpec("desconto", 78, 92, "number", False, 3),
        FieldSpec("acrescimo_frete", 93, 107, "number", False, 3),
        FieldSpec("valor_pedido", 108, 121, "number", True, 2),
    ),
)


def formatar_texto(
    valor: Any,
    tamanho: int,
    *,
    align: str = "left",
    pad: str = " ",
    encoding: str = DEFAULT_OUTPUT_ENCODING,
) -> str:
    """Formata um campo textual de largura fixa."""

    texto_original = "" if valor is None else str(valor)
    texto = _normalizar_texto_ascii(texto_original)
    if not texto and texto_original.strip():
        raise NeoGridEncodingError(
            "Campo textual nao possui caracteres compativeis com a codificacao do arquivo: "
            f"{texto_original!r}"
        )
    _validar_caracteres(texto, encoding=encoding)
    if len(texto) > tamanho:
        raise NeoGridConformityError(
            f"Campo textual excede o tamanho {tamanho}: {texto!r}"
        )
    if align == "right":
        return texto.rjust(tamanho, pad)
    return texto.ljust(tamanho, pad)


def formatar_numero(
    valor: Any,
    tamanho: int,
    decimais: int = 0,
    *,
    align: str = "right",
    pad: str = "0",
) -> str:
    """Formata um numero sem separador decimal em largura fixa."""

    numero = _decimal_or_zero(valor)
    fator = Decimal(10) ** decimais
    inteiro = int((numero * fator).quantize(Decimal("1")))
    texto = str(inteiro)
    if len(texto) > tamanho:
        raise NeoGridConformityError(
            f"Campo numerico excede o tamanho {tamanho}: {numero}"
        )
    if align == "left":
        return texto.ljust(tamanho, pad)
    return texto.rjust(tamanho, pad)


def formatar_data(data: str, formato_saida: str = "%Y%m%d") -> str:
    """Converte uma data para o formato numerico usado no arquivo."""

    if not data:
        raise NeoGridMappingError("Data obrigatoria nao informada.")
    if _parece_formato_final(data, formato_saida):
        return data

    for formato in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(str(data), formato).strftime(formato_saida)
        except ValueError:
            continue

    raise NeoGridConformityError(f"Data invalida: {data!r}")


def formatar_data_hora(valor: str, formato_saida: str = "%Y%m%d%H%M") -> str:
    """Converte uma data/hora para o formato numerico usado no arquivo."""

    if not valor:
        raise NeoGridMappingError("Data/hora obrigatoria nao informada.")
    if _parece_formato_final(valor, formato_saida):
        return valor

    for formato in DATETIME_INPUT_FORMATS:
        try:
            return datetime.strptime(str(valor), formato).strftime(formato_saida)
        except ValueError:
            continue

    for formato in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(str(valor), formato).strftime(formato_saida)
        except ValueError:
            continue

    raise NeoGridConformityError(f"Data/hora invalida: {valor!r}")


def somente_numeros(valor: Any) -> str:
    """Remove qualquer caractere que nao seja numero."""

    return "".join(char for char in str(valor or "") if char.isdigit())


def gerar_registro_019(cabecalho: dict[str, Any]) -> str:
    """Gera o cabecalho no layout aceito pela Syscomp."""

    return _build_record(REGISTRO_019, cabecalho)


def gerar_registro_024(pagamento: dict[str, Any]) -> str:
    """Gera o registro de pagamento."""

    return _build_record(REGISTRO_024, pagamento)


def gerar_registro_040(item_convertido: dict[str, Any]) -> str:
    """Gera o registro de item."""

    return _build_record(REGISTRO_040, item_convertido)


def gerar_registro_090(sumario: dict[str, Any]) -> str:
    """Gera o sumario final do pedido."""

    return _build_record(REGISTRO_090, sumario)


def gerar_txt_neogrid(
    dados_oc: dict[str, Any],
    relatorio_conversao: pd.DataFrame,
    caminho_saida: str | Path,
) -> Path:
    """Gera o TXT aceito pela importacao Syscomp."""

    if relatorio_conversao.empty:
        raise NeoGridMappingError("Nao ha itens no relatorio de conversao para gerar o TXT.")

    statuses = set(relatorio_conversao["status"].dropna().astype(str))
    if not statuses.issubset(ALLOWED_STATUSES):
        raise NeoGridMappingError(
            "O TXT so pode ser gerado quando todos os itens estiverem com status "
            "'encontrado_exato' ou 'encontrado_aproximado'."
        )

    pedido = mapear_pedido_para_syscomp(dados_oc, relatorio_conversao)
    linhas = [gerar_registro_019(pedido["registro_019"])]
    linhas.extend(gerar_registro_024(item) for item in pedido["registros_024"])
    linhas.extend(gerar_registro_040(item) for item in pedido["registros_040"])
    linhas.append(gerar_registro_090(pedido["registro_090"]))
    _validar_linhas_geradas(linhas)

    numero_oc = str(pedido["registro_019"]["pedido_cliente"]).strip()
    output_dir = Path(caminho_saida)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"OC_{numero_oc}.txt"
    output_path.write_bytes(("\r\n".join(linhas) + "\r\n").encode(DEFAULT_OUTPUT_ENCODING))
    return output_path


def mapear_pedido_para_syscomp(
    dados_oc: dict[str, Any],
    relatorio_conversao: pd.DataFrame,
) -> dict[str, Any]:
    """Converte o modelo interno do projeto para o layout aceito pela Syscomp."""

    registro_019 = _build_registro_019_payload(dados_oc)
    registros_024 = _build_registros_024_payload(dados_oc)
    registros_040 = _build_registros_040_payload(dados_oc, relatorio_conversao, registro_019)
    registro_090 = _build_registro_090_payload(dados_oc, registros_040)
    return {
        "registro_019": registro_019,
        "registros_024": registros_024,
        "registros_040": registros_040,
        "registro_090": registro_090,
    }


def generate_neogrid_txt(order: PurchaseOrder) -> str:
    """Wrapper legado para o fluxo antigo em memoria."""

    linhas = [
        "H|{pedido}|{fornecedor}|{cnpj}|{data_entrega}".format(
            pedido=order.pedido,
            fornecedor=order.fornecedor,
            cnpj=order.cnpj,
            data_entrega=order.data_entrega,
        )
    ]
    for sequence, item in enumerate(order.itens, start=1):
        linhas.append(
            "D|{sequence}|{codigo}|{descricao}|{quantidade}|{unidade}|{preco}".format(
                sequence=sequence,
                codigo=item.codigo_neogrid or item.codigo,
                descricao=item.descricao,
                quantidade=f"{item.quantidade:.2f}",
                unidade=item.unidade,
                preco=f"{item.preco_unitario:.2f}",
            )
        )
    return "\n".join(linhas) + "\n"


def _build_registro_019_payload(dados_oc: dict[str, Any]) -> dict[str, Any]:
    """Monta o payload do cabecalho 019."""

    cabecalho = dict(dados_oc.get("cabecalho", {}))
    syscomp = _merge_dicts(dados_oc.get("syscomp", {}), cabecalho.get("syscomp", {}))
    entrega = (
        syscomp.get("data_entrega")
        or cabecalho.get("data_entrega")
        or _first_item_value(dados_oc, "data_entrega")
    )
    emissao = syscomp.get("data_emissao") or cabecalho.get("data_emissao") or entrega
    lancamento = syscomp.get("data_lancamento") or cabecalho.get("data_lancamento") or entrega

    cnpj_cliente = _digits_or_blank(
        syscomp.get("cnpj_cliente")
        or cabecalho.get("cnpj_faturamento")
        or cabecalho.get("cnpj_local_entrega")
    )
    cnpj_empresa = _digits_or_blank(
        syscomp.get("cnpj_empresa") or cabecalho.get("cnpj_fornecedor")
    )

    return {
        "tipo_registro": "019",
        "tipo_pedido": syscomp.get("tipo_pedido", "001"),
        "pedido_cliente": syscomp.get("pedido_cliente") or cabecalho.get("numero_oc"),
        "pedido_sistema": syscomp.get("pedido_sistema", ""),
        "data_emissao": _to_syscomp_datetime(emissao),
        "data_lancamento": _to_syscomp_datetime(lancamento),
        "data_entrega": _to_syscomp_datetime(entrega),
        "numero_contrato": syscomp.get("numero_contrato", ""),
        "lista_preco": syscomp.get("lista_preco", ""),
        "gln_fornecedor": _digits_or_blank(syscomp.get("gln_fornecedor")),
        "gln_comprador": _digits_or_blank(syscomp.get("gln_comprador")),
        "gln_faturamento": _digits_or_blank(syscomp.get("gln_faturamento")),
        "gln_entrega": _digits_or_blank(syscomp.get("gln_entrega")),
        "cnpj_empresa": cnpj_empresa,
        "cnpj_cliente": cnpj_cliente,
        "cnpj_faturamento": _digits_or_blank(syscomp.get("cnpj_faturamento")) or cnpj_cliente,
        "reserva_cnpj_entrega": syscomp.get("reserva_cnpj_entrega", ""),
        "cnpj_entrega": _digits_or_blank(syscomp.get("cnpj_entrega")),
        "transportadora": syscomp.get("transportadora", ""),
        "tipo_frete": _normalize_freight_type(syscomp.get("tipo_frete") or syscomp.get("condicao_entrega") or "CIF"),
        "secao_pedido": syscomp.get("secao_pedido", "000"),
        "observacao": syscomp.get("observacao", ""),
        "vendedor_codigo": syscomp.get("vendedor_codigo", "0"),
    }


def _build_registros_024_payload(dados_oc: dict[str, Any]) -> list[dict[str, Any]]:
    """Monta os registros 024."""

    totais = dados_oc.get("totais", {})
    syscomp = dict(dados_oc.get("syscomp", {}) or {})
    pagamentos = list(syscomp.get("pagamentos", []) or [])
    if not pagamentos:
        data_vencimento = (
            syscomp.get("data_vencimento")
            or cabecalho_valor(dados_oc, "data_vencimento")
            or cabecalho_valor(dados_oc, "data_entrega")
            or _first_item_value(dados_oc, "data_entrega")
        )
        pagamentos = [
            {
                "condicao_pagamento_codigo": syscomp.get("condicao_pagamento_codigo", "5"),
                "referencia_data_codigo": syscomp.get("referencia_data_codigo", "1"),
                "tipo_periodo_codigo": syscomp.get("tipo_periodo_codigo", "D"),
                "numero_periodos": syscomp.get("numero_periodos", 0),
                "data_vencimento": data_vencimento,
                "valor_a_pagar": totais.get("total_fornecedor", 0),
                "percentual_a_pagar": syscomp.get("percentual_a_pagar", 100),
            }
        ]

    registros: list[dict[str, Any]] = []
    for pagamento in pagamentos:
        registros.append(
            {
                "tipo_registro": "024",
                "condicao_pagamento_codigo": pagamento.get("condicao_pagamento_codigo", "5"),
                "referencia_data_codigo": pagamento.get("referencia_data_codigo", "1"),
                "tipo_periodo_codigo": pagamento.get("tipo_periodo_codigo", "D"),
                "numero_periodos": f"{int(pagamento.get('numero_periodos', 0) or 0):03d}",
                "data_vencimento": _to_syscomp_date(pagamento.get("data_vencimento")),
                "valor_a_pagar": pagamento.get("valor_a_pagar", totais.get("total_fornecedor", 0)),
                "percentual_a_pagar": pagamento.get("percentual_a_pagar", 100),
            }
        )
    return registros


def _build_registros_040_payload(
    dados_oc: dict[str, Any],
    relatorio_conversao: pd.DataFrame,
    registro_019: dict[str, Any],
) -> list[dict[str, Any]]:
    """Monta os registros 040."""

    relatorio_por_sequencia = {
        int(row["sequencia"]): row for row in relatorio_conversao.to_dict(orient="records")
    }
    syscomp = dict(dados_oc.get("syscomp", {}) or {})
    vendedor_codigo = syscomp.get("vendedor_codigo", "0")
    tipo_pedido = str(registro_019.get("tipo_pedido", "001"))

    registros: list[dict[str, Any]] = []
    for item in dados_oc.get("itens", []):
        sequencia = int(item.get("sequencia", 0) or 0)
        relatorio_item = relatorio_por_sequencia.get(sequencia)
        if relatorio_item is None:
            raise NeoGridMappingError(
                f"Item de sequencia {sequencia} nao encontrado no relatorio de conversao."
            )

        item_syscomp = _merge_dicts(item.get("syscomp", {}), relatorio_item.get("syscomp", {}))
        quantidade = _decimal_or_zero(relatorio_item.get("quantidade", 0))
        valor_unitario = _decimal_or_zero(relatorio_item.get("valor_unitario", 0))
        valor_total = _decimal_or_zero(relatorio_item.get("valor_total", 0))
        codigo_produto = (
            item_syscomp.get("codigo_produto")
            or item_syscomp.get("ean")
            or item_syscomp.get("codigo_barras")
            or relatorio_item.get("codigo_silo")
        )
        if not codigo_produto:
            raise NeoGridMappingError(
                f"Item {sequencia} sem codigo de produto para o registro 040."
            )

        tipo_codigo = item_syscomp.get("tipo_codigo_produto") or _infer_tipo_codigo(codigo_produto)
        unidades_emb = item_syscomp.get("unidades_por_embalagem", item.get("qtde_emb", 0))
        quantidade_bonificada = quantidade if tipo_pedido == "002" else item_syscomp.get("quantidade_bonificada", 0)
        quantidade_pedida = 0 if tipo_pedido == "002" else quantidade
        unidade = item_syscomp.get("unidade") or _map_unidade_syscomp(relatorio_item.get("unidade") or item.get("unidade"))
        unidade_base = item_syscomp.get("unidade_base_preco") or unidade[:2]

        registros.append(
            {
                "tipo_registro": "040",
                "sequencia_linha": item_syscomp.get("sequencia_linha", sequencia * 10),
                "numero_item": item_syscomp.get("numero_item", 0),
                "tipo_codigo_produto": tipo_codigo,
                "codigo_produto": codigo_produto,
                "descricao_produto": item_syscomp.get("descricao_produto") or relatorio_item.get("descricao_erp") or item.get("item_pdf", ""),
                "referencia_produto": item_syscomp.get("referencia_produto", ""),
                "unidade": unidade,
                "unidades_por_embalagem": item_syscomp.get("unidades_por_embalagem", unidades_emb),
                "quantidade_pedida": quantidade_pedida,
                "quantidade_bonificada": quantidade_bonificada,
                "quantidade_troca": item_syscomp.get("quantidade_troca", 0),
                "tipo_embalagem": item_syscomp.get("tipo_embalagem") or _map_tipo_embalagem(item.get("embalagem", "")),
                "numero_embalagens": item_syscomp.get("numero_embalagens", 0),
                "valor_bruto": item_syscomp.get("valor_bruto", valor_total),
                "valor_liquido": item_syscomp.get("valor_liquido", valor_total),
                "preco_bruto": item_syscomp.get("preco_bruto", valor_unitario),
                "preco_liquido": item_syscomp.get("preco_liquido", valor_unitario),
                "base_preco": item_syscomp.get("base_preco", 0),
                "unidade_base_preco": unidade_base,
                "reserva_pos_unidade_base": item_syscomp.get("reserva_pos_unidade_base", ""),
                "desconto_unitario": item_syscomp.get("desconto_unitario", 0),
                "percentual_desconto": item_syscomp.get("percentual_desconto", 0),
                "ipi_unitario": item_syscomp.get("ipi_unitario", 0),
                "aliquota_ipi": item_syscomp.get("aliquota_ipi", 0),
                "despesa_tributada": item_syscomp.get("despesa_tributada", 0),
                "despesa_nao_tributada": item_syscomp.get("despesa_nao_tributada", 0),
                "encargo_frete": item_syscomp.get("encargo_frete", 0),
                "valor_pauta": item_syscomp.get("valor_pauta", 0),
                "codigo_rms": item_syscomp.get("codigo_rms", relatorio_item.get("codigo_silo", "0")),
                "codigo_ncm": item_syscomp.get("codigo_ncm", ""),
                "vendedor_codigo": item_syscomp.get("vendedor_codigo", vendedor_codigo),
                "campo_final": item_syscomp.get("campo_final", "0"),
            }
        )
    return registros


def _build_registro_090_payload(
    dados_oc: dict[str, Any],
    registros_040: list[dict[str, Any]],
) -> dict[str, Any]:
    """Monta o sumario 090."""

    totais = dict(dados_oc.get("totais", {}) or {})
    syscomp = dict(dados_oc.get("syscomp", {}) or {})
    sumario = dict(syscomp.get("sumario", {}) or {})

    valor_produtos = _decimal_or_zero(sumario.get("valor_produtos"))
    if valor_produtos == 0:
        valor_produtos = sum(_decimal_or_zero(item["valor_bruto"]) for item in registros_040)

    valor_pedido = _decimal_or_zero(sumario.get("valor_pedido"))
    if valor_pedido == 0:
        valor_pedido = _decimal_or_zero(totais.get("total_fornecedor", 0)) or valor_produtos

    return {
        "tipo_registro": "090",
        "valor_produtos": valor_produtos,
        "desconto_itens": sumario.get("desconto_itens", 0),
        "valor_icms": sumario.get("valor_icms", 0),
        "valor_icms_st": sumario.get("valor_icms_st", 0),
        "valor_fcp_st": sumario.get("valor_fcp_st", 0),
        "desconto": sumario.get("desconto", 0),
        "acrescimo_frete": sumario.get("acrescimo_frete", 0),
        "valor_pedido": valor_pedido,
    }


def _build_record(record_spec: RecordSpec, values: dict[str, Any]) -> str:
    """Monta uma linha fixa conforme o schema informado."""

    caracteres = [" "] * record_spec.length
    for field in record_spec.fields:
        raw_value = values.get(field.name, MISSING)
        texto = _format_field(field, raw_value)
        caracteres[field.start : field.end + 1] = list(texto)

    linha = "".join(caracteres)
    if len(linha) != record_spec.length:
        raise NeoGridConformityError(
            f"Registro {record_spec.code} gerado com tamanho invalido: {len(linha)}"
        )
    return linha


def _format_field(field: FieldSpec, raw_value: Any) -> str:
    """Formata um campo conforme o formatter definido no schema."""

    if raw_value is MISSING or raw_value is None:
        if field.required:
            raise NeoGridMappingError(f"Campo obrigatorio '{field.name}' ausente.")
        return " " * field.width

    if field.formatter == "text":
        if raw_value == "" and field.required:
            raise NeoGridMappingError(f"Campo obrigatorio '{field.name}' vazio.")
        return formatar_texto(
            raw_value,
            field.width,
            align=field.align,
            pad=field.pad,
        )

    if field.formatter == "code":
        return formatar_texto(
            somente_numeros(raw_value) if str(raw_value).isdigit() else raw_value,
            field.width,
            align=field.align,
            pad=field.pad,
        )

    if field.formatter == "code3":
        digits = somente_numeros(raw_value)
        if not digits and field.required:
            raise NeoGridMappingError(f"Campo obrigatorio '{field.name}' vazio.")
        return formatar_texto(
            digits.zfill(3),
            field.width,
            align=field.align,
            pad=field.pad,
        )

    if field.formatter == "digits14":
        digits = _digits_or_blank(raw_value)
        if not digits:
            raise NeoGridMappingError(f"Campo obrigatorio '{field.name}' vazio.")
        return formatar_texto(digits, field.width, align="right", pad="0")

    if field.formatter == "digits14_optional":
        digits = _digits_or_blank(raw_value)
        if not digits:
            return " " * field.width
        return formatar_texto(digits, field.width, align="right", pad="0")

    if field.formatter == "digits14_zero_optional":
        digits = _digits_or_blank(raw_value)
        if not digits:
            digits = "0" * field.width
        return formatar_texto(digits, field.width, align="right", pad="0")

    if field.formatter == "number":
        if raw_value == "" and field.required:
            raise NeoGridMappingError(f"Campo obrigatorio '{field.name}' vazio.")
        return formatar_numero(raw_value, field.width, field.decimals)

    if field.formatter == "date":
        return formatar_data(str(raw_value))

    if field.formatter == "datetime":
        return formatar_data_hora(str(raw_value))

    raise NeoGridConformityError(f"Formatter desconhecido: {field.formatter}")


def _validar_linhas_geradas(linhas: list[str]) -> None:
    """Confere prefixos e comprimentos antes da escrita final."""

    for index, linha in enumerate(linhas, start=1):
        prefixo = linha[:3]
        if prefixo not in SYS_COMP_RECORD_LENGTHS:
            raise NeoGridConformityError(
                f"Linha {index} possui registro invalido: {prefixo}."
            )
        tamanho_esperado = SYS_COMP_RECORD_LENGTHS[prefixo]
        if len(linha) != tamanho_esperado:
            raise NeoGridConformityError(
                f"Linha {index} do registro {prefixo} possui tamanho {len(linha)} "
                f"mas o esperado e {tamanho_esperado}."
            )


def _map_unidade_syscomp(unidade: Any) -> str:
    """Traduz a unidade interna para o codigo esperado pela Syscomp."""

    normalized = str(unidade or "").strip().upper()
    if not normalized:
        return "EA"
    return UNIT_CODE_MAP.get(normalized, normalized[:2])


def _map_tipo_embalagem(embalagem: Any) -> str:
    """Traduz o tipo de embalagem para o codigo usado no TXT."""

    normalized = str(embalagem or "").strip().upper()
    if not normalized:
        return ""
    return PACKAGING_CODE_MAP.get(normalized, normalized[:3])


def _infer_tipo_codigo(codigo_produto: Any) -> str:
    """Infere o qualificador do codigo do produto."""

    digits = somente_numeros(codigo_produto)
    if len(digits) in {8, 12, 13, 14}:
        return "EN"
    return "PRD"


def _normalize_freight_type(valor: Any) -> str:
    """Normaliza o tipo de frete para CIF/FOB."""

    text = str(valor or "").strip().upper()
    if "FOB" in text:
        return "FOB"
    if "CIF" in text or not text:
        return "CIF"
    return text[:3]


def _to_syscomp_datetime(valor: Any) -> str:
    """Converte data ou data/hora para AAAAMMDDHHMM."""

    text = str(valor or "").strip()
    if not text:
        raise NeoGridMappingError("Data/hora obrigatoria nao informada.")
    if _parece_formato_final(text, "%Y%m%d%H%M"):
        return text

    for formato in DATETIME_INPUT_FORMATS:
        try:
            return datetime.strptime(text, formato).strftime("%Y%m%d%H%M")
        except ValueError:
            continue

    for formato in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text, formato).strftime("%Y%m%d0000")
        except ValueError:
            continue

    raise NeoGridConformityError(f"Data/hora invalida: {text!r}")


def _to_syscomp_date(valor: Any) -> str:
    """Converte data para AAAAMMDD."""

    text = str(valor or "").strip()
    if not text:
        raise NeoGridMappingError("Data obrigatoria nao informada.")
    if _parece_formato_final(text, "%Y%m%d"):
        return text
    for formato in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text, formato).strftime("%Y%m%d")
        except ValueError:
            continue
    raise NeoGridConformityError(f"Data invalida: {text!r}")


def _first_item_value(dados_oc: dict[str, Any], field_name: str) -> str:
    """Retorna o primeiro valor encontrado nos itens para o campo informado."""

    for item in dados_oc.get("itens", []):
        valor = item.get(field_name)
        if valor not in (None, ""):
            return str(valor)
    return ""


def cabecalho_valor(dados_oc: dict[str, Any], field_name: str) -> str:
    """Le um valor do cabecalho sem levantar excecao."""

    return str(dados_oc.get("cabecalho", {}).get(field_name, "") or "")


def _merge_dicts(*values: Any) -> dict[str, Any]:
    """Mescla apenas dicionarios validos em um payload unico."""

    merged: dict[str, Any] = {}
    for value in values:
        if isinstance(value, dict):
            merged.update(value)
    return merged


def _normalizar_texto_ascii(valor: str) -> str:
    """Converte texto livre para uma representacao ASCII segura para o TXT."""

    texto = valor.replace("\r", " ").replace("\n", " ")
    texto = texto.translate(
        str.maketrans(
            {
                "\u2013": "-",
                "\u2014": "-",
                "\u2018": "'",
                "\u2019": "'",
                "\u201c": '"',
                "\u201d": '"',
                "\u00aa": "a",
                "\u00ba": "o",
            }
        )
    )
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = "".join(char if ord(char) < 128 else " " for char in texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _validar_caracteres(valor: str, *, encoding: str) -> None:
    """Garante que o texto pode ser gravado na codificacao final."""

    try:
        valor.encode(encoding, errors="strict")
    except UnicodeEncodeError as exc:
        raise NeoGridEncodingError(
            "Campo textual contem caracteres incompatíveis com a codificacao do arquivo: "
            f"{valor!r}"
        ) from exc


def _decimal_or_zero(valor: Any) -> Decimal:
    """Converte valores vazios para Decimal zero."""

    if valor in (None, ""):
        return Decimal("0")
    return Decimal(str(valor))


def _digits_or_blank(valor: Any) -> str:
    """Extrai apenas os digitos de um campo textual."""

    return somente_numeros(valor)


def _parece_formato_final(valor: str, formato_saida: str) -> bool:
    """Valida se a string ja esta no formato final esperado."""

    try:
        datetime.strptime(valor, formato_saida)
    except ValueError:
        return False
    return len(valor) == len(datetime.now().strftime(formato_saida))


REPORT_EXPORT_COLUMNS = [
    "numero_oc",
    "sequencia",
    "item_pdf",
    "item_encontrado_tabela",
    "codigo_silo",
    "descricao_erp",
    "quantidade",
    "unidade",
    "valor_unitario",
    "valor_total",
    "score",
    "status",
]
