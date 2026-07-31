"""Integra o pipeline com o cadastro oficial do Syscomp via Firebird ODBC."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from dotenv import load_dotenv

ALLOWED_AUTOMATIC_STATUSES = {"encontrado_exato", "encontrado_aproximado"}
DEFAULT_FIREBIRD_CHARSET = "UTF8"
DEFAULT_QUERY_BATCH_SIZE = 500
MISSING = object()

SYSCOMP_REPORT_COLUMNS = [
    "codigo_produto_syscomp",
    "descricao_syscomp",
    "descricao_txt_syscomp",
    "codigo_ncm",
    "codigo_barras_oficial",
    "possui_codigo_barras_oficial",
    "codigo_barras",
    "unidade_syscomp",
    "codigo_rms_syscomp",
    "referencia_produto_syscomp",
    "status_syscomp",
    "syscomp",
]


@dataclass(frozen=True)
class SyscompDbConfig:
    """Agrupa as configuracoes necessarias para abrir a conexao Firebird."""

    dsn: str | None
    host: str
    port: str
    database: str
    user: str
    password: str
    charset: str
    empresa: str | None


def carregar_configuracao_syscomp() -> SyscompDbConfig:
    """Le as configuracoes de ambiente usadas na conexao com o Syscomp."""

    load_dotenv()

    dsn = _read_optional_env("FIREBIRD_DSN") or _read_optional_env("SYSCOMP_ODBC_DSN")
    host = _read_required_env("FIREBIRD_HOST")
    port = _read_required_env("FIREBIRD_PORT")
    database = normalize_database_path(_read_required_env("FIREBIRD_DATABASE"))
    user = _read_required_env("FIREBIRD_USER")
    password = _read_required_env("FIREBIRD_PASSWORD")
    charset = _read_optional_env("FIREBIRD_CHARSET") or DEFAULT_FIREBIRD_CHARSET
    empresa = _read_optional_env("SYSCOMP_EMPRESA") or _read_optional_env("FIREBIRD_EMPRESA")

    return SyscompDbConfig(
        dsn=dsn,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        charset=charset,
        empresa=empresa,
    )


def carregar_produtos_syscomp(
    codigos_silo: Iterable[Any],
    *,
    batch_size: int = DEFAULT_QUERY_BATCH_SIZE,
) -> pd.DataFrame:
    """Carrega em lote os produtos do Syscomp a partir dos codigos mapeados no de/para."""

    codigos = _normalizar_codigos(codigos_silo)
    if not codigos:
        return pd.DataFrame(columns=_product_columns())

    conexao = connect_syscomp()
    try:
        return _carregar_produtos_syscomp_com_conexao(
            conexao,
            codigos,
            batch_size=batch_size,
        )
    finally:
        conexao.close()


def enriquecer_relatorio_conversao_com_syscomp(
    relatorio_conversao: pd.DataFrame,
    produtos_syscomp: pd.DataFrame,
) -> pd.DataFrame:
    """Anexa ao relatorio os campos oficiais do cadastro do ERP para o gerador do TXT."""

    dataframe = relatorio_conversao.copy()
    existing_columns = [column for column in SYSCOMP_REPORT_COLUMNS if column in dataframe.columns]
    if existing_columns:
        dataframe = dataframe.drop(columns=existing_columns)

    if dataframe.empty:
        for column in SYSCOMP_REPORT_COLUMNS:
            dataframe[column] = ""
        return dataframe

    if produtos_syscomp.empty:
        dataframe["status_syscomp"] = dataframe["status"].map(
            lambda status: "pendente_syscomp"
            if str(status) in ALLOWED_AUTOMATIC_STATUSES
            else "nao_aplicado"
        )
        dataframe["syscomp"] = dataframe["status_syscomp"].map(
            lambda status: {} if status == "pendente_syscomp" else ""
        )
        return dataframe

    lookup = {
        _normalizar_codigo_produto(row.get("codigo_silo")): row
        for row in produtos_syscomp.to_dict(orient="records")
        if _normalizar_codigo_produto(row.get("codigo_silo"))
    }

    registros_syscomp: list[dict[str, Any]] = []
    for row in dataframe.to_dict(orient="records"):
        status_match = str(row.get("status", "") or "")
        codigo_silo = _normalizar_codigo_produto(row.get("codigo_silo"))
        produto = lookup.get(codigo_silo)
        registros_syscomp.append(
            _build_syscomp_report_data(
                row=row,
                status_match=status_match,
                codigo_silo=codigo_silo,
                produto=produto,
            )
        )

    syscomp_df = pd.DataFrame(registros_syscomp, columns=SYSCOMP_REPORT_COLUMNS)
    return pd.concat([dataframe.reset_index(drop=True), syscomp_df], axis=1)


def validar_enriquecimento_syscomp(relatorio_conversao: pd.DataFrame) -> list[str]:
    """Bloqueia a geracao do TXT quando o cadastro oficial do ERP estiver ausente ou incompleto."""

    if not isinstance(relatorio_conversao, pd.DataFrame):
        return []

    if relatorio_conversao.empty or "status_syscomp" not in relatorio_conversao.columns:
        return []

    erros: list[str] = []
    pendentes = relatorio_conversao.loc[
        relatorio_conversao["status_syscomp"] == "pendente_syscomp"
    ]
    if not pendentes.empty:
        itens = ", ".join(_listar_itens_relatorio(pendentes))
        erros.append(
            "Nao foi possivel localizar no Syscomp os produtos correspondentes para: "
            f"{itens}."
        )

    incompletos = relatorio_conversao.loc[
        relatorio_conversao["status_syscomp"] == "dados_incompletos"
    ]
    if not incompletos.empty:
        itens = ", ".join(_listar_itens_relatorio(incompletos))
        erros.append(
            "O cadastro do Syscomp ainda nao possui dados obrigatorios suficientes "
            f"para gerar o TXT dos itens: {itens}."
        )

    return erros


def gerar_relatorio_produtos_sem_codigo_barras(
    df_depara: pd.DataFrame,
    produtos_syscomp: pd.DataFrame,
) -> pd.DataFrame:
    """Lista apenas os produtos do de/para que ainda nao possuem codigo de barras oficial no Syscomp."""

    return gerar_relatorio_status_codigo_barras(
        df_depara,
        produtos_syscomp,
        somente_sem_codigo_barras=True,
    )


def gerar_relatorio_status_codigo_barras(
    df_depara: pd.DataFrame,
    produtos_syscomp: pd.DataFrame,
    *,
    somente_sem_codigo_barras: bool = False,
) -> pd.DataFrame:
    """Gera um relatorio com o status do codigo de barras oficial no Syscomp."""

    if not isinstance(df_depara, pd.DataFrame) or df_depara.empty:
        return pd.DataFrame(columns=_barcode_report_columns())

    if not isinstance(produtos_syscomp, pd.DataFrame) or produtos_syscomp.empty:
        return pd.DataFrame(columns=_barcode_report_columns())

    depara = df_depara.copy()
    catalogo = produtos_syscomp.copy()

    depara["codigo_silo_normalizado"] = depara.get("COD. SILO", "").map(_normalizar_codigo_produto)
    catalogo["codigo_silo_normalizado"] = catalogo.get("codigo_silo", "").map(
        _normalizar_codigo_produto
    )

    base_depara = depara.loc[:, [column for column in depara.columns if column in {"Item", "COD. SILO", "DESCRIÇÃO"}]]
    base_depara["codigo_silo_normalizado"] = depara["codigo_silo_normalizado"]

    merge = base_depara.merge(
        catalogo,
        how="inner",
        on="codigo_silo_normalizado",
        suffixes=("_depara", "_syscomp"),
    )

    merge["codigo_silo"] = merge.get("codigo_silo", "").where(
        merge.get("codigo_silo", "").map(_normalize_text) != "",
        merge.get("COD. SILO", ""),
    )
    merge["item_tabela"] = merge.get("Item", "").map(_normalize_text)
    merge["descricao_depara"] = merge.get("DESCRIÇÃO", "").map(_normalize_text)
    merge["status_cadastro"] = merge["codigo_barras_oficial"].map(
        lambda value: "com_codigo_barras" if _normalize_text(value) else "sem_codigo_barras"
    )

    if somente_sem_codigo_barras:
        merge = merge.loc[merge["status_cadastro"] == "sem_codigo_barras"].copy()

    if merge.empty:
        return pd.DataFrame(columns=_barcode_report_columns())

    merge = merge.drop_duplicates(
        subset=["codigo_silo_normalizado"]
    ).reset_index(drop=True)

    return merge[_barcode_report_columns()]


def salvar_relatorio_produtos_sem_codigo_barras(
    dataframe: pd.DataFrame,
    pasta_saida: str | Path,
    *,
    nome_arquivo: str = "produtos_sem_codigo_barras_syscomp.xlsx",
) -> Path:
    """Salva em Excel o relatorio de produtos sem codigo de barras oficial."""

    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_saida = pasta / nome_arquivo
    dataframe.to_excel(caminho_saida, index=False)
    return caminho_saida


def listar_codigos_barras_existentes(conexao: Any) -> set[str]:
    """Retorna todos os codigos de barras atualmente cadastrados no Syscomp."""

    sql = """
        SELECT TRIM(COALESCE(NULLIF(CODIGOBARRASEAN13, ''), NULLIF(CODIGOBARRAS128, ''), '')) AS codigo_barras
        FROM PRODUTOCODIGOBARRAS
    """
    dataframe = _query_to_dataframe(conexao, sql, [])
    if dataframe.empty:
        return set()
    return {
        _somente_numeros(value)
        for value in dataframe["codigo_barras"].tolist()
        if _somente_numeros(value)
    }


def calcular_digito_ean13(base12: str) -> str:
    """Calcula o digito verificador de um EAN-13 a partir dos 12 primeiros digitos."""

    digits = _somente_numeros(base12)
    if len(digits) != 12:
        raise ValueError("O EAN base precisa conter exatamente 12 digitos.")

    total = 0
    for index, digit in enumerate(digits):
        peso = 1 if index % 2 == 0 else 3
        total += int(digit) * peso

    dv = (10 - (total % 10)) % 10
    return str(dv)


def gerar_codigo_barras_interno(
    codigo_silo: Any,
    *,
    sequencia: int = 0,
    prefixo: str = "200",
) -> str:
    """Gera um EAN-13 interno com base no codigo do produto e em uma sequencia numerica."""

    codigo = _normalizar_codigo_produto(codigo_silo)
    if not codigo or not codigo.isdigit():
        raise ValueError(f"Codigo SILO invalido para gerar codigo de barras: {codigo_silo}")

    if len(prefixo) != 3 or not prefixo.isdigit():
        raise ValueError("O prefixo do codigo de barras precisa conter 3 digitos numericos.")

    if sequencia < 0 or sequencia > 999:
        raise ValueError("A sequencia do codigo de barras precisa estar entre 0 e 999.")

    base12 = f"{prefixo}{codigo}{sequencia:03d}"
    return base12 + calcular_digito_ean13(base12)


def gerar_proposta_codigos_barras(
    dataframe: pd.DataFrame,
    *,
    codigos_para_substituir: Iterable[Any] | None = None,
    codigos_existentes: set[str] | None = None,
    prefixo: str = "200",
) -> pd.DataFrame:
    """Gera uma proposta de novos codigos de barras sem repetir valores ja existentes."""

    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return pd.DataFrame(columns=_barcode_proposal_columns())

    codigos_existentes = {_somente_numeros(value) for value in (codigos_existentes or set())}
    substituir = {
        _normalizar_codigo_produto(value) for value in (codigos_para_substituir or []) if value is not None
    }

    base = dataframe.copy()
    base["codigo_silo_normalizado"] = base.get("codigo_silo", "").map(_normalizar_codigo_produto)
    base["codigo_barras_oficial"] = base.get("codigo_barras_oficial", "").map(_somente_numeros)
    base["incluido_na_proposta"] = (
        base.get("status_cadastro", "").map(_normalize_text).eq("sem_codigo_barras")
        | base["codigo_silo_normalizado"].isin(substituir)
    )
    base = base.loc[base["incluido_na_proposta"]].copy()
    if base.empty:
        return pd.DataFrame(columns=_barcode_proposal_columns())

    usados = set(codigos_existentes)
    propostas: list[dict[str, Any]] = []
    for _, row in base.sort_values(["codigo_silo_normalizado", "item_tabela"]).iterrows():
        codigo_silo = row.get("codigo_silo_normalizado") or row.get("codigo_silo")
        novo_codigo = ""
        for sequencia in range(1000):
            candidato = gerar_codigo_barras_interno(
                codigo_silo,
                sequencia=sequencia,
                prefixo=prefixo,
            )
            if candidato not in usados:
                novo_codigo = candidato
                usados.add(candidato)
                break

        if not novo_codigo:
            raise RuntimeError(
                f"Nao foi possivel gerar um codigo de barras unico para o produto {codigo_silo}."
            )

        codigo_antigo = row.get("codigo_barras_oficial", "")
        motivo = "substituir_codigo_existente" if _somente_numeros(codigo_antigo) else "novo_codigo"

        propostas.append(
            {
                "item_tabela": _normalize_text(row.get("item_tabela")),
                "codigo_silo": _normalizar_codigo_produto(row.get("codigo_silo")),
                "descricao_syscomp": _normalize_text(row.get("descricao_syscomp")),
                "codigo_barras_atual": codigo_antigo,
                "novo_codigo_barras": novo_codigo,
                "status_cadastro_atual": _normalize_text(row.get("status_cadastro")),
                "motivo_proposta": motivo,
            }
        )

    return pd.DataFrame(propostas, columns=_barcode_proposal_columns())


def connect_syscomp():
    """Abre a conexao Firebird via ODBC usando DSN ou string de conexao direta."""

    pyodbc = _import_pyodbc()
    config = carregar_configuracao_syscomp()

    attempts: list[tuple[str, str]] = []
    for connection_label, connection_string in build_connection_variants(config, pyodbc):
        try:
            return pyodbc.connect(connection_string, timeout=10)
        except pyodbc.Error as exc:
            attempts.append((connection_label, str(exc)))

    messages = "\n".join(
        f"- {label}\n  erro: {error}" for label, error in attempts
    )
    raise RuntimeError(
        "Falha ao conectar no Firebird via ODBC para consultar o Syscomp. "
        "Verifique DSN, driver, credenciais e disponibilidade da rede.\n"
        f"{messages}"
    )


def build_connection_variants(config: SyscompDbConfig, pyodbc_module: Any) -> list[tuple[str, str]]:
    """Monta as variacoes de conexao testadas em sequencia."""

    driver = find_firebird_driver(pyodbc_module)
    database_remote = f"{config.host}/{config.port}:{config.database}"
    variants: list[tuple[str, str]] = []

    if config.dsn:
        variants.append(
            (
                f"DSN={config.dsn}",
                (
                    f"DSN={config.dsn};"
                    f"UID={config.user};PWD={config.password};"
                    f"CHARSET={config.charset};"
                ),
            )
        )

    variants.extend(
        [
            (
                "DBNAME remoto",
                (
                    f"DRIVER={{{driver}}};"
                    f"DBNAME={database_remote};"
                    f"UID={config.user};PWD={config.password};"
                    f"CHARSET={config.charset};"
                ),
            ),
            (
                "DATABASE remoto",
                (
                    f"DRIVER={{{driver}}};"
                    f"DATABASE={database_remote};"
                    f"UID={config.user};PWD={config.password};"
                    f"CHARSET={config.charset};"
                ),
            ),
            (
                "SERVER PORT DATABASE",
                (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={config.host};PORT={config.port};DATABASE={config.database};"
                    f"UID={config.user};PWD={config.password};"
                    f"CHARSET={config.charset};"
                ),
            ),
        ]
    )

    return variants


def find_firebird_driver(pyodbc_module: Any) -> str:
    """Seleciona um driver Firebird/Interbase entre os drivers ODBC instalados."""

    installed = pyodbc_module.drivers()
    candidates = [
        driver
        for driver in installed
        if "firebird" in driver.lower() or "interbase" in driver.lower()
    ]
    if not candidates:
        raise RuntimeError(
            "Nenhum driver ODBC do Firebird foi encontrado. "
            "Instale o driver e confirme se ele aparece em pyodbc.drivers()."
        )
    return candidates[0]


def normalize_database_path(database: str) -> str:
    """Normaliza caminhos vindos do ambiente para o formato esperado pelo driver."""

    value = database.strip()
    if ":" in value and not _is_windows_drive_path(value):
        _, remainder = value.split(":", 1)
        cleaned = remainder.strip()
        if cleaned:
            return cleaned
    return value


def _carregar_produtos_syscomp_com_conexao(
    conexao: Any,
    codigos_silo: list[str],
    *,
    batch_size: int,
) -> pd.DataFrame:
    """Executa a consulta em lotes para evitar um IN excessivamente grande."""

    frames: list[pd.DataFrame] = []
    config = carregar_configuracao_syscomp()

    for batch in _iter_batches(codigos_silo, batch_size):
        sql, params = _build_products_query(batch, empresa=config.empresa)
        frame = _query_to_dataframe(conexao, sql, params)
        frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=_product_columns())

    dataframe = pd.concat(frames, ignore_index=True)
    if dataframe.empty:
        return pd.DataFrame(columns=_product_columns())

    dataframe = dataframe.drop_duplicates(subset=["codigo_silo"]).reset_index(drop=True)
    return _post_process_products_dataframe(dataframe)


def _build_products_query(codigos_silo: list[str], *, empresa: str | None) -> tuple[str, list[Any]]:
    """Monta a query base do cadastro de produtos do Syscomp."""

    placeholders = ", ".join("?" for _ in codigos_silo)
    params: list[Any] = []
    empresa_join = ""
    if empresa:
        empresa_join = (
            "LEFT JOIN PRODUTOEMPRESA pe "
            "  ON pe.IDPRODUTO = p.ID "
            " AND pe.EMPRESA = ?"
        )
        params.append(empresa)
    else:
        empresa_join = (
            "LEFT JOIN ("
            "    SELECT IDPRODUTO, MIN(EMPRESA) AS EMPRESA "
            "    FROM PRODUTOEMPRESA "
            "    GROUP BY IDPRODUTO"
            ") pe ON pe.IDPRODUTO = p.ID"
        )

    sql = f"""
        SELECT
            TRIM(p.CODIGO) AS codigo_silo,
            p.ID AS id_produto_syscomp,
            TRIM(p.CODIGO) AS codigo_produto_syscomp,
            TRIM(COALESCE(NULLIF(p.ETIQNOMECOMER, ''), NULLIF(p.NOME, ''), p.CODIGO)) AS descricao_syscomp,
            TRIM(COALESCE(NULLIF(p.NOME, ''), p.CODIGO)) AS descricao_completa_syscomp,
            TRIM(COALESCE(NULLIF(p.REFERENCIA, ''), '')) AS referencia_produto_syscomp,
            TRIM(COALESCE(NULLIF(p.CODIGOIPI, ''), '')) AS codigo_ipi_syscomp,
            TRIM(COALESCE(NULLIF(p.NUMEROMS, ''), '')) AS codigo_rms_syscomp,
            TRIM(CAST(p.MEDIDAPADRAO AS VARCHAR(20))) AS unidade_syscomp,
            TRIM(COALESCE(NULLIF(cb.CODIGOBARRASEAN13, ''), NULLIF(cb.CODIGOBARRAS128, ''), '')) AS codigo_barras,
            TRIM(COALESCE(NULLIF(pe.EMPRESA, ''), '')) AS empresa_syscomp
        FROM PRODUTO p
        {empresa_join}
        LEFT JOIN (
            SELECT
                IDPRODUTO,
                MIN(COALESCE(NULLIF(TRIM(CODIGOBARRASEAN13), ''), NULLIF(TRIM(CODIGOBARRAS128), ''))) AS CODIGOBARRASEAN13,
                MIN(NULLIF(TRIM(CODIGOBARRAS128), '')) AS CODIGOBARRAS128
            FROM PRODUTOCODIGOBARRAS
            GROUP BY IDPRODUTO
        ) cb
          ON cb.IDPRODUTO = p.ID
        WHERE TRIM(p.CODIGO) IN ({placeholders})
    """
    params.extend(codigos_silo)
    return sql, params


def _query_to_dataframe(conexao: Any, sql: str, params: list[Any]) -> pd.DataFrame:
    """Executa uma consulta e devolve o resultado como DataFrame."""

    cursor = conexao.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    columns = [str(column[0]).strip().lower() for column in cursor.description]
    return pd.DataFrame.from_records(rows, columns=columns)


def _post_process_products_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normaliza os campos retornados do Firebird para uso no pipeline."""

    dataframe = dataframe.copy()
    for column in dataframe.columns:
        if dataframe[column].dtype == object:
            dataframe[column] = dataframe[column].map(_normalize_text)

    dataframe["unidade_syscomp"] = dataframe["unidade_syscomp"].map(_normalize_unidade_syscomp)
    dataframe["codigo_ncm"] = dataframe["codigo_ipi_syscomp"].map(_normalizar_ncm)
    dataframe["codigo_barras_oficial"] = dataframe["codigo_barras"].map(_somente_numeros)
    dataframe["possui_codigo_barras_oficial"] = dataframe["codigo_barras_oficial"] != ""
    dataframe["codigo_barras"] = dataframe["codigo_barras_oficial"]
    dataframe["codigo_barras"] = dataframe["codigo_barras"].mask(
        dataframe["codigo_barras"] == "",
        dataframe["codigo_produto_syscomp"].map(_somente_numeros),
    )
    dataframe["descricao_txt_syscomp"] = dataframe.apply(
        lambda row: criar_descricao_txt_syscomp(
            row.get("descricao_syscomp", ""),
            fallback=row.get("descricao_completa_syscomp", ""),
        ),
        axis=1,
    )
    dataframe["codigo_rms_syscomp"] = dataframe["codigo_rms_syscomp"].mask(
        dataframe["codigo_rms_syscomp"] == "",
        dataframe["codigo_produto_syscomp"],
    )
    return dataframe[_product_columns()]


