"""
Módulo de autenticação de dois fatores (2FA) por e-mail.
"""

import os
import random
import smtplib
import string
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import streamlit as st

from app.utils.constants import TWO_FACTOR_CODE_LENGTH, TWO_FACTOR_EXPIRY_SECONDS


def generate_2fa_code() -> str:
    """Gera um código 2FA numérico."""
    return "".join(random.choices(string.digits, k=TWO_FACTOR_CODE_LENGTH))


def send_2fa_email(to_email: str, code: str) -> bool:
    """Envia o código 2FA por e-mail via SMTP.

    Busca as credenciais SMTP primeiro do banco de dados e, se não
    encontradas, das variáveis de ambiente.

    Args:
        to_email: E-mail do destinatário.
        code: Código 2FA a ser enviado.

    Returns:
        True se o e-mail foi enviado com sucesso.
    """
    from app.database.database import get_smtp_config

    cfg = get_smtp_config()

    smtp_email = cfg["smtp_email"]
    smtp_password = cfg["smtp_password"]
    smtp_server = cfg["smtp_server"]
    smtp_port = cfg["smtp_port"]
    use_tls = cfg.get("use_tls", True)

    if not smtp_email or not smtp_password:
        st.warning(
            "⚠️ Configuração SMTP não encontrada. "
            "Acesse **Configurações** após o login para configurar o envio de e-mails. "
            "Código 2FA exibido na tela para desenvolvimento."
        )
        st.info(f"🔑 Código 2FA (dev): **{code}**")
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_email
        msg["To"] = to_email
        msg["Subject"] = "Código de Verificação - Simulador Financeiro"

        body = f"""
        <html>
        <body>
            <h2>Código de Verificação</h2>
            <p>Seu código de acesso é:</p>
            <h1 style="color: #2196F3; letter-spacing: 8px;">{code}</h1>
            <p>Este código expira em 5 minutos.</p>
            <p><small>Se você não solicitou este código, ignore este e-mail.</small></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        if use_tls:
            server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())
        server.quit()

        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {str(e)}")
        return False


def initiate_2fa():
    """Inicia o processo de 2FA gerando e enviando o código."""
    user = st.session_state.get("user")
    if not user:
        return

    code = generate_2fa_code()
    st.session_state["2fa_code"] = code
    st.session_state["2fa_expiry"] = time.time() + TWO_FACTOR_EXPIRY_SECONDS

    send_2fa_email(user["email"], code)


def render_2fa_form():
    """Renderiza o formulário de verificação 2FA."""
    st.markdown("## 🔐 Verificação em Duas Etapas")
    st.markdown("---")

    user = st.session_state.get("user", {})
    email = user.get("email", "")
    masked_email = email[:3] + "***" + email[email.index("@"):] if "@" in email else email

    st.info(f"📧 Um código foi enviado para **{masked_email}**")

    # Enviar código se ainda não foi enviado
    if "2fa_code" not in st.session_state:
        initiate_2fa()

    with st.form("2fa_form"):
        code_input = st.text_input(
            "Código de Verificação",
            max_chars=TWO_FACTOR_CODE_LENGTH,
            placeholder="Digite o código de 6 dígitos",
        )
        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("Verificar", use_container_width=True)
        with col2:
            resend = st.form_submit_button(
                "Reenviar Código", use_container_width=True
            )

        if submitted:
            stored_code = st.session_state.get("2fa_code", "")
            expiry = st.session_state.get("2fa_expiry", 0)

            if time.time() > expiry:
                st.error("⏰ Código expirado. Clique em 'Reenviar Código'.")
            elif code_input == stored_code:
                st.session_state["authenticated"] = True
                st.session_state["login_step"] = "done"
                # Limpar dados sensíveis
                st.session_state.pop("2fa_code", None)
                st.session_state.pop("2fa_expiry", None)
                st.rerun()
            else:
                st.error("❌ Código incorreto. Tente novamente.")

        if resend:
            initiate_2fa()
            st.success("✅ Novo código enviado!")
            st.rerun()
