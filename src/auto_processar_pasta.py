"""Executa o processamento automatico dos PDFs da pasta de entrada do servidor."""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from config import AppConfig, get_config
from main import preparar_tabela_produtos, processar_pdf

LOGGER_NAME = "silo_automacao.auto_processar_pasta"


def garantir_diretorios_automacao(config: AppConfig) -> None:
    """Garante que as pastas operacionais da automacao existam."""

    diretorios = [
        config.input_dir,
        config.processing_dir,
        config.processed_dir,
        config.error_dir,
        config.output_dir,
        config.output_txt_dir,
        config.output_reports_dir,
        config.support_dir,
        config.logs_dir,
    ]
    for diretorio in diretorios:
        diretorio.mkdir(parents=True, exist_ok=True)


def listar_pdfs_entrada(input_dir: Path) -> list[Path]:
    """Lista os PDFs disponiveis na pasta de entrada."""

    return sorted(path for path in input_dir.glob("*.pdf") if path.is_file())


def arquivo_esta_pronto_para_processamento(
    pdf_path: Path,
    stability_wait_seconds: float,
    stable_read_checks: int,
) -> bool:
    """Valida se o PDF terminou de ser copiado e pode ser aberto com seguranca."""

    tamanho_anterior = _obter_tamanho_arquivo(pdf_path)
    if tamanho_anterior is None:
        return False

    for _ in range(stable_read_checks):
        if stability_wait_seconds > 0:
            time.sleep(stability_wait_seconds)

        tamanho_atual = _obter_tamanho_arquivo(pdf_path)
        if tamanho_atual is None or tamanho_atual != tamanho_anterior:
            return False
        tamanho_anterior = tamanho_atual

    return _arquivo_pode_ser_aberto(pdf_path)


def mover_arquivo_para_pasta(origem: Path, pasta_destino: Path) -> Path:
    """Move um arquivo para a pasta de destino preservando o nome quando possivel."""

    pasta_destino.mkdir(parents=True, exist_ok=True)
    destino = _resolver_destino_disponivel(pasta_destino / origem.name)
    return origem.replace(destino)


def processar_arquivo_automaticamente(
    pdf_entrada: Path,
    df_depara: Any,
    config: AppConfig,
) -> dict[str, Any]:
    """Move um PDF para processamento, executa o pipeline e arquiva o resultado."""

    pdf_em_processamento = mover_arquivo_para_pasta(pdf_entrada, config.processing_dir)

    try:
        resultados = processar_pdf(pdf_em_processamento, df_depara)
    except Exception as exc:
        pdf_erro = mover_arquivo_para_pasta(pdf_em_processamento, config.error_dir)
        return {
            "arquivo_original": str(pdf_entrada),
            "arquivo_processado": str(pdf_erro),
            "status": "erro",
            "tipo_erro": "tecnico",
            "resultados": [],
            "ocs_encontradas": [],
            "erros": [str(exc)],
        }

    ocs_encontradas = _coletar_numeros_ocs(resultados)

    if _processamento_foi_bem_sucedido(resultados):
        pdf_processado = arquivar_pdf_processado(
            pdf_em_processamento,
            config.processed_dir,
            ocs_encontradas,
        )
        return {
            "arquivo_original": str(pdf_entrada),
            "arquivo_processado": str(pdf_processado),
            "status": "ok",
            "tipo_erro": "",
            "resultados": resultados,
            "ocs_encontradas": ocs_encontradas,
            "erros": [],
        }

    _remover_txts_parciais(resultados)
    pdf_erro = mover_arquivo_para_pasta(pdf_em_processamento, config.error_dir)
    return {
        "arquivo_original": str(pdf_entrada),
        "arquivo_processado": str(pdf_erro),
        "status": "erro",
        "tipo_erro": "negocio",
        "resultados": resultados,
        "ocs_encontradas": ocs_encontradas,
        "erros": _coletar_erros_resultados(resultados),
    }


