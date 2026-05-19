"""Testes do orquestrador principal e resolucao de entrada."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import preparar_tabela_produtos, processar_pdf, resolver_pdfs_entrada


def test_resolver_pdfs_entrada_aceita_arquivo_unico(tmp_path: Path) -> None:
    pdf = tmp_path / "ordem.pdf"
    pdf.write_bytes(b"fake")

    resultado = resolver_pdfs_entrada(pdf)

    assert resultado == [pdf]


def test_resolver_pdfs_entrada_lista_pdfs_da_pasta(tmp_path: Path) -> None:
    pdf_b = tmp_path / "b.pdf"
    pdf_a = tmp_path / "a.pdf"
    txt = tmp_path / "nota.txt"
    pdf_b.write_bytes(b"fake")
    pdf_a.write_bytes(b"fake")
    txt.write_text("ignorar", encoding="utf-8")

    resultado = resolver_pdfs_entrada(tmp_path)

    assert resultado == [pdf_a, pdf_b]


def test_preparar_tabela_produtos_retorna_erro_claro_quando_planilha_esta_bloqueada(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = SimpleNamespace(
        products_mapping_file=tmp_path / "Tabela de produtos.xlsx",
        output_reports_dir=tmp_path / "relatorios",
    )
    monkeypatch.setattr("main.get_config", lambda: config)

    def _falhar(_):
        raise PermissionError("Acesso negado")

    monkeypatch.setattr("main.tratar_duplicatas_produtos", _falhar)

    try:
        preparar_tabela_produtos()
    except RuntimeError as exc:
        assert "Erro tecnico ao acessar a tabela de produtos no servidor" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Era esperado erro claro ao falhar a leitura da planilha.")


def test_processar_pdf_mantem_caminho_txt_mesmo_quando_validacao_final_falha(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "ordem.pdf"
    pdf.write_bytes(b"%PDF")
    config = SimpleNamespace(
        output_reports_dir=tmp_path / "relatorios",
        output_txt_dir=tmp_path / "txts",
    )

    monkeypatch.setattr("main.get_config", lambda: config)
    monkeypatch.setattr("main.extrair_texto_pdf", lambda caminho: "texto")
    monkeypatch.setattr(
        "main.parse_ordens_compra",
        lambda texto: [
            {
                "cabecalho": {"numero_oc": "123"},
                "itens": [{"sequencia": 1}],
                "totais": {"total_fornecedor": 10.0},
            }
        ],
    )
    monkeypatch.setattr("main.gerar_relatorio_conversao", lambda dados_oc, df: object())
    monkeypatch.setattr(
        "main.salvar_relatorio_conversao",
        lambda relatorio, pasta, numero_oc: Path(pasta) / f"relatorio_conversao_OC_{numero_oc}.xlsx",
    )
    monkeypatch.setattr(
        "main.validar_processamento",
        lambda dados_oc, relatorio, caminho_txt=None: (
            {"status": "ok", "erros": []}
            if caminho_txt is None
            else {"status": "erro", "erros": ["Falha final"]}
        ),
    )
    monkeypatch.setattr(
        "main.gerar_txt_neogrid",
        lambda dados_oc, relatorio, caminho_saida: Path(caminho_saida) / "OC_123.txt",
    )

    resultados = processar_pdf(pdf, object())

    assert resultados[0]["status"] == "erro"
    assert resultados[0]["caminho_txt"].endswith("OC_123.txt")
