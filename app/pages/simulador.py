"""
Página: Simulador FIRE (independência financeira).

Permite configurar parâmetros e executar simulações de projeção
patrimonial com análise FIRE.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.models.scenario import Scenario
from app.models.asset_class import AssetClass
from app.services.projection_engine import ProjectionEngine
from app.services.market_data import get_indicators
from app.utils.financial_calculations import format_currency, format_percentage


def render():
    """Renderiza a página do simulador FIRE."""
    st.markdown("# 🎯 Simulador de Independência Financeira")
    st.markdown("---")

    assets = AssetClass.get_all()
    if not assets:
        st.warning(
            "⚠️ Cadastre pelo menos uma classe de ativo antes de usar o simulador."
        )
        return

    # Selecionar ou criar cenário
    scenarios = Scenario.get_all()
    scenario_options = {s.name: s.id for s in scenarios if s.status == "editavel"}

    col_select, col_new = st.columns([3, 1])

    with col_select:
        if scenario_options:
            selected_name = st.selectbox(
                "Cenário",
                options=list(scenario_options.keys()),
                key="sim_scenario_select",
            )
            scenario_id = scenario_options[selected_name]
        else:
            st.info("Nenhum cenário editável encontrado. Crie um novo.")
            scenario_id = None

    with col_new:
        st.markdown("")
        st.markdown("")
        if st.button("➕ Novo Cenário", use_container_width=True):
            new_id = Scenario.create(f"Cenário {len(scenarios) + 1}")
            st.success("Cenário criado!")
            st.rerun()

    if not scenario_id:
        return

    params = Scenario.get_parameters(scenario_id)
    if not params:
        st.error("Parâmetros do cenário não encontrados.")
        return

    # Parâmetros da simulação
    st.markdown("### ⚙️ Parâmetros da Simulação")

    # Indicadores BCB (informativo)
    if "_market_indicators" not in st.session_state:
        st.session_state["_market_indicators"] = get_indicators()
    indicators = st.session_state["_market_indicators"]

    if indicators["success"]:
        st.info(
            f"🏦 **Indicadores BCB** — "
            f"Atualizado em {indicators['updated_at']}  \n"
            f"SELIC: **{indicators.get('selic', 'N/A')}%** | "
            f"CDI: **{indicators.get('cdi', 'N/A')}%** | "
            f"IPCA 12m: **{indicators.get('ipca', 'N/A')}%**"
        )

    # Resolver valores: BCB tem prioridade sobre defaults
    def _resolve_bcb(indicator_key):
        """Retorna o valor do BCB se disponível."""
        return indicators.get(indicator_key)

    _bcb_inflation = _resolve_bcb("inflation")
    _bcb_selic = _resolve_bcb("selic")
    _bcb_cdi = _resolve_bcb("cdi")
    _bcb_ipca = _resolve_bcb("ipca")

    with st.form("simulation_params"):
        tab_basic, tab_contributions, tab_fire, tab_advanced = st.tabs(
            ["📊 Macroeconômico", "💰 Aportes e Retiradas", "🎯 FIRE", "⚡ Avançado"]
        )

        with tab_basic:
            st.caption(
                "💡 Indicadores carregados do **Banco Central do Brasil**. "
                "Você pode ajustar manualmente antes de simular."
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                inflation = st.number_input(
                    "Inflação (% a.a.)",
                    value=_bcb_inflation if _bcb_inflation is not None else params.inflation,
                    min_value=0.0,
                    max_value=50.0,
                    step=0.25,
                    format="%.2f",
                    help=(
                        "Inflação geral esperada para o período da simulação. "
                        "Usada para calcular o patrimônio em valores reais (descontada a inflação). "
                        "Ex.: 4.50 = 4,5%% ao ano."
                    ),
                )
                selic = st.number_input(
                    "SELIC (% a.a.)",
                    value=_bcb_selic if _bcb_selic is not None else params.selic,
                    min_value=0.0,
                    max_value=50.0,
                    step=0.25,
                    format="%.2f",
                    help=(
                        "Taxa Selic vigente ou projetada. É a taxa básica de juros da economia e "
                        "referência para investimentos de renda fixa como Tesouro Selic. "
                        "Ex.: 13.75 = 13,75%% ao ano."
                    ),
                )
            with col2:
                cdi = st.number_input(
                    "CDI (% a.a.)",
                    value=_bcb_cdi if _bcb_cdi is not None else params.cdi,
                    min_value=0.0,
                    max_value=50.0,
                    step=0.25,
                    format="%.2f",
                    help=(
                        "Taxa do CDI anual, geralmente muito próxima da Selic. "
                        "Serve como benchmark para CDBs, LCIs, LCAs e fundos DI. "
                        "Ex.: 13.65 = 13,65%% ao ano. Se seu CDB rende '110%% do CDI', "
                        "o retorno será 110%% × este valor."
                    ),
                )
                ipca = st.number_input(
                    "IPCA (% a.a.)",
                    value=_bcb_ipca if _bcb_ipca is not None else params.ipca,
                    min_value=0.0,
                    max_value=50.0,
                    step=0.25,
                    format="%.2f",
                    help=(
                        "IPCA projetado — índice oficial de inflação. Usado como base para "
                        "títulos atrelados à inflação (Tesouro IPCA+). Geralmente igual ou "
                        "próximo ao campo 'Inflação'. Ex.: 4.50 = 4,5%% ao ano."
                    ),
                )
            with col3:
                salary_growth = st.number_input(
                    "Crescimento Salarial (% a.a.)",
                    value=params.salary_growth,
                    min_value=0.0,
                    max_value=30.0,
                    step=0.5,
                    format="%.2f",
                    help=(
                        "Estimativa de aumento anual da sua renda/salário. Impacta o crescimento "
                        "do aporte mensal ao longo do tempo. Se você espera reajustes apenas pela "
                        "inflação, coloque o mesmo valor do IPCA. Se espera promoções ou aumento "
                        "real, coloque algo maior. Ex.: 3.00 = 3% ao ano."
                    ),
                )
                projection_months = st.number_input(
                    "Período de Projeção (meses)",
                    value=params.projection_months,
                    min_value=12,
                    max_value=1200,
                    step=12,
                    help=(
                        "Horizonte da simulação em meses. Exemplos: "
                        "120 = 10 anos | 240 = 20 anos | 360 = 30 anos. "
                        "Quanto maior o período, mais distante a projeção — ideal para FIRE."
                    ),
                )

        with tab_contributions:
            st.caption(
                "💡 Informe os valores que você **realmente consegue investir** todo mês, "
                "além de eventuais aportes extras e retiradas planejadas."
            )
            col1, col2 = st.columns(2)
            with col1:
                monthly_contribution = st.number_input(
                    "Aporte Mensal (R$)",
                    value=params.monthly_contribution,
                    min_value=0.0,
                    step=100.0,
                    format="%.2f",
                    help=(
                        "Valor que você consegue **separar do salário/renda** e investir todo mês. "
                        "NÃO inclua aqui os rendimentos dos seus investimentos (dividendos de FIIs, "
                        "juros de renda fixa, etc.) — esses já são calculados automaticamente pela "
                        "simulação com base nos ativos cadastrados.\n\n"
                        "✅ Inclua: sobra do salário, renda extra de freelance, aluguel, etc.\n"
                        "❌ Não inclua: dividendos de FIIs, cupons de renda fixa, rendimentos.\n\n"
                        "Ex.: Se seu salário é R$ 8.000 e seus custos fixos são R$ 5.000, "
                        "coloque **3000.00**."
                    ),
                )
                extra_contribution = st.number_input(
                    "Aporte Extra Pontual (R$)",
                    value=params.extra_contribution,
                    min_value=0.0,
                    step=1000.0,
                    format="%.2f",
                    help=(
                        "Valor único e pontual que você pretende investir em um mês específico. "
                        "Ideal para simular entradas extras como:\n"
                        "• 13º salário (ex.: R$ 5.000)\n"
                        "• Restituição do IR (ex.: R$ 3.000)\n"
                        "• Saque de FGTS (ex.: R$ 20.000)\n"
                        "• Rescisão trabalhista\n"
                        "• Venda de um bem\n\n"
                        "Ex.: 10000.00 = aporte extra de R$ 10.000 no mês indicado abaixo."
                    ),
                )
                extra_contribution_month = st.number_input(
                    "Mês do Aporte Extra",
                    value=params.extra_contribution_month or 0,
                    min_value=0,
                    max_value=1200,
                    help=(
                        "Em qual mês da simulação o aporte extra será aplicado. "
                        "O mês 1 = próximo mês, mês 12 = daqui 1 ano, mês 24 = daqui 2 anos.\n\n"
                        "Coloque **0** se não deseja aporte extra.\n\n"
                        "Ex.: Se pretende investir o 13º daqui a 6 meses, coloque **6**."
                    ),
                )

                # Destino do aporte extra
                target_options = [
                    "Proporcional (manter alocação atual)",
                    "FII",
                    "Ações",
                    "ETF",
                    "Renda Fixa",
                    "Fundos",
                ]
                target_map = {
                    "Proporcional (manter alocação atual)": "proporcional",
                    "FII": "FII",
                    "Ações": "Ações",
                    "ETF": "ETF",
                    "Renda Fixa": "Renda Fixa",
                    "Fundos": "Fundos",
                }
                reverse_map = {v: k for k, v in target_map.items()}
                current_target = getattr(params, "extra_contribution_target", "proporcional")
                current_label = reverse_map.get(current_target, target_options[0])

                extra_contribution_target = st.selectbox(
                    "Destino do Aporte Extra",
                    options=target_options,
                    index=target_options.index(current_label) if current_label in target_options else 0,
                    help=(
                        "Para onde o aporte extra será direcionado. Isso afeta diretamente "
                        "o cálculo da **renda passiva** gerada após o aporte:\n\n"
                        "• **Proporcional** — distribui entre todos os ativos mantendo a "
                        "alocação atual. A renda cresce conforme o yield médio do portfólio.\n\n"
                        "• **FII** — direciona para Fundos Imobiliários. Como FIIs pagam "
                        "dividendos mensais, o impacto na renda passiva é **imediato e alto**. "
                        "Ex.: yield de 0,8%/mês → R$ 10.000 geram ~R$ 80/mês de renda.\n\n"
                        "• **Ações / ETF** — direciona para renda variável. O impacto na renda "
                        "passiva depende do dividend yield (geralmente menor que FIIs). "
                        "O ganho principal vem da valorização do patrimônio.\n\n"
                        "• **Renda Fixa** — direciona para CDBs, Tesouro, LCIs, etc. "
                        "Gera renda previsível via juros, mas geralmente com come-cotas ou IR.\n\n"
                        "• **Fundos** — direciona para fundos de investimento diversos."
                    ),
                )
                extra_target_value = target_map[extra_contribution_target]
            with col2:
                withdrawal_start_month = st.number_input(
                    "Início das Retiradas (mês)",
                    value=params.withdrawal_start_month or 0,
                    min_value=0,
                    max_value=1200,
                    help=(
                        "Mês da simulação em que você planeja **começar a viver da renda passiva** "
                        "(parar de aportar e começar a retirar). "
                        "Coloque **0** se não pretende simular retiradas.\n\n"
                        "Ex.: 240 = começar a retirar após 20 anos | "
                        "120 = começar após 10 anos."
                    ),
                )
                monthly_withdrawal = st.number_input(
                    "Retirada Mensal (R$)",
                    value=params.monthly_withdrawal,
                    min_value=0.0,
                    step=100.0,
                    format="%.2f",
                    help=(
                        "Valor que você pretende **retirar por mês** do patrimônio após o mês de "
                        "início das retiradas. Esse valor simula seu custo de vida na aposentadoria.\n\n"
                        "⚠️ Se esse valor for maior que a renda passiva gerada, o patrimônio será "
                        "consumido ao longo do tempo.\n\n"
                        "Ex.: 5000.00 = retirar R$ 5.000/mês para despesas pessoais."
                    ),
                )

        with tab_fire:
            st.caption(
                "💡 Configure aqui a sua **meta de independência financeira**. "
                "O simulador calcula quanto você precisa acumular para viver da renda passiva."
            )
            col1, col2 = st.columns(2)
            with col1:
                desired_monthly_income = st.number_input(
                    "Renda Mensal Desejada Líquida (R$)",
                    value=params.desired_monthly_income,
                    min_value=0.0,
                    step=500.0,
                    format="%.2f",
                    help=(
                        "Quanto você deseja receber **por mês de renda líquida** (já descontados "
                        "impostos, taxas de administração e come-cotas) ao atingir a "
                        "independência financeira. Pense no seu custo de vida mensal desejado, "
                        "incluindo moradia, alimentação, saúde, lazer e reserva.\n\n"
                        "Ex.: Se seus gastos mensais hoje são R$ 5.000 e quer uma margem, "
                        "coloque **7000.00**.\n\n"
                        "⚠️ Este valor é nominal (sem considerar inflação futura). "
                        "O simulador já corrige pela inflação configurada."
                    ),
                )
            with col2:
                safe_withdrawal_rate = st.number_input(
                    "Taxa de Retirada Segura (% a.a.)",
                    value=params.safe_withdrawal_rate,
                    min_value=1.0,
                    max_value=10.0,
                    step=0.5,
                    format="%.2f",
                    help=(
                        "Percentual anual que você pode retirar do patrimônio sem esgotá-lo. "
                        "A regra mais conhecida é a dos **4%** (Regra dos 4%), que indica:\n\n"
                        "Patrimônio necessário = (Renda Anual Desejada) ÷ 4%\n\n"
                        "Ex.: Para renda de R$ 5.000/mês = R$ 60.000/ano ÷ 4% = **R$ 1.500.000** "
                        "de patrimônio-alvo.\n\n"
                        "Valores mais conservadores (3%) exigem mais patrimônio, mas são mais seguros. "
                        "Valores maiores (5-6%) são mais arriscados e podem consumir o patrimônio."
                    ),
                )

        with tab_advanced:
            st.caption(
                "💡 Simule cenários de **crise** para testar a resiliência do seu portfólio. "
                "Opcional — deixe zerado se não quiser simular crises."
            )
            col1, col2 = st.columns(2)
            with col1:
                crisis_year = st.number_input(
                    "Ano da Crise Simulada",
                    value=params.crisis_year or 0,
                    min_value=0,
                    max_value=100,
                    help=(
                        "Em qual ano da simulação ocorreria uma crise hipotética. "
                        "A crise aplica uma queda percentual no patrimônio naquele ano.\n\n"
                        "Coloque **0** para não simular crise.\n\n"
                        "Ex.: 5 = crise no 5º ano | 10 = crise no 10º ano.\n"
                        "Referência: a crise de 2008 causou quedas de 30-50% em bolsa."
                    ),
                )
            with col2:
                crisis_drop_percent = st.number_input(
                    "Queda na Crise (%)",
                    value=params.crisis_drop_percent,
                    min_value=0.0,
                    max_value=80.0,
                    step=5.0,
                    format="%.1f",
                    help=(
                        "Percentual de queda que o patrimônio sofreria no ano da crise.\n\n"
                        "Exemplos históricos:\n"
                        "• Crise moderada: 15-20%\n"
                        "• Crise de 2008 (bolsa): 35-50%\n"
                        "• Covid-19 2020 (bolsa): 30-45%\n"
                        "• Renda fixa em crise: 5-10%\n\n"
                        "Ex.: 30.0 = queda de 30% no patrimônio no ano indicado."
                    ),
                )

        submitted = st.form_submit_button(
            "🚀 Executar Simulação", use_container_width=True, type="primary"
        )

    if submitted:
        # Atualizar parâmetros
        Scenario.update_parameters(
            scenario_id,
            inflation=inflation,
            selic=selic,
            cdi=cdi,
            ipca=ipca,
            salary_growth=salary_growth,
            monthly_contribution=monthly_contribution,
            extra_contribution=extra_contribution,
            extra_contribution_month=extra_contribution_month if extra_contribution_month > 0 else None,
            extra_contribution_target=extra_target_value,
            desired_monthly_income=desired_monthly_income,
            safe_withdrawal_rate=safe_withdrawal_rate,
            withdrawal_start_month=withdrawal_start_month if withdrawal_start_month > 0 else None,
            monthly_withdrawal=monthly_withdrawal,
            crisis_year=crisis_year if crisis_year > 0 else None,
            crisis_drop_percent=crisis_drop_percent,
            projection_months=projection_months,
        )

        with st.spinner("Calculando projeção..."):
            engine = ProjectionEngine(scenario_id)
            projections = engine.run_and_save()
            fire_analysis = engine.get_fire_analysis()

        if projections:
            st.session_state["last_projections"] = projections
            st.session_state["last_fire_analysis"] = fire_analysis
            st.session_state["last_scenario_id"] = scenario_id
            st.success("✅ Simulação concluída!")

    # Exibir resultados
    projections = st.session_state.get("last_projections")
    fire_analysis = st.session_state.get("last_fire_analysis")

    if projections and fire_analysis:
        _render_fire_metrics(fire_analysis)
        _render_projection_charts(projections, fire_analysis)
        _render_projection_table(projections)


def _render_fire_metrics(fire_analysis: dict):
    """Exibe métricas FIRE."""
    st.markdown("---")
    st.markdown("### 🎯 Análise FIRE")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🏦 Patrimônio Necessário",
            format_currency(fire_analysis["fire_target"]),
        )
    with col2:
        st.metric(
            "📊 Progresso",
            format_percentage(fire_analysis["progress_pct"]),
        )
    with col3:
        months = fire_analysis["months_to_fire"]
        if months > 0:
            st.metric(
                "⏱️ Tempo para FIRE",
                f"{fire_analysis['years_to_fire']} anos ({months} meses)",
            )
        elif months == 0:
            st.metric("⏱️ Tempo para FIRE", "🎉 Já atingido!")
        else:
            st.metric("⏱️ Tempo para FIRE", "Não atingível")

    with col4:
        st.metric(
            "💵 Renda Líquida Desejada",
            format_currency(fire_analysis["desired_monthly_income"]),
        )

    # Barra de progresso
    progress = min(fire_analysis["progress_pct"] / 100, 1.0)
    st.progress(progress, text=f"Progresso: {fire_analysis['progress_pct']:.1f}%")


def _render_projection_charts(projections: list, fire_analysis: dict):
    """Exibe gráficos da projeção."""
    st.markdown("---")
    st.markdown("### 📈 Projeção Patrimonial")

    df = pd.DataFrame(projections)

    # Converter meses para anos para melhor visualização
    df["Ano"] = df["month"] / 12

    # Gráfico de patrimônio
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Ano"],
            y=df["total_assets"],
            mode="lines",
            name="Patrimônio (Nominal)",
            line=dict(color="#2196F3", width=2),
        )
    )

    if "total_assets_real" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Ano"],
                y=df["total_assets_real"],
                mode="lines",
                name="Patrimônio (Real)",
                line=dict(color="#4CAF50", width=2, dash="dash"),
            )
        )

    # Linha FIRE target
    fig.add_hline(
        y=fire_analysis["fire_target"],
        line_dash="dot",
        line_color="red",
        annotation_text=f"Meta FIRE: {format_currency(fire_analysis['fire_target'])}",
    )

    # Benchmarks
    for bench_name, bench_col, color in [
        ("CDI", "benchmark_cdi", "#FF9800"),
        ("SELIC", "benchmark_selic", "#9C27B0"),
        ("IPCA", "benchmark_ipca", "#607D8B"),
    ]:
        if bench_col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["Ano"],
                    y=df[bench_col],
                    mode="lines",
                    name=bench_name,
                    line=dict(color=color, width=1, dash="dot"),
                    visible="legendonly",
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

    # Gráfico de renda passiva
    st.markdown("### 💵 Projeção de Renda Passiva Líquida")

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=df["Ano"],
            y=df["passive_income"],
            mode="lines",
            name="Renda Líquida",
            line=dict(color="#4CAF50", width=2),
            fill="tozeroy",
            fillcolor="rgba(76, 175, 80, 0.1)",
        )
    )

    # Linha de renda desejada
    fig2.add_hline(
        y=fire_analysis["desired_monthly_income"],
        line_dash="dot",
        line_color="red",
        annotation_text=f"Meta: {format_currency(fire_analysis['desired_monthly_income'])}",
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


def _render_projection_table(projections: list):
    """Exibe tabela com projeção resumida (anual)."""
    st.markdown("### 📋 Projeção Detalhada (Anual)")

    if not projections:
        return

    df_all = pd.DataFrame(projections)

    # Calcular o ano de cada mês (mês 1-12 = ano 1, etc.)
    df_all["Ano"] = ((df_all["month"] - 1) // 12) + 1

    # Agregar por ano: patrimônio final, renda do último mês, soma de aportes/extras/retiradas
    annual = (
        df_all.groupby("Ano")
        .agg(
            Patrimônio=("total_assets", "last"),
            Renda_Líquida=("net_income", "last"),
            Aporte_Mensal_Total=("contribution", "sum"),
            Aporte_Extra=("extra_contribution", "sum"),
            Retirada_Total=("withdrawal", "sum"),
        )
        .reset_index()
    )

    # Aporte total = soma dos aportes mensais + extras no ano
    annual["Aporte Total"] = annual["Aporte_Mensal_Total"] + annual["Aporte_Extra"]

    annual = annual.rename(
        columns={
            "Renda_Líquida": "Renda Líquida",
            "Aporte_Extra": "Aporte Extra",
            "Retirada_Total": "Retirada",
        }
    )

    display_cols = [
        "Ano", "Patrimônio", "Renda Líquida",
        "Aporte Total", "Aporte Extra", "Retirada",
    ]
    df_display = annual[display_cols]

    st.dataframe(
        df_display.style.format(
            {
                "Patrimônio": "R$ {:,.2f}",
                "Renda Líquida": "R$ {:,.2f}",
                "Aporte Total": "R$ {:,.2f}",
                "Aporte Extra": "R$ {:,.2f}",
                "Retirada": "R$ {:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
