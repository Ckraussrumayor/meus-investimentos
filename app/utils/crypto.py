"""
Módulo de criptografia para dados sensíveis (ex.: senha SMTP).

Usa Fernet (AES-128-CBC + HMAC-SHA256) com chave derivada de uma
variável de ambiente via PBKDF2. Se a variável não estiver definida,
gera uma chave automaticamente e a salva em um arquivo local.
"""

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Salt fixo para derivação – pode ser qualquer valor estável
_SALT = b"SimuladorFinanceiro2026"

# Caminho do arquivo de chave local (fallback)
_KEY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".encryption_key"


def _derive_key(passphrase: str) -> bytes:
    """Deriva uma chave Fernet a partir de uma passphrase via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _get_fernet() -> Fernet:
    """Retorna uma instância Fernet com a chave correta.

    Prioridade:
    1. Variável de ambiente ENCRYPTION_KEY
    2. Arquivo local data/.encryption_key (criado automaticamente)
    """
    # Busca em st.secrets (Streamlit Cloud) ou os.environ (.env local)
    try:
        import streamlit as st
        env_key = st.secrets.get("ENCRYPTION_KEY", "") if hasattr(st, "secrets") else ""
    except Exception:
        env_key = ""
    if not env_key:
        env_key = os.environ.get("ENCRYPTION_KEY", "")

    if env_key:
        key = _derive_key(env_key)
    else:
        # Gera/lê chave local automaticamente
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _KEY_FILE.exists():
            key = _KEY_FILE.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            _KEY_FILE.write_bytes(key)
        # Chave já é base64 Fernet-compatível, não precisa derivar

    return Fernet(key)


def encrypt(plain_text: str) -> str:
    """Criptografa uma string e retorna o token como string base64.

    Args:
        plain_text: Texto em claro.

    Returns:
        Token criptografado (string).
    """
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt(encrypted_text: str) -> str:
    """Descriptografa um token Fernet e retorna o texto original.

    Se o token for inválido (ex.: dado salvo antes da criptografia),
    retorna o texto como está (fallback transparente).

    Args:
        encrypted_text: Token criptografado.

    Returns:
        Texto em claro.
    """
    if not encrypted_text:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        # Fallback: o valor pode ser texto plano antigo (pré-criptografia)
        return encrypted_text
