import re
import streamlit as st
import pandas as pd
import base64
import json
import requests

# Configuração da página
st.set_page_config(page_title="Sistema de Catalogação Dinâmico", layout="wide", page_icon="📦")

# --- CSS PROFISSIONAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F1F5F9; }
    .header-box { background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); padding: 28px 32px; border-radius: 16px; margin-bottom: 28px; box-shadow: 0 8px 24px rgba(30, 58, 138, 0.25); }
    .header-box h1 { color: #FFFFFF; font-size: 26px; font-weight: 800; margin: 0; }
    section[data-testid="stSidebar"] { background-color: #0F172A; }
    section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    .card-wrapper { background-color: #FFFFFF; border-radius: 14px; border: 1px solid #E2E8F0; margin-bottom: 18px; position: relative; }
    .foto-frame { height: 220px; width: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden; border-radius: 14px 14px 0 0; background: #EEE; }
    .foto-frame img { max-height: 220px; max-width: 100%; object-fit: contain; }
    .card-info { padding: 14px; font-size: 13px; border-top: 1px solid #E2E8F0; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""<div class="header-box"><h1>📦 Sistema de Catalogação</h1><p>Upload direto para Drive</p></div>""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
URL_PLANILHA = st.secrets["connections"]["google_script_url"] if "connections" in st.secrets else ""
PADRAO_ID_DRIVE = re.compile(r"[-\w]{25,}")

def montar_url_drive(valor):
    file_id = PADRAO_ID_DRIVE.search(str(valor))
    return f"https://drive.google.com/thumbnail?id={file_id.group(0)}&sz=w1000" if file_id else None

@st.cache_data(show_spinner=False, ttl=3600)
def obter_bytes_imagem(valor):
    if not valor or valor == "PENDENTE_UPLOAD_DRIVE": raise ValueError("Sem imagem")
    url = montar_url_drive(valor)
    if not url: return None
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.content

# --- INTERFACE LATERAL ---
if "form_counter" not in st.session_state: st.session_state.form_counter = 0
key_suffix = st.session_state.form_counter

st.sidebar.header("📸 Adicionar Item")
origem = st.sidebar.radio("Método:", ["Tirar Foto", "Upload Galeria"], key=f"o_{key_suffix}")
foto = st.sidebar.camera_input("Foto", key=f"c_{key_suffix}") if origem == "Tirar Foto" else st.sidebar.file_uploader("Arquivo", type=["jpg","png"], key=f"u_{key_suffix}")

if foto:
    s = st.sidebar.text_input("SÉRIE:", key=f"s_{key_suffix}").upper()
    m = st.sidebar.text_input("MODELO:", key=f"m_{key_suffix}").upper()
    a = st.sidebar.selectbox("AMBIENTE:", ["Externa", "Interna"], key=f"a_{key_suffix}")
    c = st.sidebar.text_input("CÓDIGO:", key=f"c_code_{key_suffix}").upper()

    if st.sidebar.button("💾 Enviar ao Sistema", key=f"btn_{key_suffix}"):
        with st.spinner("Enviando..."):
            dados = {
                "serie": s, "modelo": m, "ambiente": a, "codigo": c,
                "filedata": base64.b64encode(foto.getvalue()).decode('utf-8'),
                "filename": f"{c}.jpg", "mimetype": "image/jpeg"
            }
            try:
                r = requests.post(URL_PLANILHA, data=json.dumps(dados), timeout=60)
                if r.status_code == 200:
                    st.sidebar.success("✅ Sucesso!")
                    st.session_state.form_counter += 1
                    st.rerun()
                else:
                    st.sidebar.error("Erro no envio.")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

# --- BUSCA E EXIBIÇÃO ---
busca_c = st.text_input("🔍 Filtrar por Código")
try:
    df = st.connection("gsheets", type="gsheets").read(ttl="5s")
    df.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
    if busca_c: df = df[df['Código'].astype(str).str.contains(busca_c, na=False)]
    
    cols = st.columns(4)
    for idx, row in df.reset_index().iterrows():
        with cols[idx % 4]:
            try:
                b = obter_bytes_imagem(row['Imagem'])
                st.markdown(f'<div class="card-wrapper"><div class="foto-frame"><img src="data:image/jpeg;base64,{base64.b64encode(b).decode()}"></div><div class="card-info"><b>{row["Código"]}</b><br>{row["Modelo"]}</div></div>', unsafe_allow_html=True)
            except:
                st.markdown(f'<div class="card-wrapper"><div class="foto-frame">Sem imagem</div><div class="card-info"><b>{row["Código"]}</b></div></div>', unsafe_allow_html=True)
except:
    st.error("Erro ao carregar planilha.")
