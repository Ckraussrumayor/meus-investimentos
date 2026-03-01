"""
Funções utilitárias para cálculos financeiros.
"""

import numpy as np
from app.utils.constants import (
    IR_REGRESSIVO,
    TAX_RATE_ACOES_ETF,
    TAX_RATE_FII_DIVIDENDOS,
    COME_COTAS_RATE_LONGO_PRAZO,
    MONTHS_PER_YEAR,
)


def annual_to_monthly_rate(annual_rate_pct: float) -> float:
    """Converte taxa anual (%) para taxa mensal decimal.

    Args:
        annual_rate_pct: Taxa anual em percentual (ex.: 12.0 para 12%).

    Returns:
        Taxa mensal decimal (ex.: 0.00949 para ~12% ao ano).
    """
    return (1 + annual_rate_pct / 100) ** (1 / MONTHS_PER_YEAR) - 1


def monthly_to_annual_rate(monthly_rate: float) -> float:
    """Converte taxa mensal decimal para taxa anual em percentual.

    Args:
        monthly_rate: Taxa mensal decimal.

    Returns:
        Taxa anual em percentual.
    """
    return ((1 + monthly_rate) ** MONTHS_PER_YEAR - 1) * 100


def compound_growth(principal: float, monthly_rate: float, months: int) -> float:
    """Calcula crescimento com juros compostos.

    Args:
        principal: Valor inicial.
        monthly_rate: Taxa mensal decimal.
        months: Número de meses.

    Returns:
        Valor final após juros compostos.
    """
    return principal * (1 + monthly_rate) ** months


def future_value_with_contributions(
    principal: float,
    monthly_rate: float,
    monthly_contribution: float,
    months: int,
) -> float:
    """Calcula valor futuro com aportes mensais constantes.

    Args:
        principal: Valor inicial.
        monthly_rate: Taxa mensal decimal.
        monthly_contribution: Aporte mensal.
        months: Número de meses.

    Returns:
        Valor futuro total.
    """
    if monthly_rate == 0:
        return principal + monthly_contribution * months

    fv_principal = principal * (1 + monthly_rate) ** months
    fv_contributions = monthly_contribution * (
        ((1 + monthly_rate) ** months - 1) / monthly_rate
    )
    return fv_principal + fv_contributions


def calculate_ir_regressivo(gain: float, holding_days: int) -> float:
    """Calcula IR regressivo sobre o ganho de capital em renda fixa.

    Args:
        gain: Ganho de capital (lucro).
        holding_days: Dias de holding do ativo.

    Returns:
        Valor do imposto a pagar.
    """
    if gain <= 0:
        return 0.0

    for limit, rate in IR_REGRESSIVO:
        if limit is None or holding_days <= limit:
            return gain * rate

    return gain * IR_REGRESSIVO[-1][1]


def calculate_tax_by_type(
    gain: float, asset_type: str, holding_days: int = 730
) -> float:
    """Calcula imposto baseado no tipo de ativo.

    Args:
        gain: Ganho de capital.
        asset_type: Tipo do ativo (FII, Ações, ETF, Renda Fixa, Fundos).
        holding_days: Dias de holding (para IR regressivo).

    Returns:
        Valor do imposto.
    """
    if gain <= 0:
        return 0.0

    if asset_type == "FII":
        # Dividendos de FII são isentos, mas ganho de capital paga 20%
        return gain * 0.20
    elif asset_type in ("Ações", "ETF"):
        return gain * TAX_RATE_ACOES_ETF
    elif asset_type == "Renda Fixa":
        return calculate_ir_regressivo(gain, holding_days)
    elif asset_type == "Fundos":
        return calculate_ir_regressivo(gain, holding_days)
    else:
        return gain * TAX_RATE_ACOES_ETF


def calculate_come_cotas(fund_value: float, gain: float) -> float:
    """Calcula come-cotas semestral para fundos.

    Args:
        fund_value: Valor atual do fundo.
        gain: Rendimento acumulado no semestre.

    Returns:
        Valor do come-cotas (imposto antecipado).
    """
    if gain <= 0:
        return 0.0
    return gain * COME_COTAS_RATE_LONGO_PRAZO


def calculate_net_income(
    gross_income: float, asset_type: str, is_dividend: bool = True
) -> float:
    """Calcula renda líquida após impostos.

    Args:
        gross_income: Renda bruta mensal.
        asset_type: Tipo do ativo.
        is_dividend: Se é dividendo (relevante para FII).

    Returns:
        Renda líquida mensal.
    """
    if asset_type == "FII" and is_dividend:
        return gross_income  # Dividendos de FII são isentos
    elif asset_type in ("Ações", "ETF"):
        return gross_income  # Dividendos de ações são isentos (no Brasil)
    elif asset_type in ("Renda Fixa", "Fundos"):
        tax = calculate_ir_regressivo(gross_income, 730)
        return gross_income - tax
    return gross_income


def calculate_fire_target(
    desired_monthly_income: float, swr: float
) -> float:
    """Calcula o patrimônio necessário para independência financeira.

    Args:
        desired_monthly_income: Renda mensal desejada.
        swr: Safe Withdrawal Rate anual (%).

    Returns:
        Patrimônio-alvo para FIRE.
    """
    annual_income = desired_monthly_income * MONTHS_PER_YEAR
    return annual_income / (swr / 100)


def months_to_fire(
    current_assets: float,
    monthly_contribution: float,
    monthly_rate: float,
    fire_target: float,
) -> int:
    """Calcula o número de meses até atingir o patrimônio FIRE.

    Args:
        current_assets: Patrimônio atual.
        monthly_contribution: Aporte mensal.
        monthly_rate: Taxa de retorno mensal decimal.
        fire_target: Patrimônio-alvo.

    Returns:
        Número de meses estimados, ou -1 se não atingível.
    """
    if current_assets >= fire_target:
        return 0

    if monthly_rate <= 0 and monthly_contribution <= 0:
        return -1

    assets = current_assets
    for month in range(1, 12001):  # Máximo 1000 anos
        assets = assets * (1 + monthly_rate) + monthly_contribution
        if assets >= fire_target:
            return month

    return -1


def adjust_for_inflation(value: float, monthly_inflation: float, months: int) -> float:
    """Ajusta um valor pela inflação.

    Args:
        value: Valor nominal.
        monthly_inflation: Taxa de inflação mensal decimal.
        months: Número de meses de inflação.

    Returns:
        Valor real (ajustado pela inflação).
    """
    return value / (1 + monthly_inflation) ** months


def format_currency(value: float) -> str:
    """Formata valor como moeda brasileira."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percentage(value: float) -> str:
    """Formata valor como percentual."""
    return f"{value:.2f}%".replace(".", ",")
