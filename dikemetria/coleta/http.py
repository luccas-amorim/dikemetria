"""Cliente HTTP educado: identifica o projeto, respeita intervalo mínimo e tenta de novo."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

from dikemetria import __version__

log = logging.getLogger(__name__)

USER_AGENT = (
    f"Dikemetria/{__version__} (pesquisa jurimetrica aberta; "
    "+https://github.com/luccas-amorim/dikemetria)"
)


@dataclass(frozen=True)
class Proveniencia:
    """De onde veio um dado: permite auditar e reproduzir a coleta."""

    url: str
    metodo: str
    parametros: str  # JSON da consulta ou da query string
    coletado_em: str  # ISO 8601, UTC
    sha256: str  # hash do corpo da resposta

    def como_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)


class ErroColeta(RuntimeError):
    pass


class Cliente:
    def __init__(
        self,
        intervalo: float = 1.0,
        tentativas: int = 5,
        tempo_limite: float = 60.0,
        cabecalhos: dict[str, str] | None = None,
        sessao: requests.Session | None = None,
    ) -> None:
        self.intervalo = intervalo
        self.tentativas = tentativas
        self.tempo_limite = tempo_limite
        self.sessao = sessao or requests.Session()
        self.sessao.headers.update({"User-Agent": USER_AGENT, **(cabecalhos or {})})
        self._ultima = 0.0

    def _aguardar(self) -> None:
        espera = self.intervalo - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        self._ultima = time.monotonic()

    def requisitar(
        self, metodo: str, url: str, *, params: dict | None = None, json_corpo: dict | None = None
    ) -> tuple[dict, Proveniencia]:
        """Faz a requisição, devolve o JSON e a proveniência. Tenta de novo em 429 e 5xx."""
        ultimo_erro: Exception | None = None
        for tentativa in range(self.tentativas):
            self._aguardar()
            try:
                resposta = self.sessao.request(
                    metodo, url, params=params, json=json_corpo, timeout=self.tempo_limite
                )
            except requests.RequestException as erro:
                ultimo_erro = erro
            else:
                if resposta.status_code == 200:
                    proveniencia = Proveniencia(
                        url=url,
                        metodo=metodo,
                        parametros=json.dumps(json_corpo or params or {}, ensure_ascii=False),
                        coletado_em=datetime.now(UTC).isoformat(timespec="seconds"),
                        sha256=hashlib.sha256(resposta.content).hexdigest(),
                    )
                    return resposta.json(), proveniencia
                if resposta.status_code not in (429, 500, 502, 503, 504):
                    raise ErroColeta(
                        f"{metodo} {url} -> HTTP {resposta.status_code}: {resposta.text[:300]}"
                    )
                ultimo_erro = ErroColeta(f"HTTP {resposta.status_code}")
            pausa = min(60, 2 ** (tentativa + 1))
            log.warning("Falha em %s (%s); nova tentativa em %ss", url, ultimo_erro, pausa)
            time.sleep(pausa)
        raise ErroColeta(f"{metodo} {url} falhou após {self.tentativas} tentativas: {ultimo_erro}")
