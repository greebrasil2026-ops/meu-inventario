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
    .stApp { background-color: #EEF1F6; }

    /* Assinatura */
    .assinatura {
        font-size: 12px; font-weight: 700; color: #64748B;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
    }

    /* Cabeçalho principal — slate + índigo, mais sóbrio */
    .header-box {
        background: linear-gradient(135deg, #1E1B4B 0%, #3730A3 55%, #4338CA 100%);
        padding: 28px 32px; border-radius: 16px; margin-bottom: 28px;
        box-shadow: 0 8px 24px rgba(30, 27, 75, 0.28);
        border: 1px solid rgba(255,255,255,0.06);
    }
    .header-box h1 {
        color: #FFFFFF; font-size: 26px; font-weight: 800; margin: 0;
        letter-spacing: -0.2px;
    }
    .header-box p {
        color: #C7D2FE; font-size: 14px; margin: 4px 0 0 0; font-weight: 500;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0B1120 !important;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stCaption {
        color: #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important; font-weight: 800 !important;
    }

    /* Texto das opções de rádio (Tirar Foto / Subir da Galeria) */
    section[data-testid="stSidebar"] .stRadio label p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #F1F5F9 !important; font-weight: 500 !important; font-size: 14.5px;
    }
    /* Pílula da opção selecionada: tom índigo suave em vez de cinza sem graça */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: rgba(99, 102, 241, 0.18) !important;
        border-radius: 8px;
    }

    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        background-color: #16213A !important; color: #F1F5F9 !important;
        border-radius: 8px !important; border: 1px solid #2A3752 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
        color: #F1F5F9 !important;
    }

    section[data-testid="stSidebar"] .stTextInput input {
        color: #F1F5F9 !important;
        -webkit-text-fill-color: #F1F5F9 !important;
        caret-color: #F1F5F9 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] .stTextInput input::placeholder {
        color: #7B8AA8 !important;
        -webkit-text-fill-color: #7B8AA8 !important;
        opacity: 1 !important;
    }

    /* Radio buttons da sidebar (deixa de ser vermelho, vira índigo) */
    section[data-testid="stSidebar"] .stRadio label span[data-baseweb="radio"] div:first-child {
        border-color: #818CF8 !important;
    }
    section[data-testid="stSidebar"] .stRadio label span[data-baseweb="radio"] div div {
        background-color: #818CF8 !important;
    }

    /* Os widgets de câmera e upload têm fundo CLARO próprio (não é a
    sidebar escura) — então o texto deles precisa ser ESCURO, não claro.
    Isso sobrescreve, só para esses dois componentes, a regra geral que
    deixa o texto da sidebar claro. */
    section[data-testid="stSidebar"] div[data-testid="stFileUploader"],
    section[data-testid="stSidebar"] div[data-testid="stFileUploader"] *,
    section[data-testid="stSidebar"] div[data-testid="stCameraInput"],
    section[data-testid="stSidebar"] div[data-testid="stCameraInput"] * {
        color: #1E293B !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stFileUploader"] section,
    section[data-testid="stSidebar"] div[data-testid="stCameraInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stFileUploader"] button,
    section[data-testid="stSidebar"] div[data-testid="stCameraInput"] button {
        background-color: #FFFFFF !important; color: #1E293B !important;
        border: 1px solid #CBD5E1 !important; font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stFileUploader"] small,
    section[data-testid="stSidebar"] div[data-testid="stCameraInput"] small {
        color: #64748B !important;
    }

    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stCaption p,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #94A3B8 !important; font-size: 12.5px;
    }

    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, #4338CA, #3730A3); color: #FFFFFF !important;
        font-weight: 700; border-radius: 10px; border: none; padding: 10px 0;
        width: 100%; transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(135deg, #3730A3, #312E81); transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(67, 56, 202, 0.45);
    }

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
        margin: 0 auto; transition: transform 0.3s ease;
    }
    .foto-frame:hover { overflow: visible; z-index: 9000; }
    .foto-frame:hover img {
        transform: scale(2.2); box-shadow: 0 22px 55px rgba(15, 23, 42, 0.45);
        border-radius: 10px; background-color: #FFFFFF;
    }

    /* Botãozinho de expandir, no canto superior direito da foto */
    .expand-btn {
        position: absolute; top: 8px; right: 8px; width: 26px; height: 26px;
        background-color: rgba(15, 23, 42, 0.65); color: #FFFFFF !important;
        border-radius: 6px; display: flex; align-items: center; justify-content: center;
        font-size: 13px; text-decoration: none; z-index: 20; line-height: 1;
        transition: background-color 0.15s ease, transform 0.15s ease;
    }
    .expand-btn:hover { background-color: #4338CA; transform: scale(1.08); }

    /* ---- CORREÇÃO DE Z-INDEX / OVERFLOW: o zoom precisa ficar por cima
    dos containers do Streamlit (colunas / blocos), não só do card. ---- */
    div[data-testid="stHorizontalBlock"],
    div[data-testid="column"],
    div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="element-container"] {
        overflow: visible !important;
    }
    div[data-testid="column"]:has(.foto-frame:hover) {
        position: relative;
        z-index: 9000 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.foto-frame:hover) {
        z-index: 9000 !important;
    }
    /* O ponto principal: eleva o CARTÃO exato (não só a coluna) acima de
    todos os outros cartões, inclusive os que vêm depois dele na mesma
    coluna — era isso que ficava por cima da foto ampliada. */
    div[data-testid="element-container"]:has(.foto-frame:hover) {
        position: relative;
        z-index: 9500 !important;
    }
    .card-wrapper:has(.foto-frame:hover) {
        position: relative;
        z-index: 9500 !important;
    }

    /* Rótulos dos campos na área principal (Filtros de Busca) */
    div[data-testid="stTextInput"] label p,
    div[data-testid="stSelectbox"] label p {
        color: #312E81 !important; font-weight: 700 !important; font-size: 13.5px;
    }

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
    .card-info .linha { display: flex; justify-content: space-between; color: #475569; }
    .card-info .linha span { color: #64748B; }
    .card-info .linha b { color: #1E1B4B; font-weight: 700; }

    .contador-resultados {
        font-size: 15px; font-weight: 700; color: #312E81; margin-bottom: 16px;
    }

    /* ---- LIGHTBOX (foto em tela cheia + botão de baixar), 100% CSS ---- */
    .lightbox-overlay {
        display: none;
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(11, 17, 32, 0.96);
        z-index: 99999;
        align-items: center; justify-content: center; flex-direction: column;
        padding: 0; margin: 0; box-sizing: border-box;
    }
    .lightbox-overlay:target { display: flex; }
    .lightbox-content {
        display: flex; flex-direction: column; align-items: center; gap: 20px;
        width: 100%; height: 100%; justify-content: center; padding: 20px;
        box-sizing: border-box;
    }
    .lightbox-content img {
        max-width: 96vw; max-height: 84vh; width: auto; height: auto;
        border-radius: 8px; object-fit: contain;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6); background: #fff;
    }
    .lightbox-close {
        position: fixed; top: 22px; right: 30px; color: #FFFFFF;
        font-size: 30px; font-weight: 800; text-decoration: none; line-height: 1;
        background: rgba(255,255,255,0.14); width: 44px; height: 44px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        z-index: 100000;
    }
    .lightbox-close:hover { background: rgba(255,255,255,0.28); }
    .lightbox-download {
        background: linear-gradient(135deg, #4338CA, #3730A3); color: #FFFFFF !important;
        padding: 12px 28px; border-radius: 10px; text-decoration: none;
        font-weight: 700; font-size: 14px; box-shadow: 0 6px 18px rgba(67, 56, 202, 0.4);
    }
    .lightbox-download:hover { background: linear-gradient(135deg, #3730A3, #312E81); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="assinatura">Desenvolvido por Zellic Araújo</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="header-box">
        <h1>📦 Sistema de Catalogação e Inventário de Imagens</h1>
        <p>Registre, organize e consulte fotos de componentes em tempo real</p>
    </div>
""", unsafe_allow_html=True)

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

def slug(valor: str) -> str:
    """Deixa o texto seguro para usar em nome de arquivo / id de HTML."""
    valor = str(valor or "item")
    return re.sub(r"[^A-Za-z0-9_-]+", "_", valor).strip("_") or "item"

@st.cache_data(show_spinner=False, ttl=3600, max_entries=3000)
def obter_bytes_imagem(valor):
    if valor is None or valor == "PENDENTE_UPLOAD_DRIVE": raise ValueError("Sem imagem")
    valor = str(valor).strip()
    if not valor: raise ValueError("Sem imagem")
    if valor.startswith("data:image"): return base64.b64decode(valor.split(",")[1])
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
    st.sidebar.caption(
        "⚠️ Se a câmera não aparecer: o navegador precisa da sua permissão. "
        "Clique no ícone de cadeado/câmera na barra de endereço e escolha "
        "'Permitir'. Isso só funciona em endereços com HTTPS (o Streamlit "
        "Cloud já usa HTTPS por padrão)."
    )
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
            with st.spinner("Enviando foto para o Drive..."):
                bytes_imagem_envio = foto_com_dados.getvalue()
                dados_envio = {
                    "serie": input_serie,
                    "modelo": input_modelo,
                    "ambiente": input_ambiente,
                    "codigo": input_codigo,
                    "imagem": f"data:image/jpeg;base64,{base64.b64encode(bytes_imagem_envio).decode('utf-8')}"
                }
                try:
                    resposta = requests.post(URL_PLANILHA, data=json.dumps(dados_envio), headers={'Content-Type': 'application/json'}, timeout=60)
                    if resposta.status_code == 200:
                        st.sidebar.success("✅ Salvo com sucesso!")
                        st.session_state.form_counter += 1
                        st.rerun()
                    else:
                        st.sidebar.error(f"⚠️ Erro ao salvar: {resposta.status_code}")
                except Exception as e:
                    st.sidebar.error(f"Erro de conexão: {e}")

with st.container(border=True):
    st.markdown('<h3>🔍 Filtros de Busca</h3>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1: busca_s = st.text_input("Filtrar por Série", placeholder="Ex: CASSETE, INVERTER...").upper()
    with col2: busca_m = st.text_input("Buscar por Modelo", placeholder="Ex: CF100, CB601...").upper()
    with col3: busca_a = st.selectbox("Ambiente", ["Todos", "Interna", "Externa"])
    with col4: busca_c = st.text_input("Buscar por Código", placeholder="Digitar código...").upper()

try:
    from streamlit_gsheets import GSheetsConnection
    df_dados = st.connection("gsheets", type=GSheetsConnection).read(ttl="5s")
    df_dados.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
    df_filtrado = df_dados.copy()
    if busca_s: df_filtrado = df_filtrado[df_filtrado['Série'].str.upper().str.contains(busca_s, na=False)]
    if busca_m: df_filtrado = df_filtrado[df_filtrado['Modelo'].str.upper().str.contains(busca_m, na=False)]
    if busca_a != "Todos": df_filtrado = df_filtrado[df_filtrado['Ambiente'] == busca_a]
    if busca_c: df_filtrado = df_filtrado[df_filtrado['Código'].astype(str).str.contains(busca_c, na=False)]

    if not df_filtrado.empty:
        colunas_mosaico = st.columns(4)
        for idx, Server_linha in df_filtrado.reset_index().iterrows():
            with colunas_mosaico[idx % 4]:
                # id único para essa foto (usado pelo lightbox em #target)
                lb_id = f"lb_{idx}_{slug(Server_linha['Código'])}"
                nome_arquivo = f"{slug(Server_linha['Série'])}_{slug(Server_linha['Código'])}.jpg"

                try:
                    b = obter_bytes_imagem(Server_linha['Imagem'])
                    img_b64 = base64.b64encode(b).decode('utf-8')
                    data_uri = f"data:image/jpeg;base64,{img_b64}"

                    # A foto em si não abre mais nada ao clicar (só dá zoom
                    # no hover). O botãozinho no canto abre o lightbox com
                    # a opção de baixar.
                    html_foto = f'''
                        <div class="foto-frame">
                            <img src="{data_uri}">
                            <a href="#{lb_id}" class="expand-btn" title="Expandir foto">⤢</a>
                        </div>
                        <div class="lightbox-overlay" id="{lb_id}">
                            <a href="#" class="lightbox-close" title="Fechar">✕</a>
                            <div class="lightbox-content">
                                <img src="{data_uri}">
                                <a href="{data_uri}" download="{nome_arquivo}" class="lightbox-download">⬇️ Baixar Foto</a>
                            </div>
                        </div>
                    '''
                except Exception:
                    html_foto = '<div class="foto-indisponivel">⚠️ Imagem indisponível.</div>'

                st.markdown(
                    f'<div class="card-wrapper">{html_foto}<div class="card-info">'
                    f'<div class="linha"><span>Série</span><b>{Server_linha["Série"]}</b></div>'
                    f'<div class="linha"><span>Modelo</span><b>{Server_linha["Modelo"]}</b></div>'
                    f'<div class="linha"><span>Ambiente</span><b>{Server_linha["Ambiente"]}</b></div>'
                    f'<div class="linha"><span>Código</span><b>{Server_linha["Código"]}</b></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
    else:
        st.info("💡 Nenhum item encontrado.")
except Exception:
    st.info("💡 Planilha aguardando dados.")
