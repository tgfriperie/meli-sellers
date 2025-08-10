import streamlit as st
import pandas as pd
import os

# Módulos do nosso sistema
from meli_auth import get_valid_token
from meli_enricher import get_seller_data, extract_relevant_data
from web_scraper import buscar_cnpj_rapidamente

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Meli Sheets Enricher")

# --- Funções Auxiliares ---
@st.cache_data
def convert_df_to_csv(df):
    """Converte o DataFrame para CSV em memória para o download."""
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- Interface Principal ---
st.title("🚀 Sistema de Enriquecimento de Vendedores Mercado Livre")

# --- Barra Lateral e Verificação de Autenticação ---
st.sidebar.header("Status da Autenticação")
if os.path.exists('client.csv'):
    st.sidebar.success("✅ Arquivo 'client.csv' encontrado.")
    st.sidebar.info("O sistema está pronto. O token será gerado ou atualizado automaticamente.")
    credentials_ok = True
else:
    st.sidebar.error("❌ Arquivo 'client.csv' não encontrado.")
    st.sidebar.info(
        "**Para usar a aplicação, crie o arquivo `client.csv` na mesma pasta com a seguinte estrutura e preencha com suas chaves:**"
    )
    st.sidebar.code(
        """
client_name,app_id,client_secret,refresh_token
NOME_DA_APP,123...,SEU_SECRET,SEU_REFRESH_TOKEN
        """, language='csv'
    )
    credentials_ok = False

# --- Lógica Principal da Aplicação ---
if credentials_ok:
    st.header("1. Faça o upload da sua planilha de vendedores")
    uploaded_file = st.file_uploader(
        "Arraste e solte o arquivo .xlsx ou .csv aqui",
        type=['xlsx', 'csv']
    )

    if uploaded_file is not None:
        # Inicializa o estado de processamento para desabilitar o botão
        if 'processing' not in st.session_state:
            st.session_state.processing = False

        if st.button("▶️ Iniciar Processamento", type="primary", disabled=st.session_state.processing):
            st.session_state.processing = True
            
            # --- Etapa 0: Obter Token Válido ---
            with st.spinner("Autenticando com o Mercado Livre..."):
                access_token = get_valid_token()
                if not access_token:
                    st.error("Falha na autenticação. Verifique seu `client.csv` e a conexão.")
                    st.session_state.processing = False
                    st.stop()
            st.success("Autenticação bem-sucedida!")

            # --- Etapa 1: Enriquecimento via API ---
            with st.spinner("ETAPA 1/2: Buscando dados na API do Mercado Livre..."):
                try:
                    df_input = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo: {e}")
                    st.session_state.processing = False
                    st.stop()
                
                enriched_rows = []
                progress_bar_api = st.progress(0, text="Progresso da API...")
                total_rows = len(df_input)
                coluna_id = df_input.columns[0]

                for index, row in df_input.iterrows():
                    seller_id = row[coluna_id]
                    if pd.isna(seller_id):
                        continue
                    
                    # Desempacota a tupla para pegar os dados e o token separadamente
                    api_data, access_token = get_seller_data(int(seller_id), access_token)
                    
                    relevant_data = extract_relevant_data(api_data)
                    relevant_data['id_consultado'] = seller_id
                    enriched_rows.append(relevant_data)
                    progress_bar_api.progress((index + 1) / total_rows, text=f"Progresso da API: {index+1}/{total_rows}")

                df_api_data = pd.DataFrame(enriched_rows)
                st.session_state['df_api'] = df_api_data
                progress_bar_api.empty()
            st.success("✅ Etapa 1 concluída!")

            # --- Etapa 2: Busca de CNPJ com Selenium ---
            with st.spinner("ETAPA 2/2: Buscando CNPJs com Selenium... (Isso pode levar vários minutos!)"):
                df_api_data['cnpj_encontrado'] = 'N/A'
                progress_bar_cnpj = st.progress(0, text="Progresso da busca de CNPJ...")
                
                for index, row in df_api_data.iterrows():
                    nickname = row['nickname']
                    cidade = row['city']
                    
                    if pd.notna(nickname) and "ERRO" not in nickname and pd.notna(cidade) and cidade != 'N/A':
                        cnpj = buscar_cnpj_rapidamente(nickname, cidade)
                        df_api_data.at[index, 'cnpj_encontrado'] = cnpj
                    
                    progress_bar_cnpj.progress((index + 1) / total_rows, text=f"Progresso da busca de CNPJ: {index+1}/{total_rows}")
                
                st.session_state['df_final'] = df_api_data
                progress_bar_cnpj.empty()
            
            st.success("✅ Etapa 2 concluída! Processamento finalizado.")
            st.session_state.processing = False
            st.rerun()

# --- Exibição dos Resultados e Botão de Download ---
if 'df_final' in st.session_state:
    st.header("2. Resultados")
    final_df = st.session_state['df_final']
    st.dataframe(final_df)

    csv_data = convert_df_to_csv(final_df)
    
    st.download_button(
        label="📥 Baixar planilha com resultados (.csv)",
        data=csv_data,
        file_name='resultados_enriquecidos.csv',
        mime='text/csv',
    )