# Arquivo: meli_enricher.py

import requests
from meli_auth import refresh_access_token # Importa a função de refresh

def get_seller_data(seller_id, access_token):
    """Busca os dados de um vendedor, com lógica de retentativa e retorno do novo token."""
    url = f"https://api.mercadolibre.com/users/{seller_id}"
    headers = {'Authorization': f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers)
        
        # Se o token expirou, tenta atualizar e refazer a chamada
        if response.status_code in [401, 403]:
            print(f"Token inválido para ID {seller_id}. Tentando atualizar...")
            new_access_token = refresh_access_token()
            if new_access_token:
                # ATUALIZAÇÃO IMPORTANTE: usa o novo token para a chamada e o retorna
                access_token = new_access_token
                headers['Authorization'] = f"Bearer {access_token}"
                print("-> Refazendo a chamada com o novo token...")
                response = requests.get(url, headers=headers)
            else:
                 return {'error': 'AuthError', 'message': 'Falha ao atualizar o token'}, access_token

        if response.status_code == 200:
            return response.json(), access_token
        else:
            return {'error': response.status_code, 'message': response.text}, access_token
            
    except requests.exceptions.RequestException as e:
        return {'error': 'ConnectionError', 'message': str(e)}, access_token

def extract_relevant_data(data):
    # (Esta função continua exatamente igual à versão anterior)
    if "error" in data:
        return {"nickname": f"ERRO {data.get('error')}", "city": "N/A", "state": "N/A", "power_seller_status": "N/A"}

    address = data.get("address", {})
    reputation = data.get("seller_reputation", {})
    
    return {
        "nickname": data.get("nickname", "N/A"),
        "city": address.get("city", "N/A"),
        "state": address.get("state", "N/A"),
        "power_seller_status": reputation.get("power_seller_status", "N/A")
    }