def criar_descricao_txt_syscomp(texto: Any, *, fallback: Any = "") -> str:
    """Prepara uma descricao curta e compativel com o limite do layout final."""

    candidato = _normalize_text(texto) or _normalize_text(fallback)
    if not candidato:
        return ""
    if len(candidato) <= 40:
        return candidato

    sem_sufixo = re.sub(r"\s*-\s*[^-]+$", "", candidato).strip()
    if sem_sufixo and len(sem_sufixo) <= 40:
        return sem_sufixo

    return _truncate_text_preserving_words(sem_sufixo or candidato, 40)


def _build_syscomp_report_data(
    *,
    row: dict[str, Any],
    status_match: str,
    codigo_silo: str,
    produto: dict[str, Any] | None,
) -> dict[str, Any]:
    """Monta os campos adicionais do relatorio de conversao com base no cadastro do ERP."""

    if status_match not in ALLOWED_AUTOMATIC_STATUSES or not codigo_silo:
        return {
            "codigo_produto_syscomp": "",
            "descricao_syscomp": "",
            "descricao_txt_syscomp": "",
            "codigo_ncm": "",
            "codigo_barras_oficial": "",
            "possui_codigo_barras_oficial": False,
            "codigo_barras": "",
            "unidade_syscomp": "",
            "codigo_rms_syscomp": "",
            "referencia_produto_syscomp": "",
            "status_syscomp": "nao_aplicado",
            "syscomp": "",
        }

    if produto is None:
        return {
            "codigo_produto_syscomp": "",
            "descricao_syscomp": "",
            "descricao_txt_syscomp": "",
            "codigo_ncm": "",
            "codigo_barras_oficial": "",
            "possui_codigo_barras_oficial": False,
            "codigo_barras": "",
            "unidade_syscomp": "",
            "codigo_rms_syscomp": "",
            "referencia_produto_syscomp": "",
            "status_syscomp": "pendente_syscomp",
            "syscomp": {},
        }

    descricao_txt = _normalize_text(produto.get("descricao_txt_syscomp"))
    codigo_ncm = _normalize_text(produto.get("codigo_ncm"))
    unidade_syscomp = _normalize_text(produto.get("unidade_syscomp")) or _normalize_text(
        row.get("unidade")
    )
    codigo_barras_oficial = _normalize_text(produto.get("codigo_barras_oficial"))
    possui_codigo_barras_oficial = bool(produto.get("possui_codigo_barras_oficial"))

    payload = {
        "codigo_produto": codigo_barras_oficial
        or _normalize_text(produto.get("codigo_produto_syscomp"))
        or codigo_silo,
        "tipo_codigo_produto": "EN"
        if len(_somente_numeros(codigo_barras_oficial)) in {8, 12, 13, 14}
        else "PRD",
        "descricao_produto": descricao_txt or _normalize_text(produto.get("descricao_syscomp")),
        "referencia_produto": _normalize_text(produto.get("referencia_produto_syscomp")),
        "codigo_ncm": codigo_ncm,
        "codigo_rms": _normalize_text(produto.get("codigo_rms_syscomp")) or codigo_silo,
        "unidade": unidade_syscomp,
        "codigo_barras": codigo_barras_oficial,
        "codigo_produto_syscomp": _normalize_text(produto.get("codigo_produto_syscomp")),
    }

    status_syscomp = "ok"
    if (
        not payload["descricao_produto"]
        or not payload["codigo_ncm"]
        or not possui_codigo_barras_oficial
    ):
        status_syscomp = "dados_incompletos"

    return {
        "codigo_produto_syscomp": _normalize_text(produto.get("codigo_produto_syscomp")),
        "descricao_syscomp": _normalize_text(produto.get("descricao_syscomp")),
        "descricao_txt_syscomp": descricao_txt,
        "codigo_ncm": codigo_ncm,
        "codigo_barras_oficial": codigo_barras_oficial,
        "possui_codigo_barras_oficial": possui_codigo_barras_oficial,
        "codigo_barras": _normalize_text(produto.get("codigo_barras")),
        "unidade_syscomp": unidade_syscomp,
        "codigo_rms_syscomp": _normalize_text(produto.get("codigo_rms_syscomp")),
        "referencia_produto_syscomp": _normalize_text(produto.get("referencia_produto_syscomp")),
        "status_syscomp": status_syscomp,
        "syscomp": payload,
    }


