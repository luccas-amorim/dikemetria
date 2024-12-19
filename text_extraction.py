import PyPDF2

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ''
            return text
    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo PDF: {e}")