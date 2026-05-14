"""Extrai texto bruto de ordens de compra em PDF e salva arquivos de apoio."""

from __future__ import annotations

import re
from pathlib import Path


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai o texto de todas as paginas do PDF preservando a estrutura das linhas."""

    pdf_path = Path(caminho_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF nao encontrado: {pdf_path}")

    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise RuntimeError(
            "pdfplumber nao esta disponivel. Instale as dependencias do projeto."
        ) from exc

    paginas_extraidas: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto_pagina = page.extract_text() or ""
            texto_pagina = _limpar_texto_mantendo_linhas(texto_pagina)
            if texto_pagina.strip():
                paginas_extraidas.append(texto_pagina)

    return "\n".join(paginas_extraidas)


def salvar_texto_extraido(caminho_pdf: str, pasta_saida: str) -> str:
    """Extrai o texto do PDF e salva um arquivo TXT com o mesmo nome base."""

    pdf_path = Path(caminho_pdf)
    output_dir = Path(pasta_saida)
    output_dir.mkdir(parents=True, exist_ok=True)

    texto_extraido = extrair_texto_pdf(caminho_pdf)
    output_path = output_dir / f"{pdf_path.stem}.txt"
    output_path.write_text(texto_extraido, encoding="utf-8")
    return str(output_path)


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Wrapper de compatibilidade para o nome antigo da funcao."""

    return extrair_texto_pdf(str(pdf_path))


def _limpar_texto_mantendo_linhas(texto: str) -> str:
    """Remove excesso de espacos linha a linha sem destruir a estrutura do texto."""

    linhas_limpas: list[str] = []
    for linha in texto.splitlines():
        linha = linha.replace("\r", " ")
        linha = re.sub(r"[ \t]+", " ", linha).strip()
        linhas_limpas.append(linha)

    return "\n".join(linhas_limpas).strip()
