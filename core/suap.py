"""Login pelo SUAP (OAuth2 — Authorization Code), como no IFKey e no site da ASIFRN.

Fluxo:
1. O botão "Entrar com SUAP" leva a  {SUAP_URL}/o/authorize/?client_id=...&response_type=code&redirect_uri=...
2. A pessoa faz login na própria página do SUAP.
3. O SUAP devolve para  SUAP_REDIRECT_URI?code=...&state=...
4. O AutoPEI troca o code por um token em  {SUAP_URL}/o/token/  (client_id + client_secret).
5. Com o token, lê  /api/rh/eu/  → identificacao (matrícula), nome_usual, email, campus,
   tipo_usuario (ex.: "Servidor (Docente)").

A senha do SUAP nunca passa pelo AutoPEI.
Para usar, cadastre uma aplicação em https://suap.ifrn.edu.br/api/ (Authorization code).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from . import config


class SuapError(Exception):
    pass


@dataclass
class DadosSuap:
    username: str  # matrícula SUAP (identificacao)
    nome: str
    email: str = ""
    campus: str = ""
    tipo: str = ""  # tipo_usuario: "Servidor (Docente)", "Servidor (Técnico-Administrativo)", "Aluno"...
    login: str = ""  # vinculo.login (quando existir)

    @property
    def docente(self) -> bool:
        t = self.tipo.lower()
        return "docente" in t or "professor" in t


def _primeiro(d: dict, *chaves: str) -> str:
    for chave in chaves:
        atual = d
        for parte in chave.split("."):
            atual = atual.get(parte) if isinstance(atual, dict) else None
        if atual:
            return str(atual)
    return ""


def interpretar(d: dict) -> DadosSuap:
    username = _primeiro(d, "identificacao", "matricula", "vinculo.matricula", "username")
    if not username:
        raise SuapError("O SUAP não retornou a matrícula do usuário.")
    return DadosSuap(
        username=username.strip().lower(),
        nome=_primeiro(d, "nome_usual", "nome_social", "nome_registro", "nome") or username,
        email=_primeiro(d, "email", "email_preferencial", "email_academico",
                        "email_google_classroom", "email_secundario"),
        campus=_primeiro(d, "campus", "vinculo.campus"),
        tipo=_primeiro(d, "tipo_usuario", "tipo_vinculo", "vinculo.categoria"),
        login=_primeiro(d, "vinculo.login"),
    )


# ---------------------------------------------------------------------------
# state (proteção contra CSRF), assinado e com validade de 10 minutos
# ---------------------------------------------------------------------------
def _assinar(ts: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), ts.encode(), hashlib.sha256).hexdigest()[:32]


def gerar_state() -> str:
    ts = str(int(time.time()))
    return f"{ts}.{_assinar(ts)}"


def state_valido(state: str) -> bool:
    try:
        ts, assinatura = state.split(".")
        return hmac.compare_digest(assinatura, _assinar(ts)) and time.time() - int(ts) < 600
    except ValueError:
        return False


# ---------------------------------------------------------------------------
def configurado() -> bool:
    return bool(config.SUAP_CLIENT_ID and config.SUAP_CLIENT_SECRET) or config.SUAP_FAKE


def url_autorizacao() -> str:
    params = {
        "client_id": config.SUAP_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": config.SUAP_REDIRECT_URI,
        "state": gerar_state(),
    }
    if config.SUAP_OAUTH_SCOPE:
        params["scope"] = config.SUAP_OAUTH_SCOPE
    return f"{config.SUAP_URL}/o/authorize/?{urlencode(params)}"


def _ler_usuario(token: str) -> DadosSuap:
    ultimo = ""
    for ep in config.SUAP_ME_ENDPOINTS:
        try:
            r = requests.get(config.SUAP_URL + ep, timeout=config.SUAP_TIMEOUT,
                             headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        except requests.RequestException as exc:
            ultimo = str(exc)
            continue
        if r.status_code == 200:
            return interpretar(r.json())
        ultimo = f"{ep}: HTTP {r.status_code}"
    raise SuapError(f"Não foi possível ler seus dados no SUAP ({ultimo}).")


def trocar_codigo(code: str) -> DadosSuap:
    if config.SUAP_FAKE and code.startswith("fake:"):
        # Desenvolvimento: code = "fake:<matricula>:<tipo>:<nome>"
        _, matricula, tipo, nome = (code.split(":", 3) + ["", "", ""])[:4]
        return DadosSuap(username=matricula.lower(), nome=nome or f"Usuário SUAP {matricula}",
                         email=f"{matricula}@ifrn.edu.br", campus="CN", tipo=tipo)
    try:
        r = requests.post(
            f"{config.SUAP_URL}/o/token/",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": config.SUAP_CLIENT_ID,
                "client_secret": config.SUAP_CLIENT_SECRET,
                "redirect_uri": config.SUAP_REDIRECT_URI,
            },
            timeout=config.SUAP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SuapError(f"Não foi possível conectar ao SUAP: {exc}") from exc
    if r.status_code != 200:
        raise SuapError("O SUAP não confirmou o login. Tente entrar novamente.")
    token = r.json().get("access_token")
    if not token:
        raise SuapError("O SUAP não retornou o token de acesso.")
    return _ler_usuario(token)
