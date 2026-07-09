import re
import streamlit as st
import pandas as pd
import base64
import json
import requests

# Configuração da página para ocupar a tela inteira (layout wide para mosaico)
st.set_page_config(page_title="Sistema de Catalogação Dinâmico", layout="wide", page_icon="📦")

# --- ESTILIZAÇÃO CSS PROFISSIONAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Fundo geral suave */
    .stApp { background-color: #F1F5F9; }

    /* Assinatura */
    .assinatura {
        font-size: 12px; font-weight: 700; color: #64748B;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
    }

    /* Cabeçalho principal */
    .header-box {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
        padding: 28px 32px; border-radius: 16px; margin-bottom: 28px;
        box-shadow: 0 8px 24px rgba(30, 58, 138, 0.25);
    }
    .header-box h1 {
        color: #FFFFFF; font-size: 26px; font-weight: 800; margin: 0;
    }
    .header-box p {
        color: #DBEAFE; font-size: 14px; margin: 4px 0 0 0; font-weight: 500;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
    }
    section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important; font-weight: 800 !important;
    }
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        background-color: #1E293B !important; color: #F8FAFC !important;
        border-radius: 8px !important; border: 1px solid #334155 !important;
    }

    /* Campo de texto */
    section[data-testid="stSidebar"] .stTextInput input {
        color: #F8FAFC !important;
        -webkit-text-fill-color: #F8FAFC !important;
        caret-color: #F8FAFC !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] .stTextInput input::placeholder {
        color: #94A3B8 !important;
        -webkit-text-fill-color: #94A3B8 !important;
        opacity: 1 !important;
    }

    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFFFFF !important;
        font-weight: 700; border-radius: 10px; border: none; padding: 10px 0;
        width: 100%; transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF); transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }

    /* Cards do mosaico */
    .card-wrapper {
        background-color: #FFFFFF; border-radius: 14px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease; margin-bottom: 18px;
        position: relative;
    }
    .card-wrapper:hover {
        transform: translateY(-3px); box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
    }

    .foto-frame {
        position: relative; height: 220px; width: 100%;
        background-color: #FFFFFF; display: flex;
        align-items: center; justify-content: center;
        overflow: hidden; border-radius: 14px 14px 0 0;
    }
    .foto-frame img {
        max-height: 220px; max-width: 100%; width: auto; height: auto;
        object-fit: contain; object-position: center center; display: block;
        margin: 0 auto; cursor: zoom-in; transition: transform 0.3s ease;
    }
    .foto-frame:hover { overflow: visible; z-index: 200; }
    .foto-frame:hover img {
        transform: scale(2.2); box-shadow: 0 22px 55px rgba(15, 23, 42, 0.45);
        border-radius: 10px; background-color: #FFFFFF;
    }
    div[data-testid="column"]:has(.foto-frame:hover) { position: relative; z-index: 200; }

    .foto-indisponivel {
        height: 220px; width: 100%; display: flex; align-items: center;
        justify-content: center; text-align: center; padding: 0 16px;
        background-color: #FEF2F2; color: #991B1B; font-size: 13px; font-weight: 600;
        border-radius: 14px 14px 0 0;
    }

    .card-info {
        background-color: #F8FAFC; padding: 14px 16px; border-top: 1px solid #E2E8F0;
        font-size: 13.5px; line-height: 1.7; border-radius: 0 0 14px 14px;
    }
    .card-info .linha { display: flex; justify-content: space-between; color: #334155; }
    .card-info .linha b { color: #0F172A; font-weight: 700; }

    .contador-resultados {
        font-size: 15px; font-weight: 700; color: #1E293B; margin-bottom: 16px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="assinatura">Desenvolvido por Zellic Araújo</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="header-box">
        <h1>📦 Sistema de Catalogação e Inventário de Imagens</h1>
        <p>Registre, organize e consulte fotos de componentes em tempo real</p>
    </div>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O SEU GOOGLE SHEETS VIA SECRET API ---
URL_PLANILHA = ""
if "connections" in st.secrets and "google_script_url" in st.secrets["connections"]:
    URL_PLANILHA = st.secrets["connections"]["google_script_url"]

PADRAO_ID_DRIVE = re.compile(r"[-\w]{25,}")

def extrair_id_drive(valor: str):
    m = PADRAO_ID_DRIVE.search(valor)
    return m.group(0) if m else valor

def montar_url_drive(valor: str) -> str:
    file_id = extrair_id_drive(valor)
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"

@st.cache_data(show_spinner=False, ttl=3600, max_entries=3000)
def obter_bytes_imagem(valor):
    if valor is None: raise ValueError("Sem imagem")
    valor = str(valor).strip()
    if not valor: raise ValueError("Sem imagem")
    if valor.startswith("data:image"):
        return base64.b64decode(valor.split(",")[1])
    url = montar_url_drive(valor)
    resposta = requests.get(url, timeout=20)
    resposta.raise_for_status()
    conteudo = resposta.content
    tipo = resposta.headers.get("Content-Type", "")
    if "image" not in tipo: raise ValueError("Drive não retornou uma imagem")
    return conteudo

if "form_counter" not in st.session_state: st.session_state.form_counter = 0
key_suffix = st.session_state.form_counter

st.sidebar.header("📸 Adicionar Novo Item")
origem = st.sidebar.radio("Selecione o método:", ["Tirar Foto (Celular/PC)", "Subir da Galeria de Fotos"], key=f"origem_{key_suffix}")

foto_com_dados = None
if origem == "Tirar Foto (Celular/PC)":
    foto_com_dados = st.sidebar.camera_input("Aponte a câmera para o componente", key=f"camera_{key_suffix}")
else:
    foto_com_dados = st.sidebar.file_uploader("Escolha a imagem", type=["jpg", "jpeg", "png", "webp"], key=f"upload_{key_suffix}")

if foto_com_dados is not None:
    st.sidebar.subheader("📝 Informações de Registro")
    input_serie = st.sidebar.text_input("SÉRIE:", key=f"serie_{key_suffix}").strip().upper()
    input_modelo = st.sidebar.text_input("MODELO:", key=f"modelo_{key_suffix}").strip().upper()
    input_ambiente = st.sidebar.selectbox("AMBIENTE:", ["Externa", "Interna"], key=f"ambiente_{key_suffix}")
    input_codigo = st.sidebar.text_input("CÓDIGO:", key=f"codigo_{key_suffix}").strip().upper()

    if st.sidebar.button("💾 Enviar Direto para o Sistema", key=f"btn_enviar_{key_suffix}"):
        if input_serie and input_modelo and input_codigo and URL_PLANILHA:
            with st.spinner("Registrando dados..."):
                dados_envio = {
                    "serie": input_serie,
                    "modelo": input_modelo,
                    "ambiente": input_ambiente,
                    "codigo": input_codigo,
                    "imagem": "PENDENTE_UPLOAD_DRIVE"
                }
                try:
                    resposta = requests.post(URL_PLANILHA, data=json.dumps(dados_envio), headers={'Content-Type': 'application/json'}, timeout=30)
                    if resposta.status_code == 200:
                        st.sidebar.success("✅ Dados salvos na Planilha! (Realize o upload da foto no Drive)")
                        st.session_state.form_counter += 1
                        st.rerun()
                    else:
                        st.sidebar.error(f"⚠️ Apps Script retornou status {resposta.status_code}")
                except Exception as e:
                    st.sidebar.error(f"Erro ao conectar com a planilha: {e}")

with st.container(border=True):
    st.markdown('<h3>🔍 Filtros de Busca</h3>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1: busca_s = st.text_input("Filtrar por Série", placeholder="Ex: CASSETE, INVERTER...").upper()
    with col2: busca_m = st.text_input("Buscar por Modelo", placeholder="Ex: CF100, CB601...").upper()
    with col3: busca_a = st.selectbox("Ambiente", ["Todos", "Interna", "Externa"])
    with col4: busca_c = st.text_input("Buscar por Código", placeholder="Digitar código...").upper()

try:
    from streamlit_gsheets import GSheetsConnection
    conexao_sheets = st.connection("gsheets", type=GSheetsConnection)
    df_dados = conexao_sheets.read(ttl="5s")
except Exception:
    st.info("💡 Pronto para rodar! Adicione os Secrets no painel do Streamlit Cloud.")
    st.stop()

if not df_dados.empty:
    df_dados.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
    df_filtrado = df_dados.copy()
    if busca_s: df_filtrado = df_filtrado[df_filtrado['Série'].str.upper().str.contains(busca_s, na=False)]
    if busca_m: df_filtrado = df_filtrado[df_filtrado['Modelo'].str.upper().str.contains(busca_m, na=False)]
    if busca_a != "Todos": df_filtrado = df_filtrado[df_filtrado['Ambiente'] == busca_a]
    if busca_c: df_filtrado = df_filtrado[df_filtrado['Código'].astype(str).str.contains(busca_c, na=False)]

    if not df_filtrado.empty:
        colunas_mosaico = st.columns(4)
        for idx, Server_linha in df_filtrado.reset_index().iterrows():
            coluna_da_vez = colunas_mosaico[idx % 4]
            with coluna_da_vez:
                bytes_imagem = None
                try:
                    bytes_imagem = obter_bytes_imagem(Server_linha['Imagem'])
                    img_b64 = base64.b64encode(bytes_imagem).decode('utf-8')
                    html_foto = f'<div class="foto-frame"><img src="data:image/jpeg;base64,{img_b64}" alt="Foto do componente"></div>'
                except Exception:
                    html_foto = '<div class="foto-indisponivel">⚠️ Imagem indisponível.<br>Verifique o compartilhamento no Drive.</div>'
                st.markdown(f"""
                    <div class="card-wrapper">
                        {html_foto}
                        <div class="card-info">
                            <div class="linha"><span>Série</span><b>{Server_linha['Série']}</b></div>
                            <div class="linha"><span>Modelo</span><b>{Server_linha['Modelo']}</b></div>
                            <div class="linha"><span>Ambiente</span><b>{Server_linha['Ambiente']}</b></div>
                            <div class="linha"><span>Código</span><b>{Server_linha['Código']}</b></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if bytes_imagem is not None:
                    st.download_button("📥 Baixar Foto", data=bytes_imagem, file_name=f"{Server_linha['Série']}_{Server_linha['Modelo']}_{Server_linha['Código']}.jpg", mime="image/jpeg", key=f"btn_dl_{idx}", use_container_width=True)
    else:
        st.info("💡 Nenhuma foto corresponde aos filtros aplicados.")
else:
    st.info("💡 A planilha está conectada, mas não possui nenhum registro fotográfico ainda.")
