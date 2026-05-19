"""Gera arquivos TXT em layout NeoGrid com registros 019, 024, 040 e 090."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from parser_oc import PurchaseOrder

RECORD_SIZE = 200
ALLOWED_STATUSES = {"encontrado_exato", "encontrado_aproximado"}


def formatar_texto(valor: Any, tamanho: int) -> str:
    """Converte um valor em texto fixo alinhado a esquerda."""

    texto = "" if valor is None else str(valor)
    texto = texto.replace("\r", " ").replace("\n", " ").strip()
    return texto[:tamanho].ljust(tamanho)


def formatar_numero(valor: Any, tamanho: int, decimais: int = 0) -> str:
    """Converte um numero para campo fixo sem separadores e preenchido com zeros."""

    numero = Decimal(str(valor or 0))
    fator = Decimal(10) ** decimais
    inteiro = int((numero * fator).quantize(Decimal("1")))
    return str(inteiro).zfill(tamanho)[-tamanho:]


def formatar_data(
    data: str,
    formato_origem: str = "%d/%m/%Y",
    formato_saida: str = "%Y%m%d",
) -> str:
    """Converte datas do formato origem para o formato de saida."""

    if not data:
        return "0" * len(datetime.now().strftime(formato_saida))
    return datetime.strptime(data, formato_origem).strftime(formato_saida)


def somente_numeros(valor: Any) -> str:
    """Remove qualquer caractere que nao seja numero."""

    return "".join(char for char in str(valor or "") if char.isdigit())


def gerar_registro_019(cabecalho: dict[str, Any]) -> str:
    """Gera o registro 019 com os campos principais do pedido.

    TODO: revisar ordem exata dos campos e larguras com o layout NeoGrid oficial.
    Campos ainda nao mapeados permanecem como espacos.
    """

    base = "".join(
        [
            "019",
            formatar_texto(cabecalho.get("numero_oc", ""), 20),
            formatar_texto(cabecalho.get("fornecedor", ""), 50),
            formatar_texto(somente_numeros(cabecalho.get("cnpj_fornecedor", "")), 14),
            formatar_data(cabecalho.get("data_entrega", "")),
            formatar_texto(cabecalho.get("unidade_entrega", ""), 50),
            formatar_texto(cabecalho.get("endereco_entrega", ""), 40),
            formatar_texto(cabecalho.get("cidade_entrega", ""), 25),
            formatar_texto(cabecalho.get("uf_entrega", ""), 2),
        ]
    )
    return _ajustar_tamanho_registro(base)


def gerar_registro_024(cabecalho: dict[str, Any]) -> str:
    """Gera o registro 024 com informacoes de pagamento.

    TODO: complementar dados financeiros e demais colunas exigidas pelo NeoGrid.
    """

    base = "".join(
        [
            "024",
            formatar_texto(cabecalho.get("condicao_pagamento", ""), 30),
            formatar_texto(cabecalho.get("comprador", ""), 40),
            formatar_texto(somente_numeros(cabecalho.get("cnpj_faturamento", "")), 14),
        ]
    )
    return _ajustar_tamanho_registro(base)


def gerar_registro_040(item_convertido: dict[str, Any]) -> str:
    """Gera o registro 040 para um item convertido.

    TODO: validar campos comerciais adicionais, NCM, embalagem oficial e impostos
    quando o layout NeoGrid completo estiver definido.
    """

    base = "".join(
        [
            "040",
            formatar_numero(item_convertido.get("sequencia", 0), 5),
            formatar_texto(item_convertido.get("codigo_silo", ""), 20),
            formatar_texto(item_convertido.get("descricao_erp", ""), 70),
            formatar_numero(item_convertido.get("quantidade", 0), 15, decimais=2),
            formatar_texto(item_convertido.get("unidade", ""), 3),
            formatar_numero(item_convertido.get("valor_unitario", 0), 15, decimais=2),
            formatar_numero(item_convertido.get("valor_total", 0), 15, decimais=2),
        ]
    )
    return _ajustar_tamanho_registro(base)


def gerar_registro_090(itens_convertidos: list[dict[str, Any]]) -> str:
    """Gera o registro 090 de sumario com total de itens e valor consolidado.

    TODO: complementar totais auxiliares assim que o layout oficial for validado.
    """

    total_itens = len(itens_convertidos)
    valor_total = sum(Decimal(str(item.get("valor_total", 0) or 0)) for item in itens_convertidos)
    base = "".join(
        [
            "090",
            formatar_numero(total_itens, 5),
            formatar_numero(valor_total, 18, decimais=2),
        ]
    )
    return _ajustar_tamanho_registro(base)


def gerar_txt_neogrid(
    dados_oc: dict[str, Any],
    relatorio_conversao: pd.DataFrame,
    caminho_saida: str | Path,
) -> Path:
    """Gera o TXT NeoGrid no disco quando todos os itens estao liberados."""

    if relatorio_conversao.empty:
        raise ValueError("Nao ha itens no relatorio de conversao para gerar o TXT.")

    statuses = set(relatorio_conversao["status"].dropna().astype(str))
    if not statuses.issubset(ALLOWED_STATUSES):
        raise ValueError(
            "O TXT so pode ser gerado quando todos os itens estiverem com status "
            "'encontrado_exato' ou 'encontrado_aproximado'."
        )

    cabecalho = dict(dados_oc.get("cabecalho", {}))
    numero_oc = str(cabecalho.get("numero_oc", "")).strip()
    if not numero_oc:
        raise ValueError("Numero da OC nao informado nos dados da ordem.")

    if not cabecalho.get("data_entrega") and dados_oc.get("itens"):
        cabecalho["data_entrega"] = dados_oc["itens"][0].get("data_entrega", "")

    itens_convertidos = relatorio_conversao[REPORT_EXPORT_COLUMNS].to_dict(orient="records")
    linhas = [
        gerar_registro_019(cabecalho),
        gerar_registro_024(cabecalho),
        *[gerar_registro_040(item) for item in itens_convertidos],
        gerar_registro_090(itens_convertidos),
    ]

    output_dir = Path(caminho_saida)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"OC_{numero_oc}.txt"
    output_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return output_path


def generate_neogrid_txt(order: PurchaseOrder) -> str:
    """Wrapper de compatibilidade para o fluxo antigo do projeto.

    Mantem um formato simples em memoria para nao quebrar o restante do codigo
    legado enquanto o pipeline completo para NeoGrid nao e integrado ponta a ponta.
    """

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


def _ajustar_tamanho_registro(valor: str) -> str:
    """Ajusta um registro para o tamanho fixo configurado."""

    return valor[:RECORD_SIZE].ljust(RECORD_SIZE)


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