def _import_pyodbc():
    """Importa pyodbc sob demanda para manter os testes desacoplados do driver."""

    try:
        import pyodbc  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Dependencia ausente: pyodbc. Instale a biblioteca no ambiente do "
            "silo-automacao antes de usar a integracao com o Syscomp."
        ) from exc
    return pyodbc


def _read_required_env(name: str) -> str:
    """Le uma variavel obrigatoria do ambiente."""

    value = os.getenv(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f"Variavel de ambiente obrigatoria ausente: {name}")
    return str(value).strip()


def _read_optional_env(name: str) -> str | None:
    """Le uma variavel opcional do ambiente."""

    value = os.getenv(name)
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_text(value: Any) -> str:
    """Normaliza texto removendo espacos excedentes."""

    if value in (None, MISSING):
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalizar_ncm(value: Any) -> str:
    """Converte o codigo fiscal bruto do cadastro para um NCM de 8 digitos."""

    digits = _somente_numeros(value)
    if len(digits) >= 8:
        return digits[:8]
    return ""


def _somente_numeros(value: Any) -> str:
    """Extrai apenas digitos de um texto."""

    return "".join(char for char in str(value or "") if char.isdigit())


def _normalize_unidade_syscomp(value: Any) -> str:
    """Limpa pseudo-unidades numericas do cadastro e preserva apenas valores textuais uteis."""

    text = _normalize_text(value)
    if re.fullmatch(r"0+(?:[.,]0+)?", text):
        return ""
    return text


