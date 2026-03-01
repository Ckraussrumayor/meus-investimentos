"""
Model para Classes de Ativos.
"""

from dataclasses import dataclass
from app.database.database import execute_query


@dataclass
class AssetClass:
    id: int | None
    name: str
    type: str
    invested_value: float
    current_value: float
    monthly_income: float
    expected_annual_return: float
    admin_fee: float
    tax_type: str
    has_come_cotas: bool
    cdi_percentage: float = 0.0

    @staticmethod
    def create(
        name: str,
        type: str,
        invested_value: float,
        current_value: float,
        monthly_income: float,
        expected_annual_return: float,
        admin_fee: float,
        tax_type: str,
        has_come_cotas: bool,
        cdi_percentage: float = 0.0,
    ) -> int:
        """Cria uma nova classe de ativo no banco de dados."""
        return execute_query(
            """INSERT INTO asset_classes 
               (name, type, invested_value, current_value, monthly_income,
                expected_annual_return, admin_fee, tax_type, has_come_cotas, cdi_percentage)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                type,
                invested_value,
                current_value,
                monthly_income,
                expected_annual_return,
                admin_fee,
                tax_type,
                1 if has_come_cotas else 0,
                cdi_percentage,
            ),
        )

    @staticmethod
    def get_all() -> list:
        """Retorna todas as classes de ativos."""
        rows = execute_query("SELECT * FROM asset_classes ORDER BY type, name", fetch=True)
        return [AssetClass._from_row(row) for row in rows]

    @staticmethod
    def get_by_id(asset_id: int):
        """Retorna uma classe de ativo por ID."""
        rows = execute_query(
            "SELECT * FROM asset_classes WHERE id = ?", (asset_id,), fetch=True
        )
        if rows:
            return AssetClass._from_row(rows[0])
        return None

    @staticmethod
    def get_by_type(asset_type: str) -> list:
        """Retorna classes de ativos filtradas por tipo."""
        rows = execute_query(
            "SELECT * FROM asset_classes WHERE type = ? ORDER BY name",
            (asset_type,),
            fetch=True,
        )
        return [AssetClass._from_row(row) for row in rows]

    @staticmethod
    def update(
        asset_id: int,
        name: str,
        type: str,
        invested_value: float,
        current_value: float,
        monthly_income: float,
        expected_annual_return: float,
        admin_fee: float,
        tax_type: str,
        has_come_cotas: bool,
        cdi_percentage: float = 0.0,
    ):
        """Atualiza uma classe de ativo existente."""
        execute_query(
            """UPDATE asset_classes 
               SET name=?, type=?, invested_value=?, current_value=?,
                   monthly_income=?, expected_annual_return=?, admin_fee=?,
                   tax_type=?, has_come_cotas=?, cdi_percentage=?
               WHERE id=?""",
            (
                name,
                type,
                invested_value,
                current_value,
                monthly_income,
                expected_annual_return,
                admin_fee,
                tax_type,
                1 if has_come_cotas else 0,
                cdi_percentage,
                asset_id,
            ),
        )

    @staticmethod
    def delete(asset_id: int):
        """Remove uma classe de ativo."""
        execute_query("DELETE FROM asset_classes WHERE id = ?", (asset_id,))

    @staticmethod
    def get_total_invested() -> float:
        """Retorna o total investido em todas as classes."""
        rows = execute_query(
            "SELECT COALESCE(SUM(invested_value), 0) as total FROM asset_classes",
            fetch=True,
        )
        return rows[0]["total"] if rows else 0.0

    @staticmethod
    def get_total_current() -> float:
        """Retorna o valor atual total de todas as classes."""
        rows = execute_query(
            "SELECT COALESCE(SUM(current_value), 0) as total FROM asset_classes",
            fetch=True,
        )
        return rows[0]["total"] if rows else 0.0

    @staticmethod
    def get_total_monthly_income() -> float:
        """Retorna a renda mensal total de todas as classes."""
        rows = execute_query(
            "SELECT COALESCE(SUM(monthly_income), 0) as total FROM asset_classes",
            fetch=True,
        )
        return rows[0]["total"] if rows else 0.0

    @staticmethod
    def _from_row(row) -> "AssetClass":
        """Converte uma linha do banco em um objeto AssetClass."""
        return AssetClass(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            invested_value=row["invested_value"],
            current_value=row["current_value"],
            monthly_income=row["monthly_income"],
            expected_annual_return=row["expected_annual_return"],
            admin_fee=row["admin_fee"],
            tax_type=row["tax_type"],
            has_come_cotas=bool(row["has_come_cotas"]),
            cdi_percentage=row["cdi_percentage"] if "cdi_percentage" in row.keys() else 0.0,
        )
