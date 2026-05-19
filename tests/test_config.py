"""Testes da configuracao central de caminhos do projeto."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import get_config


def test_get_config_monta_caminhos_do_servidor_a_partir_do_root_configurado(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raiz = tmp_path / "AUTOMAÇÃO OC"
    apoio = raiz / "apoio"
    apoio.mkdir(parents=True)
    (apoio / "Tabela de produtos.xlsx").write_text("fake", encoding="utf-8")
    (apoio / "NeoGrid PEDIDOS.pdf").write_bytes(b"%PDF")
    monkeypatch.setenv("AUTOMACAO_OC_ROOT", str(raiz))
    monkeypatch.setenv("AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS", "2.5")
    monkeypatch.setenv("AUTOMACAO_OC_READY_STABLE_CHECKS", "3")

    config = get_config()

    assert config.automation_root == raiz
    assert config.input_dir == raiz / "entrada"
    assert config.processing_dir == raiz / "processando"
    assert config.processed_dir == raiz / "processados"
    assert config.error_dir == raiz / "erro"
    assert config.output_dir == raiz / "saida"
    assert config.output_txt_dir == raiz / "saida" / "txt_gerados"
    assert config.output_reports_dir == raiz / "saida" / "relatorios"
    assert config.support_dir == apoio
    assert config.logs_dir == raiz / "logs"
    assert config.runner_lock_file == raiz / ".automacao_oc.lock"
    assert config.products_mapping_file == apoio / "Tabela de produtos.xlsx"
    assert config.neogrid_reference_pdf == apoio / "NeoGrid PEDIDOS.pdf"
    assert config.ready_file_check_interval_seconds == 2.5
    assert config.ready_file_stable_checks == 3


def test_get_config_resolve_root_relativo_ao_projeto(monkeypatch) -> None:
    monkeypatch.setenv("AUTOMACAO_OC_ROOT", "ambiente_servidor/AUTOMAÇÃO OC")

    config = get_config()

    assert config.automation_root == (
        config.project_root / "ambiente_servidor" / "AUTOMAÇÃO OC"
    ).resolve()
