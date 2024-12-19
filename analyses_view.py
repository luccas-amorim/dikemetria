import matplotlib.pyplot as plt

def plot_most_common_words(most_common):
    try:
        words, counts = zip(*most_common)
        plt.bar(words, counts)
        plt.xlabel('Palavras')
        plt.ylabel('Frequência')
        plt.title('Palavras mais frequentes')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        raise ValueError(f"Erro ao gerar visualização: {e}")