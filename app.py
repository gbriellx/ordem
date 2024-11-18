import gspread
import requests
import time
import random
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
import os
import re

# Carregar variáveis de ambiente
load_dotenv()

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# Função para formatar números de telefone sem o '+'
def format_phone_number(number):
    if not number:
        return None
    number = re.sub(r'\D', '', str(number))

    if len(number) == 11:
        return f'55{number}'

    if number.startswith('55') and len(number) == 13:
        return number

    while number.startswith('55') and len(number) > 13:
        number = number[2:]

    if not number.startswith('55'):
        return f'55{number}'

    return number

# Função para formatar todos os números na planilha
def format_sheet_numbers(sheet):
    try:
        data = sheet.get_all_records()
        for i, row in enumerate(data, start=2):
            number = row.get('Numero')
            if number:
                formatted_number = format_phone_number(number)
                if formatted_number and formatted_number != number:
                    sheet.update_cell(i, 2, formatted_number)
                    log_message(f'Número formatado para {formatted_number} na linha {i}')
    except Exception as e:
        log_message(f"Erro ao formatar números: {str(e)}")

# Configuração da autenticação do Google Sheets
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_file = os.getenv('CREDENTIALS_FILE')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    if not creds_file or not sheet_id:
        raise ValueError("Credenciais ou ID da planilha não foram configurados corretamente nas variáveis de ambiente.")

    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)

    main_sheet = client.open_by_key(sheet_id)
    sheet_automacao = main_sheet.worksheet("Automação")
    sheet_ativo = main_sheet.worksheet("Ativo")

except Exception as e:
    log_message(f"Erro na configuração do Google Sheets: {str(e)}")
    raise SystemExit(e)

url = os.getenv('API_URL')
api_key = os.getenv('API_KEY')
if not url or not api_key:
    log_message("URL da API ou chave de API não configuradas. Verifique suas variáveis de ambiente.")
    raise SystemExit("Configuração inválida.")

headers = {
    "apikey": api_key,
    "Content-Type": "application/json"
}

# Formatar números na planilha "Automação"
format_sheet_numbers(sheet_automacao)
format_sheet_numbers(sheet_ativo)

# Função para enviar mensagens com texto personalizado
def send_messages(sheet, custom_text):
    try:
        data = sheet.get_all_records()
        for i, row in enumerate(data, start=2):
            number = row.get('Numero')
            status = row.get('Status')
            name = row.get('Nome')

            if status == 'Pendente':
                formatted_number = format_phone_number(number)
                if not formatted_number:
                    log_message(f"Formato inválido para o número {number}. Não foi possível corrigir.")
                    continue

                if formatted_number != number:
                    sheet.update_cell(i, 2, formatted_number)
                    log_message(f"Corrigido e formatado o número para {formatted_number} na linha {i}")

                text = custom_text.format(name=name)
                payload = {"number": formatted_number, "text": text}

                try:
                    response = requests.post(url, json=payload, headers=headers)
                    response.raise_for_status()

                    log_message(f'Mensagem enviada para {formatted_number}: {response.text}')
                    sheet.update_cell(i, 3, 'Concluído')
                    log_message(f'Status atualizado para "Concluído" para {formatted_number}')

                    wait_time = random.randint(180, 420)
                    log_message(f'Aguardando {wait_time // 60} minutos...')
                    time.sleep(wait_time)

                except requests.RequestException as e:
                    log_message(f'Erro ao enviar mensagem para {formatted_number}: {str(e)}')
                    sheet.update_cell(i, 3, 'Erro')
                    log_message(f'Status atualizado para "Erro" para {formatted_number}')

            else:
                log_message(f'Pulando número {number} - Status: {status}')

    except gspread.exceptions.APIError as e:
        log_message(f"Erro na API do Google Sheets: {str(e)}")
        time.sleep(60)
    except Exception as e:
        log_message(f"Erro ao processar planilha: {str(e)}")
        time.sleep(60)

# Mensagem personalizada para "Automação"
mensagem_automacao = "Olá {name}, tudo bem? Percebemos que você preencheu nosso formulário para agendar sua sessão estratégica gratuita. Está tudo certo para finalizarmos o agendamento e começarmos a transformar sua estratégia de vendas?"

# Mensagem personalizada para "Ativo"
mensagem_ativo = "Olá {name}, estamos animados em saber que você já está ativo conosco! Gostaríamos de compartilhar algumas atualizações para potencializar ainda mais sua experiência."

# Loop de envio para as duas planilhas
while True:
    send_messages(sheet_automacao, mensagem_automacao)
    send_messages(sheet_ativo, mensagem_ativo)
    time.sleep(60)
