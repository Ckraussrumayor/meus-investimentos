"""
Motor de Benchmarks.

Calcula a evolução de benchmarks de mercado para comparação
com a carteira do usuário.
"""

from app.utils.financial_calculations import annual_to_monthly_rate
from app.utils.constants import BENCHMARK_DEFAULTS
from app.models.scenario import ScenarioParameters


class BenchmarkEngine:
    """Calcula benchmarks para comparação."""

    def __init__(self, params: ScenarioParameters | None = None):
        """Inicializa com os parâmetros do cenário.

        Args:
            params: Parâmetros do cenário com taxas de referência.
        """
        if params:
            self.rates = {
                "cdi": annual_to_monthly_rate(params.cdi),
                "ipca": annual_to_monthly_rate(params.ipca),
                "selic": annual_to_monthly_rate(params.selic),
                "ibov": annual_to_monthly_rate(BENCHMARK_DEFAULTS["IBOV"]),
                "ifix": annual_to_monthly_rate(BENCHMARK_DEFAULTS["IFIX"]),
            }
        else:
            self.rates = {
                "cdi": annual_to_monthly_rate(BENCHMARK_DEFAULTS["CDI"]),
                "ipca": annual_to_monthly_rate(BENCHMARK_DEFAULTS["IPCA"]),
                "selic": annual_to_monthly_rate(BENCHMARK_DEFAULTS["SELIC"]),
                "ibov": annual_to_monthly_rate(BENCHMARK_DEFAULTS["IBOV"]),
                "ifix": annual_to_monthly_rate(BENCHMARK_DEFAULTS["IFIX"]),
            }

    def calculate_month(self, month: int, initial_value: float) -> dict:
        """Calcula o valor dos benchmarks para um dado mês.

        Args:
            month: Número do mês na projeção.
            initial_value: Valor inicial para o benchmark.

        Returns:
            Dicionário com valores dos benchmarks.
        """
        return {
            benchmark: initial_value * (1 + rate) ** month
            for benchmark, rate in self.rates.items()
        }

    def calculate_full_projection(
        self, months: int, initial_value: float
    ) -> list[dict]:
        """Calcula a projeção completa de todos os benchmarks.

        Args:
            months: Número total de meses.
            initial_value: Valor inicial.

        Returns:
            Lista de dicts com valores mensais de cada benchmark.
        """
        projections = []
        for month in range(1, months + 1):
            values = self.calculate_month(month, initial_value)
            values["month"] = month
            projections.append(values)
        return projections

    def get_annual_rates(self) -> dict:
        """Retorna as taxas anuais configuradas."""
        return {
            name: round(((1 + rate) ** 12 - 1) * 100, 2)
            for name, rate in self.rates.items()
        }

    def compare_with_portfolio(
        self, portfolio_projections: list, initial_value: float
    ) -> dict:
        """Compara a performance do portfólio com os benchmarks.

        Args:
            portfolio_projections: Projeções do portfólio.
            initial_value: Valor inicial do investimento.

        Returns:
            Dicionário com comparações de performance.
        """
        if not portfolio_projections:
            return {}

        last_month = portfolio_projections[-1]
        final_portfolio = last_month.get("total_assets", 0)
        months = last_month.get("month", 0)

        benchmarks = self.calculate_month(months, initial_value)
        portfolio_return = (
            (final_portfolio / initial_value - 1) * 100 if initial_value > 0 else 0
        )

        comparison = {
            "portfolio": {
                "final_value": round(final_portfolio, 2),
                "total_return_pct": round(portfolio_return, 2),
            }
        }

        for name, value in benchmarks.items():
            bench_return = (value / initial_value - 1) * 100 if initial_value > 0 else 0
            comparison[name] = {
                "final_value": round(value, 2),
                "total_return_pct": round(bench_return, 2),
                "vs_portfolio": round(portfolio_return - bench_return, 2),
            }

        return comparison
