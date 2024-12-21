# Importar bibliotecas necessárias
import re
import logging
from collections import Counter
import docx
import spacy
import matplotlib.pyplot as plt
from google.colab import drive
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

# Baixar recursos NLTK necessários
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# Montar Google Drive
drive.mount('/content/drive')

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Carregar modelo NLP
nlp = spacy.load("pt_core_news_sm")

# Lista adicional de stopwords específicas
additional_stopwords = {
    "fls", "you", "and", "autor", "autora", "requerente", "requerido", "sobre", "the", "acima",
    "abaixo", "sob", "ainda", "bem", "your", "poderá", "relação", "cada", "sendo", "inclusive",
    "quanto", "portanto", "from", "seguintes"
}

# Função para extrair texto de um arquivo DOCX
def extract_text_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo DOCX: {e}")

# Função para extrair número do processo
def extract_case_number(text):
    try:
        case_number_match = re.search(r'(?i)processo\s*n[\u00ba\.:]?\s*\d+', text)
        case_number = case_number_match.group(0).strip() if case_number_match else "Número do processo não encontrado"
        return case_number
    except Exception as e:
        logging.error(f"Erro ao extrair número do processo: {e}")
        return "Número do processo não encontrado"

# Função para limpar texto
def clean_text(text):
    try:
        text = text.lower()
        text = re.sub(r'[^a-záéíóúãõç\s]', '', text)
        try:
            tokens = word_tokenize(text)
        except LookupError:
            tokens = text.split()
        # Filtrar palavras com ruído
        valid_tokens = [word for word in tokens if len(word) > 2 and re.match(r'^[a-záéíóúãõç]+$', word)]
        return ' '.join(valid_tokens)
    except Exception as e:
        logging.error(f"Erro ao limpar o texto: {e}")
        raise ValueError(f"Erro ao limpar o texto: {e}")

# Função para extrair artigos jurídicos citados
def extract_legal_references(text):
    articles = re.findall(r'\b(?:art(?:igo)?\.?\s?\d+[a-z]?)\b(?:\s(?:da|do|de)\s[^\.,;]+)?', text, re.IGNORECASE)
    return {"articles": articles}

# Função para coletar jurisprudências completas
def extract_jurisprudences(text):
    patterns = [r'\b(?:jurisprudência:?\s.*?\b(STJ|TRF|TSE|TST|tribunais).*?[;.!])']
    jurisprudences = []
    for pattern in patterns:
        jurisprudences.extend(re.findall(pattern, text, re.IGNORECASE))
    return jurisprudences

# Função para coletar argumentos jurídicos
def extract_arguments(text):
    doc = nlp(text)
    patterns = ["considerando que", "diante disso", "com base no artigo"]
    arguments = [sent.text for sent in doc.sents if any(pattern in sent.text.lower() for pattern in patterns)]
    return arguments

# Função para análise de texto com remoção de stopwords
def analyze_text(cleaned_text):
    try:
        stop_words = set(stopwords.words('portuguese')).union(additional_stopwords)
        tokens = [word for word in cleaned_text.split() if word not in stop_words]
        word_counts = Counter(tokens)

        # Criar lista de listas com palavras agrupadas por ocorrências
        grouped_words = {}
        for word, count in word_counts.items():
            if count not in grouped_words:
                grouped_words[count] = []
            grouped_words[count].append(word)

        # Quebrar linhas a cada 15 palavras em cada lista interna
        for count in grouped_words:
            grouped_words[count] = [
                grouped_words[count][i:i + 15] for i in range(0, len(grouped_words[count]), 15)
            ]

        # Ordenar as ocorrências
        grouped_words = dict(sorted(grouped_words.items(), key=lambda x: x[0], reverse=True))

        return {"word_counts": word_counts, "grouped_words": grouped_words}
    except Exception as e:
        raise ValueError(f"Erro ao analisar o texto: {e}")

# Função para visualização de palavras mais comuns
def plot_most_common_words(most_common):
    try:
        # Gráfico de barras com as 10 palavras mais comuns
        words, counts = zip(*most_common[:10])
        plt.figure(figsize=(10, 5))
        plt.bar(words, counts)
        plt.xlabel('Palavras')
        plt.ylabel('Frequência')
        plt.title('Top 10 Palavras Mais Frequentes')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

        # Gráfico de pizza com as 30 palavras mais comuns
        words_30, counts_30 = zip(*most_common[:30])
        percentages = [count / sum(counts_30) * 100 for count in counts_30]
        plt.figure(figsize=(10, 10))
        plt.pie(percentages, labels=words_30, autopct='%1.1f%%', startangle=140)
        plt.title('Distribuição Percentual das 30 Palavras Mais Frequentes')
        plt.tight_layout()
        plt.show()

    except Exception as e:
        raise ValueError(f"Erro ao gerar visualização: {e}")

# Função principal
def main():
    docx_path = "/content/drive/My Drive/JI/data/juris_studycase2.docx"  # Atualize o caminho do arquivo
    try:
        # Extração de texto
        raw_text = extract_text_from_docx(docx_path)
        case_number = extract_case_number(raw_text)
        print("Número do processo:", case_number)

        # Limpeza de texto
        cleaned_text = clean_text(raw_text)

        # Análise de texto
        analysis_results = analyze_text(cleaned_text)

        # Exibe palavras agrupadas por ocorrências
        print("\nPalavras agrupadas por número de ocorrências:")
        for count, word_lists in analysis_results["grouped_words"].items():
            print(f"{count} ocorrências:")
            for sublist in word_lists:
                print(sublist)
                print()  # Linha vazia entre sublistas

        print(f"\n\nTotal de palavras no documento: {len(cleaned_text.split())}")

        # Extração de artigos jurídicos
        legal_references = extract_legal_references(cleaned_text)
        print("\nArtigos encontrados:")
        for article in legal_references["articles"]:
            print(article)

        # Extração de jurisprudências
        jurisprudences = extract_jurisprudences(raw_text)
        print("\nJurisprudências encontradas:")
        for jurisprudence in jurisprudences:
            print(jurisprudence)

        # Extração de argumentos jurídicos
        arguments = extract_arguments(cleaned_text)
        print("\nArgumentos jurídicos encontrados:")
        for argument in arguments:
            print(f"- {argument}")

        # Visualização
        plot_most_common_words(analysis_results["word_counts"].most_common(30))
    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

# Execute o código
main()
