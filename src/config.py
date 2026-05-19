"""Configuracao central do projeto e resolucao de caminhos de trabalho."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_AUTOMATION_ROOT = Path("\\\\Servidor\\arquivos rede\\AUTOMA\u00c7\u00c3O OC")
DEFAULT_READY_FILE_CHECK_INTERVAL_SECONDS = 1.0
DEFAULT_READY_FILE_STABLE_CHECKS = 2


@dataclass(frozen=True)
class AppConfig:
    """Agrupa os caminhos principais usados pelo pipeline da aplicacao."""

    project_root: Path
    automation_root: Path
    input_dir: Path
    processing_dir: Path
    processed_dir: Path
    error_dir: Path
    output_dir: Path
    output_txt_dir: Path
    output_reports_dir: Path
    support_dir: Path
    logs_dir: Path
    runner_lock_file: Path
    examples_dir: Path
    products_mapping_file: Path
    neogrid_reference_pdf: Path
    ready_file_check_interval_seconds: float
    ready_file_stable_checks: int


def get_config() -> AppConfig:
    """Carrega variaveis de ambiente e devolve os caminhos padrao do projeto."""

    load_dotenv()
    project_root = Path(__file__).resolve().parents[1]
    automation_root = _resolve_root_path(
        os.getenv("AUTOMACAO_OC_ROOT"),
        project_root,
        DEFAULT_AUTOMATION_ROOT,
    )

    output_dir = automation_root / "saida"
    support_dir = automation_root / "apoio"

    return AppConfig(
        project_root=project_root,
        automation_root=automation_root,
        input_dir=automation_root / "entrada",
        processing_dir=automation_root / "processando",
        processed_dir=automation_root / "processados",
        error_dir=automation_root / "erro",
        output_dir=output_dir,
        output_txt_dir=output_dir / "txt_gerados",
        output_reports_dir=output_dir / "relatorios",
        support_dir=support_dir,
        logs_dir=automation_root / "logs",
        runner_lock_file=automation_root / ".automacao_oc.lock",
        examples_dir=project_root / "data" / "exemplos",
        products_mapping_file=_resolve_first_existing_path(
            [
                support_dir / "Tabela de produtos.xlsx",
                support_dir / "tabela_produtos.xlsx",
            ]
        ),
        neogrid_reference_pdf=_resolve_first_existing_path(
            [
                support_dir / "NeoGrid PEDIDOS.pdf",
                project_root / "data" / "exemplos" / "ordem_compra_exemplo.pdf",
            ]
        ),
        ready_file_check_interval_seconds=_read_float_env(
            "AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS",
            DEFAULT_READY_FILE_CHECK_INTERVAL_SECONDS,
        ),
        ready_file_stable_checks=_read_int_env(
            "AUTOMACAO_OC_READY_STABLE_CHECKS",
            DEFAULT_READY_FILE_STABLE_CHECKS,
        ),
    )


def _resolve_root_path(
    configured_root: str | None,
    project_root: Path,
    default_root: Path,
) -> Path:
    """Resolve a raiz operacional a partir do ambiente ou do padrao do servidor."""

    if not configured_root:
        return default_root

    candidate = Path(configured_root)
    if candidate.is_absolute():
        return candidate

    return (project_root / candidate).resolve()


def _resolve_first_existing_path(candidates: list[Path]) -> Path:
    """Retorna o primeiro caminho existente ou o primeiro candidato como padrao."""

    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue

    return candidates[0]


def _read_float_env(variable_name: str, default: float) -> float:
    """Le um valor float do ambiente, com fallback seguro para o padrao."""

    raw_value = os.getenv(variable_name)
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError:
        return default


def _read_int_env(variable_name: str, default: int) -> int:
    """Le um valor inteiro do ambiente, com fallback seguro para o padrao."""

    raw_value = os.getenv(variable_name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default
