from flask import Flask, request, send_file, render_template, send_from_directory, jsonify
import os
import pandas as pd
from pdfminer.high_level import extract_text
import tempfile
import unidecode
from difflib import SequenceMatcher
import time
import decimal
import re
import shutil

app = Flask(__name__)

# Função para verificar se uma palavra-chave está presente no texto do PDF com base nos parâmetros de similaridade
def check_keywords_in_pdf(keywords, pdf_path, ignore_case, ignore_accents, similarity_threshold, fuzzy_match):
    text = extract_text(pdf_path)
    if ignore_case:
        text = text.lower()
    if ignore_accents:
        text = unidecode.unidecode(text)
    
    # Remover pontuações e caracteres especiais do texto
    text = re.sub(r'[^a-zA-Z0-9]', '', text)
    
    matches = {}
    for keyword in keywords:
        keyword_to_check = keyword
        if ignore_case:
            keyword_to_check = keyword_to_check.lower()
        if ignore_accents:
            keyword_to_check = unidecode.unidecode(keyword_to_check)
        
        # Remover pontuações e caracteres especiais da palavra-chave
        keyword_to_check = re.sub(r'[^a-zA-Z0-9]', '', keyword_to_check)
        
        # Verificar se a palavra-chave está presente como substring no texto completo
        if keyword_to_check in text:
            matches[keyword] = True
        else:
            # Verificar similaridade com base no limiar fornecido se fuzzy matching estiver habilitado
            if fuzzy_match:
                similarity_ratio = SequenceMatcher(None, keyword_to_check, text).ratio()
                matches[keyword] = similarity_ratio >= (similarity_threshold / 100.0)
                matches[f"{keyword} (similaridade)"] = f"{decimal.Decimal(similarity_ratio):.4f}"
            else:
                matches[keyword] = False
    return matches

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return "", 204  # Resposta vazia com status 204 (Sem conteúdo)

@app.route('/upload', methods=['POST'])
def upload_files():
    start_time = time.time()
    # Recebendo arquivos PDF e a lista de palavras-chave
    keywords_string = request.form.get('keywords')
    pdf_files = request.files.getlist('pdfs')
    ignore_case = request.form.get('ignore_case') == 'on'
    ignore_accents = request.form.get('ignore_accents') == 'on'
    fuzzy_match = request.form.get('fuzzy_match') == 'on'
    similarity_threshold = float(request.form.get('fuzz_threshold', 80))
    
    if not keywords_string or not pdf_files:
        return jsonify({'error': 'Palavras-chave ou PDFs não fornecidos'}), 400

    # Dividir as palavras-chave pela vírgula e remover espaços em branco
    keywords = [keyword.strip() for keyword in keywords_string.split(',')]

    # Criar DataFrame para armazenar resultados
    results_df = pd.DataFrame(index=keywords)

    # Dicionário para armazenar palavras-chave sem correspondência
    unmatched_keywords = {keyword: [] for keyword in keywords}

    # Processar cada PDF e verificar correspondência com palavras-chave
    for pdf in pdf_files:
        if not pdf.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Por favor, envie apenas arquivos PDF'}), 400

        with tempfile.NamedTemporaryFile(delete=False) as tmp_pdf:
            pdf.save(tmp_pdf.name)
        try:
            matches = check_keywords_in_pdf(keywords, tmp_pdf.name, ignore_case, ignore_accents, similarity_threshold, fuzzy_match)
            results_df[pdf.filename] = pd.Series(matches)

            # Atualizar a lista de palavras-chave sem correspondência
            for keyword, match in matches.items():
                if match is False and "(similaridade)" not in keyword:
                    unmatched_keywords[keyword].append(pdf.filename)
        finally:
            os.unlink(tmp_pdf.name)  # Remover o arquivo temporário

    # Salvar os resultados em um arquivo Excel
    output_path = os.path.join(tempfile.gettempdir(), 'resultado.xlsx')
    results_df.to_excel(output_path)

    # Gerar relatório de palavras-chave sem correspondência
    report_path = os.path.join(tempfile.gettempdir(), 'relatorio_nao_correspondidos.txt')
    with open(report_path, 'w') as report_file:
        for keyword, pdf_list in unmatched_keywords.items():
            if pdf_list:
                report_file.write(f"Palavra-chave: {keyword}\n")
                report_file.write("PDFs sem correspondência:\n")
                for pdf in pdf_list:
                    report_file.write(f"- {pdf}\n")
                report_file.write("\n")

    # Monitorar o tempo de processamento
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Tempo de processamento: {processing_time:.2f} segundos")

    # Criar um arquivo zip contendo o Excel e o relatório de texto
    zip_output_path = os.path.join(tempfile.gettempdir(), 'resultado_relatorio.zip')
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_excel_path = os.path.join(temp_dir, 'resultado.xlsx')
        temp_report_path = os.path.join(temp_dir, 'relatorio_nao_correspondidos.txt')
        shutil.copy(output_path, temp_excel_path)
        shutil.copy(report_path, temp_report_path)
        shutil.make_archive(zip_output_path.replace('.zip', ''), 'zip', temp_dir)

    # Enviar o arquivo zip como anexo
    response = {
        'processing_time': f"{processing_time:.2f}",
        'files': [
            {'filename': 'resultado_relatorio.zip', 'path': f"/download/{os.path.basename(zip_output_path)}"}
        ]
    }
    return jsonify(response)

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(tempfile.gettempdir(), filename, as_attachment=True)

if __name__ == '__main__':
    # Definir a porta e executar o aplicativo Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
