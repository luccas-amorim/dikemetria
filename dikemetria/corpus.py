"""Banco local (SQLite) do corpus: processos do DataJud, documentos pseudonimizados e progresso.

O banco nunca guarda texto com dados pessoais: só a versão pseudonimizada e o hash do original.
Também não guarda nome de órgão julgador, para não permitir perfis de magistrados (regra 5).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from dikemetria.coleta.datajud import Processo
from dikemetria.coleta.djen import Documento
from dikemetria.coleta.http import Proveniencia

ESQUEMA = """
CREATE TABLE IF NOT EXISTS processos (
    tribunal TEXT NOT NULL,
    numero TEXT NOT NULL,
    grau TEXT NOT NULL DEFAULT '',
    classe_codigo INTEGER,
    classe_nome TEXT,
    assuntos TEXT,            -- JSON [{codigo, nome}]
    municipio_ibge INTEGER,
    data_ajuizamento TEXT,
    data_julgamento TEXT,
    duracao_dias INTEGER,
    resultado TEXT NOT NULL,
    evidencia TEXT,
    sensivel INTEGER NOT NULL DEFAULT 0,
    proveniencia TEXT,        -- JSON
    municipio_codigo TEXT,    -- código como veio do tribunal
    municipio_metodo TEXT,    -- ibge, tabela, nome do órgão, não resolvido
    orgao_codigo INTEGER,     -- unidade judiciária: só controle estatístico, nunca publicada
    PRIMARY KEY (tribunal, numero, grau)
);
CREATE TABLE IF NOT EXISTS documentos (
    id TEXT PRIMARY KEY,
    fonte TEXT NOT NULL,
    tribunal TEXT,
    numero TEXT,
    tipo TEXT,
    data TEXT,
    classe_nome TEXT,
    texto TEXT NOT NULL,      -- pseudonimizado
    sha256_original TEXT NOT NULL,
    resultado TEXT NOT NULL,
    evidencia TEXT,
    sensivel INTEGER NOT NULL DEFAULT 0,
    substituicoes TEXT,       -- JSON {tipo: quantidade}
    url TEXT,
    proveniencia TEXT,
    avaliacao TEXT            -- JSON: capítulos, motivo, confiança e cálculo (avaliacao.py)
);
CREATE INDEX IF NOT EXISTS documentos_numero ON documentos (numero);
CREATE TABLE IF NOT EXISTS progresso (
    fonte TEXT NOT NULL,
    recorte TEXT NOT NULL,
    tribunal TEXT NOT NULL,
    cursor TEXT,
    concluido INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT,
    PRIMARY KEY (fonte, recorte, tribunal)
);
"""


_COLUNAS_NOVAS_PROCESSOS = (
    ("municipio_codigo", "TEXT"),
    ("municipio_metodo", "TEXT"),
    ("orgao_codigo", "INTEGER"),
)
_COLUNAS_PROCESSOS = (
    "tribunal, numero, grau, classe_codigo, classe_nome, assuntos, municipio_ibge, "
    "data_ajuizamento, data_julgamento, duracao_dias, resultado, evidencia, sensivel, "
    "proveniencia, municipio_codigo, municipio_metodo, orgao_codigo"
)

_COLUNAS_DOCUMENTOS = (
    "id, fonte, tribunal, numero, tipo, data, classe_nome, texto, sha256_original, resultado, "
    "evidencia, sensivel, substituicoes, url, proveniencia, avaliacao"
)


class Corpus:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.conexao = sqlite3.connect(self.caminho)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.executescript(ESQUEMA)
        self._migrar()

    def _migrar(self) -> None:
        """Acrescenta colunas criadas depois da primeira versão do banco."""
        colunas = {linha[1] for linha in self.conexao.execute("PRAGMA table_info(documentos)")}
        if "avaliacao" not in colunas:
            with self.conexao:
                self.conexao.execute("ALTER TABLE documentos ADD COLUMN avaliacao TEXT")
        colunas = {linha[1] for linha in self.conexao.execute("PRAGMA table_info(processos)")}
        with self.conexao:
            for coluna, tipo in _COLUNAS_NOVAS_PROCESSOS:
                if coluna not in colunas:
                    self.conexao.execute(f"ALTER TABLE processos ADD COLUMN {coluna} {tipo}")

    def fechar(self) -> None:
        self.conexao.close()

    def __enter__(self) -> Corpus:
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    # Gravação -------------------------------------------------------------------------------

    def gravar_processos(
        self, processos: Iterable[Processo], proveniencia: Proveniencia | None = None
    ) -> int:
        linhas = [
            (
                p.tribunal,
                p.numero,
                p.grau or "",
                p.classe_codigo,
                p.classe_nome,
                json.dumps(p.assuntos, ensure_ascii=False),
                p.municipio_ibge,
                p.data_ajuizamento,
                p.data_julgamento,
                p.duracao_dias,
                p.resultado,
                p.evidencia,
                int(p.sensivel),
                proveniencia.como_json() if proveniencia else None,
                p.municipio_codigo,
                p.municipio_metodo,
                p.orgao_codigo,
            )
            for p in processos
        ]
        with self.conexao:
            self.conexao.executemany(
                f"INSERT OR REPLACE INTO processos ({_COLUNAS_PROCESSOS}) "
                f"VALUES ({','.join('?' * 17)})",
                linhas,
            )
        return len(linhas)

    def gravar_documentos(
        self, documentos: Iterable[Documento], proveniencia: Proveniencia | None = None
    ) -> int:
        linhas = [
            (
                d.id,
                d.fonte,
                d.tribunal,
                d.numero,
                d.tipo,
                d.data,
                d.classe_nome,
                d.texto,
                d.sha256_original,
                d.resultado,
                d.evidencia,
                int(d.sensivel),
                json.dumps(d.substituicoes),
                d.url,
                proveniencia.como_json() if proveniencia else None,
                json.dumps(d.avaliacao, ensure_ascii=False),
            )
            for d in documentos
        ]
        with self.conexao:
            self.conexao.executemany(
                f"INSERT OR REPLACE INTO documentos ({_COLUNAS_DOCUMENTOS}) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                linhas,
            )
        return len(linhas)

    def atualizar_avaliacao_documento(
        self, id_: str, resultado: str, evidencia: str, avaliacao: dict
    ) -> None:
        with self.conexao:
            self.conexao.execute(
                "UPDATE documentos SET resultado = ?, evidencia = ?, avaliacao = ? WHERE id = ?",
                (resultado, evidencia, json.dumps(avaliacao, ensure_ascii=False), id_),
            )

    # Progresso ------------------------------------------------------------------------------

    def cursor(self, fonte: str, recorte: str, tribunal: str) -> tuple[object, bool]:
        linha = self.conexao.execute(
            "SELECT cursor, concluido FROM progresso WHERE fonte=? AND recorte=? AND tribunal=?",
            (fonte, recorte, tribunal),
        ).fetchone()
        if not linha:
            return None, False
        return (json.loads(linha["cursor"]) if linha["cursor"] else None), bool(linha["concluido"])

    def salvar_cursor(
        self, fonte: str, recorte: str, tribunal: str, cursor: object, concluido: bool = False
    ) -> None:
        with self.conexao:
            self.conexao.execute(
                "INSERT OR REPLACE INTO progresso VALUES (?,?,?,?,?,?)",
                (
                    fonte,
                    recorte,
                    tribunal,
                    json.dumps(cursor, default=str),
                    int(concluido),
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )

    # Leitura --------------------------------------------------------------------------------

    def processos(self, incluir_sensiveis: bool = False) -> Iterator[dict]:
        sql = "SELECT * FROM processos" + ("" if incluir_sensiveis else " WHERE sensivel = 0")
        with closing(self.conexao.execute(sql)) as cursor:
            for linha in cursor:
                registro = dict(linha)
                registro["assuntos"] = json.loads(registro["assuntos"] or "[]")
                yield registro

    def documentos(self, incluir_sensiveis: bool = False) -> Iterator[dict]:
        sql = "SELECT * FROM documentos" + ("" if incluir_sensiveis else " WHERE sensivel = 0")
        with closing(self.conexao.execute(sql)) as cursor:
            for linha in cursor:
                registro = dict(linha)
                registro["avaliacao"] = json.loads(registro.get("avaliacao") or "{}")
                yield registro

    def resumo(self) -> dict:
        consulta = self.conexao.execute
        return {
            "processos": consulta("SELECT COUNT(*) FROM processos").fetchone()[0],
            "documentos": consulta("SELECT COUNT(*) FROM documentos").fetchone()[0],
            "tribunais": consulta(
                "SELECT COUNT(DISTINCT tribunal) FROM ("
                "SELECT tribunal FROM processos UNION SELECT tribunal FROM documentos)"
            ).fetchone()[0],
            "sensiveis": consulta(
                "SELECT (SELECT COUNT(*) FROM processos WHERE sensivel=1) + "
                "(SELECT COUNT(*) FROM documentos WHERE sensivel=1)"
            ).fetchone()[0],
        }
