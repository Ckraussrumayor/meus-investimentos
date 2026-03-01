"""
Módulo de conexão e inicialização do banco de dados SQLite.
"""

import sqlite3
import os
from pathlib import Path


def _get_secret(key: str, default: str = "") -> str:
    """Busca valor em st.secrets (Streamlit Cloud) ou os.environ (.env local)."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def get_db_path() -> str:
    """Retorna o caminho do banco de dados SQLite."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_path = base_dir / "data" / "investimentos.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados SQLite."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Inicializa o banco de dados executando o schema SQL."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    conn = get_connection()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()

        # Migrations: adicionar colunas que podem não existir em bancos antigos
        _run_migrations(conn)
    finally:
        conn.close()


def _run_migrations(conn):
    """Executa migrações incrementais para manter o banco atualizado."""
    # Verificar se a coluna extra_contribution_target existe
    cursor = conn.execute("PRAGMA table_info(scenario_parameters)")
    columns = [row[1] for row in cursor.fetchall()]

    if "extra_contribution_target" not in columns:
        conn.execute(
            "ALTER TABLE scenario_parameters "
            "ADD COLUMN extra_contribution_target TEXT NOT NULL DEFAULT 'proporcional'"
        )
        conn.commit()

    # Verificar se a coluna cdi_percentage existe em asset_classes
    cursor = conn.execute("PRAGMA table_info(asset_classes)")
    asset_columns = [row[1] for row in cursor.fetchall()]

    if "cdi_percentage" not in asset_columns:
        conn.execute(
            "ALTER TABLE asset_classes "
            "ADD COLUMN cdi_percentage REAL NOT NULL DEFAULT 0"
        )
        conn.commit()


def execute_query(query: str, params: tuple = (), fetch: bool = False):
    """Executa uma query no banco de dados.

    Args:
        query: SQL a ser executado.
        params: Parâmetros para a query.
        fetch: Se True, retorna os resultados (fetchall).

    Returns:
        Lista de resultados se fetch=True, senão o lastrowid.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            results = cursor.fetchall()
            return results
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def execute_many(query: str, params_list: list):
    """Executa uma query com múltiplos conjuntos de parâmetros."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
    finally:
        conn.close()


