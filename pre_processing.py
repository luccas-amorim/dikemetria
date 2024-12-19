import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import nltk

# Baixar os dados do NLTK (somente na primeira execução)
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

def clean_text(text):
    try:
        # Converter para minúsculas
        text = text.lower()
        # Remover caracteres especiais
        text = re.sub(r'[^a-z\s]', '', text)
        # Tokenizar
        tokens = word_tokenize(text)
        # Remover stopwords
        stop_words = set(stopwords.words('portuguese'))
        tokens = [word for word in tokens if word not in stop_words]
        # Lematizar (normalizar palavras)
        lemmatizer = WordNetLemmatizer()
        tokens = [lemmatizer.lemmatize(word) for word in tokens]
        return ' '.join(tokens)
    except Exception as e:
        raise ValueError(f"Erro ao limpar o texto: {e}")