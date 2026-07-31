"""Testes da geracao do TXT aceito pela Syscomp."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gerar_txt_neogrid import (
    DEFAULT_OUTPUT_ENCODING,
    SYS_COMP_RECORD_LENGTHS,
    NeoGridConformityError,
    NeoGridMappingError,
    formatar_data,
    formatar_data_hora,
    formatar_numero,
    formatar_texto,
    gerar_registro_019,
    gerar_registro_024,
    gerar_registro_040,
    gerar_registro_090,
    gerar_txt_neogrid,
    somente_numeros,
)


def _build_dados_oc_syscomp() -> dict[str, object]:
    return {
        "cabecalho": {
            "numero_oc": "838271002",
            "cnpj_fornecedor": "77.383.479/0001-17",
            "cnpj_faturamento": "84.897.313/0008-50",
        },
        "itens": [
            {
                "data_entrega": "16/12/2025",
                "sequencia": 1,
                "numero_oc": "838271002",
                "item_pdf": "SALGADINHO DE BACON 300gr",
                "embalagem": "CAIXA",
                "qtde_emb": 10,
                "qtde": 40,
                "unidade": "PCT",
                "valor_unitario": 9.43,
                "valor_total": 377.20,
                "syscomp": {
                    "codigo_produto": "7896812200553",
                    "tipo_codigo_produto": "EN",
                    "descricao_produto": "SALGADINHO DE BACON 300gr",
                    "unidade": "EA",
                    "unidades_por_embalagem": 10,
                    "tipo_embalagem": "BX",
                    "base_preco": 0,
                    "unidade_base_preco": "EA",
                    "codigo_rms": "000000000",
                    "codigo_ncm": "19059090",
                    "vendedor_codigo": "170",
                    "campo_final": "005000000000000",
                },
            }
        ],
        "totais": {
            "total_unidade": 377.20,
            "total_fornecedor": 377.20,
        },
        "syscomp": {
            "tipo_pedido": "001",
            "data_emissao": "15/12/2025",
            "data_lancamento": "16/12/2025",
            "data_entrega": "16/12/2025",
            "cnpj_empresa": "77.383.479/0001-17",
            "cnpj_cliente": "84.897.313/0008-50",
            "cnpj_faturamento": "84.897.313/0008-50",
            "tipo_codigo_transportadora": "000",
            "tipo_frete": "CIF",
            "secao_pedido": "000",
            "vendedor_codigo": "170",
            "pagamentos": [
                {
                    "condicao_pagamento_codigo": "5",
                    "referencia_data_codigo": "1",
                    "tipo_periodo_codigo": "D",
                    "numero_periodos": 28,
                    "data_vencimento": "13/01/2026",
                    "valor_a_pagar": 377.20,
                    "percentual_a_pagar": 100,
                }
            ],
        },
    }


def _build_relatorio_syscomp() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "numero_oc": "838271002",
                "sequencia": 1,
                "item_pdf": "SALGADINHO DE BACON 300gr",
                "item_encontrado_tabela": "SALGADINHO DE BACON 300gr",
                "codigo_silo": "000000000",
                "descricao_erp": "SALGADINHO DE BACON 300gr",
                "quantidade": 40.0,
                "unidade": "PCT",
                "valor_unitario": 9.43,
                "valor_total": 377.20,
                "score": 100,
                "status": "encontrado_exato",
            }
        ]
    )


def test_funcoes_auxiliares_formatam_valores() -> None:
    assert formatar_texto("ABC", 5) == "ABC  "
    assert formatar_texto("ESTICÁVEL", 10) == "ESTICAVEL "
    assert formatar_numero(12.34, 8, decimais=2) == "00001234"
    assert formatar_data("23/04/2026") == "20260423"
    assert formatar_data_hora("23/04/2026") == "202604230000"
    assert somente_numeros("12.345.678/0001-90") == "12345678000190"


def test_gerar_registros_retorna_tamanhos_aceitos_pela_syscomp() -> None:
    registro_019 = gerar_registro_019(
        {
            "tipo_registro": "019",
            "tipo_pedido": "001",
            "pedido_cliente": "838271002",
            "pedido_sistema": "",
            "data_emissao": "202512150000",
            "data_lancamento": "202512160000",
            "data_entrega": "202512160000",
            "numero_contrato": "",
            "lista_preco": "",
            "gln_fornecedor": "",
            "gln_comprador": "",
            "gln_faturamento": "",
            "gln_entrega": "",
            "cnpj_empresa": "77383479000117",
            "cnpj_cliente": "84897313000850",
            "cnpj_faturamento": "84897313000850",
            "reserva_cnpj_entrega": "",
            "cnpj_entrega": "",
            "transportadora": "",
            "tipo_frete": "CIF",
            "secao_pedido": "000",
            "observacao": "",
            "vendedor_codigo": "170",
        }
    )
    registro_024 = gerar_registro_024(
        {
            "tipo_registro": "024",
            "condicao_pagamento_codigo": "5",
            "referencia_data_codigo": "1",
            "tipo_periodo_codigo": "D",
            "numero_periodos": 28,
            "data_vencimento": "20260113",
            "valor_a_pagar": 377.20,
            "percentual_a_pagar": 100,
        }
    )
    registro_040 = gerar_registro_040(
        {
            "tipo_registro": "040",
            "sequencia_linha": 10,
            "numero_item": 0,
            "tipo_codigo_produto": "EN",
            "codigo_produto": "7896812200553",
            "descricao_produto": "SALGADINHO DE BACON 300gr",
            "referencia_produto": "",
            "unidade": "EA",
            "unidades_por_embalagem": 10,
            "quantidade_pedida": 40,
            "quantidade_bonificada": 0,
            "quantidade_troca": 0,
            "tipo_embalagem": "BX",
            "numero_embalagens": 0,
            "valor_bruto": 377.20,
            "valor_liquido": 377.20,
            "preco_bruto": 9.43,
            "preco_liquido": 9.43,
            "base_preco": 0,
            "unidade_base_preco": "EA",
            "reserva_pos_unidade_base": "",
            "desconto_unitario": 0,
            "percentual_desconto": 0,
            "ipi_unitario": 0,
            "aliquota_ipi": 0,
            "despesa_tributada": 0,
            "despesa_nao_tributada": 0,
            "encargo_frete": 0,
            "valor_pauta": 0,
            "codigo_rms": "000000000",
            "codigo_ncm": "19059090",
            "vendedor_codigo": "170",
            "campo_final": "005000000000000",
        }
    )
    registro_090 = gerar_registro_090(
        {
            "tipo_registro": "090",
            "valor_produtos": 377.20,
            "desconto_itens": 0,
            "valor_icms": 0,
            "valor_icms_st": 0,
            "valor_fcp_st": 0,
            "desconto": 0,
            "acrescimo_frete": 0,
            "valor_pedido": 377.20,
        }
    )

    assert len(registro_019) == SYS_COMP_RECORD_LENGTHS["019"]
    assert len(registro_024) == SYS_COMP_RECORD_LENGTHS["024"]
    assert len(registro_040) == SYS_COMP_RECORD_LENGTHS["040"]
    assert len(registro_090) == SYS_COMP_RECORD_LENGTHS["090"]
    assert registro_019.startswith("019")
    assert registro_024.startswith("024")
    assert registro_040.startswith("040")
    assert registro_090.startswith("090")
    assert registro_019[255:258] == "CIF"
    assert registro_019[208:225] == "   00000000000000"
    assert registro_024[12:17] == "  028"
    assert registro_024[25:40] == "000000000037720"
    assert registro_040[17:31].strip() == "7896812200553"
    assert registro_040[100:115] == "000000000040000"
    assert registro_040[153:168] == "000000000377200"
    assert registro_040[183:198] == "000000000009430"
    assert registro_040[213:220] == "0000EA "
    assert registro_040[320:330] == "19059090  "
    assert registro_040[330:335] == "00170"
    assert registro_090[3:18] == "000000000377200"


def test_gerar_txt_neogrid_salva_arquivo_no_layout_syscomp(tmp_path: Path) -> None:
    dados_oc = _build_dados_oc_syscomp()
    relatorio = _build_relatorio_syscomp()

    caminho = gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    conteudo = caminho.read_text(encoding=DEFAULT_OUTPUT_ENCODING).splitlines()

    assert caminho.exists()
    assert caminho.name == "OC_838271002.txt"
    assert [linha[:3] for linha in conteudo] == ["019", "024", "040", "090"]
    assert len(conteudo[0]) == SYS_COMP_RECORD_LENGTHS["019"]
    assert len(conteudo[1]) == SYS_COMP_RECORD_LENGTHS["024"]
    assert len(conteudo[2]) == SYS_COMP_RECORD_LENGTHS["040"]
    assert len(conteudo[3]) == SYS_COMP_RECORD_LENGTHS["090"]


def test_gerar_txt_neogrid_bloqueia_status_revisar(tmp_path: Path) -> None:
    dados_oc = _build_dados_oc_syscomp()
    relatorio = _build_relatorio_syscomp()
    relatorio.loc[0, "status"] = "revisar"

    try:
        gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    except NeoGridMappingError as exc:
        assert "encontrado_exato" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado bloqueio para status revisar.")


def test_gerar_txt_neogrid_bloqueia_quando_falta_pedido_cliente(tmp_path: Path) -> None:
    dados_oc = _build_dados_oc_syscomp()
    relatorio = _build_relatorio_syscomp()
    dados_oc["cabecalho"]["numero_oc"] = ""
    dados_oc["syscomp"]["pedido_cliente"] = ""

    try:
        gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    except NeoGridMappingError as exc:
        assert "pedido_cliente" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado erro por falta do pedido cliente.")


def test_gerar_txt_neogrid_bloqueia_quando_falta_codigo_ncm(tmp_path: Path) -> None:
    dados_oc = _build_dados_oc_syscomp()
    relatorio = _build_relatorio_syscomp()
    dados_oc["itens"][0]["syscomp"]["codigo_ncm"] = ""

    try:
        gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    except NeoGridMappingError as exc:
        assert "codigo_ncm" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado erro por falta do NCM.")


def test_gerar_txt_neogrid_bloqueia_caractere_incompativel(tmp_path: Path) -> None:
    dados_oc = _build_dados_oc_syscomp()
    relatorio = _build_relatorio_syscomp()
    dados_oc["itens"][0]["syscomp"]["descricao_produto"] = "😀😀😀"

    try:
        gerar_txt_neogrid(dados_oc, relatorio, tmp_path)
    except NeoGridConformityError as exc:
        assert "nao possui caracteres compativeis" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado erro de codificacao.")
