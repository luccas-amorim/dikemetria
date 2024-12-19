# import re
# from nltk.corpus import stopwords
# from nltk.tokenize import word_tokenize
# from nltk.stem import WordNetLemmatizer
# import nltk
# import logging
# import os

# # Configuração de logging para monitorar o fluxo de execução
# logging.basicConfig(level=logging.INFO)

# # Definir um diretório customizado para os dados do NLTK
# nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
# nltk.data.path.append(nltk_data_dir)

# # Função para garantir que os recursos do NLTK estão disponíveis
# def ensure_nltk_resource(resource_name):
#     try:
#         nltk.data.find(resource_name)
#     except LookupError:
#         logging.warning(f"Recurso {resource_name} não encontrado. Baixando...")
#         nltk.download(resource_name, download_dir=nltk_data_dir, quiet=True)

# # Garantir recursos necessários
# ensure_nltk_resource('punkt')
# ensure_nltk_resource('stopwords')
# ensure_nltk_resource('wordnet')

# def clean_text(text):
#     """
#     Limpa e processa o texto fornecido, incluindo:
#     - Conversão para letras minúsculas
#     - Remoção de caracteres especiais
#     - Tokenização
#     - Remoção de stopwords
#     - Lematização

#     Args:
#         text (str): Texto bruto a ser processado.

#     Returns:
#         str: Texto limpo e processado.

#     Raises:
#         ValueError: Em caso de erro no processamento.
#     """
#     logging.info("Iniciando limpeza do texto...")
#     try:
#         # Converter para minúsculas
#         text = text.lower()
#         logging.info("Texto convertido para minúsculas.")

#         # Remover caracteres especiais
#         text = re.sub(r'[^a-z\s]', '', text)
#         logging.info("Caracteres especiais removidos.")

#         # Tokenizar
#         tokens = word_tokenize(text)
#         logging.info("Texto tokenizado com sucesso.")

#         # Remover stopwords
#         stop_words = set(stopwords.words('portuguese'))
#         tokens = [word for word in tokens if word not in stop_words]
#         logging.info("Stopwords removidas.")

#         # Lematizar (normalizar palavras)
#         lemmatizer = WordNetLemmatizer()
#         try:
#             tokens = [lemmatizer.lemmatize(word) for word in tokens]
#             logging.info("Lematização concluída.")
#         except Exception as lemmatization_error:
#             logging.warning(f"Erro durante a lematização: {lemmatization_error}")

#         return ' '.join(tokens)
#     except Exception as e:
#         logging.error(f"Erro ao limpar o texto: {e}")
#         raise ValueError(f"Erro ao limpar o texto: {e}")

import re
import logging

# Configuração de logging para monitorar o fluxo de execução
logging.basicConfig(level=logging.INFO)

# Lista de stopwords básica em português
STOPWORDS = {
    "a", "as", "o", "os", "um", "uns", "uma", "umas", "e", "ou", "mas", "porque", "por", "com",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "para", "por", "se", "que",
    "como", "foi", "p", "é", "ao", "entre", "mais", "são", "também", "s", "figura", "são", "paulo"
}

def clean_text(text):
    """
    Limpa e processa o texto fornecido, incluindo:
    - Conversão para letras minúsculas
    - Remoção de caracteres especiais
    - Tokenização simples
    - Remoção de stopwords

    Args:
        text (str): Texto bruto a ser processado.

    Returns:
        str: Texto limpo e processado.

    Raises:
        ValueError: Em caso de erro no processamento.
    """
    logging.info("Iniciando limpeza do texto...")
    try:
        # Converter para minúsculas
        text = text.lower()
        logging.info("Texto convertido para minúsculas.")

        # Remover caracteres especiais
        text = re.sub(r'[^a-záéíóúãõç\s]', '', text)
        logging.info("Caracteres especiais removidos.")

        # Tokenizar (dividir em palavras)
        tokens = text.split()
        logging.info("Texto tokenizado com sucesso.")

        # Remover stopwords
        tokens = [word for word in tokens if word not in STOPWORDS]
        logging.info("Stopwords removidas.")

        # Retornar texto limpo
        return ' '.join(tokens)
    except Exception as e:
        logging.error(f"Erro ao limpar o texto: {e}")
        raise ValueError(f"Erro ao limpar o texto: {e}")
