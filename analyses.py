from collections import Counter

def analyze_text(cleaned_text):
    try:
        # Contar a frequência das palavras
        word_counts = Counter(cleaned_text.split())
        # Identificar palavras mais comuns
        most_common = word_counts.most_common(10)
        return word_counts, most_common
    except Exception as e:
        raise ValueError(f"Erro ao analisar o texto: {e}")