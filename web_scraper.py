import logging
import re
import tempfile
from typing import Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuração do Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constantes ---
PADRAO_CNPJ = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
SELETOR_BLOCOS_RESULTADO = 'div.tF2Cxc, div.g, div.MjjYud'
SITES_ALVO = (
    "site:econodata.com.br OR site:cnpja.com OR site:cnpj.biz OR site:cadastroempresa.com.br"
)
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
)

CHROME_PATHS = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser"
]


def _analisar_html(html_content: str, nickname_limpo: str, cidade: str) -> Optional[str]:
    soup = BeautifulSoup(html_content, 'lxml')
    melhor_documento: Optional[str] = None
    maior_pontuacao = -1

    nickname_comparavel = re.sub(r'[^a-zA-Z0-9]', '', nickname_limpo).lower()
    blocos_de_resultado = soup.select(SELETOR_BLOCOS_RESULTADO) or [soup.body]

    logging.info(f"Analisando {len(blocos_de_resultado)} blocos de resultado.")

    for bloco in blocos_de_resultado:
        texto_bloco = bloco.get_text(separator=' ').lower()
        cnpjs_no_bloco = PADRAO_CNPJ.findall(texto_bloco)
        if not cnpjs_no_bloco:
            continue

        pontuacao_bloco = 10
        if nickname_comparavel in re.sub(r'[^a-zA-Z0-9]', '', texto_bloco):
            pontuacao_bloco += 5
        if cidade.lower() in texto_bloco:
            pontuacao_bloco += 2

        if pontuacao_bloco > maior_pontuacao:
            maior_pontuacao = pontuacao_bloco
            melhor_documento = cnpjs_no_bloco[0]

    return melhor_documento


def _buscar_com_selenium_fallback(url: str, nickname_limpo: str, cidade: str) -> str:
    logging.warning("Abordagem rápida falhou. Usando fallback com Selenium (mais lento).")
    driver = None
    try:
        options = Options()
        options.add_argument(f'user-agent={USER_AGENT}')
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--log-level=3')
        options.page_load_strategy = 'eager'
        options.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )

        # Define diretório de dados temporário único
        temp_user_data_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={temp_user_data_dir}")

        # Detecta e define binário do Chrome se existir
        for path in CHROME_PATHS:
            try:
                with open(path):
                    options.binary_location = path
                    logging.info(f"Usando binário do Chrome em: {path}")
                    break
            except FileNotFoundError:
                continue

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "rso")))

        html_final = driver.page_source
        resultado = _analisar_html(html_final, nickname_limpo, cidade)

        return resultado if resultado else "Nao encontrado (Selenium)"

    except Exception as e:
        logging.error(f"Ocorreu um erro com o Selenium: {e}", exc_info=True)
        return "Erro Selenium"
    finally:
        if driver:
            driver.quit()


def buscar_cnpj_rapidamente(nickname: str, cidade: str) -> str:
    nickname_limpo = re.sub(r'^\.|\.$', '', nickname).strip()
    query = f'"{nickname_limpo}" "{cidade}" {SITES_ALVO}'
    url = f"https://www.google.com/search?q={quote_plus(query)}&gl=br&hl=pt"

    logging.info(f"Busca RÁPIDA por: {nickname_limpo} em {cidade}")

    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        if "Nossos sistemas detectaram tráfego incomum" in response.text:
            logging.warning("Google retornou página de bloqueio para o `requests`.")
            return _buscar_com_selenium_fallback(url, nickname_limpo, cidade)

        resultado = _analisar_html(response.text, nickname_limpo, cidade)
        if resultado:
            logging.info(f"SUCESSO (Requests)! CNPJ encontrado: {resultado}")
            return resultado
        else:
            logging.warning("Nenhum CNPJ encontrado com `requests`. Tentando com Selenium.")
            return _buscar_com_selenium_fallback(url, nickname_limpo, cidade)

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição HTTP: {e}. Usando fallback com Selenium.")
        return _buscar_com_selenium_fallback(url, nickname_limpo, cidade)