def executar_processamento_automatico() -> dict[str, Any]:
    """Executa o processamento em lote de todos os PDFs encontrados na pasta de entrada."""

    config = get_config()
    garantir_diretorios_automacao(config)
    logger, caminho_log = configurar_logger(config)

    lock_adquirido = False
    try:
        lock_adquirido = adquirir_trava_execucao(config)
    except FileExistsError:
        logger.warning("Execucao bloqueada: outra instancia da automacao ja esta em andamento.")
        return _montar_resumo_execucao(
            arquivos_processados=[],
            caminho_revisao="",
            caminho_log=caminho_log,
            bloqueado_concorrencia=True,
        )

    try:
        pdfs = listar_pdfs_entrada(config.input_dir)
        registrar_inicio_execucao(logger, config, len(pdfs))

        try:
            df_depara, caminho_revisao = preparar_tabela_produtos()
        except Exception as exc:
            logger.error("Falha tecnica ao preparar a tabela de produtos: %s", exc)
            resumo = _montar_resumo_execucao(
                arquivos_processados=[],
                caminho_revisao="",
                caminho_log=caminho_log,
                bloqueado_concorrencia=False,
                total_pdfs=len(pdfs),
                erro_inicializacao=str(exc),
            )
            registrar_fim_execucao(logger, resumo)
            return resumo

        arquivos_processados: list[dict[str, Any]] = []
        for pdf in pdfs:
            if not arquivo_esta_pronto_para_processamento(
                pdf,
                stability_wait_seconds=config.ready_file_check_interval_seconds,
                stable_read_checks=config.ready_file_stable_checks,
            ):
                resultado = {
                    "arquivo_original": str(pdf),
                    "arquivo_processado": str(pdf),
                    "status": "ignorado",
                    "tipo_erro": "",
                    "resultados": [],
                    "ocs_encontradas": [],
                    "erros": ["Arquivo ainda em copia ou indisponivel para leitura nesta execucao."],
                }
                arquivos_processados.append(resultado)
                registrar_resultado_arquivo(logger, resultado)
                continue

            resultado = processar_arquivo_automaticamente(pdf, df_depara, config)
            arquivos_processados.append(resultado)
            registrar_resultado_arquivo(logger, resultado)

        resumo = _montar_resumo_execucao(
            arquivos_processados=arquivos_processados,
            caminho_revisao=str(caminho_revisao),
            caminho_log=caminho_log,
            bloqueado_concorrencia=False,
            total_pdfs=len(pdfs),
        )
        registrar_fim_execucao(logger, resumo)
        return resumo
    finally:
        if lock_adquirido:
            liberar_trava_execucao(config)


def main(argv: list[str] | None = None) -> int:
    """Executa o runner automatico da pasta de entrada via CLI."""

    parser = argparse.ArgumentParser(
        description="Processa automaticamente os PDFs da pasta de entrada do servidor."
    )
    parser.parse_args(argv)

    resumo = executar_processamento_automatico()
    print(f"Total de PDFs encontrados: {resumo['total_pdfs_encontrados']}")
    print(f"Total com sucesso: {resumo['total_sucesso']}")
    print(f"Total com erro: {resumo['total_erro']}")
    print(f"Total ignorado: {resumo['total_ignorado']}")
    print(f"Total erro tecnico: {resumo['total_erro_tecnico']}")
    print(f"Total erro negocio: {resumo['total_erro_negocio']}")
    print(f"Execucao bloqueada por concorrencia: {resumo['bloqueado_concorrencia']}")
    print(f"Relatorio de revisao de duplicatas: {resumo['caminho_revisao_duplicatas'] or '-'}")
    print(f"Log da execucao: {resumo['caminho_log']}")
    return 0 if resumo["total_erro"] == 0 and not resumo["bloqueado_concorrencia"] else 1


def configurar_logger(
    config: AppConfig,
    current_time: datetime | None = None,
) -> tuple[logging.Logger, Path]:
    """Configura o logger de arquivo usado pelo runner automatico."""

    momento = current_time or datetime.now()
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    caminho_log = config.logs_dir / f"automacao_oc_{momento:%Y-%m-%d}.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.FileHandler(caminho_log, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, caminho_log


