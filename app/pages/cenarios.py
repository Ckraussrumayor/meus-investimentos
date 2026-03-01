"""
Página: Gerenciamento de Cenários.

Permite criar, duplicar, congelar, excluir e comparar cenários.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.models.scenario import Scenario
from app.utils.financial_calculations import format_currency


def render():
    """Renderiza a página de cenários."""
    st.markdown("# 📂 Cenários")
    st.markdown("---")

    tab_list, tab_compare = st.tabs(["📋 Gerenciar Cenários", "📊 Comparar Cenários"])

    with tab_list:
        _render_scenario_list()

    with tab_compare:
        _render_comparison()


def _render_scenario_list():
    """Lista e gerencia cenários."""
    # Botão de novo cenário
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Novo Cenário", use_container_width=True):
            scenarios = Scenario.get_all()
            Scenario.create(f"Cenário {len(scenarios) + 1}")
            st.success("Cenário criado!")
            st.rerun()

    scenarios = Scenario.get_all()

    if not scenarios:
        st.info("Nenhum cenário encontrado. Crie um novo para começar.")
        return

    for scenario in scenarios:
        with st.expander(
            f"{'🔒' if scenario.status == 'congelado' else '📝'} {scenario.name} "
            f"— {scenario.status.capitalize()} | Criado em: {scenario.created_at[:16]}",
            expanded=False,
        ):
            params = Scenario.get_parameters(scenario.id)

            if params:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"**Inflação:** {params.inflation}%")
                    st.markdown(f"**SELIC:** {params.selic}%")
                    st.markdown(f"**CDI:** {params.cdi}%")

                with col2:
                    st.markdown(
                        f"**Aporte Mensal:** {format_currency(params.monthly_contribution)}"
                    )
                    st.markdown(
                        f"**Renda Desejada:** {format_currency(params.desired_monthly_income)}"
                    )
                    st.markdown(f"**SWR:** {params.safe_withdrawal_rate}%")

                with col3:
                    st.markdown(f"**Projeção:** {params.projection_months} meses")
                    if params.crisis_year:
                        st.markdown(
                            f"**Crise:** Ano {params.crisis_year} "
                            f"(-{params.crisis_drop_percent}%)"
                        )

            # Ações
            st.markdown("---")
            col_a, col_b, col_c, col_d = st.columns(4)

            with col_a:
                if scenario.status == "editavel":
                    if st.button(
                        "🔒 Congelar",
                        key=f"freeze_{scenario.id}",
                        use_container_width=True,
                    ):
                        Scenario.freeze(scenario.id)
                        st.success(f"Cenário '{scenario.name}' congelado!")
                        st.rerun()

            with col_b:
                if st.button(
                    "📋 Duplicar",
                    key=f"dup_{scenario.id}",
                    use_container_width=True,
                ):
                    Scenario.duplicate(scenario.id, f"{scenario.name} (Cópia)")
                    st.success("Cenário duplicado!")
                    st.rerun()

            with col_c:
                # Ver projeções
                projections = Scenario.get_projections(scenario.id)
                if projections:
                    st.markdown(f"📊 {len(projections)} meses projetados")
                else:
                    st.markdown("📊 Sem projeção")

            with col_d:
                if st.button(
                    "🗑️ Excluir",
                    key=f"del_{scenario.id}",
                    use_container_width=True,
                ):
                    Scenario.delete(scenario.id)
                    st.success("Cenário excluído!")
                    st.rerun()


def _render_comparison():
    """Compara múltiplos cenários."""
    scenarios = Scenario.get_all()
    scenarios_with_data = []

    for s in scenarios:
        projections = Scenario.get_projections(s.id)
        if projections:
            scenarios_with_data.append(s)

    if len(scenarios_with_data) < 2:
        st.info(
            "É necessário ter pelo menos 2 cenários com projeções executadas para comparação. "
            "Execute simulações na página do Simulador."
        )
        return

    # Seleção de cenários para comparar
    selected_names = st.multiselect(
        "Selecione cenários para comparar",
        options=[s.name for s in scenarios_with_data],
        default=[s.name for s in scenarios_with_data[:3]],
        max_selections=5,
    )

    if len(selected_names) < 2:
        st.warning("Selecione pelo menos 2 cenários.")
        return

    selected_ids = [s.id for s in scenarios_with_data if s.name in selected_names]

    # Gráfico comparativo de patrimônio
    st.markdown("### 📈 Comparação de Patrimônio")

    fig = go.Figure()
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336"]

    for i, scenario_id in enumerate(selected_ids):
        scenario = Scenario.get_by_id(scenario_id)
        projections = Scenario.get_projections(scenario_id)

        if projections:
            df = pd.DataFrame(projections)
            fig.add_trace(
                go.Scatter(
                    x=df["month"] / 12,
                    y=df["total_assets"],
                    mode="lines",
                    name=scenario.name,
                    line=dict(color=colors[i % len(colors)], width=2),
                )
            )

    fig.update_layout(
        xaxis_title="Anos",
        yaxis_title="R$",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=40, l=60, r=20),
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico comparativo de renda
    st.markdown("### 💵 Comparação de Renda Passiva")

    fig2 = go.Figure()
    for i, scenario_id in enumerate(selected_ids):
        scenario = Scenario.get_by_id(scenario_id)
        projections = Scenario.get_projections(scenario_id)

        if projections:
            df = pd.DataFrame(projections)
            fig2.add_trace(
                go.Scatter(
                    x=df["month"] / 12,
                    y=df["net_income"],
                    mode="lines",
                    name=scenario.name,
                    line=dict(color=colors[i % len(colors)], width=2),
                )
            )

    fig2.update_layout(
        xaxis_title="Anos",
        yaxis_title="R$ /mês",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=40, l=60, r=20),
        height=350,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Tabela comparativa
    st.markdown("### 📋 Resumo Comparativo")

    summary_data = []
    for scenario_id in selected_ids:
        scenario = Scenario.get_by_id(scenario_id)
        params = Scenario.get_parameters(scenario_id)
        projections = Scenario.get_projections(scenario_id)

        if projections and params:
            last = projections[-1]
            summary_data.append(
                {
                    "Cenário": scenario.name,
                    "Patrimônio Final": last["total_assets"],
                    "Renda Líquida Final": last["net_income"],
                    "Aporte Mensal": params.monthly_contribution,
                    "Inflação": f"{params.inflation}%",
                    "SELIC": f"{params.selic}%",
                    "Meses": params.projection_months,
                }
            )

    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(
            df_summary.style.format(
                {
                    "Patrimônio Final": "R$ {:,.2f}",
                    "Renda Líquida Final": "R$ {:,.2f}",
                    "Aporte Mensal": "R$ {:,.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
