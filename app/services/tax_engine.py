"""
Motor Tributário.

Simula a tributação sobre rendimentos e resgates de acordo com
as regras brasileiras para cada classe de ativo.
"""

from app.utils.constants import (
    IR_REGRESSIVO,
    TAX_RATE_ACOES_ETF,
    COME_COTAS_RATE_LONGO_PRAZO,
    COME_COTAS_MONTHS,
)
from app.utils.financial_calculations import (
    calculate_ir_regressivo,
    calculate_come_cotas,
    calculate_tax_by_type,
)
from app.database.database import get_app_settings


class TaxEngine:
    """Motor de simulação tributária."""

    def calculate_tax_on_withdrawal(
        self, withdrawal: float, gain_ratio: float, asset_type: str, holding_days: int = 730
    ) -> dict:
        """Calcula imposto sobre resgate.

        Args:
            withdrawal: Valor do resgate.
            gain_ratio: Proporção do resgate que é ganho (0 a 1).
            asset_type: Tipo do ativo.
            holding_days: Dias de posse do ativo.

        Returns:
            Dicionário com detalhes da tributação.
        """
        gain = withdrawal * gain_ratio
        tax = calculate_tax_by_type(gain, asset_type, holding_days)

        return {
            "withdrawal": round(withdrawal, 2),
            "taxable_gain": round(gain, 2),
            "tax": round(tax, 2),
            "net_withdrawal": round(withdrawal - tax, 2),
            "effective_rate": round((tax / withdrawal * 100) if withdrawal > 0 else 0, 2),
        }

    def calculate_come_cotas_impact(
        self, fund_value: float, semester_gain: float, month: int
    ) -> float:
        """Calcula o impacto do come-cotas para fundos.

        O come-cotas incide em maio e novembro.

        Args:
            fund_value: Valor atual do fundo.
            semester_gain: Rendimento do semestre.
            month: Mês atual (1-12).

        Returns:
            Valor do come-cotas, ou 0 se não for mês de incidência.
        """
        if month not in COME_COTAS_MONTHS:
            return 0.0

        return calculate_come_cotas(fund_value, semester_gain)

    def calculate_net_portfolio_income(
        self, gross_income: float, assets: list
    ) -> float:
        """Calcula a renda líquida do portfólio após impostos.

        Estima a tributação proporcional por tipo de ativo.

        Args:
            gross_income: Renda bruta total.
            assets: Lista de AssetClass.

        Returns:
            Renda líquida estimada.
        """
        if not assets or gross_income <= 0:
            return 0.0

        total_income = sum(a.monthly_income for a in assets)
        if total_income <= 0:
            return gross_income * 0.85  # Fallback: 15% de imposto médio

        net_income = 0.0
        for asset in assets:
            if total_income > 0:
                proportion = asset.monthly_income / total_income
            else:
                proportion = 1 / len(assets)

            asset_gross = gross_income * proportion
            tax = self._calculate_income_tax(asset_gross, asset.type)
            net_income += asset_gross - tax

        return round(net_income, 2)

    def _calculate_income_tax(self, income: float, asset_type: str) -> float:
        """Calcula imposto sobre renda passiva por tipo.

        Usa a alíquota configurável de IR para Renda Fixa/Fundos/ETF
        (padrão 17,5% — regra 2025).

        Args:
            income: Renda bruta do ativo.
            asset_type: Tipo do ativo.

        Returns:
            Valor do imposto.
        """
        if income <= 0:
            return 0.0

        # Buscar alíquota configurada
        settings = get_app_settings()
        ir_rate = settings.get("ir_renda_fixa", 17.5) / 100

        if asset_type == "FII":
            # Dividendos de FII são isentos de IR para pessoa física
            return 0.0
        elif asset_type == "Ações":
            # Dividendos de ações são isentos (por enquanto no Brasil)
            return 0.0
        elif asset_type in ("ETF", "Renda Fixa", "Fundos"):
            # Alíquota única configurável (17,5% padrão)
            return income * ir_rate
        else:
            return income * ir_rate

    def generate_tax_summary(self, projections: list, assets: list) -> dict:
        """Gera um resumo tributário da projeção.

        Args:
            projections: Lista de projeções mensais.
            assets: Lista de AssetClass.

        Returns:
            Dicionário com resumo tributário.
        """
        if not projections:
            return {
                "total_gross_income": 0,
                "total_net_income": 0,
                "total_tax_paid": 0,
                "effective_tax_rate": 0,
            }

        total_gross = sum(p.get("passive_income", 0) for p in projections)
        total_net = sum(p.get("net_income", 0) for p in projections)
        total_tax = total_gross - total_net

        return {
            "total_gross_income": round(total_gross, 2),
            "total_net_income": round(total_net, 2),
            "total_tax_paid": round(total_tax, 2),
            "effective_tax_rate": round(
                (total_tax / total_gross * 100) if total_gross > 0 else 0, 2
            ),
        }
