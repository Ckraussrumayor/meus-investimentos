"""
Módulo de login e autenticação.
"""

import random
import string
import time

import bcrypt
import streamlit as st

from app.database.database import (
    execute_query,
    get_user_by_email,
    reset_user_password_by_email,
)
from app.utils.constants import TWO_FACTOR_CODE_LENGTH, TWO_FACTOR_EXPIRY_SECONDS


def verify_password(username: str, password: str) -> dict | None:
    """Verifica as credenciais do usuário.

    Args:
        username: Nome de usuário.
        password: Senha em texto plano.

    Returns:
        Dados do usuário se autenticado, None caso contrário.
    """
    results = execute_query(
        "SELECT id, username, password_hash, email FROM user WHERE username = ?",
        (username,),
        fetch=True,
    )

    if not results:
        return None

    user = results[0]
    stored_hash = user["password_hash"]

    if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
        }

    return None


def render_login_form():
    """Renderiza o formulário de login no Streamlit."""
    st.markdown("## 🔐 Login")
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="Digite seu usuário")
        password = st.text_input(
            "Senha", type="password", placeholder="Digite sua senha"
        )
        submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Preencha todos os campos.")
                return False

            user = verify_password(username, password)
            if user:
                st.session_state["user"] = user
                st.session_state["login_step"] = "2fa"
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
                return False

    # Link para recuperação de senha
    st.markdown("")
    if st.button("🔑 Esqueci minha senha", use_container_width=True):
        st.session_state["login_step"] = "forgot_password"
        st.rerun()

    return False


# ─────────────────── Fluxo: Esqueci Minha Senha ───────────────────


def _send_reset_code(to_email: str, code: str) -> bool:
    """Envia o código de redefinição de senha por e-mail."""
    from app.auth.two_factor import send_2fa_email

    # Reutiliza a infraestrutura de envio já existente (SMTP do banco/env)
    from app.database.database import get_smtp_config
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    cfg = get_smtp_config()
    smtp_email = cfg["smtp_email"]
    smtp_password = cfg["smtp_password"]

    if not smtp_email or not smtp_password:
        st.warning(
            "⚠️ Configuração SMTP não encontrada. "
            "Código exibido na tela para desenvolvimento."
        )
        st.info(f"🔑 Código de redefinição (dev): **{code}**")
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_email
        msg["To"] = to_email
        msg["Subject"] = "Redefinição de Senha - Simulador Financeiro"

        body = f"""
        <html>
        <body>
            <h2>Redefinição de Senha</h2>
            <p>Você solicitou a redefinição da sua senha.</p>
            <p>Seu código de verificação é:</p>
            <h1 style="color: #FF5722; letter-spacing: 8px;">{code}</h1>
            <p>Este código expira em 5 minutos.</p>
            <p><small>Se você não solicitou esta redefinição, ignore este e-mail.</small></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=10)
        if cfg.get("use_tls", True):
            server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


def render_forgot_password_form():
    """Renderiza o formulário para solicitar redefinição de senha."""
    st.markdown("## 🔑 Esqueci Minha Senha")
    st.markdown("---")
    st.info(
        "Digite o **e-mail** cadastrado na sua conta. "
        "Enviaremos um código para redefinir a senha."
    )

    with st.form("forgot_pw_form"):
        email = st.text_input(
            "E-mail cadastrado", placeholder="seu_email@exemplo.com"
        )
        submitted = st.form_submit_button(
            "📧 Enviar Código", use_container_width=True
        )

        if submitted:
            if not email or "@" not in email:
                st.error("Informe um e-mail válido.")
            else:
                user = get_user_by_email(email)
                if not user:
                    st.error("Nenhuma conta encontrada com esse e-mail.")
                else:
                    code = "".join(
                        random.choices(string.digits, k=TWO_FACTOR_CODE_LENGTH)
                    )
                    st.session_state["reset_code"] = code
                    st.session_state["reset_code_expiry"] = (
                        time.time() + TWO_FACTOR_EXPIRY_SECONDS
                    )
                    st.session_state["reset_email"] = email
                    ok = _send_reset_code(email, code)
                    if ok:
                        st.session_state["login_step"] = "reset_password"
                        st.rerun()

    st.markdown("")
    if st.button("⬅️ Voltar ao Login", use_container_width=True):
        st.session_state["login_step"] = "login"
        st.rerun()


def render_reset_password_form():
    """Renderiza o formulário para digitar o código e definir nova senha."""
    st.markdown("## 🔑 Redefinir Senha")
    st.markdown("---")

    email = st.session_state.get("reset_email", "")
    if email and "@" in email:
        masked = email[:3] + "***" + email[email.index("@"):]
        st.info(f"📧 Código enviado para **{masked}**")

    with st.form("reset_pw_form"):
        code_input = st.text_input(
            "Código de Verificação",
            max_chars=TWO_FACTOR_CODE_LENGTH,
            placeholder="Digite o código de 6 dígitos",
        )
        new_pw = st.text_input(
            "Nova Senha",
            type="password",
            placeholder="Digite a nova senha (mín. 6 caracteres)",
        )
        confirm_pw = st.text_input(
            "Confirmar Nova Senha",
            type="password",
            placeholder="Repita a nova senha",
        )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button(
                "✅ Redefinir Senha", use_container_width=True
            )
        with col2:
            resend = st.form_submit_button(
                "📧 Reenviar Código", use_container_width=True
            )

        if submitted:
            stored_code = st.session_state.get("reset_code", "")
            expiry = st.session_state.get("reset_code_expiry", 0)

            if time.time() > expiry:
                st.error("⏰ Código expirado. Clique em 'Reenviar Código'.")
            elif code_input != stored_code:
                st.error("❌ Código incorreto.")
            elif not new_pw or len(new_pw) < 6:
                st.error("A nova senha deve ter pelo menos 6 caracteres.")
            elif new_pw != confirm_pw:
                st.error("As senhas não conferem.")
            else:
                new_hash = bcrypt.hashpw(
                    new_pw.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")
                ok = reset_user_password_by_email(email, new_hash)
                if ok:
                    # Limpar dados de reset
                    for k in [
                        "reset_code",
                        "reset_code_expiry",
                        "reset_email",
                    ]:
                        st.session_state.pop(k, None)
                    st.session_state["login_step"] = "login"
                    st.success(
                        "✅ Senha redefinida com sucesso! Faça login com a nova senha."
                    )
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Erro ao redefinir. Verifique o e-mail e tente novamente.")

        if resend:
            code = "".join(
                random.choices(string.digits, k=TWO_FACTOR_CODE_LENGTH)
            )
            st.session_state["reset_code"] = code
            st.session_state["reset_code_expiry"] = (
                time.time() + TWO_FACTOR_EXPIRY_SECONDS
            )
            _send_reset_code(email, code)
            st.success("✅ Novo código enviado!")
            st.rerun()

    st.markdown("")
    if st.button("⬅️ Voltar ao Login", use_container_width=True):
        for k in ["reset_code", "reset_code_expiry", "reset_email"]:
            st.session_state.pop(k, None)
        st.session_state["login_step"] = "login"
        st.rerun()


def is_authenticated() -> bool:
    """Verifica se o usuário está autenticado."""
    return st.session_state.get("authenticated", False)


def logout():
    """Realiza o logout do usuário."""
    keys_to_clear = [
        "user", "authenticated", "login_step",
        "2fa_code", "2fa_expiry",
        "reset_code", "reset_code_expiry", "reset_email",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    st.rerun()
