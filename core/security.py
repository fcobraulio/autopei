"""Hash de senhas (PBKDF2-SHA256, biblioteca padrão do Python)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_ITERACOES = 390_000


def hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, _ITERACOES)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERACOES, base64.b64encode(sal).decode(), base64.b64encode(dk).decode()
    )


def verificar_senha(senha: str, armazenado: str | None) -> bool:
    if not armazenado:
        return False
    try:
        algoritmo, iteracoes, sal, dk = armazenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac(
            "sha256", senha.encode(), base64.b64decode(sal), int(iteracoes)
        )
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


def senha_forte(senha: str) -> str | None:
    """Retorna uma mensagem de erro, ou None se a senha for aceitável."""
    if len(senha) < 8:
        return "A senha precisa ter pelo menos 8 caracteres."
    if senha.isdigit() or senha.isalpha():
        return "Use letras e números na senha."
    return None