def init_default_user():
    """Cria o usuário padrão a partir das variáveis de ambiente ou st.secrets, se não existir."""
    import bcrypt

    username = _get_secret("APP_USERNAME", "admin").strip()
    password = _get_secret("APP_PASSWORD", "admin123")
    email = _get_secret("APP_EMAIL", "admin@example.com").strip()
    password_hash_env = _get_secret("APP_PASSWORD_HASH", "")

    existing = execute_query(
        "SELECT id, password_hash, email FROM user WHERE username = ?",
        (username,),
        fetch=True,
    )
    if existing:
        user = existing[0]
        updates = []
        params = []

        if password_hash_env:
            if user["password_hash"] != password_hash_env:
                updates.append("password_hash = ?")
                params.append(password_hash_env)
        else:
            try:
                password_ok = bcrypt.checkpw(
                    password.encode("utf-8"),
                    user["password_hash"].encode("utf-8"),
                )
            except Exception:
                password_ok = False

            if not password_ok:
                new_hash = bcrypt.hashpw(
                    password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")
                updates.append("password_hash = ?")
                params.append(new_hash)

        if email and email != (user["email"] or ""):
            updates.append("email = ?")
            params.append(email)

        if updates:
            params.append(user["id"])
            execute_query(
                f"UPDATE user SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
        return

    if password_hash_env:
        pw_hash = password_hash_env
    else:
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

    execute_query(
        "INSERT INTO user (username, password_hash, email) VALUES (?, ?, ?)",
        (username, pw_hash, email),
    )


def get_smtp_config() -> dict:
    """Retorna a configuração SMTP salva no banco de dados.

    A senha SMTP é descriptografada automaticamente.

    Returns:
        Dicionário com as configurações SMTP ou valores padrão.
    """
    from app.utils.crypto import decrypt

    results = execute_query(
        "SELECT smtp_server, smtp_port, smtp_email, smtp_password, use_tls "
        "FROM smtp_config WHERE id = 1",
        fetch=True,
    )
    if results:
        row = results[0]
        return {
            "smtp_server": row["smtp_server"],
            "smtp_port": row["smtp_port"],
            "smtp_email": row["smtp_email"],
            "smtp_password": decrypt(row["smtp_password"]),
            "use_tls": bool(row["use_tls"]),
        }

    # Fallback: variáveis de ambiente ou st.secrets
    return {
        "smtp_server": _get_secret("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(_get_secret("SMTP_PORT", "587")),
        "smtp_email": _get_secret("SMTP_EMAIL", ""),
        "smtp_password": _get_secret("SMTP_PASSWORD", ""),
        "use_tls": True,
    }


def save_smtp_config(smtp_server: str, smtp_port: int, smtp_email: str,
                      smtp_password: str, use_tls: bool = True):
    """Salva a configuração SMTP no banco de dados (upsert).

    A senha SMTP é criptografada antes de ser salva.

    Args:
        smtp_server: Endereço do servidor SMTP.
        smtp_port: Porta do servidor SMTP.
        smtp_email: E-mail remetente (login SMTP).
        smtp_password: Senha do e-mail / senha de app.
        use_tls: Se deve usar TLS (STARTTLS).
    """
    from app.utils.crypto import encrypt

    encrypted_password = encrypt(smtp_password)

    existing = execute_query(
        "SELECT id FROM smtp_config WHERE id = 1", fetch=True
    )
    if existing:
        execute_query(
            "UPDATE smtp_config SET smtp_server = ?, smtp_port = ?, "
            "smtp_email = ?, smtp_password = ?, use_tls = ? WHERE id = 1",
            (smtp_server, smtp_port, smtp_email, encrypted_password, int(use_tls)),
        )
    else:
        execute_query(
            "INSERT INTO smtp_config (id, smtp_server, smtp_port, smtp_email, "
            "smtp_password, use_tls) VALUES (1, ?, ?, ?, ?, ?)",
            (smtp_server, smtp_port, smtp_email, encrypted_password, int(use_tls)),
        )


def update_user_email(user_id: int, new_email: str):
    """Atualiza o e-mail de um usuário.

    Args:
        user_id: ID do usuário.
        new_email: Novo endereço de e-mail.
    """
    execute_query(
        "UPDATE user SET email = ? WHERE id = ?",
        (new_email, user_id),
    )


def update_username(user_id: int, new_username: str) -> bool:
    """Atualiza o nome de usuário.

    Args:
        user_id: ID do usuário.
        new_username: Novo nome de usuário.

    Returns:
        True se atualizado, False se o username já existe.
    """
    existing = execute_query(
        "SELECT id FROM user WHERE username = ? AND id != ?",
        (new_username, user_id),
        fetch=True,
    )
    if existing:
        return False
    execute_query(
        "UPDATE user SET username = ? WHERE id = ?",
        (new_username, user_id),
    )
    return True


def update_user_password(user_id: int, new_password_hash: str):
    """Atualiza o hash da senha de um usuário.

    Args:
        user_id: ID do usuário.
        new_password_hash: Novo hash bcrypt da senha.
    """
    execute_query(
        "UPDATE user SET password_hash = ? WHERE id = ?",
        (new_password_hash, user_id),
    )


def get_user_by_email(email: str) -> dict | None:
    """Busca um usuário pelo e-mail.

    Args:
        email: E-mail a buscar.

    Returns:
        Dicionário com id, username e email ou None.
    """
    results = execute_query(
        "SELECT id, username, email FROM user WHERE email = ?",
        (email,),
        fetch=True,
    )
    if not results:
        return None
    row = results[0]
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


def get_app_settings() -> dict:
    """Retorna as configurações gerais do aplicativo."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
        if row:
            return dict(row)
        # Inserir valores padrão se não existir
        conn.execute(
            "INSERT OR IGNORE INTO app_settings (id, ir_renda_fixa) VALUES (1, 17.5)"
        )
        conn.commit()
        return {"id": 1, "ir_renda_fixa": 17.5}
    finally:
        conn.close()


def save_app_settings(ir_renda_fixa: float):
    """Salva as configurações gerais do aplicativo."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO app_settings (id, ir_renda_fixa) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET ir_renda_fixa = excluded.ir_renda_fixa",
            (ir_renda_fixa,),
        )
        conn.commit()
    finally:
        conn.close()


def reset_user_password_by_email(email: str, new_password_hash: str) -> bool:
    """Redefine a senha de um usuário pelo e-mail.

    Args:
        email: E-mail do usuário.
        new_password_hash: Novo hash bcrypt.

    Returns:
        True se o usuário foi encontrado e atualizado.
    """
    user = get_user_by_email(email)
    if not user:
        return False
    execute_query(
        "UPDATE user SET password_hash = ? WHERE id = ?",
        (new_password_hash, user["id"]),
    )
    return True
