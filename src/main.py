"""Orquestra o processamento completo de uma ordem de compra em PDF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import get_config
from extrair_pdf import extrair_texto_pdf
from gerar_txt_neogrid import gerar_txt_neogrid
from parser_oc import parse_ordens_compra
from produtos_depara import carregar_depara_produtos
from relatorio_processamento import gerar_relatorio_conversao, salvar_relatorio_conversao
from tratar_duplicatas import tratar_duplicatas_produtos
from validar_txt import validar_processamento


def preparar_tabela_produtos() -> tuple[Any, Path]:
    """Trata duplicatas e carrega a tabela limpa de produtos uma unica vez."""

    config = get_config()
    tabela_produtos_path = config.products_mapping_file
    try:
        tratar_duplicatas_produtos(str(tabela_produtos_path))
    except OSError as exc:
        raise RuntimeError(
            "Erro tecnico ao acessar a tabela de produtos no servidor. "
            f"Verifique permissoes, bloqueio do arquivo ou disponibilidade de rede: {tabela_produtos_path}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            "Falha ao preparar a tabela de produtos para processamento automatico. "
            f"Arquivo analisado: {tabela_produtos_path}"
        ) from exc

    caminho_produtos_unicos = config.output_reports_dir / "produtos_unicos.xlsx"
    caminho_revisao_duplicatas = config.output_reports_dir / "produtos_duplicados_para_revisao.xlsx"

    try:
        df_depara = carregar_depara_produtos(str(caminho_produtos_unicos))
    except OSError as exc:
        raise RuntimeError(
            "Erro tecnico ao carregar a tabela tratada de produtos. "
            f"Verifique acesso ao arquivo: {caminho_produtos_unicos}"
        ) from exc
    return df_depara, caminho_revisao_duplicatas


def resolver_pdfs_entrada(caminho_entrada: str | Path) -> list[Path]:
    """Resolve um arquivo unico ou uma pasta em uma lista ordenada de PDFs."""

    entrada = Path(caminho_entrada)
    if not entrada.exists():
        raise FileNotFoundError(f"Caminho nao encontrado: {entrada}")

    if entrada.is_file():
        if entrada.suffix.lower() != ".pdf":
            raise ValueError(f"O arquivo informado nao e um PDF: {entrada}")
        return [entrada]

    pdfs = sorted(entrada.glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"Nenhum PDF encontrado na pasta: {entrada}")
    return pdfs


def processar_pdf(caminho_pdf: str | Path, df_depara: Any) -> list[dict[str, Any]]:
    """Executa o fluxo completo de conversao para um PDF de entrada."""

    config = get_config()
    pdf_path = Path(caminho_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF nao encontrado: {pdf_path}")

    texto_extraido = extrair_texto_pdf(str(pdf_path))
    ordens = parse_ordens_compra(texto_extraido)

    if not ordens:
        raise ValueError("Nenhuma ordem de compra foi identificada no PDF informado.")

    resultados: list[dict[str, Any]] = []
    for dados_oc in ordens:
        numero_oc = str(dados_oc.get("cabecalho", {}).get("numero_oc", "")).strip()
        relatorio = gerar_relatorio_conversao(dados_oc, df_depara)
        caminho_relatorio = salvar_relatorio_conversao(
            relatorio,
            str(config.output_reports_dir),
            numero_oc or "sem_numero",
        )

        validacao_previa = validar_processamento(dados_oc, relatorio)
        quantidade_itens = len(dados_oc.get("itens", []))
        valor_total = float(dados_oc.get("totais", {}).get("total_fornecedor", 0) or 0)

        if validacao_previa["status"] == "erro":
            resultados.append(
                {
                    "numero_oc": numero_oc,
                    "quantidade_itens": quantidade_itens,
                    "valor_total": valor_total,
                    "status": "erro",
                    "caminho_txt": "",
                    "caminho_relatorio": str(caminho_relatorio),
                    "erros": validacao_previa["erros"],
                }
            )
            break

        caminho_txt = gerar_txt_neogrid(dados_oc, relatorio, config.output_txt_dir)
        validacao_final = validar_processamento(dados_oc, relatorio, caminho_txt)

        resultados.append(
            {
                "numero_oc": numero_oc,
                "quantidade_itens": quantidade_itens,
                "valor_total": valor_total,
                "status": validacao_final["status"],
                "caminho_txt": str(caminho_txt),
                "caminho_relatorio": str(caminho_relatorio),
                "erros": validacao_final["erros"],
            }
        )

        if validacao_final["status"] == "erro":
            break

    return resultados


def main(argv: list[str] | None = None) -> int:
    """Executa o processamento completo a partir de um PDF ou pasta informados via CLI."""

    parser = argparse.ArgumentParser(
        description="Processa ordens de compra em PDF e gera TXT NeoGrid."
    )
    parser.add_argument(
        "caminho_entrada",
        help="Caminho de um PDF ou de uma pasta contendo PDFs de ordens de compra.",
    )
    args = parser.parse_args(argv)

    try:
        pdfs = resolver_pdfs_entrada(args.caminho_entrada)
        df_depara, _ = preparar_tabela_produtos()
    except Exception as exc:
        print(f"Status do processamento: erro")
        print(str(exc))
        return 1

    exit_code = 0
    for pdf_path in pdfs:
        try:
            resultados = processar_pdf(pdf_path, df_depara)
        except Exception as exc:
            print(f"Arquivo processado: {pdf_path}")
            print("Status do processamento: erro")
            print(str(exc))
            return 1

        for resultado in resultados:
            print(f"Arquivo processado: {pdf_path}")
            print(f"Numero da OC: {resultado['numero_oc']}")
            print(f"Quantidade de itens: {resultado['quantidade_itens']}")
            print(f"Valor total: {resultado['valor_total']:.2f}")
            print(f"Status do processamento: {resultado['status']}")
            print(f"Caminho do TXT gerado: {resultado['caminho_txt'] or '-'}")
            print(f"Caminho do relatorio gerado: {resultado['caminho_relatorio']}")

            if resultado["erros"]:
                exit_code = 1
                for erro in resultado["erros"]:
                    print(f"Erro: {erro}")
                print(
                    "Processamento interrompido. Consulte o relatorio de revisao em: "
                    f"{resultado['caminho_relatorio']}"
                )
                return exit_code

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