def registrar_inicio_execucao(logger: logging.Logger, config: AppConfig, total_pdfs: int) -> None:
    """Registra o inicio da execucao automatica."""

    logger.info("Inicio da execucao automatica.")
    logger.info("Pasta de entrada: %s", config.input_dir)
    logger.info("Quantidade de PDFs encontrados: %s", total_pdfs)


def registrar_resultado_arquivo(logger: logging.Logger, resultado: dict[str, Any]) -> None:
    """Registra o resultado do processamento de um arquivo."""

    logger.info("Arquivo processado: %s", resultado.get("arquivo_original", ""))
    logger.info("Arquivo arquivado: %s", resultado.get("arquivo_processado", ""))
    logger.info("OCs encontradas: %s", ", ".join(resultado.get("ocs_encontradas", [])) or "-")
    logger.info("Status do arquivo: %s", resultado.get("status", "desconhecido"))
    if resultado.get("tipo_erro"):
        logger.info("Tipo de erro: %s", resultado.get("tipo_erro"))

    for item in resultado.get("resultados", []):
        numero_oc = str(item.get("numero_oc", "") or "").strip() or "sem_numero"
        caminho_txt = str(item.get("caminho_txt", "") or "-")
        caminho_relatorio = str(item.get("caminho_relatorio", "") or "-")
        logger.info("OC %s | TXT gerado: %s", numero_oc, caminho_txt)
        logger.info("OC %s | Relatorio gerado: %s", numero_oc, caminho_relatorio)

    for erro in resultado.get("erros", []):
        if resultado.get("status") == "ignorado":
            logger.warning("Aviso no arquivo: %s", erro)
        else:
            logger.error("Erro no arquivo: %s", erro)


def registrar_fim_execucao(logger: logging.Logger, resumo: dict[str, Any]) -> None:
    """Registra o encerramento da execucao automatica."""

    logger.info("Fim da execucao automatica.")
    logger.info("Total de PDFs encontrados: %s", resumo["total_pdfs_encontrados"])
    logger.info("Total com sucesso: %s", resumo["total_sucesso"])
    logger.info("Total com erro: %s", resumo["total_erro"])
    logger.info("Total ignorado: %s", resumo["total_ignorado"])
    logger.info("Total erro tecnico: %s", resumo["total_erro_tecnico"])
    logger.info("Total erro negocio: %s", resumo["total_erro_negocio"])
    logger.info("Execucao bloqueada por concorrencia: %s", resumo["bloqueado_concorrencia"])
    logger.info("Relatorio de revisao de duplicatas: %s", resumo["caminho_revisao_duplicatas"] or "-")
    logger.info("Erro de inicializacao: %s", resumo["erro_inicializacao"] or "-")
    logger.info("Log da execucao: %s", resumo["caminho_log"])


def adquirir_trava_execucao(config: AppConfig) -> bool:
    """Cria uma trava simples para impedir duas execucoes simultaneas do runner."""

    lock_path = config.runner_lock_file
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
        lock_file.write(f"pid={os.getpid()}\n")
        lock_file.write(f"timestamp={datetime.now().isoformat(timespec='seconds')}\n")
    return True


def liberar_trava_execucao(config: AppConfig) -> None:
    """Remove a trava de execucao ao final do processamento."""

    try:
        config.runner_lock_file.unlink(missing_ok=True)
    except OSError:
        return


def _processamento_foi_bem_sucedido(resultados: list[dict[str, Any]]) -> bool:
    """Indica se todos os resultados do PDF foram processados com sucesso."""

    if not resultados:
        return False

    for resultado in resultados:
        if resultado.get("status") != "ok":
            return False
        if resultado.get("erros"):
            return False

    return True


def _coletar_erros_resultados(resultados: list[dict[str, Any]]) -> list[str]:
    """Consolida os erros retornados pelo pipeline do PDF."""

    erros: list[str] = []
    for resultado in resultados:
        for erro in resultado.get("erros", []):
            if erro not in erros:
                erros.append(str(erro))
    return erros


