"""Extração de texto de decisões em PDF, DOCX ou texto puro."""

from __future__ import annotations

from pathlib import Path


class ErroExtracao(RuntimeError):
    """O arquivo não pôde ser lido ou não contém texto extraível."""


def extrair_texto(caminho: str | Path) -> str:
    """Devolve o texto de um arquivo .pdf, .docx, .txt ou .html."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroExtracao(f"Arquivo não encontrado: {caminho}")

    sufixo = caminho.suffix.lower()
    if sufixo == ".pdf":
        texto = _extrair_pdf(caminho)
    elif sufixo == ".docx":
        texto = _extrair_docx(caminho)
    elif sufixo in {".txt", ".md"}:
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    elif sufixo in {".html", ".htm"}:
        from dikemetria.limpeza import html_para_texto

        texto = html_para_texto(caminho.read_text(encoding="utf-8", errors="replace"))
    else:
        raise ErroExtracao(f"Formato não suportado: {sufixo}")

    if not texto.strip():
        raise ErroExtracao(
            f"Nenhum texto extraído de {caminho.name}. "
            "Se o PDF for digitalizado (imagem), é preciso OCR antes."
        )
    return texto


def _extrair_pdf(caminho: Path) -> str:
    from pypdf import PdfReader

    try:
        leitor = PdfReader(caminho)
        # Quebra de página ("\f") entre linhas próprias: preserva os limites das páginas, que
        # `autos.py` usa para separar as peças, sem colar a última linha de uma página na próxima.
        return "\n\f\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
    except Exception as erro:  # pypdf lança vários tipos de erro para PDFs corrompidos
        raise ErroExtracao(f"Erro ao ler o PDF {caminho.name}: {erro}") from erro


def _extrair_docx(caminho: Path) -> str:
    import docx

    try:
        documento = docx.Document(str(caminho))
    except Exception as erro:
        raise ErroExtracao(f"Erro ao ler o DOCX {caminho.name}: {erro}") from erro
    return "\n".join(paragrafo.text for paragrafo in documento.paragraphs)
