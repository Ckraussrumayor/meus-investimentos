"""
Página de Configurações – Conta, Segurança e SMTP.
"""

import smtplib
from email.mime.text import MIMEText

import bcrypt
import streamlit as st

from app.database.database import (
    execute_query,
    get_smtp_config,
    save_smtp_config,
    update_user_email,
    update_username,
    update_user_password,
    get_app_settings,
    save_app_settings,
)


def _test_smtp_connection(cfg: dict) -> tuple[bool, str]:
    """Testa a conexão SMTP com as configurações fornecidas.

    Returns:
        (sucesso, mensagem)
    """
    try:
        server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=10)
        if cfg["use_tls"]:
            server.starttls()
        server.login(cfg["smtp_email"], cfg["smtp_password"])
        server.quit()
        return True, "Conexão SMTP bem-sucedida!"
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Falha de autenticação. Verifique e-mail e senha. "
            "Se usar Gmail, é necessário uma **Senha de App** "
            "(https://myaccount.google.com/apppasswords)."
        )
    except smtplib.SMTPConnectError as e:
        return False, f"Não foi possível conectar ao servidor: {e}"
    except Exception as e:
        return False, f"Erro: {e}"


def _send_test_email(cfg: dict, to_email: str) -> tuple[bool, str]:
    """Envia um e-mail de teste usando as configurações SMTP."""
    try:
        msg = MIMEText(
            "<h2>✅ Teste de configuração</h2>"
            "<p>Se você recebeu este e-mail, a configuração SMTP está correta!</p>",
            "html",
        )
        msg["From"] = cfg["smtp_email"]
        msg["To"] = to_email
        msg["Subject"] = "Teste SMTP – Simulador Financeiro"

        server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=10)
        if cfg["use_tls"]:
            server.starttls()
        server.login(cfg["smtp_email"], cfg["smtp_password"])
        server.sendmail(cfg["smtp_email"], to_email, msg.as_string())
        server.quit()
        return True, "E-mail de teste enviado com sucesso!"
    except Exception as e:
        return False, f"Falha ao enviar e-mail de teste: {e}"


