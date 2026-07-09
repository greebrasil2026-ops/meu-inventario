import streamlit as st
import pandas as pd
import base64
import json
import requests

st.set_page_config(page_title="Sistema de Catalogação", layout="wide")

st.markdown("""
    <style>
    .assinatura { font-size: 13px; font-weight: 800; color: #1E3A8A; text-transform: uppercase; border-bottom: 2px solid #3B82F6; padding-bottom: 2px; margin-bottom: 15px; }
    .card-info { background-color: #F8FAFC; padding: 12px; border-radius: 0 0 12px 12px; border: 1px solid #E2E8F0; border-top: none; font-size: 13.5px; }
    [data-testid="stImage"] img { border-radius: 12px 12px 0 0; object-fit: cover; height: 230px !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Sistema de Catalogação e Inventário")

# Carrega os segredos de forma segura
try:
    URL_PLANILHA = st.secrets["connections"]["google_script_url"]
except KeyError:
    st.error("ERRO: 'google_script_url' não encontrado nos Secrets.")
    URL_PLANILHA = None

st.sidebar.header("📸 Adicionar Novo Item")
origem = st.sidebar.radio("Selecione o método:", ["Tirar Foto (Celular/PC)", "Subir da Galeria de Fotos"])

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
            st.sidebar.warning("Preencha todos os campos e verifique os Secrets.")

# Leitura da Planilha
try:
    conexao = st.connection("gsheets", type=st.connection.GSheetsConnection)
    df = conexao.read(ttl=1)
    if not df.empty:
        df.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
        st.subheader("Itens Cadastrados")
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                st.image(row['Imagem'])
                st.markdown(f'<div class="card-info">Série: {row["Série"]}<br>Mod: {row["Modelo"]}</div>', unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Atenção: Planilha não conectada. Verifique os Secrets no painel. Detalhe: {e}")
