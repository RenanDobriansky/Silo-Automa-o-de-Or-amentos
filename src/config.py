"""Configuracao central do projeto e resolucao de caminhos de trabalho."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    """Agrupa os caminhos principais usados pelo pipeline da aplicacao."""

    project_root: Path
    input_dir: Path
    output_txt_dir: Path
    output_reports_dir: Path
    support_dir: Path
    examples_dir: Path
    products_mapping_file: Path
    neogrid_reference_pdf: Path


def get_config() -> AppConfig:
    """Carrega variaveis de ambiente e devolve os caminhos padrao do projeto."""

    load_dotenv()
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    support_dir = data_dir / "apoio"

    return AppConfig(
        project_root=project_root,
        input_dir=data_dir / "entrada" / "ordens_pdf",
        output_txt_dir=data_dir / "saida" / "txt_gerados",
        output_reports_dir=data_dir / "saida" / "relatorios",
        support_dir=support_dir,
        examples_dir=data_dir / "exemplos",
        products_mapping_file=_resolve_first_existing_path(
            [
                support_dir / "Tabela de produtos.xlsx",
                support_dir / "tabela_produtos.xlsx",
            ]
        ),
        neogrid_reference_pdf=_resolve_first_existing_path(
            [
                support_dir / "NeoGrid PEDIDOS.pdf",
                data_dir / "exemplos" / "ordem_compra_exemplo.pdf",
            ]
        ),
    )


def _resolve_first_existing_path(candidates: list[Path]) -> Path:
    """Retorna o primeiro caminho existente ou o primeiro candidato como padrao."""

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]
