from text_extraction import extract_text_from_pdf
from pre_processing import clean_text
from analyses import analyze_text
from analyses_view import plot_most_common_words

def main():
    pdf_path = "temp/data/documento.pdf"

    try:
        # Etapa 1: Extrair texto
        raw_text = extract_text_from_pdf(pdf_path)
        print("Texto bruto extraído: ", raw_text[:500])  # Exibe os primeiros 500 caracteres

        # Etapa 2: Limpeza do texto
        cleaned_text = clean_text(raw_text)
        print("\nTexto limpo: ", cleaned_text[:500])

        # Etapa 3: Análise do texto
        word_counts, most_common = analyze_text(cleaned_text)
        print("\nPalavras mais comuns: ", most_common)

        # Etapa 4: Visualização
        plot_most_common_words(most_common)

    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

if __name__ == "__main__":
    main()