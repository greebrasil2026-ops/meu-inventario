import re
import streamlit as st
import pandas as pd
import base64
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    /* Grid do mosaico renderizado como UM bloco HTML só (em vez de
    N st.columns / N st.markdown), o que reduz muito o número de
    componentes que o Streamlit precisa montar e mandar pro navegador. */
    .mosaico-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 18px;
        margin-top: 6px;
    }
    @media (max-width: 1200px) {
        .mosaico-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 700px) {
        .mosaico-grid { grid-template-columns: 1fr; }
    }

    .card-wrapper {
        background-color: #FFFFFF; border-radius: 14px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
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
        margin: 0 auto; transition: transform 0.3s ease; cursor: pointer;
        /* ajuda o navegador a não travar decodificando tudo de uma vez */
        loading: lazy;
    }
    .foto-frame:hover { overflow: visible; z-index: 100; }
    .foto-frame:hover img {
        transform: scale(2.2); box-shadow: 0 22px 55px rgba(15, 23, 42, 0.45);
        border-radius: 10px; background-color: #FFFFFF;
    }

    /* Overflow visível para o zoom não cortar, e z-index para o card
    em hover ficar por cima dos vizinhos. Como agora é um grid CSS puro
    (não st.columns), isso fica bem mais simples e leve que antes. */
    .mosaico-grid { overflow: visible; }
    .card-wrapper:has(.foto-frame:hover) { z-index: 200; }

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

    /* Tela de login */
    .login-box {
        background-color: #FFFFFF; border-radius: 16px; padding: 36px 32px;
        border: 1px solid #E2E8F0; box-shadow: 0 12px 32px rgba(30, 27, 75, 0.12);
        margin-top: 60px;
    }
    .login-box h2 {
        color: #1E1B4B; font-size: 22px; font-weight: 800; margin: 0 0 6px 0;
    }
    .login-box p {
        color: #64748B; font-size: 13.5px; margin: 0 0 20px 0;
    }
    div[data-testid="stForm"] .stButton button {
        background: linear-gradient(135deg, #4338CA, #3730A3); color: #FFFFFF !important;
        font-weight: 700; border-radius: 10px; border: none; padding: 10px 0;
        width: 100%;
    }
    div[data-testid="stForm"] .stButton button:hover {
        background: linear-gradient(135deg, #3730A3, #312E81);
    }

    </style>
""", unsafe_allow_html=True)

# --- AUTENTICAÇÃO (usuário e senha) ---
USUARIOS_VALIDOS = {}
if "auth" in st.secrets and "usuarios" in st.secrets["auth"]:
    USUARIOS_VALIDOS = dict(st.secrets["auth"]["usuarios"])

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_esq, col_meio, col_dir = st.columns([1, 1.1, 1])
    with col_meio:
        st.markdown(
            '<div class="login-box"><h2>🔒 Acesso Restrito</h2>'
            '<p>Digite seu usuário e senha para visualizar o catálogo.</p></div>',
            unsafe_allow_html=True
        )
        with st.form("form_login", clear_on_submit=False):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            if not USUARIOS_VALIDOS:
                st.error("⚠️ Nenhum usuário configurado ainda nos Secrets do Streamlit Cloud.")
            elif usuario_input in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario_input] == senha_input:
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()  # impede que o resto do app (catálogo) seja renderizado


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

# OTIMIZAÇÃO 1: o thumbnail do Drive era pedido em w1000 (imagem enorme)
# para ser exibido num quadro de 220px de altura. Isso multiplicava por
# ~5x o tamanho de cada imagem baixada e o tempo de decodificação no
# navegador, sem nenhum ganho visual. w400 já é mais que suficiente
# mesmo com o zoom de hover (2.2x de 220px ≈ 484px).
def montar_url_drive(valor: str, tamanho: int = 400) -> str:
    file_id = extrair_id_drive(valor)
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w{tamanho}"

def slug(valor: str) -> str:
    """Deixa o texto seguro para usar em nome de arquivo / id de HTML."""
    valor = str(valor or "item")
    return re.sub(r"[^A-Za-z0-9_-]+", "_", valor).strip("_") or "item"

# OTIMIZAÇÃO 2: cacheia direto a data-URI (base64) já pronta para
# inserir no <img src="...">, em vez de cachear só os bytes e refazer
# o base64.b64encode(...) a cada rerun do Streamlit (isso rodava de
# novo pra CADA item, em CADA interação do usuário, mesmo com cache).
@st.cache_data(show_spinner=False, ttl=3600, max_entries=1000)
def obter_data_uri_imagem(valor):
    if valor is None or valor == "PENDENTE_UPLOAD_DRIVE":
        raise ValueError("Sem imagem")
    valor = str(valor).strip()
    if not valor:
        raise ValueError("Sem imagem")
    if valor.startswith("data:image"):
        return valor
    url = montar_url_drive(valor)
    resposta = requests.get(url, timeout=20)
    resposta.raise_for_status()
    conteudo = resposta.content
    tipo = resposta.headers.get("Content-Type", "")
    if "image" not in tipo:
        raise ValueError("Drive não retornou uma imagem")
    b64 = base64.b64encode(conteudo).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

if "form_counter" not in st.session_state: st.session_state.form_counter = 0
key_suffix = st.session_state.form_counter

st.sidebar.markdown(f"👤 Logado como **{st.session_state.get('usuario_logado', '')}**")
if st.sidebar.button("🚪 Sair", key="btn_logout"):
    st.session_state.autenticado = False
    st.rerun()
st.sidebar.divider()

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

    # OTIMIZAÇÃO 3: ttl="5s" fazia o app reler a planilha inteira do
    # Google Sheets a cada 5 segundos em qualquer interação (digitar um
    # filtro, mudar de página, etc). 60s já é suficiente pra um catálogo
    # de inventário e reduz muito as chamadas de rede. Some um botão de
    # "atualizar agora" pra quando o usuário realmente precisar do dado
    # mais recente na hora.
    col_titulo, col_refresh = st.columns([6, 1])
    with col_refresh:
        forcar_refresh = st.button("🔄 Atualizar", use_container_width=True)

    ttl_planilha = "0s" if forcar_refresh else "60s"
    df_dados = st.connection("gsheets", type=GSheetsConnection).read(ttl=ttl_planilha)
    df_dados.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
    df_filtrado = df_dados.copy()
    if busca_s: df_filtrado = df_filtrado[df_filtrado['Série'].str.upper().str.contains(busca_s, na=False)]
    if busca_m: df_filtrado = df_filtrado[df_filtrado['Modelo'].str.upper().str.contains(busca_m, na=False)]
    if busca_a != "Todos": df_filtrado = df_filtrado[df_filtrado['Ambiente'] == busca_a]
    if busca_c: df_filtrado = df_filtrado[df_filtrado['Código'].astype(str).str.contains(busca_c, na=False)]

    total_itens = len(df_filtrado)

    if total_itens > 0:
        # OTIMIZAÇÃO 4: paginação. Antes TODOS os itens filtrados eram
        # renderizados de uma vez — com um catálogo grande isso significa
        # dezenas/centenas de imagens em base64 embutidas na página ao
        # mesmo tempo, o que deixa o carregamento e a rolagem pesados.
        # Agora só a página atual é buscada e desenhada.
        ITENS_POR_PAGINA = 20
        total_paginas = max(1, (total_itens - 1) // ITENS_POR_PAGINA + 1)

        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = 1
        # se o filtro mudou e a página ficou fora do intervalo, corrige
        if st.session_state.pagina_atual > total_paginas:
            st.session_state.pagina_atual = 1

        col_contador, col_paginacao = st.columns([3, 2])
        with col_contador:
            st.markdown(
                f'<div class="contador-resultados">📊 {total_itens} item(ns) encontrado(s)</div>',
                unsafe_allow_html=True
            )
        with col_paginacao:
            if total_paginas > 1:
                st.session_state.pagina_atual = st.number_input(
                    f"Página (1 a {total_paginas})",
                    min_value=1, max_value=total_paginas,
                    value=st.session_state.pagina_atual, step=1,
                    label_visibility="collapsed"
                )

        inicio = (st.session_state.pagina_atual - 1) * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        df_pagina = df_filtrado.reset_index(drop=True).iloc[inicio:fim]

        # OTIMIZAÇÃO 5: busca as imagens da página em paralelo (só as
        # ~20 da página atual, não do catálogo inteiro), o que acelera
        # bastante quando várias ainda não estão em cache.
        def carregar_linha(linha):
            try:
                data_uri = obter_data_uri_imagem(linha["Imagem"])
                return (linha.name, data_uri, None)
            except Exception as e:
                return (linha.name, None, str(e))

        resultados_imagens = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futuros = [executor.submit(carregar_linha, linha) for _, linha in df_pagina.iterrows()]
            for futuro in as_completed(futuros):
                idx, data_uri, erro = futuro.result()
                resultados_imagens[idx] = data_uri

        # OTIMIZAÇÃO 6: monta o mosaico inteiro como UM único bloco HTML
        # (grid CSS) e chama st.markdown() uma vez só, em vez de um
        # st.columns()/st.markdown() por card. Isso reduz drasticamente
        # o número de componentes que o Streamlit precisa criar e
        # sincronizar com o navegador a cada renderização.
        cards_html = []
        for idx, linha in df_pagina.iterrows():
            nome_arquivo = f"{slug(linha['Série'])}_{slug(linha['Código'])}.jpg"
            data_uri = resultados_imagens.get(idx)

            if data_uri:
                html_foto = f'''
                    <div class="foto-frame">
                        <a href="{data_uri}" download="{nome_arquivo}" title="Clique para baixar a foto">
                            <img src="{data_uri}" loading="lazy">
                        </a>
                    </div>
                '''
            else:
                html_foto = '<div class="foto-indisponivel">⚠️ Imagem indisponível.</div>'

            cards_html.append(
                f'<div class="card-wrapper">{html_foto}<div class="card-info">'
                f'<div class="linha"><span>Série</span><b>{linha["Série"]}</b></div>'
                f'<div class="linha"><span>Modelo</span><b>{linha["Modelo"]}</b></div>'
                f'<div class="linha"><span>Ambiente</span><b>{linha["Ambiente"]}</b></div>'
                f'<div class="linha"><span>Código</span><b>{linha["Código"]}</b></div>'
                f'</div></div>'
            )

        st.markdown(f'<div class="mosaico-grid">{"".join(cards_html)}</div>', unsafe_allow_html=True)

        if total_paginas > 1:
            st.caption(f"Página {st.session_state.pagina_atual} de {total_paginas}")
    else:
        st.info("💡 Nenhum item encontrado.")
except Exception:
    st.info("💡 Planilha aguardando dados.")
