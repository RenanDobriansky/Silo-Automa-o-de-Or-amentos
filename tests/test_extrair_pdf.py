"""Testes da extracao de texto bruto a partir de arquivos PDF."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extrair_pdf import extrair_texto_pdf, salvar_texto_extraido


class _FakePage:
    """Pagina fake com retorno controlado de texto."""

    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    """Context manager fake para simular pdfplumber.open."""

    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self) -> "_FakePdf":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_extrair_texto_pdf_retorna_texto(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "ordem.pdf"
    pdf_path.write_bytes(b"fake-pdf")

    fake_pdf = _FakePdf(
        [
            _FakePage("PEDIDO: 123\nITEM   1"),
            _FakePage("FORNECEDOR: Teste\n\nITEM   2"),
        ]
    )

    class _FakePdfPlumber:
        @staticmethod
        def open(path: Path) -> _FakePdf:
            assert path == pdf_path
            return fake_pdf

    monkeypatch.setitem(sys.modules, "pdfplumber", _FakePdfPlumber)

    texto = extrair_texto_pdf(str(pdf_path))

    assert "PEDIDO: 123" in texto
    assert "ITEM 1" in texto
    assert "FORNECEDOR: Teste" in texto
    assert "ITEM 2" in texto


def test_salvar_texto_extraido_cria_txt(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "ordem_compra.pdf"
    pdf_path.write_bytes(b"fake-pdf")
    pasta_saida = tmp_path / "saida"

    fake_pdf = _FakePdf([_FakePage("LINHA 1\nLINHA 2")])

    class _FakePdfPlumber:
        @staticmethod
        def open(path: Path) -> _FakePdf:
            assert path == pdf_path
            return fake_pdf

    monkeypatch.setitem(sys.modules, "pdfplumber", _FakePdfPlumber)

    caminho_txt = salvar_texto_extraido(str(pdf_path), str(pasta_saida))
    arquivo_salvo = Path(caminho_txt)

    assert arquivo_salvo.exists()
    assert arquivo_salvo.name == "ordem_compra.txt"
    assert arquivo_salvo.read_text(encoding="utf-8") == "LINHA 1\nLINHA 2"
