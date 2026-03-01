"""
Motor de Renda Passiva.

Calcula a renda passiva mensal estimada do portfólio
com base nos ativos e suas características.
Inclui renda direta (dividendos) e renda teórica (RF/Fundos que acumulam).
"""

from app.utils.financial_calculations import annual_to_monthly_rate
from app.database.database import get_app_settings
from app.services.market_data import get_indicators


class IncomeEngine:
    """Calcula renda passiva do portfólio."""

    def calculate_monthly_income(
        self, total_assets: float, weighted_annual_return: float, assets: list
    ) -> float:
        """Calcula a renda passiva mensal estimada LÍQUIDA.

        Inclui:
        - Renda direta (dividendos de FIIs, Ações): yield on cost
        - Renda teórica (RF, Fundos): rendimento acumulado, descontado
          admin fee, come-cotas e IR

        A renda é escalada proporcionalmente ao patrimônio projetado.

        Args:
            total_assets: Patrimônio total projetado.
            weighted_annual_return: Retorno anual ponderado (%).
            assets: Lista de AssetClass.

        Returns:
            Renda passiva mensal estimada (líquida).
        """
        if not assets or total_assets <= 0:
            return 0.0

        total_current = sum(a.current_value for a in assets)
        if total_current <= 0:
            monthly_rate = annual_to_monthly_rate(weighted_annual_return)
            return total_assets * monthly_rate

        # Buscar configurações para cálculo líquido
        settings = get_app_settings()
        ir_rate = settings.get("ir_renda_fixa", 17.5) / 100

        # Buscar CDI do BCB para ativos atrelados ao CDI
        indicators = get_indicators()
        bcb_cdi = indicators.get("cdi") if indicators["success"] else None

        # Calcular renda mensal de cada ativo nos valores atuais
        total_monthly_income = 0.0
        for a in assets:
            if a.monthly_income > 0:
                # Renda direta (dividendos, cupons) — já é líquida para FIIs/Ações
                total_monthly_income += a.monthly_income
            elif a.current_value > 0 and (a.expected_annual_return > 0 or a.cdi_percentage > 0):
                # Renda teórica de ativos que acumulam
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
                # Descontar IR
                net_return *= (1 - ir_rate)

                monthly_theoretical = a.current_value * (net_return / 100) / 12
                total_monthly_income += monthly_theoretical

        if total_monthly_income <= 0:
            monthly_rate = annual_to_monthly_rate(weighted_annual_return)
            return total_assets * monthly_rate

        # Escalar proporcionalmente ao patrimônio projetado
        income_yield = total_monthly_income / total_current
        return total_assets * income_yield

    def calculate_income_by_asset_type(
        self, total_assets: float, assets: list
    ) -> dict:
        """Calcula a renda por tipo de ativo proporcionalmente.

        Args:
            total_assets: Patrimônio total projetado.
            assets: Lista de AssetClass.

        Returns:
            Dicionário com renda por tipo de ativo.
        """
        if not assets or total_assets <= 0:
            return {}

        total_current = sum(a.current_value for a in assets)
        if total_current <= 0:
            return {}

        income_by_type = {}
        for asset in assets:
            proportion = asset.current_value / total_current
            projected_value = total_assets * proportion

            # Calcular renda baseada no yield atual do ativo
            if asset.current_value > 0:
                asset_yield = asset.monthly_income / asset.current_value
            else:
                asset_yield = annual_to_monthly_rate(asset.expected_annual_return)

            asset_income = projected_value * asset_yield

            if asset.type not in income_by_type:
                income_by_type[asset.type] = 0.0
            income_by_type[asset.type] += asset_income

        return income_by_type

    def estimate_passive_income_at_fire(
        self, fire_target: float, assets: list
    ) -> dict:
        """Estima a renda passiva quando atingir o patrimônio FIRE.

        Args:
            fire_target: Patrimônio-alvo FIRE.
            assets: Lista de AssetClass atuais.

        Returns:
            Dicionário com análise de renda no ponto FIRE.
        """
        total_current = sum(a.current_value for a in assets)
        total_income = sum(a.monthly_income for a in assets)

        if total_current <= 0:
            return {
                "estimated_gross_income": 0,
                "income_by_type": {},
            }

        # Escalar a renda proporcionalmente
        scale_factor = fire_target / total_current if total_current > 0 else 0
        estimated_income = total_income * scale_factor

        income_by_type = {}
        for asset in assets:
            proportion = asset.current_value / total_current
            projected_value = fire_target * proportion
            if asset.current_value > 0:
                asset_yield = asset.monthly_income / asset.current_value
            else:
                asset_yield = 0
            income = projected_value * asset_yield

            if asset.type not in income_by_type:
                income_by_type[asset.type] = 0.0
            income_by_type[asset.type] += income

        return {
            "estimated_gross_income": round(estimated_income, 2),
            "income_by_type": {k: round(v, 2) for k, v in income_by_type.items()},
        }
