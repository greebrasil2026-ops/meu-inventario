import streamlit as st
import pandas as pd
import base64
import requests
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(page_title="Sistema de Catalogação", layout="wide")

st.markdown("""
    <style>
    .card-info { background-color: #F8FAFC; padding: 12px; border-radius: 0 0 12px 12px; border: 1px solid #E2E8F0; border-top: none; font-size: 13.5px; }
    [data-testid="stImage"] img { border-radius: 12px 12px 0 0; object-fit: cover; height: 230px !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Sistema de Catalogação e Inventário")

# --- CONEXÃO COM SECRET ---
# Certifique-se de que no painel Secrets do Streamlit Cloud você tenha:
# [connections.gsheets]
# spreadsheet = "SEU_ID_DA_PLANILHA"
#
# [connections]
# google_script_url = "SUA_URL_DO_WEB_APP"

try:
    URL_PLANILHA = st.secrets["connections"]["google_script_url"]
except:
    st.error("Erro: A URL do Script não foi configurada nos Secrets.")
    URL_PLANILHA = None

st.sidebar.header("📸 Adicionar Novo Item")
origem = st.sidebar.radio("Método:", ["Tirar Foto (Celular/PC)", "Subir da Galeria"])
foto_com_dados = st.sidebar.camera_input("Aponte a câmera") if origem == "Tirar Foto (Celular/PC)" else st.sidebar.file_uploader("Escolha a imagem", type=["jpg", "png"])

if foto_com_dados:
    input_serie = st.sidebar.text_input("SÉRIE:").strip().upper()
    input_modelo = st.sidebar.text_input("MODELO:").strip().upper()
    input_ambiente = st.sidebar.selectbox("AMBIENTE:", ["Interna", "Externa"])
    input_codigo = st.sidebar.text_input("CÓDIGO:").strip().upper()
    
    if st.sidebar.button("💾 Enviar"):
        if URL_PLANILHA and input_serie and input_modelo and input_codigo:
            img_b64 = base64.b64encode(foto_com_dados.getvalue()).decode('utf-8')
            dados = {"serie": input_serie, "modelo": input_modelo, "ambiente": input_ambiente, "codigo": input_codigo, "imagem": f"data:image/jpeg;base64,{img_b64}"}
            try:
                res = requests.post(URL_PLANILHA, json=dados)
                if res.status_code == 200:
                    st.sidebar.success("✅ Enviado!")
                    st.rerun()
                else:
                    st.sidebar.error(f"Erro no servidor: {res.status_code}")
            except Exception as e:
                st.sidebar.error(f"Falha na rede: {e}")
        else:
            st.sidebar.warning("Preencha todos os campos!")

# --- LEITURA DA PLANILHA ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=1)
    if not df.empty:
        df.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
        st.subheader("Itens Cadastrados")
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                st.image(row['Imagem'])
                st.markdown(f'<div class="card-info">Série: {row["Série"]}<br>Mod: {row["Modelo"]}</div>', unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Conexão com a planilha pendente. Detalhe: {e}")