def render():
    """Renderiza a página de configurações."""
    st.markdown("## ⚙️ Configurações")
    st.markdown("---")

    user = st.session_state.get("user", {})

    # ───────────────────── Seção 1: Dados da Conta ─────────────────────
    st.markdown("### 👤 Dados da Conta")

    current_email = user.get("email", "")
    current_username = user.get("username", "")

    with st.form("account_form"):
        new_username = st.text_input(
            "Nome de Usuário",
            value=current_username,
            placeholder="Digite o novo nome de usuário",
        )
        new_email = st.text_input(
            "E-mail da conta (para receber o código 2FA)",
            value=current_email,
            placeholder="seu_email@exemplo.com",
        )
        save_account = st.form_submit_button(
            "💾 Salvar Dados da Conta", use_container_width=True
        )

        if save_account:
            changes = []
            errors = []

            # Validar e atualizar username
            if new_username != current_username:
                if not new_username or len(new_username) < 3:
                    errors.append("O nome de usuário deve ter pelo menos 3 caracteres.")
                else:
                    ok = update_username(user["id"], new_username)
                    if ok:
                        st.session_state["user"]["username"] = new_username
                        changes.append(f"Usuário alterado para **{new_username}**")
                    else:
                        errors.append(
                            f"O nome de usuário **{new_username}** já está em uso."
                        )

            # Validar e atualizar email
            if new_email != current_email:
                if not new_email or "@" not in new_email:
                    errors.append("Informe um e-mail válido.")
                else:
                    update_user_email(user["id"], new_email)
                    st.session_state["user"]["email"] = new_email
                    changes.append(f"E-mail atualizado para **{new_email}**")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            if changes:
                st.success("✅ " + " | ".join(changes))
            elif not errors:
                st.info("Nenhuma alteração detectada.")

    st.markdown("---")

    # ───────────────────── Seção 2: Alterar Senha ─────────────────────
    st.markdown("### 🔑 Alterar Senha")

    with st.form("password_form"):
        current_pw = st.text_input(
            "Senha Atual", type="password", placeholder="Digite sua senha atual"
        )
        new_pw = st.text_input(
            "Nova Senha", type="password", placeholder="Digite a nova senha"
        )
        confirm_pw = st.text_input(
            "Confirmar Nova Senha",
            type="password",
            placeholder="Repita a nova senha",
        )
        change_pw = st.form_submit_button(
            "🔒 Alterar Senha", use_container_width=True
        )

        if change_pw:
            if not current_pw or not new_pw or not confirm_pw:
                st.error("Preencha todos os campos de senha.")
            elif len(new_pw) < 6:
                st.error("A nova senha deve ter pelo menos 6 caracteres.")
            elif new_pw != confirm_pw:
                st.error("A nova senha e a confirmação não conferem.")
            else:
                # Verificar senha atual
                from app.auth.login import verify_password

                check = verify_password(user["username"], current_pw)
                if not check:
                    st.error("❌ Senha atual incorreta.")
                else:
                    new_hash = bcrypt.hashpw(
                        new_pw.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8")
                    update_user_password(user["id"], new_hash)
                    st.success("✅ Senha alterada com sucesso!")

    st.markdown("---")

    # ───────────────────── Seção 2: Configuração SMTP ─────────────────────
    st.markdown("### 📧 Configuração SMTP (envio de e-mails)")
    st.caption(
        "Configure aqui os dados do servidor de e-mail que será usado para "
        "enviar o código de verificação 2FA. Se usar Gmail, crie uma "
        "[Senha de App](https://myaccount.google.com/apppasswords)."
    )

    cfg = get_smtp_config()

    with st.form("smtp_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            smtp_server = st.text_input(
                "Servidor SMTP", value=cfg["smtp_server"],
                placeholder="smtp.gmail.com",
            )
        with col2:
            smtp_port = st.number_input(
                "Porta", value=cfg["smtp_port"], min_value=1, max_value=65535,
                step=1,
            )

        smtp_email = st.text_input(
            "E-mail remetente (login SMTP)",
            value=cfg["smtp_email"],
            placeholder="seu_email@gmail.com",
        )
        smtp_password = st.text_input(
            "Senha / Senha de App",
            value=cfg["smtp_password"],
            type="password",
            placeholder="Senha de App do Gmail ou senha do e-mail",
        )
        use_tls = st.checkbox("Usar TLS (STARTTLS)", value=cfg["use_tls"])

        col_save, col_test, col_send = st.columns(3)
        with col_save:
            save_smtp = st.form_submit_button(
                "💾 Salvar SMTP", use_container_width=True
            )
        with col_test:
            test_conn = st.form_submit_button(
                "🔌 Testar Conexão", use_container_width=True
            )
        with col_send:
            send_test = st.form_submit_button(
                "📨 Enviar E-mail Teste", use_container_width=True
            )

    # Processar ações do formulário SMTP
    new_cfg = {
        "smtp_server": smtp_server,
        "smtp_port": int(smtp_port),
        "smtp_email": smtp_email,
        "smtp_password": smtp_password,
        "use_tls": use_tls,
    }

    if save_smtp:
        if not smtp_email or not smtp_password:
            st.error("Preencha pelo menos o e-mail e a senha SMTP.")
        else:
            save_smtp_config(**new_cfg)
            st.success("✅ Configuração SMTP salva com sucesso!")

    if test_conn:
        if not smtp_email or not smtp_password:
            st.error("Preencha o e-mail e a senha antes de testar.")
        else:
            with st.spinner("Testando conexão SMTP..."):
                ok, msg = _test_smtp_connection(new_cfg)
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    if send_test:
        dest = st.session_state.get("user", {}).get("email", "")
        if not dest or "@" not in dest:
            st.error(
                "Configure primeiro o e-mail da sua conta (seção acima) "
                "para receber o e-mail de teste."
            )
        elif not smtp_email or not smtp_password:
            st.error("Preencha o e-mail e a senha SMTP antes de enviar.")
        else:
            with st.spinner(f"Enviando e-mail de teste para {dest}..."):
                ok, msg = _send_test_email(new_cfg, dest)
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    # ───────────── Seção: Parâmetros Fiscais ─────────────
    st.markdown("---")
    st.markdown("### 💰 Parâmetros Fiscais")
    st.caption(
        "Configure as alíquotas de imposto utilizadas nos cálculos do Dashboard. "
        "Esses valores podem mudar com novas regras do governo."
    )

    app_settings = get_app_settings()
    current_ir = app_settings.get("ir_renda_fixa", 17.5)

    with st.form("fiscal_settings_form"):
        ir_renda_fixa = st.number_input(
            "Alíquota IR sobre Renda Fixa / Fundos (%)",
            min_value=0.0,
            max_value=50.0,
            value=current_ir,
            step=0.5,
            format="%.1f",
            help=(
                "Imposto de Renda incidente sobre os rendimentos no resgate. "
                "Em 2025, a regra mudou para alíquota única de **17,5%** "
                "(sem mais tabela regressiva por prazo). "
                "Altere aqui caso o governo mude novamente."
            ),
        )
        save_fiscal = st.form_submit_button("💾 Salvar Parâmetros Fiscais", use_container_width=True)

        if save_fiscal:
            save_app_settings(ir_renda_fixa=ir_renda_fixa)
            st.success(f"✅ Alíquota IR atualizada para {ir_renda_fixa:.1f}%")

    # ───────────────────── Dicas ─────────────────────
    st.markdown("---")
    with st.expander("💡 Como configurar o Gmail para envio de e-mails"):
        st.markdown(
            """
1. Acesse [myaccount.google.com](https://myaccount.google.com)
2. Vá em **Segurança** → **Verificação em duas etapas** (ative se necessário)
3. Depois vá em **Senhas de app** ([link direto](https://myaccount.google.com/apppasswords))
4. Crie uma senha de app com nome "Simulador Financeiro"
5. Use essa senha no campo **Senha / Senha de App** acima
6. **Servidor:** `smtp.gmail.com` | **Porta:** `587` | **TLS:** ativado

> ⚠️ **Não use sua senha normal do Gmail.** Use apenas a Senha de App gerada.
            """
        )

    with st.expander("💡 Outros provedores de e-mail"):
        st.markdown(
            """
| Provedor | Servidor SMTP | Porta |
|----------|--------------|-------|
| Gmail | smtp.gmail.com | 587 |
| Outlook/Hotmail | smtp-mail.outlook.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |
| Zoho | smtp.zoho.com | 587 |
            """
        )
