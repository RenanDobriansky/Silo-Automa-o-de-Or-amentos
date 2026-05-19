"""Testes do runner automatico da pasta de entrada do servidor."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auto_processar_pasta import (
    adquirir_trava_execucao,
    arquivar_pdf_processado,
    arquivo_esta_pronto_para_processamento,
    configurar_logger,
    executar_processamento_automatico,
    liberar_trava_execucao,
    listar_pdfs_entrada,
    processar_arquivo_automaticamente,
)


def test_listar_pdfs_entrada_retorna_apenas_pdfs_ordenados(tmp_path: Path) -> None:
    (tmp_path / "b.pdf").write_bytes(b"fake")
    (tmp_path / "a.pdf").write_bytes(b"fake")
    (tmp_path / "nota.txt").write_text("ignorar", encoding="utf-8")

    resultado = listar_pdfs_entrada(tmp_path)

    assert resultado == [tmp_path / "a.pdf", tmp_path / "b.pdf"]


def test_arquivo_esta_pronto_para_processamento_retorna_false_quando_tamanho_muda(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "arquivo.pdf"
    pdf.write_bytes(b"%PDF")
    tamanhos = iter([10, 10, 20])

    monkeypatch.setattr(
        "auto_processar_pasta._obter_tamanho_arquivo",
        lambda caminho: next(tamanhos),
    )

    assert (
        arquivo_esta_pronto_para_processamento(
            pdf,
            stability_wait_seconds=0,
            stable_read_checks=2,
        )
        is False
    )


def test_arquivo_esta_pronto_para_processamento_retorna_false_quando_nao_abre(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "arquivo.pdf"
    pdf.write_bytes(b"%PDF")

    monkeypatch.setattr("auto_processar_pasta._obter_tamanho_arquivo", lambda caminho: 10)
    monkeypatch.setattr("auto_processar_pasta._arquivo_pode_ser_aberto", lambda caminho: False)

    assert (
        arquivo_esta_pronto_para_processamento(
            pdf,
            stability_wait_seconds=0,
            stable_read_checks=2,
        )
        is False
    )


def test_processar_arquivo_automaticamente_move_para_processados_quando_sucesso(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    pdf = config.input_dir / "teste.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF")

    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: [
            {
                "numero_oc": "123",
                "quantidade_itens": 1,
                "valor_total": 10.0,
                "status": "ok",
                "caminho_txt": "saida.txt",
                "caminho_relatorio": "relatorio.xlsx",
                "erros": [],
            }
        ],
    )

    resultado = processar_arquivo_automaticamente(pdf, object(), config)

    caminho_final = config.processed_dir / "OC_123.pdf"
    assert resultado["status"] == "ok"
    assert resultado["ocs_encontradas"] == ["123"]
    assert caminho_final.exists()
    assert not pdf.exists()
    assert not (config.processing_dir / "teste.pdf").exists()
    assert not (config.error_dir / "teste.pdf").exists()


def test_processar_arquivo_automaticamente_move_para_erro_quando_pipeline_retorna_erro(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    pdf = config.input_dir / "teste.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF")

    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: [
            {
                "numero_oc": "123",
                "quantidade_itens": 1,
                "valor_total": 10.0,
                "status": "erro",
                "caminho_txt": "",
                "caminho_relatorio": "relatorio.xlsx",
                "erros": ["Produto nao encontrado"],
            }
        ],
    )

    resultado = processar_arquivo_automaticamente(pdf, object(), config)

    caminho_final = config.error_dir / "teste.pdf"
    assert resultado["status"] == "erro"
    assert resultado["tipo_erro"] == "negocio"
    assert resultado["erros"] == ["Produto nao encontrado"]
    assert caminho_final.exists()
    assert not (config.processing_dir / "teste.pdf").exists()


def test_processar_arquivo_automaticamente_limpa_txt_parcial_em_erro_de_negocio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    pdf = config.input_dir / "teste.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    config.output_txt_dir.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF")
    txt_parcial = config.output_txt_dir / "OC_123.txt"
    txt_parcial.write_text("parcial", encoding="utf-8")

    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: [
            {
                "numero_oc": "123",
                "quantidade_itens": 1,
                "valor_total": 10.0,
                "status": "ok",
                "caminho_txt": str(txt_parcial),
                "caminho_relatorio": "relatorio_123.xlsx",
                "erros": [],
            },
            {
                "numero_oc": "124",
                "quantidade_itens": 1,
                "valor_total": 20.0,
                "status": "erro",
                "caminho_txt": "",
                "caminho_relatorio": "relatorio_124.xlsx",
                "erros": ["Falha de validacao"],
            },
        ],
    )

    resultado = processar_arquivo_automaticamente(pdf, object(), config)

    assert resultado["status"] == "erro"
    assert resultado["tipo_erro"] == "negocio"
    assert not txt_parcial.exists()
    assert (config.error_dir / "teste.pdf").exists()


def test_processar_arquivo_automaticamente_classifica_erro_tecnico_em_excecao(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    pdf = config.input_dir / "teste.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF")

    def _falhar(caminho_pdf, df_depara):
        raise RuntimeError("Falha tecnica ao ler o PDF")

    monkeypatch.setattr("auto_processar_pasta.processar_pdf", _falhar)

    resultado = processar_arquivo_automaticamente(pdf, object(), config)

    assert resultado["status"] == "erro"
    assert resultado["tipo_erro"] == "tecnico"
    assert resultado["erros"] == ["Falha tecnica ao ler o PDF"]
    assert (config.error_dir / "teste.pdf").exists()


def test_processar_arquivo_automaticamente_mantem_um_pdf_quando_ha_multiplas_ocs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    pdf = config.input_dir / "lote.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF")

    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: [
            {
                "numero_oc": "123",
                "quantidade_itens": 1,
                "valor_total": 10.0,
                "status": "ok",
                "caminho_txt": "OC_123.txt",
                "caminho_relatorio": "relatorio_123.xlsx",
                "erros": [],
            },
            {
                "numero_oc": "124",
                "quantidade_itens": 2,
                "valor_total": 20.0,
                "status": "ok",
                "caminho_txt": "OC_124.txt",
                "caminho_relatorio": "relatorio_124.xlsx",
                "erros": [],
            },
        ],
    )

    resultado = processar_arquivo_automaticamente(pdf, object(), config)

    assert resultado["status"] == "ok"
    assert resultado["ocs_encontradas"] == ["123", "124"]
    assert (config.processed_dir / "OC_123.pdf").exists()
    assert not (config.processed_dir / "OC_124.pdf").exists()


def test_arquivar_pdf_processado_adiciona_sufixo_quando_nome_ja_existe(tmp_path: Path) -> None:
    pasta_processados = tmp_path / "processados"
    pasta_processados.mkdir(parents=True, exist_ok=True)
    existente = pasta_processados / "OC_123.pdf"
    existente.write_bytes(b"%PDF")
    pdf = tmp_path / "em_processamento.pdf"
    pdf.write_bytes(b"%PDF")

    destino = arquivar_pdf_processado(pdf, pasta_processados, ["123"])

    assert destino == pasta_processados / "OC_123_1.pdf"
    assert destino.exists()
    assert existente.exists()


def test_configurar_logger_cria_arquivo_na_pasta_de_logs(tmp_path: Path) -> None:
    config = _build_config(tmp_path)

    logger, caminho_log = configurar_logger(config)
    logger.info("teste de log")

    assert caminho_log.exists()
    conteudo = caminho_log.read_text(encoding="utf-8")
    assert "teste de log" in conteudo


def test_adquirir_e_liberar_trava_execucao(tmp_path: Path) -> None:
    config = _build_config(tmp_path)

    assert adquirir_trava_execucao(config) is True
    assert config.runner_lock_file.exists()
    liberar_trava_execucao(config)
    assert not config.runner_lock_file.exists()


def test_executar_processamento_automatico_processa_todos_os_pdfs_da_entrada(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    config.input_dir.mkdir(parents=True, exist_ok=True)
    (config.input_dir / "a.pdf").write_bytes(b"%PDF")
    (config.input_dir / "b.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr("auto_processar_pasta.get_config", lambda: config)
    monkeypatch.setattr(
        "auto_processar_pasta.preparar_tabela_produtos",
        lambda: ("df_depara", config.output_reports_dir / "produtos_duplicados_para_revisao.xlsx"),
    )
    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: [
            {
                "numero_oc": f"OC{Path(caminho_pdf).stem.upper()}",
                "quantidade_itens": 1,
                "valor_total": 10.0,
                "status": "ok",
                "caminho_txt": "saida.txt",
                "caminho_relatorio": "relatorio.xlsx",
                "erros": [],
            }
        ],
    )

    resumo = executar_processamento_automatico()

    assert resumo["total_pdfs_encontrados"] == 2
    assert resumo["total_sucesso"] == 2
    assert resumo["total_erro"] == 0
    assert resumo["total_ignorado"] == 0
    assert resumo["total_erro_tecnico"] == 0
    assert resumo["total_erro_negocio"] == 0
    assert resumo["bloqueado_concorrencia"] is False
    assert resumo["erro_inicializacao"] == ""
    assert Path(resumo["caminho_log"]).exists()
    assert (config.processed_dir / "OC_OCA.pdf").exists()
    assert (config.processed_dir / "OC_OCB.pdf").exists()


def test_executar_processamento_automatico_ignora_arquivo_ainda_em_copia(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    config.input_dir.mkdir(parents=True, exist_ok=True)
    pdf = config.input_dir / "entrada.pdf"
    pdf.write_bytes(b"%PDF")
    chamadas: list[Path] = []

    monkeypatch.setattr("auto_processar_pasta.get_config", lambda: config)
    monkeypatch.setattr(
        "auto_processar_pasta.preparar_tabela_produtos",
        lambda: ("df_depara", config.output_reports_dir / "produtos_duplicados_para_revisao.xlsx"),
    )
    monkeypatch.setattr(
        "auto_processar_pasta.arquivo_esta_pronto_para_processamento",
        lambda caminho, stability_wait_seconds, stable_read_checks: False,
    )
    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: chamadas.append(Path(caminho_pdf)),
    )

    resumo = executar_processamento_automatico()

    assert resumo["total_pdfs_encontrados"] == 1
    assert resumo["total_sucesso"] == 0
    assert resumo["total_erro"] == 0
    assert resumo["total_ignorado"] == 1
    assert resumo["total_erro_tecnico"] == 0
    assert resumo["total_erro_negocio"] == 0
    assert chamadas == []
    assert pdf.exists()
    assert not any(config.processing_dir.glob("*.pdf"))


def test_executar_processamento_automatico_registra_eventos_no_log(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    config.input_dir.mkdir(parents=True, exist_ok=True)
    (config.input_dir / "entrada.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr("auto_processar_pasta.get_config", lambda: config)
    monkeypatch.setattr(
        "auto_processar_pasta.preparar_tabela_produtos",
        lambda: ("df_depara", config.output_reports_dir / "produtos_duplicados_para_revisao.xlsx"),
    )
    monkeypatch.setattr(
        "auto_processar_pasta.processar_pdf",
        lambda caminho_pdf, df_depara: [
            {
                "numero_oc": "630074",
                "quantidade_itens": 1,
                "valor_total": 34.5,
                "status": "ok",
                "caminho_txt": str(config.output_txt_dir / "OC_630074.txt"),
                "caminho_relatorio": str(config.output_reports_dir / "relatorio_conversao_OC_630074.xlsx"),
                "erros": [],
            }
        ],
    )

    resumo = executar_processamento_automatico()

    conteudo = Path(resumo["caminho_log"]).read_text(encoding="utf-8")
    assert "Inicio da execucao automatica." in conteudo
    assert "Quantidade de PDFs encontrados: 1" in conteudo
    assert "Arquivo processado:" in conteudo
    assert "OCs encontradas: 630074" in conteudo
    assert "Status do arquivo: ok" in conteudo
    assert "OC 630074 | TXT gerado:" in conteudo
    assert "Fim da execucao automatica." in conteudo


def test_executar_processamento_automatico_soma_erros_tecnicos_e_de_negocio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    config.input_dir.mkdir(parents=True, exist_ok=True)
    (config.input_dir / "a.pdf").write_bytes(b"%PDF")
    (config.input_dir / "b.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr("auto_processar_pasta.get_config", lambda: config)
    monkeypatch.setattr(
        "auto_processar_pasta.preparar_tabela_produtos",
        lambda: ("df_depara", config.output_reports_dir / "produtos_duplicados_para_revisao.xlsx"),
    )
    resultados = iter(
        [
            {
                "arquivo_original": str(config.input_dir / "a.pdf"),
                "arquivo_processado": str(config.error_dir / "a.pdf"),
                "status": "erro",
                "tipo_erro": "tecnico",
                "resultados": [],
                "ocs_encontradas": [],
                "erros": ["Falha tecnica"],
            },
            {
                "arquivo_original": str(config.input_dir / "b.pdf"),
                "arquivo_processado": str(config.error_dir / "b.pdf"),
                "status": "erro",
                "tipo_erro": "negocio",
                "resultados": [],
                "ocs_encontradas": ["123"],
                "erros": ["Falha de negocio"],
            },
        ]
    )
    monkeypatch.setattr(
        "auto_processar_pasta.arquivo_esta_pronto_para_processamento",
        lambda caminho, stability_wait_seconds, stable_read_checks: True,
    )
    monkeypatch.setattr(
        "auto_processar_pasta.processar_arquivo_automaticamente",
        lambda pdf, df_depara, conf: next(resultados),
    )

    resumo = executar_processamento_automatico()

    assert resumo["total_erro"] == 2
    assert resumo["total_erro_tecnico"] == 1
    assert resumo["total_erro_negocio"] == 1


def test_executar_processamento_automatico_bloqueia_concorrencia(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    config.runner_lock_file.parent.mkdir(parents=True, exist_ok=True)
    config.runner_lock_file.write_text("ocupado", encoding="utf-8")

    monkeypatch.setattr("auto_processar_pasta.get_config", lambda: config)

    resumo = executar_processamento_automatico()

    assert resumo["bloqueado_concorrencia"] is True
    assert resumo["total_pdfs_encontrados"] == 0
    assert resumo["total_erro"] == 0


def test_executar_processamento_automatico_retorna_erro_claro_em_falha_da_tabela(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _build_config(tmp_path)
    config.input_dir.mkdir(parents=True, exist_ok=True)
    (config.input_dir / "a.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr("auto_processar_pasta.get_config", lambda: config)

    def _falhar():
        raise RuntimeError("Erro tecnico ao acessar a tabela de produtos no servidor.")

    monkeypatch.setattr("auto_processar_pasta.preparar_tabela_produtos", _falhar)

    resumo = executar_processamento_automatico()

    assert resumo["total_pdfs_encontrados"] == 1
    assert resumo["total_erro"] == 0
    assert resumo["total_erro_tecnico"] == 1
    assert "Erro tecnico ao acessar a tabela de produtos no servidor." in resumo["erro_inicializacao"]


def _build_config(tmp_path: Path) -> SimpleNamespace:
    raiz = tmp_path / "automacao"
    return SimpleNamespace(
        automation_root=raiz,
        input_dir=raiz / "entrada",
        processing_dir=raiz / "processando",
        processed_dir=raiz / "processados",
        error_dir=raiz / "erro",
        output_dir=raiz / "saida",
        output_txt_dir=raiz / "saida" / "txt_gerados",
        output_reports_dir=raiz / "saida" / "relatorios",
        support_dir=raiz / "apoio",
        logs_dir=raiz / "logs",
        runner_lock_file=raiz / ".automacao_oc.lock",
        ready_file_check_interval_seconds=0,
        ready_file_stable_checks=2,
    )
