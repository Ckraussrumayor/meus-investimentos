"""
Model para Cenários de simulação.
"""

from dataclasses import dataclass
from app.database.database import execute_query, get_connection


@dataclass
class ScenarioParameters:
    scenario_id: int
    inflation: float
    selic: float
    cdi: float
    ipca: float
    salary_growth: float
    monthly_contribution: float
    extra_contribution: float
    extra_contribution_month: int | None
    extra_contribution_target: str
    desired_monthly_income: float
    safe_withdrawal_rate: float
    withdrawal_start_month: int | None
    monthly_withdrawal: float
    crisis_year: int | None
    crisis_drop_percent: float
    projection_months: int


@dataclass
class Scenario:
    id: int | None
    name: str
    status: str
    created_at: str
    based_on: int | None

    @staticmethod
    def create(name: str, based_on: int | None = None) -> int:
        """Cria um novo cenário."""
        scenario_id = execute_query(
            "INSERT INTO scenarios (name, status, based_on) VALUES (?, 'editavel', ?)",
            (name, based_on),
        )
        # Criar parâmetros padrão
        if based_on:
            # Copiar parâmetros do cenário base
            params = Scenario.get_parameters(based_on)
            if params:
                execute_query(
                    """INSERT INTO scenario_parameters 
                       (scenario_id, inflation, selic, cdi, ipca, salary_growth,
                        monthly_contribution, extra_contribution, extra_contribution_month,
                        extra_contribution_target,
                        desired_monthly_income, safe_withdrawal_rate,
                        withdrawal_start_month, monthly_withdrawal,
                        crisis_year, crisis_drop_percent, projection_months)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        scenario_id,
                        params.inflation,
                        params.selic,
                        params.cdi,
                        params.ipca,
                        params.salary_growth,
                        params.monthly_contribution,
                        params.extra_contribution,
                        params.extra_contribution_month,
                        params.extra_contribution_target,
                        params.desired_monthly_income,
                        params.safe_withdrawal_rate,
                        params.withdrawal_start_month,
                        params.monthly_withdrawal,
                        params.crisis_year,
                        params.crisis_drop_percent,
                        params.projection_months,
                    ),
                )
            else:
                Scenario._create_default_parameters(scenario_id)
        else:
            Scenario._create_default_parameters(scenario_id)

        return scenario_id

    @staticmethod
    def _create_default_parameters(scenario_id: int):
        """Cria parâmetros padrão para um cenário."""
        execute_query(
            """INSERT INTO scenario_parameters 
               (scenario_id, inflation, selic, cdi, ipca, salary_growth,
                monthly_contribution, extra_contribution, extra_contribution_month,
                extra_contribution_target,
                desired_monthly_income, safe_withdrawal_rate,
                withdrawal_start_month, monthly_withdrawal,
                crisis_year, crisis_drop_percent, projection_months)
               VALUES (?, 4.5, 13.75, 13.65, 4.5, 3.0, 0, 0, NULL, 'proporcional', 5000, 4.0, NULL, 0, NULL, 0, 360)""",
            (scenario_id,),
        )

    @staticmethod
    def get_all() -> list:
        """Retorna todos os cenários."""
        rows = execute_query(
            "SELECT * FROM scenarios ORDER BY created_at DESC", fetch=True
        )
        return [Scenario._from_row(row) for row in rows]

    @staticmethod
    def get_by_id(scenario_id: int):
        """Retorna um cenário por ID."""
        rows = execute_query(
            "SELECT * FROM scenarios WHERE id = ?", (scenario_id,), fetch=True
        )
        if rows:
            return Scenario._from_row(rows[0])
        return None

    @staticmethod
    def update_parameters(scenario_id: int, **kwargs):
        """Atualiza os parâmetros de um cenário."""
        # Verificar se o cenário é editável
        scenario = Scenario.get_by_id(scenario_id)
        if not scenario or scenario.status == "congelado":
            return False

        valid_fields = [
            "inflation", "selic", "cdi", "ipca", "salary_growth",
            "monthly_contribution", "extra_contribution", "extra_contribution_month",
            "extra_contribution_target",
            "desired_monthly_income", "safe_withdrawal_rate",
            "withdrawal_start_month", "monthly_withdrawal",
            "crisis_year", "crisis_drop_percent", "projection_months",
        ]

        set_clauses = []
        values = []
        for field, value in kwargs.items():
            if field in valid_fields:
                set_clauses.append(f"{field} = ?")
                values.append(value)

        if not set_clauses:
            return False

        values.append(scenario_id)
        execute_query(
            f"UPDATE scenario_parameters SET {', '.join(set_clauses)} WHERE scenario_id = ?",
            tuple(values),
        )
        return True

    @staticmethod
    def get_parameters(scenario_id: int) -> ScenarioParameters | None:
        """Retorna os parâmetros de um cenário."""
        rows = execute_query(
            "SELECT * FROM scenario_parameters WHERE scenario_id = ?",
            (scenario_id,),
            fetch=True,
        )
        if not rows:
            return None

        row = rows[0]
        return ScenarioParameters(
            scenario_id=row["scenario_id"],
            inflation=row["inflation"],
            selic=row["selic"],
            cdi=row["cdi"],
            ipca=row["ipca"],
            salary_growth=row["salary_growth"],
            monthly_contribution=row["monthly_contribution"],
            extra_contribution=row["extra_contribution"],
            extra_contribution_month=row["extra_contribution_month"],
            extra_contribution_target=row["extra_contribution_target"] if "extra_contribution_target" in row.keys() else "proporcional",
            desired_monthly_income=row["desired_monthly_income"],
            safe_withdrawal_rate=row["safe_withdrawal_rate"],
            withdrawal_start_month=row["withdrawal_start_month"],
            monthly_withdrawal=row["monthly_withdrawal"],
            crisis_year=row["crisis_year"],
            crisis_drop_percent=row["crisis_drop_percent"],
            projection_months=row["projection_months"],
        )

    @staticmethod
    def freeze(scenario_id: int):
        """Congela um cenário (snapshot)."""
        execute_query(
            "UPDATE scenarios SET status = 'congelado' WHERE id = ?",
            (scenario_id,),
        )

    @staticmethod
    def duplicate(scenario_id: int, new_name: str) -> int:
        """Duplica um cenário existente."""
        return Scenario.create(new_name, based_on=scenario_id)

    @staticmethod
    def delete(scenario_id: int):
        """Exclui um cenário e seus dados relacionados."""
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM scenario_projections WHERE scenario_id = ?",
                (scenario_id,),
            )
            conn.execute(
                "DELETE FROM scenario_parameters WHERE scenario_id = ?",
                (scenario_id,),
            )
            conn.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def save_projections(scenario_id: int, projections: list):
        """Salva as projeções de um cenário.

        Args:
            scenario_id: ID do cenário.
            projections: Lista de dicts com dados de projeção por mês.
        """
        conn = get_connection()
        try:
            # Limpar projeções anteriores
            conn.execute(
                "DELETE FROM scenario_projections WHERE scenario_id = ?",
                (scenario_id,),
            )
            for proj in projections:
                conn.execute(
                    """INSERT INTO scenario_projections 
                       (scenario_id, month, total_assets, passive_income, net_income,
                        benchmark_cdi, benchmark_ipca, benchmark_ibov,
                        benchmark_ifix, benchmark_selic)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        scenario_id,
                        proj["month"],
                        proj["total_assets"],
                        proj["passive_income"],
                        proj["net_income"],
                        proj.get("benchmark_cdi", 0),
                        proj.get("benchmark_ipca", 0),
                        proj.get("benchmark_ibov", 0),
                        proj.get("benchmark_ifix", 0),
                        proj.get("benchmark_selic", 0),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_projections(scenario_id: int) -> list:
        """Retorna as projeções de um cenário."""
        rows = execute_query(
            """SELECT * FROM scenario_projections 
               WHERE scenario_id = ? ORDER BY month""",
            (scenario_id,),
            fetch=True,
        )
        return [dict(row) for row in rows]

    @staticmethod
    def _from_row(row) -> "Scenario":
        """Converte uma linha do banco em um objeto Scenario."""
        return Scenario(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            created_at=row["created_at"],
            based_on=row["based_on"],
        )
