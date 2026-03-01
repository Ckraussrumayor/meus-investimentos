"""
Página: Dashboard Principal.

Exibe visão consolidada do portfólio com métricas, gráficos
e resumo de alocação.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from app.models.portfolio import Portfolio
from app.models.asset_class import AssetClass
from app.services.market_data import get_indicators
from app.database.database import get_app_settings
from app.utils.financial_calculations import format_currency, format_percentage


def _calculate_real_passive_income(assets) -> dict:
    """Calcula a renda passiva real: direta (dividendos) + teórica (rendimentos acumulados)."""
    direct_income = 0.0       # Renda que cai na conta (monthly_income > 0)
    theoretical_income = 0.0  # Renda teórica de ativos que acumulam
    breakdown = []             # Detalhamento por tipo

    # Buscar indicadores atuais do BCB para cálculos de renda teórica
    indicators = get_indicators()
    bcb_cdi = indicators.get("cdi") if indicators["success"] else None
    bcb_selic = indicators.get("selic") if indicators["success"] else None

    # Buscar alíquota de IR configurada
    app_settings = get_app_settings()
    ir_rate = app_settings.get("ir_renda_fixa", 17.5) / 100  # ex: 0.175

    type_data = {}  # Agrupamento por tipo
    for a in assets:
        if a.type not in type_data:
            type_data[a.type] = {
                "direct": 0.0,
                "theoretical": 0.0,
                "current_value": 0.0,
                "invested_value": 0.0,
            }

        type_data[a.type]["current_value"] += a.current_value
        type_data[a.type]["invested_value"] += a.invested_value

        if a.monthly_income > 0:
            # Ativo com renda direta (dividendos, cupons, etc.)
            type_data[a.type]["direct"] += a.monthly_income
            direct_income += a.monthly_income
        elif a.current_value > 0 and (a.expected_annual_return > 0 or a.cdi_percentage > 0):
            # Ativo que acumula (Renda Fixa, Fundos): renda teórica mensal
            effective_return = a.expected_annual_return

            if a.cdi_percentage > 0 and bcb_cdi and bcb_cdi > 0:
                # Tem % do CDI cadastrado → usa CDI atual do BCB
                effective_return = (a.cdi_percentage / 100) * bcb_cdi
            elif a.type in ("Renda Fixa", "Fundos") and bcb_cdi and bcb_cdi > 0 and a.expected_annual_return <= 0:
                # Sem retorno cadastrado e sem % CDI → assume ~100% CDI como fallback
                effective_return = bcb_cdi
            # Se tem expected_annual_return > 0 (ex: Previdência com 6%), usa o valor cadastrado

            # Desconta taxa de administração e come-cotas
            net_return = effective_return - a.admin_fee
            if a.has_come_cotas:
                # Come-cotas reduz ~15% do rendimento semestral
                net_return *= 0.85
            monthly_theoretical = a.current_value * (net_return / 100) / 12
            # Aplicar IR sobre o rendimento (alíquota configurável)
            monthly_theoretical *= (1 - ir_rate)
            type_data[a.type]["theoretical"] += monthly_theoretical
            theoretical_income += monthly_theoretical

    for tipo, data in type_data.items():
        breakdown.append({
            "Tipo": tipo,
            "Renda Direta": data["direct"],
            "Renda Teórica": data["theoretical"],
            "Renda Total": data["direct"] + data["theoretical"],
            "Custo (Investido)": data["invested_value"],
            "Valor Atual": data["current_value"],
        })

    total_invested = sum(data.get("invested_value", 0) for data in type_data.values())
    total_current = sum(data.get("current_value", 0) for data in type_data.values())

    # Base de cálculo do yield: invested_value para RV, current_value para RF
    TIPOS_RENDA_FIXA = {"Renda Fixa", "Fundos"}
    yield_base = sum(
        data["current_value"] if tipo in TIPOS_RENDA_FIXA else data["invested_value"]
        for tipo, data in type_data.items()
    )

    return {
        "direct_income": direct_income,
        "theoretical_income": theoretical_income,
        "total_income": direct_income + theoretical_income,
        "total_invested": total_invested,
        "total_current": total_current,
        "yield_base": yield_base,
        "ir_rate_pct": app_settings.get("ir_renda_fixa", 17.5),
        "bcb_cdi": bcb_cdi,
        "bcb_selic": bcb_selic,
        "bcb_available": indicators["success"],
        "breakdown": breakdown,
    }


def _render_real_passive_income(data: dict, total_patrimony: float):
    """Renderiza a seção de renda passiva real no dashboard."""
    st.markdown("### 🏦 Renda Passiva Real (Visão Completa)")

    # Info sobre fonte dos dados
    ir_pct = data.get("ir_rate_pct", 17.5)
    if data.get("bcb_available"):
        st.caption(
            f"Combina renda direta (dividendos) + rendimentos teóricos **líquidos** de ativos que acumulam. "
            f"**CDI atual (BCB): {data.get('bcb_cdi', 'N/A')}% a.a.** "
            f"| SELIC: {data.get('bcb_selic', 'N/A')}% a.a. "
            f"| **IR: {ir_pct:.1f}%** (configurável em ⚙️ Configurações)"
        )
    else:
        st.caption(
            "Combina a renda que cai na conta (dividendos) com os rendimentos "
            f"de ativos que acumulam. **IR: {ir_pct:.1f}%** (configurável em ⚙️ Configurações)"
        )

    total = data["total_income"]
    direct = data["direct_income"]
    theoretical = data["theoretical_income"]

    # Yield mensal e anual — base mista: custo para RV, valor atual para RF
    yield_base = data.get("yield_base", 0)
    yield_mensal = (total / yield_base * 100) if yield_base > 0 else 0
    yield_anual = yield_mensal * 12

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "💰 Renda Passiva Total",
            format_currency(total),
            help="Soma da renda direta (dividendos) + renda teórica líquida de ativos que acumulam.",
        )
    with col2:
        st.metric(
            "💵 Renda Direta",
            format_currency(direct),
            help="Dividendos, cupons e rendimentos que efetivamente caem na conta todo mês.",
        )
    with col3:
        st.metric(
            "📊 Renda Teórica (Líq.)",
            format_currency(theoretical),
            help=f"Rendimentos de Renda Fixa e Fundos que ficam acumulando. Valor **líquido** estimado: descontado taxa de administração, come-cotas e **IR {ir_pct:.1f}%**. Ajuste o IR em ⚙️ Configurações.",
        )
    with col4:
        st.metric(
            "📈 Yield (Mês / Ano)",
            f"{yield_mensal:.2f}% / {yield_anual:.2f}%",
            help="Renda Variável (FIIs, Ações, ETFs): sobre o **valor investido** (Yield on Cost). "
                 "Renda Fixa e Fundos: sobre o **valor atual** (rendimento real do montante acumulado).",
        )

    # Renda anual
    st.info(
        f"📅 **Renda passiva anual estimada:** {format_currency(total * 12)} "
        f"(equivalente a {format_currency(total)}/mês)"
    )

    # Detalhamento por tipo
    if data["breakdown"]:
        with st.expander("📋 Detalhamento por Tipo de Ativo", expanded=False):
            df = pd.DataFrame(data["breakdown"])
            df = df.sort_values("Renda Total", ascending=False).reset_index(drop=True)

            # Yield: custo para RV, valor atual para RF/Fundos
            TIPOS_RF = {"Renda Fixa", "Fundos"}
            df["Base Yield"] = df.apply(
                lambda row: row["Valor Atual"] if row["Tipo"] in TIPOS_RF else row["Custo (Investido)"],
                axis=1,
            )
            df["Yield (%)"] = df.apply(
                lambda row: (row["Renda Total"] / row["Base Yield"] * 100)
                if row["Base Yield"] > 0 else 0,
                axis=1,
            )
            df["Base"] = df["Tipo"].apply(
                lambda t: "Valor Atual" if t in TIPOS_RF else "Custo (Investido)"
            )
            df = df.drop(columns=["Base Yield"])

            st.dataframe(
                df.style.format({
                    "Renda Direta": "R$ {:,.2f}",
                    "Renda Teórica": "R$ {:,.2f}",
                    "Renda Total": "R$ {:,.2f}",
                    "Custo (Investido)": "R$ {:,.2f}",
                    "Valor Atual": "R$ {:,.2f}",
                    "Yield (%)": "{:.2f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

            # Gráfico de composição da renda
            fig = go.Figure()
            tipos = df["Tipo"].tolist()
            fig.add_trace(go.Bar(
                name="Renda Direta",
                x=tipos,
                y=df["Renda Direta"].tolist(),
                marker_color="#2196F3",
                hovertemplate="<b>%{x}</b><br>Direta: R$ %{y:,.2f}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                name="Renda Teórica",
                x=tipos,
                y=df["Renda Teórica"].tolist(),
                marker_color="#FF9800",
                hovertemplate="<b>%{x}</b><br>Teórica: R$ %{y:,.2f}<extra></extra>",
            ))
            fig.update_layout(
                barmode="stack",
                xaxis_title="",
                yaxis_title="R$ / mês",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=40, b=20, l=60, r=20),
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")


def render():
    """Renderiza o dashboard principal."""
    st.markdown("# 📊 Dashboard")
    st.markdown("---")

    summary = Portfolio.get_summary()
    passive_income_data = _calculate_real_passive_income(summary["assets"])

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💰 Patrimônio Atual",
            format_currency(summary["total_current"]),
            delta=format_currency(summary["total_gain"]),
        )
    with col2:
        st.metric(
            "📈 Total Investido",
            format_currency(summary["total_invested"]),
        )
    with col3:
        st.metric(
            "💵 Renda Mensal Direta",
            format_currency(summary["total_monthly_income"]),
            help="Renda que efetivamente cai na conta todo mês (dividendos de FII, cupons, etc.).",
        )
    with col4:
        st.metric(
            "📊 Rentabilidade",
            format_percentage(summary["gain_pct"]),
        )

    st.markdown("---")

    # Renda Passiva Real (direta + teórica)
    _render_real_passive_income(passive_income_data, summary["total_current"])

    if summary["asset_count"] == 0:
        st.info(
            "📝 Nenhuma classe de ativo cadastrada. "
            "Vá para a página **Cadastro** para adicionar seus investimentos."
        )
        return

    # Gráficos
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🎯 Alocação por Tipo")
        allocation_df = Portfolio.get_allocation_by_type()
        if not allocation_df.empty:
            fig = px.pie(
                allocation_df,
                values="Valor Atual",
                names="Tipo",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>"
                + "Valor: R$ %{value:,.2f}<br>"
                + "Percentual: %{percent}<extra></extra>",
            )
            fig.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                margin=dict(t=20, b=20, l=20, r=20),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("### 💵 Renda por Tipo")
        income_df = Portfolio.get_income_by_type()
        if not income_df.empty:
            fig = px.bar(
                income_df,
                x="Tipo",
                y="Renda Mensal",
                color="Tipo",
                color_discrete_sequence=px.colors.qualitative.Set2,
                text_auto=".2f",
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="R$",
                margin=dict(t=20, b=20, l=20, r=20),
                height=350,
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Renda: R$ %{y:,.2f}<extra></extra>"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Tabela de ativos
    st.markdown("### 📋 Classes de Ativos Cadastradas")
    assets = AssetClass.get_all()

    if assets:
        app_settings = get_app_settings()
        ir_pct = app_settings.get("ir_renda_fixa", 17.5)

        data = []
        for a in assets:
            gain = a.current_value - a.invested_value
            gain_pct = (gain / a.invested_value * 100) if a.invested_value > 0 else 0

            # Calcular retorno líquido anual
            gross_return = a.expected_annual_return
            net_return = gross_return - a.admin_fee
            if a.has_come_cotas:
                net_return *= 0.85
            # Aplicar IR para ativos que acumulam (sem renda direta)
            if a.monthly_income == 0 and gross_return > 0:
                net_return *= (1 - ir_pct / 100)

            data.append(
                {
                    "Nome": a.name,
                    "Tipo": a.type,
                    "Investido": a.invested_value,
                    "Atual": a.current_value,
                    "Ganho/Perda": gain,
                    "Rent. (%)": round(gain_pct, 2),
                    "Renda Mensal": a.monthly_income,
                    "Retorno Líq. (% a.a.)": round(net_return, 2),
                }
            )

        df = pd.DataFrame(data)
        st.dataframe(
            df.style.format(
                {
                    "Investido": "R$ {:,.2f}",
                    "Atual": "R$ {:,.2f}",
                    "Ganho/Perda": "R$ {:,.2f}",
                    "Rent. (%)": "{:.2f}%",
                    "Renda Mensal": "R$ {:,.2f}",
                    "Retorno Líq. (% a.a.)": "{:.2f}%",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # Histórico (se houver)
    history_df = Portfolio.get_history()
    if not history_df.empty:
        st.markdown("### 📈 Evolução Patrimonial (Histórico)")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=history_df["Mês"],
                y=history_df["Patrimônio"],
                mode="lines+markers",
                name="Patrimônio",
                line=dict(color="#2196F3", width=2),
            )
        )
        fig.update_layout(
            xaxis_title="Mês",
            yaxis_title="R$",
            hovermode="x unified",
            margin=dict(t=20, b=40, l=60, r=20),
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
