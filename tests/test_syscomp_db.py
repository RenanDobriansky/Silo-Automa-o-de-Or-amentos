"""Testes da integracao do catalogo Syscomp via Firebird ODBC."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from syscomp_db import (
    build_connection_variants,
    calcular_digito_ean13,
    criar_descricao_txt_syscomp,
    enriquecer_relatorio_conversao_com_syscomp,
    gerar_codigo_barras_interno,
    gerar_proposta_codigos_barras,
    gerar_relatorio_produtos_sem_codigo_barras,
    gerar_relatorio_status_codigo_barras,
    normalize_database_path,
    _normalizar_codigo_produto,
    validar_enriquecimento_syscomp,
)


def test_normalize_database_path_remove_prefixo_de_servidor() -> None:
    assert normalize_database_path(r"26.75.223.88/3050:C:\syscomp\gdb\SILO.FDB") == (
        r"C:\syscomp\gdb\SILO.FDB"
    )
    assert normalize_database_path(r"C:\syscomp\gdb\SILO.FDB") == r"C:\syscomp\gdb\SILO.FDB"


def test_criar_descricao_txt_syscomp_remove_sufixo_e_limita_tamanho() -> None:
    descricao = "BOBINA PICOTADA 40X60CM 10KG C/500 UN - TUBESPACK"

    resultado = criar_descricao_txt_syscomp(descricao)

    assert resultado == "BOBINA PICOTADA 40X60CM 10KG C/500 UN"
    assert len(resultado) <= 40


def test_normalizar_codigo_produto_remove_decimal_excel_e_completa_zeros() -> None:
    assert _normalizar_codigo_produto("5511.0") == "005511"
    assert _normalizar_codigo_produto("426") == "000426"
    assert _normalizar_codigo_produto("000426") == "000426"


def test_build_connection_variants_prioriza_dsn_quando_informado() -> None:
    class _FakePyodbc:
        @staticmethod
        def drivers() -> list[str]:
            return ["Firebird/InterBase(r) driver"]

    config = type(
        "Config",
        (),
        {
            "dsn": "Silo",
            "host": "26.75.223.88",
            "port": "3050",
            "database": r"C:\syscomp\gdb\SILO.FDB",
            "user": "SYSDBA",
            "password": "laranja",
            "charset": "UTF8",
            "empresa": "001",
        },
    )()

    variants = build_connection_variants(config, _FakePyodbc)

    assert variants[0][0] == "DSN=Silo"
    assert "DSN=Silo;" in variants[0][1]


def test_calcular_digito_ean13_e_gerar_codigo_barras_interno() -> None:
    assert calcular_digito_ean13("200005511000") == "4"
    assert gerar_codigo_barras_interno("5511") == "2000055110004"


def test_enriquecer_relatorio_conversao_com_syscomp_anexa_payload_oficial() -> None:
    relatorio = pd.DataFrame(
        [
            {
                "numero_oc": "623986",
                "sequencia": 1,
                "item_pdf": "Bobina Picotada 40x60cm",
                "item_encontrado_tabela": "Bobina Picotada 40x60cm",
                "codigo_silo": "100",
                "descricao_erp": "BOBINA PICOTADA 40X60CM 10KG C/500 UN - TUBESPACK",
                "quantidade_original": 1.0,
                "quantidade": 1.0,
                "unidade": "CX",
                "valor_unitario": 51.2,
                "valor_total": 51.2,
                "regra_conversao": "",
                "criterio_conversao": "sem_conversao",
                "score": 100,
                "status": "encontrado_exato",
            }
        ]
    )
    produtos_syscomp = pd.DataFrame(
        [
            {
                "codigo_silo": "100",
                "id_produto_syscomp": 1,
                "codigo_produto_syscomp": "000100",
                "descricao_syscomp": "BOBINA PICOTADA 40X60CM 10KG C/500 UN - TUBESPACK",
                "descricao_completa_syscomp": "BOBINA PICOTADA 40X60CM 10KG C/500 UN - TUBESPACK",
                "descricao_txt_syscomp": "BOBINA PICOTADA 40X60CM 10KG C/500 UN",
                "referencia_produto_syscomp": "BOB4060",
                "codigo_ipi_syscomp": "3926.90.90-00",
                "codigo_ncm": "39269090",
                "codigo_rms_syscomp": "000100",
                "unidade_syscomp": "CX",
                "codigo_barras_oficial": "7891234567890",
                "possui_codigo_barras_oficial": True,
                "codigo_barras": "7891234567890",
                "empresa_syscomp": "001",
            }
        ]
    )

    resultado = enriquecer_relatorio_conversao_com_syscomp(relatorio, produtos_syscomp)

    assert resultado.loc[0, "status_syscomp"] == "ok"
    assert resultado.loc[0, "codigo_ncm"] == "39269090"
    assert resultado.loc[0, "descricao_txt_syscomp"] == "BOBINA PICOTADA 40X60CM 10KG C/500 UN"
    assert resultado.loc[0, "codigo_barras"] == "7891234567890"
    payload = resultado.loc[0, "syscomp"]
    assert payload["codigo_produto"] == "7891234567890"
    assert payload["tipo_codigo_produto"] == "EN"
    assert payload["descricao_produto"] == "BOBINA PICOTADA 40X60CM 10KG C/500 UN"
    assert payload["codigo_ncm"] == "39269090"


def test_enriquecer_relatorio_conversao_com_syscomp_marca_sem_codigo_barras_como_incompleto() -> None:
    relatorio = pd.DataFrame(
        [
            {
                "numero_oc": "623986",
                "sequencia": 1,
                "item_pdf": "Fibra verde",
                "codigo_silo": "2187",
                "unidade": "PCT",
                "status": "encontrado_exato",
            }
        ]
    )
    produtos_syscomp = pd.DataFrame(
        [
            {
                "codigo_silo": "2187",
                "id_produto_syscomp": 2,
                "codigo_produto_syscomp": "002187",
                "descricao_syscomp": "FIBRACO VERDE GROSSO",
                "descricao_completa_syscomp": "FIBRACO VERDE GROSSO",
                "descricao_txt_syscomp": "FIBRACO VERDE GROSSO",
                "referencia_produto_syscomp": "",
                "codigo_ipi_syscomp": "68053090",
                "codigo_ncm": "68053090",
                "codigo_rms_syscomp": "002187",
                "unidade_syscomp": "PCT",
                "codigo_barras_oficial": "",
                "possui_codigo_barras_oficial": False,
                "codigo_barras": "002187",
                "empresa_syscomp": "001",
            }
        ]
    )

    resultado = enriquecer_relatorio_conversao_com_syscomp(relatorio, produtos_syscomp)

    assert resultado.loc[0, "status_syscomp"] == "dados_incompletos"
    assert resultado.loc[0, "codigo_barras_oficial"] == ""
    payload = resultado.loc[0, "syscomp"]
    assert payload["codigo_produto"] == "002187"
    assert payload["codigo_barras"] == ""
    assert payload["tipo_codigo_produto"] == "PRD"


def test_gerar_relatorio_produtos_sem_codigo_barras_filtra_itens_corretamente() -> None:
    df_depara = pd.DataFrame(
        [
            {"Item": "Bobina", "COD. SILO": "5511.0", "DESCRIÇÃO": "Bobina ERP"},
            {"Item": "Fibra", "COD. SILO": "2187", "DESCRIÇÃO": "Fibra ERP"},
        ]
    )
    produtos_syscomp = pd.DataFrame(
        [
            {
                "codigo_silo": "005511",
                "codigo_produto_syscomp": "005511",
                "descricao_syscomp": "BOBINA",
                "descricao_txt_syscomp": "BOBINA",
                "codigo_ncm": "39232190",
                "unidade_syscomp": "CX",
                "codigo_rms_syscomp": "005511",
                "referencia_produto_syscomp": "",
                "codigo_barras_oficial": "",
                "possui_codigo_barras_oficial": False,
                "codigo_barras": "005511",
            },
            {
                "codigo_silo": "002187",
                "codigo_produto_syscomp": "002187",
                "descricao_syscomp": "FIBRA",
                "descricao_txt_syscomp": "FIBRA",
                "codigo_ncm": "68053090",
                "unidade_syscomp": "PCT",
                "codigo_rms_syscomp": "002187",
                "referencia_produto_syscomp": "",
                "codigo_barras_oficial": "7898509281234",
                "possui_codigo_barras_oficial": True,
                "codigo_barras": "7898509281234",
            },
        ]
    )

    resultado = gerar_relatorio_produtos_sem_codigo_barras(df_depara, produtos_syscomp)

    assert len(resultado) == 1
    assert resultado.loc[0, "item_tabela"] == "Bobina"
    assert resultado.loc[0, "codigo_silo"] == "005511"
    assert resultado.loc[0, "status_cadastro"] == "sem_codigo_barras"


def test_gerar_relatorio_status_codigo_barras_traz_itens_com_e_sem_codigo() -> None:
    df_depara = pd.DataFrame(
        [
            {"Item": "Bobina", "COD. SILO": "5511.0", "DESCRIÇÃO": "Bobina ERP"},
            {"Item": "Fibra", "COD. SILO": "2187", "DESCRIÇÃO": "Fibra ERP"},
        ]
    )
    produtos_syscomp = pd.DataFrame(
        [
            {
                "codigo_silo": "005511",
                "codigo_produto_syscomp": "005511",
                "descricao_syscomp": "BOBINA",
                "descricao_txt_syscomp": "BOBINA",
                "codigo_ncm": "39232190",
                "unidade_syscomp": "CX",
                "codigo_rms_syscomp": "005511",
                "referencia_produto_syscomp": "",
                "codigo_barras_oficial": "",
                "possui_codigo_barras_oficial": False,
                "codigo_barras": "005511",
            },
            {
                "codigo_silo": "002187",
                "codigo_produto_syscomp": "002187",
                "descricao_syscomp": "FIBRA",
                "descricao_txt_syscomp": "FIBRA",
                "codigo_ncm": "68053090",
                "unidade_syscomp": "PCT",
                "codigo_rms_syscomp": "002187",
                "referencia_produto_syscomp": "",
                "codigo_barras_oficial": "7898509281234",
                "possui_codigo_barras_oficial": True,
                "codigo_barras": "7898509281234",
            },
        ]
    )

    resultado = gerar_relatorio_status_codigo_barras(df_depara, produtos_syscomp)

    assert len(resultado) == 2
    assert set(resultado["status_cadastro"]) == {"sem_codigo_barras", "com_codigo_barras"}
    assert "possui_codigo_barras_oficial" in resultado.columns


def test_gerar_proposta_codigos_barras_mantem_unicidade_e_substituicao() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "item_tabela": "Bobina",
                "codigo_silo": "005511",
                "descricao_syscomp": "BOBINA",
                "codigo_barras_oficial": "",
                "status_cadastro": "sem_codigo_barras",
            },
            {
                "item_tabela": "Soja",
                "codigo_silo": "004768",
                "descricao_syscomp": "SOJA EM GRAO",
                "codigo_barras_oficial": "7891023000001",
                "status_cadastro": "com_codigo_barras",
            },
        ]
    )

    resultado = gerar_proposta_codigos_barras(
        dataframe,
        codigos_para_substituir=["4768"],
        codigos_existentes={"7891023000001", "2000055110008"},
    )

    assert len(resultado) == 2
    assert set(resultado["codigo_silo"]) == {"005511", "004768"}
    assert resultado.loc[resultado["codigo_silo"] == "005511", "novo_codigo_barras"].iloc[0] != "2000055110008"
    assert (
        resultado.loc[resultado["codigo_silo"] == "004768", "motivo_proposta"].iloc[0]
        == "substituir_codigo_existente"
    )


def test_validar_enriquecimento_syscomp_bloqueia_pendente_e_incompleto() -> None:
    relatorio = pd.DataFrame(
        [
            {
                "numero_oc": "623986",
                "sequencia": 1,
                "codigo_silo": "100",
                "status": "encontrado_exato",
                "status_syscomp": "pendente_syscomp",
            },
            {
                "numero_oc": "623986",
                "sequencia": 2,
                "codigo_silo": "101",
                "status": "encontrado_aproximado",
                "status_syscomp": "dados_incompletos",
            },
        ]
    )

    erros = validar_enriquecimento_syscomp(relatorio)

    assert len(erros) == 2
    assert "Nao foi possivel localizar no Syscomp" in erros[0]
    assert "dados obrigatorios suficientes" in erros[1]
