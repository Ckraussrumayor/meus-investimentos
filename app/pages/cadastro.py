"""
Página: Cadastro de Classes de Ativos.

Permite criar, editar e excluir classes de ativos consolidadas.
"""

import streamlit as st

from app.models.asset_class import AssetClass
from app.services.market_data import get_indicators
from app.utils.constants import ASSET_TYPES, TAX_TYPES
from app.utils.financial_calculations import format_currency


def render():
    """Renderiza a página de cadastro de ativos."""
    st.markdown("# 📝 Cadastro de Classes de Ativos")
    st.markdown("---")

    tab_novo, tab_editar, tab_excluir = st.tabs(
        ["➕ Nova Classe", "✏️ Editar", "🗑️ Excluir"]
    )

    with tab_novo:
        _render_create_form()

    with tab_editar:
        _render_edit_form()

    with tab_excluir:
        _render_delete_form()


def _render_create_form():
    """Formulário para criar nova classe de ativo."""
    st.markdown("### Cadastrar Nova Classe de Ativo")

    # Buscar indicadores atuais do BCB para referência
    indicators = get_indicators()
    if indicators["success"]:
        _selic = indicators.get("selic", "N/A")
        _cdi = indicators.get("cdi", "N/A")
        _ipca = indicators.get("ipca", "N/A")
        st.info(
            f"📊 **Indicadores BCB atuais** — SELIC: **{_selic}%** | CDI: **{_cdi}%** | IPCA: **{_ipca}%** a.a.  \n"
            f"Use como referência para o Retorno Esperado e % do CDI."
        )

    with st.form("create_asset_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Nome da Classe *",
                placeholder="Ex.: FIIs de Logística",
                help="Identificação desta classe de ativo. Use um nome descritivo que facilite a organização, como 'FIIs de Logística', 'Ações Dividendos' ou 'Tesouro IPCA+'. Ex.: 'FIIs Shoppings'.",
            )
            asset_type = st.selectbox(
                "Tipo *",
                options=ASSET_TYPES,
                help="Categoria do ativo que define como ele será agrupado nos relatórios e simulações. Tipos disponíveis: FII (Fundos Imobiliários), Ações, ETF, Renda Fixa e Fundos de Investimento.",
            )
            invested_value = st.number_input(
                "Valor Investido (R$)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Valor total que você investiu nesta classe ao longo do tempo (custo de aquisição). Usado para calcular o retorno (lucro ou prejuízo) da classe. Ex.: se você comprou R$ 50.000 em FIIs, informe 50000.",
            )
            current_value = st.number_input(
                "Valor Atual (R$)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Valor de mercado atual desta classe de ativo (quanto ela vale hoje). A diferença entre o valor atual e o valor investido mostra seu ganho ou perda patrimonial. Ex.: se seus FIIs valem R$ 55.000 hoje, informe 55000.",
            )
            monthly_income = st.number_input(
                "Renda Mensal (R$)",
                min_value=0.0,
                step=10.0,
                format="%.2f",
                help="Renda passiva mensal gerada por esta classe (dividendos, rendimentos, juros, aluguéis, etc.). Este valor é usado nas projeções de independência financeira. Ex.: se seus FIIs pagam R$ 400/mês em dividendos, informe 400.",
            )

        with col2:
            expected_return = st.number_input(
                "Retorno Esperado (% a.a.)",
                min_value=0.0,
                max_value=100.0,
                step=0.5,
                value=10.0,
                format="%.2f",
                help="Rentabilidade anual esperada para esta classe, incluindo valorização + rendimentos. Usado nas projeções do simulador FIRE. Exemplos típicos: FIIs 8-12%%, Ações 10-15%%, Renda Fixa 10-13%%, ETFs 8-12%%.",
            )
            admin_fee = st.number_input(
                "Taxa de Administração (% a.a.)",
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                value=0.0,
                format="%.2f",
                help="Taxa cobrada anualmente pelo gestor do fundo/ativo. Reduz o retorno efetivo. Exemplos: FIIs 0,5-1,5%%, Fundos de Ações 1-2%%, ETFs 0,2-0,8%%, Ações individuais 0%%, Tesouro Direto 0,2%%.",
            )
            tax_type = st.selectbox(
                "Tipo de Tributação",
                options=TAX_TYPES,
                help="Regime de imposto de renda aplicável: • Regressivo — IR decresce com o tempo, de 22,5%% (até 180 dias) a 15%% (acima de 720 dias), comum em Renda Fixa e CDBs. • Fixo 15%% — alíquota fixa sobre o ganho de capital, comum em Ações e ETFs. • Isento — sem IR sobre rendimentos, como dividendos de FII para pessoa física.",
            )
            has_come_cotas = st.checkbox(
                "Possui Come-Cotas?",
                help="Marque se o fundo possui come-cotas: antecipação semestral de IR (maio e novembro) que reduz a quantidade de cotas. Afeta fundos de investimento abertos (Renda Fixa: 15%%, Multimercado: 15%%, Curto Prazo: 20%%). FIIs, Ações e ETFs NÃO possuem come-cotas.",
            )
            cdi_percentage = st.number_input(
                "% do CDI (se atrelado)",
                min_value=0.0,
                max_value=300.0,
                step=1.0,
                value=0.0,
                format="%.1f",
                help=(
                    "Preencha APENAS para ativos atrelados ao CDI (CDBs, LCIs, LCAs, Fundos DI). "
                    "Informe o percentual do CDI contratado. Ex.: 105 = 105%% do CDI.\n\n"
                    "Quando preenchido (> 0), o Dashboard calcula a renda teórica usando o **CDI atual "
                    "do Banco Central**, mantendo o rendimento sempre atualizado.\n\n"
                    "Deixe **0** para ativos com taxa fixa (Tesouro IPCA+, prefíxados) ou ativos que "
                    "pagam renda direta já informada no campo 'Renda Mensal'.\n\n"
                    "Exemplos: CDB 105%% CDI → informe 105 | LCI 97%% CDI → informe 97 | "
                    "Fundo DI 100%% CDI → informe 100"
                ),
            )

        submitted = st.form_submit_button("💾 Cadastrar", use_container_width=True)

        if submitted:
            if not name:
                st.error("O nome da classe é obrigatório.")
            else:
                AssetClass.create(
                    name=name,
                    type=asset_type,
                    invested_value=invested_value,
                    current_value=current_value,
                    monthly_income=monthly_income,
                    expected_annual_return=expected_return,
                    admin_fee=admin_fee,
                    tax_type=tax_type,
                    has_come_cotas=has_come_cotas,
                    cdi_percentage=cdi_percentage,
                )
                st.success(f"✅ Classe '{name}' cadastrada com sucesso!")
                st.session_state["navigate_to"] = "📊 Dashboard"
                st.rerun()