def _remover_txts_parciais(resultados: list[dict[str, Any]]) -> None:
    """Remove TXTs gerados antes de uma falha para evitar saida parcial por PDF."""

    caminhos = {
        str(resultado.get("caminho_txt", "") or "").strip()
        for resultado in resultados
        if str(resultado.get("caminho_txt", "") or "").strip()
    }
    for caminho in caminhos:
        path = Path(caminho)
        try:
            if path.exists():
                path.unlink()
        except OSError:
            continue


def arquivar_pdf_processado(
    pdf_em_processamento: Path,
    pasta_processados: Path,
    ocs_encontradas: list[str],
) -> Path:
    """Move o PDF processado para a pasta final renomeando pelo numero da OC."""

    nome_arquivo = _montar_nome_pdf_processado(ocs_encontradas)
    pasta_processados.mkdir(parents=True, exist_ok=True)
    destino = _resolver_destino_disponivel(pasta_processados / nome_arquivo)
    return pdf_em_processamento.replace(destino)


def _coletar_numeros_ocs(resultados: list[dict[str, Any]]) -> list[str]:
    """Extrai os numeros das OCs retornadas pelo pipeline do PDF."""

    ocs: list[str] = []
    for resultado in resultados:
        numero_oc = str(resultado.get("numero_oc", "") or "").strip()
        if numero_oc and numero_oc not in ocs:
            ocs.append(numero_oc)
    return ocs


def _montar_nome_pdf_processado(ocs_encontradas: list[str]) -> str:
    """Monta o nome final do PDF arquivado a partir da primeira OC encontrada."""

    if not ocs_encontradas:
        return "OC_sem_numero.pdf"
    return f"OC_{ocs_encontradas[0]}.pdf"


def _montar_resumo_execucao(
    arquivos_processados: list[dict[str, Any]],
    caminho_revisao: str,
    caminho_log: Path,
    bloqueado_concorrencia: bool,
    total_pdfs: int = 0,
    erro_inicializacao: str = "",
) -> dict[str, Any]:
    """Monta o resumo padrao de uma execucao do runner automatico."""

    return {
        "total_pdfs_encontrados": total_pdfs,
        "total_sucesso": sum(1 for item in arquivos_processados if item["status"] == "ok"),
        "total_erro": sum(1 for item in arquivos_processados if item["status"] == "erro"),
        "total_ignorado": sum(1 for item in arquivos_processados if item["status"] == "ignorado"),
        "total_erro_tecnico": sum(
            1 for item in arquivos_processados if item.get("tipo_erro") == "tecnico"
        ) + (1 if erro_inicializacao else 0),
        "total_erro_negocio": sum(
            1 for item in arquivos_processados if item.get("tipo_erro") == "negocio"
        ),
        "bloqueado_concorrencia": bloqueado_concorrencia,
        "erro_inicializacao": erro_inicializacao,
        "caminho_revisao_duplicatas": caminho_revisao,
        "caminho_log": str(caminho_log),
        "arquivos": arquivos_processados,
    }


def _resolver_destino_disponivel(destino_base: Path) -> Path:
    """Retorna um destino livre, adicionando sufixo numerico quando necessario."""

    if not destino_base.exists():
        return destino_base

    contador = 1
    while True:
        candidato = destino_base.with_name(
            f"{destino_base.stem}_{contador}{destino_base.suffix}"
        )
        if not candidato.exists():
            return candidato
        contador += 1


def _obter_tamanho_arquivo(pdf_path: Path) -> int | None:
    """Retorna o tamanho atual do arquivo ou `None` quando nao for possivel ler."""

    try:
        return pdf_path.stat().st_size
    except OSError:
        return None


def _arquivo_pode_ser_aberto(pdf_path: Path) -> bool:
    """Indica se o arquivo pode ser aberto para leitura no momento atual."""

    try:
        with pdf_path.open("rb") as file:
            file.read(1)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
