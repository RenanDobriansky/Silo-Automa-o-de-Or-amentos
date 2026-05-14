"""Testes do orquestrador principal e resolucao de entrada."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import resolver_pdfs_entrada


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
