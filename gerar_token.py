import requests
import json

# ==============================================================================
# Suas informações já preenchidas
# ==============================================================================
SEU_APP_ID = "7315198634179578"
SUA_CLIENT_SECRET = "7dsFIWIMYPOQWN9Mw2H1X2TKusltZzNL"
# Esta URL deve ser exatamente a mesma que você configurou no painel do Meli
SUA_REDIRECT_URL = "https://oauth.pstmn.io/v1/callback" 
CODE_QUE_VOCE_PEGOU = "TG-68814fdf9d40cc000174b30e-2312240624"
# ==============================================================================


url = "https://api.mercadolibre.com/oauth/token"

headers = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded"
}

data = {
    "grant_type": "authorization_code",
    "client_id": SEU_APP_ID,
    "client_secret": SUA_CLIENT_SECRET,
    "code": CODE_QUE_VOCE_PEGOU,
    "redirect_uri": SUA_REDIRECT_URL
}

try:
    print("Trocando o código pelo Access Token...")
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status() # Lança erro se a requisição falhar

    token_data = response.json()

    print("\n✅ SUCESSO! Token gerado.\n")
    print("--- Guarde estas informações em local seguro ---")
    print(f"ACCESS_TOKEN: {token_data['access_token']}")
    print(f"Expira em (segundos): {token_data['expires_in']}")
    print(f"REFRESH_TOKEN: {token_data['refresh_token']}") # Guarde isso para renovar o token no futuro!
    print("---------------------------------------------")

except requests.exceptions.HTTPError as err:
    print(f"\n❌ ERRO NA REQUISIÇÃO: {err.response.status_code}")
    print(f"   Detalhe do erro: {err.response.json()}")