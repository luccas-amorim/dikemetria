import re
from collections import Counter

def analyze_text(cleaned_text):
    try:
    # Analisa o texto processado.

    # Args:
    #     cleaned_text (str): Texto limpo.

    # Returns:
    #     dict: Resultados da análise incluindo palavras, termos jurídicos, artigos e argumentos.
        from collections import Counter

        word_counts = Counter(cleaned_text.split())
        most_common = word_counts.most_common(10)
        legal_references = extract_legal_references(cleaned_text)
        legal_terms = extract_legal_terms(cleaned_text)
        arguments = extract_arguments(cleaned_text)

        return {
            "word_counts": word_counts,
            "most_common": most_common,
            "legal_references": legal_references,
            "legal_terms": legal_terms,
            "arguments": arguments
        }

    except Exception as e:
        raise ValueError(f"Erro ao analisar o texto: {e}")


def extract_legal_references(text):
    """
    Extrai referências a códigos e artigos do Direito brasileiro no texto.

    Args:
        text (str): Texto limpo do processo.

    Returns:
        dict: Dicionário com listas de artigos e códigos encontrados.
    """
    articles = re.findall(r'(?i)(art(?:igo)?\\.?\\s?\\d+[a-z]?)(?:\\s(?:da|do|de)\\s[^\\.,;]+)?', text)
    codes = re.findall(r'(?i)(c[óo]digo\\s(?:[a-z]+\\s)?(?:civil|penal|do\\sconsumidor|de\\strânsito|eleitoral))', text)
    return {
        "articles": articles,
        "codes": codes
    }


LEGAL_TERMS = {
    "inexigibilidade", "nulidade", "prescrição", "jurisprudência",
    "boa-fé", "ônus da prova", "reparação de danos"
}

def extract_legal_terms(text):
    """
    Identifica termos jurídicos relevantes no texto.

    Args:
        text (str): Texto limpo do processo.

    Returns:
        dict: Contagem de termos jurídicos encontrados.
    """
    words = text.split()
    term_counts = {term: words.count(term) for term in LEGAL_TERMS if term in words}
    return term_counts

import spacy

nlp = spacy.load("pt_core_news_sm")

def extract_arguments(text):
    """
    Identifica argumentos no texto com base em padrões linguísticos.

    Args:
        text (str): Texto limpo do processo.

    Returns:
        list: Lista de sentenças que aparentam conter argumentos jurídicos.
    """
    doc = nlp(text)
    patterns = ["considerando que", "diante disso", "com base no artigo"]
    arguments = [sent.text for sent in doc.sents if any(pattern in sent.text.lower() for pattern in patterns)]
    return arguments
