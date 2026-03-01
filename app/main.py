"""
Simulador de Independência Financeira Avançado
================================================
Aplicação web para planejamento financeiro pessoal com:
- Controle consolidado por classe de ativo
- Simulações FIRE (Financial Independence, Retire Early)
- Projeção patrimonial com aportes, reinvestimentos e retiradas
- Simulação tributária realista
- Comparação com benchmarks de mercado
- Versionamento de cenários
- Autenticação segura com 2FA por e-mail
- Exportação em PDF e Excel
"""

import os
import sys

# Adicionar o diretório raiz ao path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Carregar variáveis de ambiente do arquivo .env
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

import streamlit as st

from app.database.database import init_db, init_default_user
from app.auth.login import (
    render_login_form,
    render_forgot_password_form,
    render_reset_password_form,
    is_authenticated,
    logout,
)
from app.auth.two_factor import render_2fa_form
from app.pages import dashboard, cadastro, simulador, cenarios, historico, relatorios, configuracoes


# Configuração da página
st.set_page_config(
    page_title="Simulador de Independência Financeira",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_app():
    """Inicializa o banco de dados e configurações."""
    if "db_initialized" not in st.session_state:
        init_db()
        init_default_user()
        st.session_state["db_initialized"] = True


def render_sidebar():
    """Renderiza a barra lateral com navegação."""
    with st.sidebar:
        st.markdown("## 📊 Simulador Financeiro")
        st.markdown("---")

        user = st.session_state.get("user", {})
        st.markdown(f"👤 **{user.get('username', 'Usuário')}**")
        st.markdown("---")

        # Se houve navegação programática (ex: salvar no Cadastro → Dashboard)
        nav_options = [
            "📊 Dashboard",
            "📝 Cadastro",
            "🎯 Simulador FIRE",
            "📂 Cenários",
            "📅 Histórico",
            "📄 Relatórios",
            "⚙️ Configurações",
        ]
        nav_to = st.session_state.pop("navigate_to", None)
        default_index = nav_options.index(nav_to) if nav_to in nav_options else 0

        page = st.radio(
            "Navegação",
            options=nav_options,
            index=default_index,
            label_visibility="collapsed",
        )

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            logout()

        st.markdown("---")
        st.caption("v1.0.0 | Simulador de Independência Financeira")

    return page


def main():
    """Função principal da aplicação."""
    init_app()

    # Fluxo de autenticação
    if not is_authenticated():
        login_step = st.session_state.get("login_step", "login")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if login_step == "login":
                st.markdown("")
                st.markdown("# 📊 Simulador de Independência Financeira")
                st.markdown("")
                render_login_form()
            elif login_step == "2fa":
                st.markdown("")
                st.markdown("# 📊 Simulador de Independência Financeira")
                st.markdown("")
                render_2fa_form()
            elif login_step == "forgot_password":
                st.markdown("")
                st.markdown("# 📊 Simulador de Independência Financeira")
                st.markdown("")
                render_forgot_password_form()
            elif login_step == "reset_password":
                st.markdown("")
                st.markdown("# 📊 Simulador de Independência Financeira")
                st.markdown("")
                render_reset_password_form()
        return

    # Aplicação autenticada
    page = render_sidebar()

    if page == "📊 Dashboard":
        dashboard.render()
    elif page == "📝 Cadastro":
        cadastro.render()
    elif page == "🎯 Simulador FIRE":
        simulador.render()
    elif page == "📂 Cenários":
        cenarios.render()
    elif page == "📅 Histórico":
        historico.render()
    elif page == "📄 Relatórios":
        relatorios.render()
    elif page == "⚙️ Configurações":
        configuracoes.render()


if __name__ == "__main__":
    main()
