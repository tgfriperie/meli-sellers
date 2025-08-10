# Arquivo: meli_auth.py

import pandas as pd
import requests
import json
import time
import os

STATIC_CREDS_FILE = 'client.csv'
DYNAMIC_TOKEN_FILE = 'token_storage.json'

def _load_static_creds():
    """Função interna para carregar as credenciais estáticas do client.csv."""
    if not os.path.exists(STATIC_CREDS_FILE):
        raise FileNotFoundError(f"Arquivo de configuração principal '{STATIC_CREDS_FILE}' não encontrado.")
    df = pd.read_csv(STATIC_CREDS_FILE)
    if df.empty:
        raise ValueError(f"O arquivo '{STATIC_CREDS_FILE}' está vazio.")
    return df.iloc[0].to_dict()

def _load_dynamic_tokens():
    """Função interna para carregar os tokens dinâmicos (access e refresh)."""
    if not os.path.exists(DYNAMIC_TOKEN_FILE):
        return {}
    try:
        with open(DYNAMIC_TOKEN_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def _save_dynamic_tokens(tokens):
    """Função interna para salvar os tokens dinâmicos."""
    with open(DYNAMIC_TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=4)

def refresh_access_token():
    """Usa as credenciais para obter e salvar um novo access_token."""
    print("-> Iniciando processo de atualização de token...")
    try:
        static_creds = _load_static_creds()
        dynamic_tokens = _load_dynamic_tokens()
        refresh_token_to_use = dynamic_tokens.get('refresh_token', static_creds.get('refresh_token'))
        if not refresh_token_to_use:
            raise ValueError("Refresh token não encontrado nem no cache nem no client.csv")

    except (FileNotFoundError, ValueError) as e:
        print(f"!! ERRO CRÍTICO ao carregar credenciais: {e}")
        return None

    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        'grant_type': 'refresh_token',
        'client_id': static_creds['app_id'],
        'client_secret': static_creds['client_secret'],
        'refresh_token': refresh_token_to_use
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        new_tokens = response.json()
        _save_dynamic_tokens(new_tokens)
        print("-> Token atualizado e salvo com sucesso em 'token_storage.json'!")
        return new_tokens.get('access_token')
    except Exception as e:
        print(f"!! ERRO INESPERADO ao atualizar token: {e}")
        return None

def get_valid_token():
    """
    Obtém um token válido. Esta é a única função que deve ser chamada de fora.
    """
    dynamic_tokens = _load_dynamic_tokens()
    access_token = dynamic_tokens.get('access_token')

    if not access_token:
        print("Nenhum token em cache. Gerando um novo...")
        return refresh_access_token()

    headers = {'Authorization': f"Bearer {access_token}"}
    test_url = "https://api.mercadolibre.com/users/me"
    try:
        response = requests.get(test_url, headers=headers, timeout=5)
        if response.status_code == 200:
            print("-> Access token em cache é válido.")
            return access_token
        else:
            print(f"-> Teste do token falhou (Status {response.status_code}). Acionando refresh.")
            return refresh_access_token()
    except requests.exceptions.RequestException:
        print("-> Teste de conexão do token falhou. Acionando refresh.")
        return refresh_access_token()