def _truncate_text_preserving_words(text: str, limit: int) -> str:
    """Trunca um texto sem quebrar no meio da palavra quando possivel."""

    if len(text) <= limit:
        return text

    truncated = text[:limit].rstrip()
    if " " not in truncated:
        return truncated
    return truncated.rsplit(" ", 1)[0].rstrip() or truncated


def _iter_batches(values: list[str], batch_size: int) -> Iterable[list[str]]:
    """Quebra uma lista grande em lotes menores para consultas SQL."""

    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]


def _normalizar_codigos(codigos_silo: Iterable[Any]) -> list[str]:
    """Normaliza a lista de codigos do de/para para uso em consultas ao Firebird."""

    vistos: set[str] = set()
    resultado: list[str] = []
    for value in codigos_silo:
        codigo = _normalizar_codigo_produto(value)
        if not codigo or codigo in vistos:
            continue
        vistos.add(codigo)
        resultado.append(codigo)
    return resultado


def _normalizar_codigo_produto(value: Any) -> str:
    """Padroniza o codigo do produto como texto sem espacos excedentes."""

    text = _normalize_text(value)
    if not text:
        return ""

    numeric_match = re.fullmatch(r"(\d+)(?:\.0+)?", text)
    if numeric_match:
        digits = numeric_match.group(1).lstrip("0") or "0"
        return digits.zfill(6)

    digits_only = _somente_numeros(text)
    if digits_only and len(digits_only) == len(text.replace(" ", "")):
        digits = digits_only.lstrip("0") or "0"
        return digits.zfill(6)

    return text


