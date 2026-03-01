"""
Página: Relatórios e Exportação.

Permite exportar projeções em Excel e relatório consolidado em PDF.
"""

import io
import streamlit as st
import pandas as pd
from datetime import datetime

from app.models.scenario import Scenario
from app.models.portfolio import Portfolio
from app.models.asset_class import AssetClass
from app.services.projection_engine import ProjectionEngine
from app.services.tax_engine import TaxEngine
from app.utils.financial_calculations import format_currency


def render():
    """Renderiza a página de relatórios."""
    st.markdown("# 📄 Relatórios e Exportação")
    st.markdown("---")

    tab_excel, tab_pdf = st.tabs(["📊 Exportar Excel", "📄 Exportar PDF"])

    with tab_excel:
        _render_excel_export()

    with tab_pdf:
        _render_pdf_export()


def _render_excel_export():
    """Exportação de projeção detalhada em Excel."""
    st.markdown("### 📊 Exportar Projeção para Excel")

    scenarios = Scenario.get_all()
    scenarios_with_data = [
        s for s in scenarios if Scenario.get_projections(s.id)
    ]

    if not scenarios_with_data:
        st.info("Nenhum cenário com projeções disponível. Execute uma simulação primeiro.")
        return

    selected_name = st.selectbox(
        "Cenário para exportar",
        options=[s.name for s in scenarios_with_data],
        key="excel_scenario",
    )

    selected = next(s for s in scenarios_with_data if s.name == selected_name)
    projections = Scenario.get_projections(selected.id)
    params = Scenario.get_parameters(selected.id)

    if not projections:
        st.warning("Cenário sem projeções.")
        return

    if st.button("📥 Gerar Excel", use_container_width=True, type="primary"):
        buffer = _generate_excel(projections, params, selected.name)
        st.download_button(
            label="⬇️ Baixar Excel",
            data=buffer,
            file_name=f"projecao_{selected.name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def _generate_excel(projections: list, params, scenario_name: str) -> bytes:
    """Gera arquivo Excel com projeções detalhadas."""
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Aba: Projeção mensal
        df_proj = pd.DataFrame(projections)
        df_proj["Ano"] = df_proj["month"] / 12

        col_mapping = {
            "month": "Mês",
            "Ano": "Ano",
            "total_assets": "Patrimônio Total",
            "passive_income": "Renda Bruta",
            "net_income": "Renda Líquida",
            "benchmark_cdi": "Benchmark CDI",
            "benchmark_ipca": "Benchmark IPCA",
            "benchmark_selic": "Benchmark SELIC",
            "benchmark_ibov": "Benchmark Ibovespa",
            "benchmark_ifix": "Benchmark IFIX",
        }

        df_export = df_proj.rename(
            columns={k: v for k, v in col_mapping.items() if k in df_proj.columns}
        )
        df_export.to_excel(writer, sheet_name="Projeção Mensal", index=False)

        # Aba: Projeção anual
        df_annual = df_proj[df_proj["month"] % 12 == 0].copy()
        df_annual = df_annual.rename(
            columns={k: v for k, v in col_mapping.items() if k in df_annual.columns}
        )
        df_annual.to_excel(writer, sheet_name="Projeção Anual", index=False)

        # Aba: Parâmetros
        if params:
            params_data = {
                "Parâmetro": [
                    "Cenário",
                    "Inflação (% a.a.)",
                    "SELIC (% a.a.)",
                    "CDI (% a.a.)",
                    "IPCA (% a.a.)",
                    "Crescimento Salarial (%)",
                    "Aporte Mensal (R$)",
                    "Renda Desejada (R$)",
                    "Taxa de Retirada Segura (%)",
                    "Período (meses)",
                ],
                "Valor": [
                    scenario_name,
                    params.inflation,
                    params.selic,
                    params.cdi,
                    params.ipca,
                    params.salary_growth,
                    params.monthly_contribution,
                    params.desired_monthly_income,
                    params.safe_withdrawal_rate,
                    params.projection_months,
                ],
            }
            df_params = pd.DataFrame(params_data)
            df_params.to_excel(writer, sheet_name="Parâmetros", index=False)

        # Aba: Portfólio atual
        assets = AssetClass.get_all()
        if assets:
            assets_data = [
                {
                    "Nome": a.name,
                    "Tipo": a.type,
                    "Valor Investido": a.invested_value,
                    "Valor Atual": a.current_value,
                    "Renda Mensal": a.monthly_income,
                    "Retorno Esperado (%)": a.expected_annual_return,
                    "Taxa Admin (%)": a.admin_fee,
                }
                for a in assets
            ]
            df_assets = pd.DataFrame(assets_data)
            df_assets.to_excel(writer, sheet_name="Portfólio", index=False)

    return buffer.getvalue()


def _render_pdf_export():
    """Exportação de relatório consolidado em PDF."""
    st.markdown("### 📄 Relatório Consolidado em PDF")

    scenarios = Scenario.get_all()
    scenarios_with_data = [
        s for s in scenarios if Scenario.get_projections(s.id)
    ]

    if not scenarios_with_data:
        st.info("Nenhum cenário com projeções disponível.")
        return

    selected_name = st.selectbox(
        "Cenário para o relatório",
        options=[s.name for s in scenarios_with_data],
        key="pdf_scenario",
    )

    selected = next(s for s in scenarios_with_data if s.name == selected_name)

    if st.button("📥 Gerar PDF", use_container_width=True, type="primary"):
        with st.spinner("Gerando relatório PDF..."):
            pdf_bytes = _generate_pdf(selected.id, selected.name)

        st.download_button(
            label="⬇️ Baixar PDF",
            data=pdf_bytes,
            file_name=f"relatorio_{selected.name}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _generate_pdf(scenario_id: int, scenario_name: str) -> bytes:
    """Gera relatório PDF consolidado."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1565C0"),
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
        textColor=colors.HexColor("#1976D2"),
    )

    elements = []

    # Título
    elements.append(
        Paragraph("Relatório de Simulação Financeira", title_style)
    )
    elements.append(
        Paragraph(
            f"Cenário: {scenario_name} | Data: {datetime.now().strftime('%d/%m/%Y')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 20))

    # Portfólio atual
    elements.append(Paragraph("Portfólio Atual", subtitle_style))

    summary = Portfolio.get_summary()
    portfolio_data = [
        ["Métrica", "Valor"],
        ["Patrimônio Total", format_currency(summary["total_current"])],
        ["Total Investido", format_currency(summary["total_invested"])],
        ["Renda Mensal", format_currency(summary["total_monthly_income"])],
        ["Ganho/Perda", format_currency(summary["total_gain"])],
        ["Rentabilidade", f"{summary['gain_pct']:.2f}%"],
    ]

    table = Table(portfolio_data, colWidths=[8 * cm, 8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Projeção
    elements.append(Paragraph("Projeção Patrimonial (Anual)", subtitle_style))

    projections = Scenario.get_projections(scenario_id)
    annual = [p for p in projections if p["month"] % 12 == 0]

    if annual:
        proj_data = [["Ano", "Patrimônio", "Renda Bruta", "Renda Líquida"]]
        for p in annual[:30]:  # Máximo 30 anos
            proj_data.append(
                [
                    f"{p['month'] // 12}",
                    format_currency(p["total_assets"]),
                    format_currency(p["passive_income"]),
                    format_currency(p["net_income"]),
                ]
            )

        proj_table = Table(proj_data, colWidths=[3 * cm, 5 * cm, 4 * cm, 4 * cm])
        proj_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(proj_table)
        elements.append(Spacer(1, 20))

    # Análise tributária
    elements.append(Paragraph("Análise Tributária", subtitle_style))

    tax_engine = TaxEngine()
    assets = AssetClass.get_all()
    tax_summary = tax_engine.generate_tax_summary(projections, assets)

    tax_data = [
        ["Métrica", "Valor"],
        ["Renda Bruta Total", format_currency(tax_summary["total_gross_income"])],
        ["Renda Líquida Total", format_currency(tax_summary["total_net_income"])],
        ["Impostos Pagos", format_currency(tax_summary["total_tax_paid"])],
        ["Alíquota Efetiva", f"{tax_summary['effective_tax_rate']:.2f}%"],
    ]

    tax_table = Table(tax_data, colWidths=[8 * cm, 8 * cm])
    tax_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(tax_table)

    # Gerar PDF
    doc.build(elements)
    return buffer.getvalue()
