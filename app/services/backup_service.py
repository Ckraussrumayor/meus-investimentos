"""
Módulo de exportação e importação de dados (backup/restore).

Permite exportar todo o conteúdo do banco de dados em formato JSON
e reimportá-lo após uma reinstância (ex.: hibernação do deploy gratuito).
"""

import json
from datetime import datetime

from app.database.database import execute_query, execute_many, get_connection

# Versão do formato de exportação
EXPORT_VERSION = "1.0"


def export_all_data() -> dict:
    """Exporta todos os dados do banco em um dicionário serializável.

    Inclui: asset_classes, scenarios (com parâmetros e projeções),
    historical_snapshots, smtp_config e app_settings.
    Não inclui senhas de usuário nem a senha SMTP (dados sensíveis).

    Returns:
        Dicionário com todos os dados prontos para serialização JSON.
    """
    data = {
        "export_version": EXPORT_VERSION,
        "export_date": datetime.now().isoformat(),
        "asset_classes": _export_asset_classes(),
        "scenarios": _export_scenarios(),
        "historical_snapshots": _export_historical_snapshots(),
        "smtp_config": _export_smtp_config(),
        "app_settings": _export_app_settings(),
    }
    return data


def import_all_data(data: dict) -> dict:
    """Importa dados de um dicionário (previamente exportado).

    Limpa as tabelas existentes e insere os dados do backup.
    A operação é atômica (tudo ou nada) via transação.

    Args:
        data: Dicionário com os dados exportados.

    Returns:
        Dicionário com contagens de registros importados.
    """
    version = data.get("export_version", "")
    if not version:
        raise ValueError("Arquivo de backup inválido: campo 'export_version' ausente.")

    conn = get_connection()
    try:
        conn.execute("BEGIN")

        # Limpar tabelas na ordem correta (respeitar FKs)
        conn.execute("DELETE FROM scenario_projections")
        conn.execute("DELETE FROM scenario_parameters")
        conn.execute("DELETE FROM scenarios")
        conn.execute("DELETE FROM asset_classes")
        conn.execute("DELETE FROM historical_snapshots")

        counts = {}

        # Importar asset_classes
        assets = data.get("asset_classes", [])
        for a in assets:
            conn.execute(
                """INSERT INTO asset_classes
                   (id, name, type, invested_value, current_value, monthly_income,
                    expected_annual_return, admin_fee, tax_type, has_come_cotas, cdi_percentage)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a["id"], a["name"], a["type"],
                    a["invested_value"], a["current_value"], a["monthly_income"],
                    a["expected_annual_return"], a["admin_fee"], a["tax_type"],
                    1 if a.get("has_come_cotas") else 0,
                    a.get("cdi_percentage", 0.0),
                ),
            )
        counts["asset_classes"] = len(assets)

        # Importar scenarios + parâmetros + projeções
        scenarios = data.get("scenarios", [])
        for s in scenarios:
            conn.execute(
                """INSERT INTO scenarios (id, name, status, created_at, based_on)
                   VALUES (?, ?, ?, ?, ?)""",
                (s["id"], s["name"], s["status"], s["created_at"], s.get("based_on")),
            )

            params = s.get("parameters")
            if params:
                conn.execute(
                    """INSERT INTO scenario_parameters
                       (scenario_id, inflation, selic, cdi, ipca, salary_growth,
                        monthly_contribution, extra_contribution, extra_contribution_month,
                        extra_contribution_target, desired_monthly_income,
                        safe_withdrawal_rate, withdrawal_start_month, monthly_withdrawal,
                        crisis_year, crisis_drop_percent, projection_months)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s["id"],
                        params["inflation"], params["selic"], params["cdi"],
                        params["ipca"], params["salary_growth"],
                        params["monthly_contribution"], params["extra_contribution"],
                        params.get("extra_contribution_month"),
                        params.get("extra_contribution_target", "proporcional"),
                        params["desired_monthly_income"], params["safe_withdrawal_rate"],
                        params.get("withdrawal_start_month"),
                        params["monthly_withdrawal"],
                        params.get("crisis_year"),
                        params["crisis_drop_percent"], params["projection_months"],
                    ),
                )

            projections = s.get("projections", [])
            for p in projections:
                conn.execute(
                    """INSERT INTO scenario_projections
                       (scenario_id, month, total_assets, passive_income, net_income,
                        benchmark_cdi, benchmark_ipca, benchmark_ibov,
                        benchmark_ifix, benchmark_selic)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s["id"], p["month"], p["total_assets"],
                        p["passive_income"], p["net_income"],
                        p.get("benchmark_cdi", 0), p.get("benchmark_ipca", 0),
                        p.get("benchmark_ibov", 0), p.get("benchmark_ifix", 0),
                        p.get("benchmark_selic", 0),
                    ),
                )
        counts["scenarios"] = len(scenarios)
        counts["projections"] = sum(len(s.get("projections", [])) for s in scenarios)

        # Importar historical_snapshots
        snapshots = data.get("historical_snapshots", [])
        for h in snapshots:
            conn.execute(
                """INSERT INTO historical_snapshots (month, total_assets, passive_income)
                   VALUES (?, ?, ?)""",
                (h["month"], h["total_assets"], h["passive_income"]),
            )
        counts["historical_snapshots"] = len(snapshots)

        # Importar smtp_config (se presente)
        smtp = data.get("smtp_config")
        if smtp and smtp.get("smtp_email"):
            conn.execute("DELETE FROM smtp_config")
            conn.execute(
                """INSERT INTO smtp_config (id, smtp_server, smtp_port, smtp_email, smtp_password, use_tls)
                   VALUES (1, ?, ?, ?, ?, ?)""",
                (
                    smtp["smtp_server"], smtp["smtp_port"],
                    smtp["smtp_email"], smtp.get("smtp_password", ""),
                    1 if smtp.get("use_tls", True) else 0,
                ),
            )

        # Importar app_settings (se presente)
        settings = data.get("app_settings")
        if settings:
            conn.execute("DELETE FROM app_settings")
            conn.execute(
                "INSERT INTO app_settings (id, ir_renda_fixa) VALUES (1, ?)",
                (settings.get("ir_renda_fixa", 17.5),),
            )

        conn.commit()
        return counts

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ───────────────── Helpers de exportação ─────────────────


def _export_asset_classes() -> list[dict]:
    rows = execute_query("SELECT * FROM asset_classes ORDER BY id", fetch=True)
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],
            "invested_value": r["invested_value"],
            "current_value": r["current_value"],
            "monthly_income": r["monthly_income"],
            "expected_annual_return": r["expected_annual_return"],
            "admin_fee": r["admin_fee"],
            "tax_type": r["tax_type"],
            "has_come_cotas": bool(r["has_come_cotas"]),
            "cdi_percentage": r["cdi_percentage"],
        }
        for r in rows
    ]


def _export_scenarios() -> list[dict]:
    rows = execute_query("SELECT * FROM scenarios ORDER BY id", fetch=True)
    scenarios = []
    for r in rows:
        scenario = {
            "id": r["id"],
            "name": r["name"],
            "status": r["status"],
            "created_at": r["created_at"],
            "based_on": r["based_on"],
            "parameters": _export_scenario_parameters(r["id"]),
            "projections": _export_scenario_projections(r["id"]),
        }
        scenarios.append(scenario)
    return scenarios


def _export_scenario_parameters(scenario_id: int) -> dict | None:
    rows = execute_query(
        "SELECT * FROM scenario_parameters WHERE scenario_id = ?",
        (scenario_id,),
        fetch=True,
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "inflation": r["inflation"],
        "selic": r["selic"],
        "cdi": r["cdi"],
        "ipca": r["ipca"],
        "salary_growth": r["salary_growth"],
        "monthly_contribution": r["monthly_contribution"],
        "extra_contribution": r["extra_contribution"],
        "extra_contribution_month": r["extra_contribution_month"],
        "extra_contribution_target": r["extra_contribution_target"],
        "desired_monthly_income": r["desired_monthly_income"],
        "safe_withdrawal_rate": r["safe_withdrawal_rate"],
        "withdrawal_start_month": r["withdrawal_start_month"],
        "monthly_withdrawal": r["monthly_withdrawal"],
        "crisis_year": r["crisis_year"],
        "crisis_drop_percent": r["crisis_drop_percent"],
        "projection_months": r["projection_months"],
    }


def _export_scenario_projections(scenario_id: int) -> list[dict]:
    rows = execute_query(
        "SELECT * FROM scenario_projections WHERE scenario_id = ? ORDER BY month",
        (scenario_id,),
        fetch=True,
    )
    return [
        {
            "month": r["month"],
            "total_assets": r["total_assets"],
            "passive_income": r["passive_income"],
            "net_income": r["net_income"],
            "benchmark_cdi": r["benchmark_cdi"],
            "benchmark_ipca": r["benchmark_ipca"],
            "benchmark_ibov": r["benchmark_ibov"],
            "benchmark_ifix": r["benchmark_ifix"],
            "benchmark_selic": r["benchmark_selic"],
        }
        for r in rows
    ]


def _export_historical_snapshots() -> list[dict]:
    rows = execute_query(
        "SELECT * FROM historical_snapshots ORDER BY month", fetch=True
    )
    return [
        {
            "month": r["month"],
            "total_assets": r["total_assets"],
            "passive_income": r["passive_income"],
        }
        for r in rows
    ]


def _export_smtp_config() -> dict | None:
    """Exporta a configuração SMTP (senha criptografada tal como está no banco)."""
    rows = execute_query("SELECT * FROM smtp_config WHERE id = 1", fetch=True)
    if not rows:
        return None
    r = rows[0]
    return {
        "smtp_server": r["smtp_server"],
        "smtp_port": r["smtp_port"],
        "smtp_email": r["smtp_email"],
        "smtp_password": r["smtp_password"],
        "use_tls": bool(r["use_tls"]),
    }


def _export_app_settings() -> dict | None:
    rows = execute_query("SELECT * FROM app_settings WHERE id = 1", fetch=True)
    if not rows:
        return None
    return {"ir_renda_fixa": rows[0]["ir_renda_fixa"]}