def _listar_itens_relatorio(dataframe: pd.DataFrame) -> list[str]:
    """Resume itens do relatorio para mensagens de erro operacionais."""

    itens: list[str] = []
    for _, row in dataframe.iterrows():
        numero_oc = _normalize_text(row.get("numero_oc"))
        sequencia = _normalize_text(row.get("sequencia"))
        codigo_silo = _normalize_text(row.get("codigo_silo"))
        itens.append(
            f"OC {numero_oc or '?'} item {sequencia or '?'} codigo {codigo_silo or '?'}"
        )
    return itens


def _is_windows_drive_path(value: str) -> bool:
    """Identifica um caminho local do Windows."""

    return len(value) >= 3 and value[1] == ":" and value[2] in ("\\", "/")


def _product_columns() -> list[str]:
    """Lista as colunas padronizadas do catalogo de produtos do Syscomp."""

    return [
        "codigo_silo",
        "id_produto_syscomp",
        "codigo_produto_syscomp",
        "descricao_syscomp",
        "descricao_completa_syscomp",
        "descricao_txt_syscomp",
        "referencia_produto_syscomp",
        "codigo_ipi_syscomp",
        "codigo_ncm",
        "codigo_rms_syscomp",
        "unidade_syscomp",
        "codigo_barras_oficial",
        "possui_codigo_barras_oficial",
        "codigo_barras",
        "empresa_syscomp",
    ]


def _barcode_report_columns() -> list[str]:
    """Lista as colunas do relatorio de produtos sem codigo de barras."""

    return [
        "item_tabela",
        "codigo_silo",
        "descricao_depara",
        "codigo_produto_syscomp",
        "descricao_syscomp",
        "descricao_txt_syscomp",
        "codigo_ncm",
        "unidade_syscomp",
        "codigo_rms_syscomp",
        "referencia_produto_syscomp",
        "codigo_barras_oficial",
        "possui_codigo_barras_oficial",
        "codigo_barras",
        "status_cadastro",
    ]


def _barcode_proposal_columns() -> list[str]:
    """Lista as colunas da proposta de novos codigos de barras."""

    return [
        "item_tabela",
        "codigo_silo",
        "descricao_syscomp",
        "codigo_barras_atual",
        "novo_codigo_barras",
        "status_cadastro_atual",
        "motivo_proposta",
    ]
