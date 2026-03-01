"""
Model para Portfólio consolidado.
"""

import pandas as pd
from app.models.asset_class import AssetClass
from app.database.database import execute_query


class Portfolio:
    """Classe para operações consolidadas do portfólio."""

    @staticmethod
    def get_summary() -> dict:
        """Retorna um resumo consolidado do portfólio."""
        assets = AssetClass.get_all()

        total_invested = sum(a.invested_value for a in assets)
        total_current = sum(a.current_value for a in assets)
        total_monthly_income = sum(a.monthly_income for a in assets)
        total_gain = total_current - total_invested
        gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0

        return {
            "total_invested": total_invested,
            "total_current": total_current,
            "total_monthly_income": total_monthly_income,
            "total_gain": total_gain,
            "gain_pct": gain_pct,
            "asset_count": len(assets),
            "assets": assets,
        }

    @staticmethod
    def get_allocation_by_type() -> pd.DataFrame:
        """Retorna a alocação por tipo de ativo."""
        assets = AssetClass.get_all()

        if not assets:
            return pd.DataFrame(columns=["Tipo", "Valor Atual", "Percentual"])

        data = {}
        for asset in assets:
            if asset.type not in data:
                data[asset.type] = 0
            data[asset.type] += asset.current_value

        total = sum(data.values())
        records = []
        for tipo, valor in data.items():
            records.append(
                {
                    "Tipo": tipo,
                    "Valor Atual": valor,
                    "Percentual": (valor / total * 100) if total > 0 else 0,
                }
            )

        df = pd.DataFrame(records)
        df = df.sort_values("Valor Atual", ascending=False).reset_index(drop=True)
        return df

    @staticmethod
    def get_income_by_type() -> pd.DataFrame:
        """Retorna a renda passiva por tipo de ativo."""
        assets = AssetClass.get_all()

        if not assets:
            return pd.DataFrame(columns=["Tipo", "Renda Mensal", "Percentual"])

        data = {}
        for asset in assets:
            if asset.type not in data:
                data[asset.type] = 0
            data[asset.type] += asset.monthly_income

        total = sum(data.values())
        records = []
        for tipo, valor in data.items():
            records.append(
                {
                    "Tipo": tipo,
                    "Renda Mensal": valor,
                    "Percentual": (valor / total * 100) if total > 0 else 0,
                }
            )

        df = pd.DataFrame(records)
        df = df.sort_values("Renda Mensal", ascending=False).reset_index(drop=True)
        return df

    @staticmethod
    def get_weighted_return() -> float:
        """Calcula o retorno ponderado médio do portfólio."""
        assets = AssetClass.get_all()
        total_current = sum(a.current_value for a in assets)

        if total_current == 0:
            return 0.0

        weighted_return = sum(
            a.expected_annual_return * (a.current_value / total_current)
            for a in assets
        )
        return weighted_return

    @staticmethod
    def save_snapshot(month: str):
        """Salva um snapshot mensal do portfólio no histórico."""
        total_assets = AssetClass.get_total_current()
        total_income = AssetClass.get_total_monthly_income()

        execute_query(
            "INSERT INTO historical_snapshots (month, total_assets, passive_income) VALUES (?, ?, ?)",
            (month, total_assets, total_income),
        )

    @staticmethod
    def get_history() -> pd.DataFrame:
        """Retorna o histórico de snapshots."""
        rows = execute_query(
            "SELECT month, total_assets, passive_income FROM historical_snapshots ORDER BY month",
            fetch=True,
        )
        if not rows:
            return pd.DataFrame(columns=["Mês", "Patrimônio", "Renda Passiva"])

        records = [
            {
                "Mês": row["month"],
                "Patrimônio": row["total_assets"],
                "Renda Passiva": row["passive_income"],
            }
            for row in rows
        ]
        return pd.DataFrame(records)
