"""
Motor de Projeção Patrimonial.

Realiza a simulação mês a mês considerando:
- Juros compostos
- Aportes mensais e extras
- Retiradas programadas
- Reinvestimento automático
- Crise simulada
- Correção pela inflação
"""

import pandas as pd
from app.utils.financial_calculations import (
    annual_to_monthly_rate,
    adjust_for_inflation,
)
from app.models.asset_class import AssetClass
from app.models.scenario import Scenario, ScenarioParameters
from app.services.tax_engine import TaxEngine
from app.services.income_engine import IncomeEngine
from app.services.benchmark_engine import BenchmarkEngine


class ProjectionEngine:
    """Motor principal de projeção patrimonial."""

    def __init__(self, scenario_id: int):
        self.scenario_id = scenario_id
        self.scenario = Scenario.get_by_id(scenario_id)
        self.params = Scenario.get_parameters(scenario_id)
        self.assets = AssetClass.get_all()
        self.tax_engine = TaxEngine()
        self.income_engine = IncomeEngine()
        self.benchmark_engine = BenchmarkEngine(self.params)

    def run_projection(self) -> list[dict]:
        """Executa a projeção completa mês a mês.

        Returns:
            Lista de dicts com dados de projeção para cada mês.
        """
        if not self.params or not self.assets:
            return []

        projections = []

        # Valores iniciais
        total_current = sum(a.current_value for a in self.assets)
        total_monthly_income = sum(a.monthly_income for a in self.assets)

        # Taxas mensais
        weighted_annual_return = self._get_weighted_return()
        monthly_return = annual_to_monthly_rate(weighted_annual_return)
        monthly_admin_fee = self._get_weighted_admin_fee() / 12 / 100
        monthly_inflation = annual_to_monthly_rate(self.params.inflation)

        # Benchmark inicial
        benchmark_initial = total_current

        for month in range(1, self.params.projection_months + 1):
            # 1. Aplicar rendimento
            gross_return = total_current * monthly_return
            admin_fee_value = total_current * monthly_admin_fee
            net_return = gross_return - admin_fee_value

            # 2. Verificar crise
            if self.params.crisis_year and self.params.crisis_drop_percent > 0:
                crisis_month = self.params.crisis_year * 12
                if month == crisis_month:
                    drop = total_current * (self.params.crisis_drop_percent / 100)
                    total_current -= drop

            # 3. Aplicar aporte mensal
            contribution = self.params.monthly_contribution

            # Crescimento salarial incorporado ao aporte (anual)
            if self.params.salary_growth > 0 and month > 12:
                years_passed = (month - 1) // 12
                growth_factor = (1 + self.params.salary_growth / 100) ** years_passed
                contribution = self.params.monthly_contribution * growth_factor

            # 4. Aporte extra pontual
            extra = 0
            if (
                self.params.extra_contribution > 0
                and self.params.extra_contribution_month
                and month == self.params.extra_contribution_month
            ):
                extra = self.params.extra_contribution

            # 5. Retirada programada
            withdrawal = 0
            if (
                self.params.withdrawal_start_month
                and month >= self.params.withdrawal_start_month
                and self.params.monthly_withdrawal > 0
            ):
                withdrawal = self.params.monthly_withdrawal
                # Corrigir retirada pela inflação
                months_since_start = month - self.params.withdrawal_start_month
                if months_since_start > 0:
                    withdrawal = self.params.monthly_withdrawal * (
                        (1 + monthly_inflation) ** months_since_start
                    )

            # 6. Atualizar patrimônio
            total_current = total_current + net_return + contribution + extra - withdrawal

            # Não permitir patrimônio negativo
            total_current = max(total_current, 0)

            # 7. Calcular renda passiva estimada
            # Se houve aporte extra neste mês, ajustar os "assets virtuais"
            # para refletir o destino escolhido (afeta o income yield)
            effective_assets = self.assets
            if extra > 0 and hasattr(self.params, "extra_contribution_target"):
                target = self.params.extra_contribution_target or "proporcional"
                if target != "proporcional":
                    effective_assets = self._assets_with_extra(extra, target)

            passive_income = self.income_engine.calculate_monthly_income(
                total_current, weighted_annual_return, effective_assets
            )

            # Manter os assets ajustados para os meses seguintes
            # (o extra fica investido permanentemente no destino)
            if extra > 0 and hasattr(self.params, "extra_contribution_target"):
                target = self.params.extra_contribution_target or "proporcional"
                if target != "proporcional":
                    self.assets = effective_assets

            # 8. Renda líquida = renda passiva (já calculada líquida pelo income_engine)
            net_income = passive_income

            # 9. Calcular benchmarks
            benchmarks = self.benchmark_engine.calculate_month(
                month, benchmark_initial
            )

            # 10. Ajustar pela inflação (valores reais)
            real_assets = adjust_for_inflation(total_current, monthly_inflation, month)
            real_income = adjust_for_inflation(net_income, monthly_inflation, month)

            projections.append(
                {
                    "month": month,
                    "total_assets": round(total_current, 2),
                    "total_assets_real": round(real_assets, 2),
                    "passive_income": round(passive_income, 2),
                    "net_income": round(net_income, 2),
                    "net_income_real": round(real_income, 2),
                    "contribution": round(contribution, 2),
                    "extra_contribution": round(extra, 2),
                    "withdrawal": round(withdrawal, 2),
                    "benchmark_cdi": round(benchmarks["cdi"], 2),
                    "benchmark_ipca": round(benchmarks["ipca"], 2),
                    "benchmark_ibov": round(benchmarks["ibov"], 2),
                    "benchmark_ifix": round(benchmarks["ifix"], 2),
                    "benchmark_selic": round(benchmarks["selic"], 2),
                }
            )

        return projections

    def run_and_save(self) -> list[dict]:
        """Executa a projeção e salva no banco de dados."""
        projections = self.run_projection()
        if projections:
            Scenario.save_projections(self.scenario_id, projections)
        return projections

    def get_fire_analysis(self) -> dict:
        """Analisa a projeção sob a ótica FIRE.

        Returns:
            Dicionário com métricas FIRE.
        """
        from app.utils.financial_calculations import (
            calculate_fire_target,
            months_to_fire,
        )

        if not self.params:
            return {}

        fire_target = calculate_fire_target(
            self.params.desired_monthly_income,
            self.params.safe_withdrawal_rate,
        )

        total_current = sum(a.current_value for a in self.assets)
        weighted_return = self._get_weighted_return()
        monthly_rate = annual_to_monthly_rate(weighted_return)

        months_needed = months_to_fire(
            total_current,
            self.params.monthly_contribution,
            monthly_rate,
            fire_target,
        )

        # Encontrar ponto FIRE na projeção
        projections = self.run_projection()
        fire_month = None
        for proj in projections:
            if proj["total_assets"] >= fire_target:
                fire_month = proj["month"]
                break

        return {
            "fire_target": round(fire_target, 2),
            "current_assets": round(total_current, 2),
            "progress_pct": round(
                min(total_current / fire_target * 100, 100) if fire_target > 0 else 0, 2
            ),
            "months_to_fire": months_needed,
            "years_to_fire": round(months_needed / 12, 1) if months_needed > 0 else 0,
            "fire_month": fire_month,
            "desired_monthly_income": self.params.desired_monthly_income,
            "swr": self.params.safe_withdrawal_rate,
        }

    def to_dataframe(self, projections: list[dict] | None = None) -> pd.DataFrame:
        """Converte as projeções para DataFrame do pandas."""
        if projections is None:
            projections = self.run_projection()
        return pd.DataFrame(projections)

    def _get_weighted_return(self) -> float:
        """Calcula o retorno anual ponderado LÍQUIDO do portfólio.

        Desconta admin fee, come-cotas e IR para cada ativo.
        """
        from app.database.database import get_app_settings
        from app.services.market_data import get_indicators

        total = sum(a.current_value for a in self.assets)
        if total == 0:
            return 0.0

        settings = get_app_settings()
        ir_rate = settings.get("ir_renda_fixa", 17.5) / 100

        indicators = get_indicators()
        bcb_cdi = indicators.get("cdi") if indicators["success"] else None

        weighted = 0.0
        for a in self.assets:
            proportion = a.current_value / total

            # Retorno efetivo do ativo
            effective_return = a.expected_annual_return
            if a.cdi_percentage > 0 and bcb_cdi and bcb_cdi > 0:
                effective_return = (a.cdi_percentage / 100) * bcb_cdi
            elif a.type in ("Renda Fixa", "Fundos") and bcb_cdi and bcb_cdi > 0 and a.expected_annual_return <= 0:
                effective_return = bcb_cdi

            # Descontar admin fee
            net_return = effective_return - a.admin_fee
            # Descontar come-cotas
            if a.has_come_cotas:
                net_return *= 0.85
            # Descontar IR para ativos que acumulam (sem renda direta)
            if a.monthly_income == 0 and effective_return > 0:
                net_return *= (1 - ir_rate)

            weighted += net_return * proportion

        return weighted

    def _get_weighted_admin_fee(self) -> float:
        """Calcula a taxa de administração ponderada."""
        total = sum(a.current_value for a in self.assets)
        if total == 0:
            return 0.0
        return sum(a.admin_fee * (a.current_value / total) for a in self.assets)

    def _assets_with_extra(self, extra_value: float, target_type: str) -> list:
        """Cria uma cópia dos assets com o aporte extra alocado no tipo-destino.

        Distribui o aporte extra proporcionalmente entre os ativos do tipo
        escolhido (ex.: FII, Ações, Renda Fixa). Isso altera as proporções
        do portfólio e, consequentemente, o income yield usado para calcular
        a renda passiva.

        Se não houver ativos do tipo-destino, distribui proporcionalmente
        entre todos (fallback).

        Args:
            extra_value: Valor do aporte extra.
            target_type: Tipo de ativo-destino (ex.: 'FII', 'Renda Fixa').

        Returns:
            Nova lista de AssetClass com valores ajustados.
        """
        import copy

        new_assets = [copy.copy(a) for a in self.assets]

        target_assets = [a for a in new_assets if a.type == target_type]

        if not target_assets:
            # Fallback: distribuir proporcionalmente entre todos
            total = sum(a.current_value for a in new_assets)
            for a in new_assets:
                proportion = a.current_value / total if total > 0 else 1 / len(new_assets)
                a.current_value += extra_value * proportion
                # Ajustar renda proporcional ao yield do ativo
                if a.current_value > 0:
                    original_total = a.current_value - extra_value * proportion
                    if original_total > 0:
                        asset_yield = a.monthly_income / original_total
                        a.monthly_income += extra_value * proportion * asset_yield
        else:
            # Distribuir proporcionalmente entre ativos do tipo-destino
            target_total = sum(a.current_value for a in target_assets)
            for a in target_assets:
                proportion = a.current_value / target_total if target_total > 0 else 1 / len(target_assets)
                added = extra_value * proportion
                original_value = a.current_value
                a.current_value += added
                # Ajustar renda: o aporte rende conforme o yield desse ativo
                if original_value > 0:
                    asset_yield = a.monthly_income / original_value
                    a.monthly_income += added * asset_yield

        return new_assets
