"""Configurações do AutoPEI, lidas de variáveis de ambiente (ou do arquivo .env)."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv é opcional
    pass


def _bool(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _lista(nome: str, padrao: str = "") -> list[str]:
    return [p.strip() for p in os.getenv(nome, padrao).split(",") if p.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://autopei:autopei@localhost:5432/autopei"
)

# --- SUAP (OAuth2 — o mesmo fluxo do "Entrar com SUAP" de outros sistemas do IFRN) ----
# 1. O botão leva a {SUAP_URL}/o/authorize/ ; 2. o SUAP volta para SUAP_REDIRECT_URI com
# ?code=... ; 3. o AutoPEI troca o code por um token em /o/token/ ; 4. lê os dados da pessoa
# em SUAP_ME_ENDPOINTS (matrícula, nome, e-mail, campus e tipo de usuário).
SUAP_URL = os.getenv("SUAP_URL", "https://suap.ifrn.edu.br").rstrip("/")
SUAP_CLIENT_ID = os.getenv("SUAP_CLIENT_ID", "")
SUAP_CLIENT_SECRET = os.getenv("SUAP_CLIENT_SECRET", "")
SUAP_REDIRECT_URI = os.getenv("SUAP_REDIRECT_URI", "http://localhost:8501/")
SUAP_OAUTH_SCOPE = os.getenv("SUAP_OAUTH_SCOPE", "")  # vazio = escopos padrão da aplicação
SUAP_ME_ENDPOINTS = _lista("SUAP_ME_ENDPOINTS", "/api/rh/eu/,/api/eu/")
SUAP_TIMEOUT = int(os.getenv("SUAP_TIMEOUT", "15"))
# SOMENTE PARA DESENVOLVIMENTO: simula o retorno do SUAP sem sair do AutoPEI.
SUAP_FAKE = _bool("AUTOPEI_SUAP_FAKE", False)
# Chave para assinar o parâmetro "state" do OAuth.
SECRET_KEY = os.getenv("AUTOPEI_SECRET_KEY", "") or (SUAP_CLIENT_SECRET + DATABASE_URL)

# --- Anexos -------------------------------------------------------------------
ANEXO_MAX_MB = int(os.getenv("AUTOPEI_ANEXO_MAX_MB", "10"))

# Matrículas SUAP que viram administradoras automaticamente ao entrar.
ADMINS_SUAP = {m.lower() for m in _lista("AUTOPEI_ADMINS_SUAP")}

# --- Administrador local inicial ---------------------------------------------
ADMIN_USERNAME = os.getenv("AUTOPEI_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("AUTOPEI_ADMIN_PASSWORD", "")
ADMIN_NOME = os.getenv("AUTOPEI_ADMIN_NOME", "Administrador(a) AutoPEI")

INSTITUICAO = os.getenv(
    "AUTOPEI_INSTITUICAO",
    "INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DO RIO GRANDE DO NORTE",
)
CAMPUS_INICIAL = os.getenv("AUTOPEI_CAMPUS_INICIAL", "Currais Novos")
CAMPUS_INICIAL_SIGLA = os.getenv("AUTOPEI_CAMPUS_INICIAL_SIGLA", "CN")
