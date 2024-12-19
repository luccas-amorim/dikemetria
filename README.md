# juris_intelligence
Repositório do código fonte do projeto JI, Juris Intelligence
---

# Sistema de Inteligência Jurídica para Análise de Processos Judiciais

Este projeto é o núcleo de um sistema de inteligência artificial voltado para a análise de processos judiciais. Ele lê e analisa textos de sentenças judiciais, identifica padrões textuais e argumentativos associados a diferentes tipos de decisões, e oferece insights valiosos para aumentar as chances de sucesso em novas ações.

## Finalidade do Projeto

- **Captura de Texto Jurídico**: Extrai o texto bruto de processos judiciais em formato PDF.
- **Análise de Padrões Textuais**: Identifica vocabulários e estruturas argumentativas comuns em decisões favoráveis.
- **Estatísticas e Visualizações**: Fornece dados sobre a frequência de decisões favoráveis dentro de escopos jurídicos específicos, como causas de inexigibilidade de débito.
- **Inteligência Estratégica**: Oferece sugestões baseadas em estratégias usadas em causas bem-sucedidas, ajudando escritórios de advocacia e empresas a melhorar suas estratégias jurídicas.

## Estrutura do Projeto

- **`text_mining.py`**: Arquivo principal para execução do pipeline completo.
- **`text_extraction.py`**: Responsável pela extração de texto de arquivos PDF contendo processos judiciais.
- **`pre_processing.py`**: Realiza a limpeza e normalização do texto jurídico.
- **`analyses.py`**: Analisa a frequência e relevância de padrões textuais e argumentativos.
- **`analyses_view.py`**: Gera gráficos e visualizações das estratégias mais bem-sucedidas e distribuições de resultados.

## Requisitos

- Python 3.8 ou superior
- Bibliotecas:
  - `PyPDF2`
  - `nltk`
  - `matplotlib`

Para instalar as dependências:
```bash
pip install PyPDF2 nltk matplotlib
```

## Como Usar

1. Coloque o arquivo PDF contendo o processo judicial no diretório `temp/data` com o nome `documento.pdf`.
2. Execute o arquivo principal para processar o texto:
   ```bash
   python text_mining.py
   ```
3. Os resultados incluem:
   - Frequência de decisões favoráveis no escopo jurídico analisado.
   - Visualização das estratégias vocabulares e argumentativas mais frequentes em causas bem-sucedidas.

## Licença

Este código está protegido por uma **licença privada**. Qualquer reprodução, redistribuição ou uso não autorizado é estritamente proibido.

---
