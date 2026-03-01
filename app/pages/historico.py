"""
Página: Histórico de Snapshots.

Exibe a evolução patrimonial ao longo do tempo e permite
salvar snapshots do portfólio atual.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from app.models.portfolio import Portfolio
from app.models.asset_class import AssetClass
from app.utils.financial_calculations import format_currency


def render():
    """Renderiza a página de histórico."""
    st.markdown("# 📅 Histórico Patrimonial")
    st.markdown("---")

    # Salvar snapshot atual
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(
            "Salve um snapshot mensal do seu portfólio para acompanhar a evolução ao longo do tempo."
        )

    with col2:
        if st.button("📸 Salvar Snapshot", use_container_width=True, type="primary"):
            month_str = datetime.now().strftime("%Y-%m")
            Portfolio.save_snapshot(month_str)
            st.success(f"✅ Snapshot de {month_str} salvo!")
            st.rerun()

    st.markdown("---")

    # Exibir histórico
    history_df = Portfolio.get_history()

    if history_df.empty:
        st.info(
            "📝 Nenhum snapshot registrado ainda. "
            "Clique no botão acima para salvar o estado atual do seu portfólio."
        )
        return

    # Métricas de variação
    if len(history_df) >= 2:
        first = history_df.iloc[0]
        last = history_df.iloc[-1]

        patrimonio_change = last["Patrimônio"] - first["Patrimônio"]
        renda_change = last["Renda Passiva"] - first["Renda Passiva"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Patrimônio Atual",
                format_currency(last["Patrimônio"]),
                delta=format_currency(patrimonio_change),
            )
        with col2:
            st.metric(
                "Renda Passiva Atual",
                format_currency(last["Renda Passiva"]),
                delta=format_currency(renda_change),
            )
        with col3:
            st.metric("Total de Registros", f"{len(history_df)} meses")

    # Gráfico de evolução patrimonial
    st.markdown("### 📈 Evolução Patrimonial")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history_df["Mês"],
            y=history_df["Patrimônio"],
            mode="lines+markers",
            name="Patrimônio",
            line=dict(color="#2196F3", width=2),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(33, 150, 243, 0.1)",
        )
    )

    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="R$",
        hovermode="x unified",
        margin=dict(t=20, b=40, l=60, r=20),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico de renda passiva
    st.markdown("### 💵 Evolução da Renda Passiva")

    fig2 = go.Figure()

    fig2.add_trace(
        go.Bar(
            x=history_df["Mês"],
            y=history_df["Renda Passiva"],
            name="Renda Passiva",
            marker_color="#4CAF50",
        )
    )

    fig2.update_layout(
        xaxis_title="Mês",
        yaxis_title="R$ /mês",
        hovermode="x unified",
        margin=dict(t=20, b=40, l=60, r=20),
        height=350,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Tabela do histórico
    st.markdown("### 📋 Dados Históricos")

    st.dataframe(
        history_df.style.format(
            {
                "Patrimônio": "R$ {:,.2f}",
                "Renda Passiva": "R$ {:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