def _render_edit_form():
    """Formulário para editar classe de ativo existente."""
    st.markdown("### Editar Classe de Ativo")

    assets = AssetClass.get_all()
    if not assets:
        st.info("Nenhuma classe cadastrada para editar.")
        return

    asset_options = {f"{a.name} ({a.type})": a.id for a in assets}
    selected = st.selectbox(
        "Selecione a classe para editar",
        options=list(asset_options.keys()),
        key="edit_select",
    )

    if selected:
        asset_id = asset_options[selected]
        asset = AssetClass.get_by_id(asset_id)

        if asset:
            with st.form("edit_asset_form"):
                col1, col2 = st.columns(2)

                with col1:
                    name = st.text_input(
                        "Nome",
                        value=asset.name,
                        help="Identificação desta classe de ativo. Use um nome descritivo que facilite a organização, como 'FIIs de Logística', 'Ações Dividendos' ou 'Tesouro IPCA+'. Ex.: 'FIIs Shoppings'.",
                    )
                    asset_type = st.selectbox(
                        "Tipo",
                        options=ASSET_TYPES,
                        index=ASSET_TYPES.index(asset.type)
                        if asset.type in ASSET_TYPES
                        else 0,
                        help="Categoria do ativo que define como ele será agrupado nos relatórios e simulações. Tipos disponíveis: FII (Fundos Imobiliários), Ações, ETF, Renda Fixa e Fundos de Investimento.",
                    )
                    invested_value = st.number_input(
                        "Valor Investido (R$)",
                        value=asset.invested_value,
                        min_value=0.0,
                        step=100.0,
                        format="%.2f",
                        help="Valor total que você investiu nesta classe ao longo do tempo (custo de aquisição). Usado para calcular o retorno (lucro ou prejuízo) da classe. Ex.: se você comprou R$ 50.000 em FIIs, informe 50000.",
                    )
                    current_value = st.number_input(
                        "Valor Atual (R$)",
                        value=asset.current_value,
                        min_value=0.0,
                        step=100.0,
                        format="%.2f",
                        help="Valor de mercado atual desta classe de ativo (quanto ela vale hoje). A diferença entre o valor atual e o valor investido mostra seu ganho ou perda patrimonial. Ex.: se seus FIIs valem R$ 55.000 hoje, informe 55000.",
                    )
                    monthly_income = st.number_input(
                        "Renda Mensal (R$)",
                        value=asset.monthly_income,
                        min_value=0.0,
                        step=10.0,
                        format="%.2f",
                        help="Renda passiva mensal gerada por esta classe (dividendos, rendimentos, juros, aluguéis, etc.). Este valor é usado nas projeções de independência financeira. Ex.: se seus FIIs pagam R$ 400/mês em dividendos, informe 400.",
                    )

                with col2:
                    expected_return = st.number_input(
                        "Retorno Esperado (% a.a.)",
                        value=asset.expected_annual_return,
                        min_value=0.0,
                        max_value=100.0,
                        step=0.5,
                        format="%.2f",
                        help="Rentabilidade anual esperada para esta classe, incluindo valorização + rendimentos. Usado nas projeções do simulador FIRE. Exemplos típicos: FIIs 8-12%%, Ações 10-15%%, Renda Fixa 10-13%%, ETFs 8-12%%.",
                    )
                    admin_fee = st.number_input(
                        "Taxa de Administração (% a.a.)",
                        value=asset.admin_fee,
                        min_value=0.0,
                        max_value=10.0,
                        step=0.1,
                        format="%.2f",
                        help="Taxa cobrada anualmente pelo gestor do fundo/ativo. Reduz o retorno efetivo. Exemplos: FIIs 0,5-1,5%%, Fundos de Ações 1-2%%, ETFs 0,2-0,8%%, Ações individuais 0%%, Tesouro Direto 0,2%%.",
                    )
                    tax_type = st.selectbox(
                        "Tipo de Tributação",
                        options=TAX_TYPES,
                        index=TAX_TYPES.index(asset.tax_type)
                        if asset.tax_type in TAX_TYPES
                        else 0,
                        help="Regime de imposto de renda aplicável: • Regressivo — IR decresce com o tempo, de 22,5%% (até 180 dias) a 15%% (acima de 720 dias), comum em Renda Fixa e CDBs. • Fixo 15%% — alíquota fixa sobre o ganho de capital, comum em Ações e ETFs. • Isento — sem IR sobre rendimentos, como dividendos de FII para pessoa física.",
                    )
                    has_come_cotas = st.checkbox(
                        "Possui Come-Cotas?",
                        value=asset.has_come_cotas,
                        help="Marque se o fundo possui come-cotas: antecipação semestral de IR (maio e novembro) que reduz a quantidade de cotas. Afeta fundos de investimento abertos (Renda Fixa: 15%%, Multimercado: 15%%, Curto Prazo: 20%%). FIIs, Ações e ETFs NÃO possuem come-cotas.",
                    )
                    cdi_percentage = st.number_input(
                        "% do CDI (se atrelado)",
                        value=asset.cdi_percentage,
                        min_value=0.0,
                        max_value=300.0,
                        step=1.0,
                        format="%.1f",
                        help=(
                            "Preencha APENAS para ativos atrelados ao CDI (CDBs, LCIs, LCAs, Fundos DI). "
                            "Informe o percentual do CDI contratado. Ex.: 105 = 105%% do CDI.\n\n"
                            "Quando preenchido (> 0), o Dashboard calcula a renda teórica usando o **CDI atual "
                            "do Banco Central**, mantendo o rendimento sempre atualizado.\n\n"
                            "Deixe **0** para ativos com taxa fixa (Tesouro IPCA+, prefíxados) ou ativos que "
                            "pagam renda direta já informada no campo 'Renda Mensal'.\n\n"
                            "Exemplos: CDB 105%% CDI → informe 105 | LCI 97%% CDI → informe 97 | "
                            "Fundo DI 100%% CDI → informe 100"
                        ),
                    )

                submitted = st.form_submit_button(
                    "💾 Salvar Alterações", use_container_width=True
                )

                if submitted:
                    AssetClass.update(
                        asset_id=asset_id,
                        name=name,
                        type=asset_type,
                        invested_value=invested_value,
                        current_value=current_value,
                        monthly_income=monthly_income,
                        expected_annual_return=expected_return,
                        admin_fee=admin_fee,
                        tax_type=tax_type,
                        has_come_cotas=has_come_cotas,
                        cdi_percentage=cdi_percentage,
                    )
                    st.success(f"✅ Classe '{name}' atualizada!")
                    st.session_state["navigate_to"] = "📊 Dashboard"
                    st.rerun()


def _render_delete_form():
    """Formulário para excluir classe de ativo."""
    st.markdown("### Excluir Classe de Ativo")

    assets = AssetClass.get_all()
    if not assets:
        st.info("Nenhuma classe cadastrada para excluir.")
        return

    asset_options = {f"{a.name} ({a.type}) - {format_currency(a.current_value)}": a.id for a in assets}
    selected = st.selectbox(
        "Selecione a classe para excluir",
        options=list(asset_options.keys()),
        key="delete_select",
    )

    if selected:
        asset_id = asset_options[selected]
        st.warning("⚠️ Esta ação é irreversível!")

        if st.button("🗑️ Confirmar Exclusão", type="primary"):
            AssetClass.delete(asset_id)
            st.success("✅ Classe excluída com sucesso!")
            st.session_state["navigate_to"] = "📊 Dashboard"
            st.rerun()
