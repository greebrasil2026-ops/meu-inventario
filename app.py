import re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import json
import io
import zipfile
import requests
import datetime
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# ATENÇÃO — BACKEND (Google Apps Script) PRECISA SER ATUALIZADO
# =============================================================================
# Este app agora envia 3 tipos de ação para o webhook (URL_PLANILHA), no
# campo "acao" do JSON:
#
#   "acao": "criar"   -> comportamento que já existia (adiciona uma linha)
#   "acao": "editar"  -> deve localizar a linha cujo Código == "codigo_original"
#                         e sobrescrever Série/Modelo/Ambiente/Código, e só
#                         trocar a coluna Imagem se o campo "imagem" vier
#                         preenchido (se vier None/ausente, mantém a foto atual)
#   "acao": "excluir" -> deve REMOVER a linha cujo Código == "codigo"
#
# Em "editar" e "excluir" o app também manda "motivo" (obrigatório só na
# exclusão) e "usuario" (quem está logado). O ideal é que o Apps Script,
# a cada editar/excluir/criar, registre uma linha numa aba separada chamada
# "Historico" com as colunas:
#
#   Data/Hora | Usuário | Ação | Série | Modelo | Ambiente | Código | Motivo
#
# Essa aba "Historico" é o que a página "🕓 Histórico" deste app lê. Se ela
# ainda não existir na planilha, a página de Histórico mostra um aviso.
# =============================================================================

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

    /* Texto das opções de rádio (Tirar Foto / Subir da Galeria / navegação) */
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

    /* Botões de navegação de página (Catálogo / Histórico), destaque
    para o botão da página ativa */
    .nav-ativo button {
        background: linear-gradient(135deg, #6366F1, #4338CA) !important;
        box-shadow: 0 0 0 1px rgba(129, 140, 248, 0.5) inset !important;
    }

    /* Cartão do mosaico */
    .card-wrapper {
        background-color: #FFFFFF; border-radius: 14px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative; margin-bottom: 0;
    }
    .card-wrapper:hover {
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
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
        loading: lazy;
    }
    .foto-frame:hover { overflow: visible; z-index: 100; }
    .foto-frame:hover img {
        transform: scale(2.2); box-shadow: 0 22px 55px rgba(15, 23, 42, 0.45);
        border-radius: 10px; background-color: #FFFFFF;
    }

    /* Rótulos dos campos na área principal (Filtros de Busca) */
    div[data-testid="stTextInput"] label p,
    div[data-testid="stSelectbox"] label p {
        color: #312E81 !important; font-weight: 700 !important; font-size: 13.5px;
    }

    /* Rótulos do formulário de cadastro na barra lateral. A regra específica
    garante texto branco mesmo com o estilo dos filtros da área principal. */
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] label p,
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13.5px !important;
        font-weight: 800 !important;
        letter-spacing: 0.2px;
    }

    .foto-indisponivel {
        height: 220px; width: 100%; display: flex; align-items: center;
        justify-content: center; text-align: center; padding: 0 16px;
        background-color: #FEF2F2; color: #991B1B; font-size: 13px; font-weight: 600;
        border-radius: 14px 14px 0 0;
    }

    .card-info {
        background-color: #F8FAFC; padding: 14px 16px; border-top: 1px solid #E2E8F0;
        font-size: 13.5px; line-height: 1.7;
    }
    .card-info .linha { display: flex; justify-content: space-between; color: #475569; }
    .card-info .linha span { color: #64748B; }
    .card-info .linha b { color: #1E1B4B; font-weight: 700; }

    /* Linha de ações (editar/excluir) embaixo de cada card */
    .card-acoes {
        display: flex; gap: 8px; padding: 10px 12px 14px 12px;
        background-color: #F8FAFC; border-radius: 0 0 14px 14px;
        border-top: 1px dashed #E2E8F0;
    }
    .card-acoes .stButton button {
        width: 100%; border-radius: 8px; font-weight: 700; font-size: 12.5px;
        padding: 6px 0; border: none;
    }
    .btn-editar button {
        background-color: #EEF2FF !important; color: #3730A3 !important;
        border: 1px solid #C7D2FE !important;
    }
    .btn-editar button:hover { background-color: #E0E7FF !important; }
    .btn-excluir button {
        background-color: #FEF2F2 !important; color: #991B1B !important;
        border: 1px solid #FECACA !important;
    }
    .btn-excluir button:hover { background-color: #FEE2E2 !important; }

    .contador-resultados {
        font-size: 15px; font-weight: 700; color: #312E81; margin-bottom: 16px;
    }

    /* Caixas de edição/exclusão em destaque */
    .caixa-acao {
        border-radius: 14px; padding: 18px 22px; margin-bottom: 22px;
        border: 1px solid; 
    }
    .caixa-editar {
        background-color: #EEF2FF; border-color: #C7D2FE;
    }
    .caixa-editar h4 { color: #312E81; margin: 0 0 4px 0; }
    .caixa-excluir {
        background-color: #FEF2F2; border-color: #FECACA;
    }
    .caixa-excluir h4 { color: #991B1B; margin: 0 0 4px 0; }
    .caixa-acao p { color: #475569; font-size: 13.5px; margin: 0 0 12px 0; }

    /* Tabela / cards de histórico */
    .hist-linha {
        display: grid; grid-template-columns: 150px 110px 100px 1fr 1fr 90px 110px 1.4fr;
        gap: 10px; padding: 10px 14px; font-size: 13px; align-items: center;
        border-bottom: 1px solid #E2E8F0; color: #334155;
    }
    .hist-linha.hist-cabecalho {
        background-color: #1E1B4B; color: #FFFFFF; font-weight: 700;
        border-radius: 10px 10px 0 0; font-size: 12px; text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .hist-tabela {
        background-color: #FFFFFF; border-radius: 10px; overflow: hidden;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 8px rgba(15,23,42,0.05);
    }
    .tag-acao {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        font-size: 11px; font-weight: 700; text-transform: uppercase;
    }
    .tag-criacao { background-color: #DCFCE7; color: #166534; }
    .tag-edicao { background-color: #DBEAFE; color: #1E40AF; }
    .tag-exclusao { background-color: #FEE2E2; color: #991B1B; }

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

# URL pública de leitura da planilha. A aba Historico é acessada pelo nome,
# pois a conexão pública do streamlit_gsheets exige GID numérico para abas
# secundárias e não aceita o texto "Historico" como identificador.
URL_BASE_DADOS = "https://docs.google.com/spreadsheets/d/1C5bL1iEyNdjPJBEPgCTW4ZWIDBSmo8Dj6vOLvunpMmg"

PADRAO_ID_DRIVE = re.compile(r"[-\w]{25,}")

def extrair_id_drive(valor: str):
    m = PADRAO_ID_DRIVE.search(valor)
    return m.group(0) if m else valor

def montar_url_drive(valor: str, tamanho: int = 400) -> str:
    file_id = extrair_id_drive(valor)
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w{tamanho}"

def slug(valor: str) -> str:
    """Deixa o texto seguro para usar em nome de arquivo / id de HTML / key do Streamlit."""
    valor = str(valor or "item")
    return re.sub(r"[^A-Za-z0-9_-]+", "_", valor).strip("_") or "item"

def rolar_para_formulario(elemento_id: str) -> None:
    """Leva a janela até o formulário aberto após clicar em Editar ou Excluir."""
    components.html(
        f"""
        <script>
        const destino = window.parent.document.getElementById({json.dumps(elemento_id)});
        if (destino) {{
            setTimeout(() => destino.scrollIntoView({{behavior: 'smooth', block: 'start'}}), 50);
        }}
        </script>
        """,
        height=0,
    )

def rolar_para_topo() -> None:
    """Leva a visualização ao início do catálogo após trocar de página."""
    components.html(
        """
        <script>
        setTimeout(() => {
            const pagina = window.parent;
            const documento = pagina.document;
            const areaPrincipal = documento.querySelector('[data-testid="stAppViewContainer"]');

            if (areaPrincipal) {
                areaPrincipal.scrollTo({top: 0, behavior: 'smooth'});
            }
            documento.documentElement.scrollTo({top: 0, behavior: 'smooth'});
            documento.body.scrollTo({top: 0, behavior: 'smooth'});
            pagina.scrollTo({top: 0, behavior: 'smooth'});
        }, 150);
        </script>
        """,
        height=0,
    )

def marcar_subida_de_pagina() -> None:
    st.session_state.rolar_para_inicio_catalogo = True

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


@st.cache_data(show_spinner=False, ttl=3600, max_entries=1000)
def baixar_imagem_para_excel(valor):
    """Baixa a foto para inseri-la fisicamente no arquivo Excel."""
    if valor is None or valor == "PENDENTE_UPLOAD_DRIVE":
        return None
    valor = str(valor).strip()
    if not valor:
        return None
    try:
        if valor.startswith("data:image"):
            return base64.b64decode(valor.split(",", 1)[1])
        # A mesma origem usada no mosaico, porém em resolução maior para Excel.
        resposta = requests.get(montar_url_drive(valor, tamanho=1600), timeout=30)
        resposta.raise_for_status()
        if "image" not in resposta.headers.get("Content-Type", ""):
            return None
        return resposta.content
    except Exception:
        return None


def preparar_imagem_excel(conteudo):
    """Garante que a imagem seja aceita pelo Excel (JPEG/PNG/GIF/BMP)."""
    if not conteudo:
        return None
    if conteudo.startswith((b"\xff\xd8\xff", b"\x89PNG", b"GIF87a", b"GIF89a", b"BM")):
        return io.BytesIO(conteudo)
    try:
        # WebP, por exemplo, é convertido para JPEG antes de ser incorporado.
        from PIL import Image
        imagem = Image.open(io.BytesIO(conteudo)).convert("RGB")
        saida = io.BytesIO()
        imagem.save(saida, format="JPEG", quality=88)
        saida.seek(0)
        return saida
    except Exception:
        return None


def criar_excel_modelo(modelo, dados_modelo, imagens):
    """Cria um Excel de um modelo, com uma imagem incorporada por linha."""
    arquivo = io.BytesIO()
    with pd.ExcelWriter(arquivo, engine="xlsxwriter") as escritor:
        workbook = escritor.book
        planilha = workbook.add_worksheet("Itens")
        escritor.sheets["Itens"] = planilha

        estilo_titulo = workbook.add_format({
            "bold": True, "font_size": 16, "font_color": "FFFFFF", "bg_color": "312E81"
        })
        estilo_cabecalho = workbook.add_format({
            "bold": True, "font_color": "FFFFFF", "bg_color": "4338CA", "border": 1
        })
        estilo_texto = workbook.add_format({"valign": "vcenter", "border": 1, "border_color": "E2E8F0"})
        estilo_aviso = workbook.add_format({
            "valign": "vcenter", "border": 1, "border_color": "E2E8F0", "font_color": "991B1B", "italic": True
        })

        planilha.merge_range("A1:E1", f"Catálogo — Modelo: {modelo}", estilo_titulo)
        planilha.set_row(0, 28)
        cabecalhos = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
        for coluna, cabecalho in enumerate(cabecalhos):
            planilha.write(1, coluna, cabecalho, estilo_cabecalho)
        planilha.set_column("A:A", 20)
        planilha.set_column("B:B", 24)
        planilha.set_column("C:C", 16)
        planilha.set_column("D:D", 20)
        planilha.set_column("E:E", 26)
        planilha.freeze_panes(2, 0)
        planilha.autofilter(1, 0, len(dados_modelo) + 1, 4)

        for linha_excel, (indice, item) in enumerate(dados_modelo.iterrows(), start=2):
            planilha.set_row(linha_excel, 96)
            for coluna, campo in enumerate(cabecalhos[:4]):
                valor = item.get(campo, "")
                planilha.write(linha_excel, coluna, "" if pd.isna(valor) else str(valor), estilo_texto)
            foto = preparar_imagem_excel(imagens.get(indice))
            if foto:
                planilha.write_blank(linha_excel, 4, None, estilo_texto)
                planilha.insert_image(linha_excel, 4, "imagem.jpg", {
                    "image_data": foto, "x_scale": 0.23, "y_scale": 0.23,
                    "x_offset": 5, "y_offset": 4, "object_position": 1,
                })
            else:
                planilha.write(linha_excel, 4, "Imagem indisponível", estilo_aviso)
    return arquivo.getvalue()


def criar_zip_excel_por_modelo(dados):
    """Retorna um ZIP com um .xlsx separado para cada modelo do catálogo."""
    imagens = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {
            executor.submit(baixar_imagem_para_excel, item["Imagem"]): indice
            for indice, item in dados.iterrows()
        }
        for futuro in as_completed(futuros):
            imagens[futuros[futuro]] = futuro.result()

    pacote = io.BytesIO()
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as zipado:
        grupos = dados["Modelo"].fillna("SEM MODELO").astype(str).str.strip().replace("", "SEM MODELO")
        nomes_usados = set()
        for modelo, itens in dados.groupby(grupos, sort=True):
            nome = slug(modelo)
            nome_base, contador = nome, 2
            while nome.casefold() in nomes_usados:
                nome = f"{nome_base}_{contador}"
                contador += 1
            nomes_usados.add(nome.casefold())
            zipado.writestr(f"catalogo_{nome}.xlsx", criar_excel_modelo(modelo, itens, imagens))
    return pacote.getvalue()


def criar_excel_catalogo_completo(dados):
    """Cria um único Excel com todos os modelos, mantendo a foto por código."""
    imagens = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {
            executor.submit(baixar_imagem_para_excel, item["Imagem"]): indice
            for indice, item in dados.iterrows()
        }
        for futuro in as_completed(futuros):
            imagens[futuros[futuro]] = futuro.result()
    return criar_excel_modelo("Todos os modelos", dados, imagens)


def enviar_para_backend(payload: dict) -> tuple:
    """Envia qualquer ação (criar/editar/excluir) para o Apps Script.
    Retorna (sucesso: bool, mensagem: str)."""
    if not URL_PLANILHA:
        return False, "URL do sistema (google_script_url) não configurada nos Secrets."
    try:
        resposta = requests.post(
            URL_PLANILHA, data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}, timeout=60
        )
        if resposta.status_code == 200:
            # O Apps Script responde HTTP 200 até para erros de validação.
            # Por isso, também verificamos o JSON devolvido pelo webhook.
            try:
                retorno = resposta.json()
                if retorno.get("ok") is False:
                    return False, retorno.get("mensagem", "O backend recusou a operação.")
            except ValueError:
                # Compatibilidade com versões antigas do Apps Script que não
                # retornavam JSON.
                pass
            return True, "ok"
        return False, f"Erro ao salvar: {resposta.status_code}"
    except Exception as e:
        return False, f"Erro de conexão: {e}"


if "form_counter" not in st.session_state: st.session_state.form_counter = 0
if "pagina_app" not in st.session_state: st.session_state.pagina_app = "catalogo"
if "editando_codigo" not in st.session_state: st.session_state.editando_codigo = None
if "excluindo_codigo" not in st.session_state: st.session_state.excluindo_codigo = None
key_suffix = st.session_state.form_counter

usuario_logado = st.session_state.get('usuario_logado', '')
st.sidebar.markdown(f"👤 Logado como **{usuario_logado}**")
if st.sidebar.button("🚪 Sair", key="btn_logout"):
    st.session_state.autenticado = False
    st.rerun()

st.sidebar.divider()
st.sidebar.header("🧭 Navegação")
col_nav1, col_nav2 = st.sidebar.columns(2)
with col_nav1:
    st.markdown('<div class="%s">' % ("nav-ativo" if st.session_state.pagina_app == "catalogo" else ""), unsafe_allow_html=True)
    if st.button("📦 Catálogo", key="nav_catalogo", use_container_width=True):
        st.session_state.pagina_app = "catalogo"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with col_nav2:
    st.markdown('<div class="%s">' % ("nav-ativo" if st.session_state.pagina_app == "historico" else ""), unsafe_allow_html=True)
    if st.button("🕓 Histórico", key="nav_historico", use_container_width=True):
        st.session_state.pagina_app = "historico"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
st.sidebar.divider()

# A navegação agora fica no conteúdo principal. O pequeno script remove os
# controles antigos da barra lateral em versões já publicadas do app.
components.html(
    """
    <script>
    setTimeout(() => {
        const lateral = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (!lateral) return;

        lateral.querySelectorAll('button').forEach((botao) => {
            const texto = (botao.innerText || '').trim();
            if (texto.includes('Catálogo') || texto.includes('Histórico')) {
                const bloco = botao.closest('[data-testid="stElementContainer"]');
                if (bloco) bloco.remove();
            }
        });

        lateral.querySelectorAll('h1, h2, h3').forEach((titulo) => {
            if ((titulo.innerText || '').trim().includes('Navegação')) {
                const bloco = titulo.closest('[data-testid="stElementContainer"]');
                if (bloco) bloco.remove();
            }
        });

        // Os separadores e o bloco horizontal pertenciam à antiga navegação.
        // Ao removê-los, o formulário de novo item fica logo abaixo do login.
        lateral.querySelectorAll('hr').forEach((linha) => {
            const bloco = linha.closest('[data-testid="stElementContainer"]');
            if (bloco) bloco.remove();
        });
        lateral.querySelectorAll('[data-testid="stHorizontalBlock"]').forEach((blocoHorizontal) => {
            if (!(blocoHorizontal.innerText || '').trim()) {
                const bloco = blocoHorizontal.closest('[data-testid="stElementContainer"]');
                if (bloco) bloco.remove();
            }
        });
    }, 100);
    </script>
    """,
    height=0,
)

with st.container(border=True):
    col_nav_titulo, col_nav1_site, col_nav2_site = st.columns([2.3, 1, 1])
    with col_nav_titulo:
        st.markdown("### 🧭 Navegação")
    with col_nav1_site:
        if st.button(
            "📦 Catálogo",
            key="nav_catalogo_site",
            use_container_width=True,
            type="primary" if st.session_state.pagina_app == "catalogo" else "secondary",
        ):
            st.session_state.pagina_app = "catalogo"
            st.rerun()
    with col_nav2_site:
        if st.button(
            "🕓 Histórico",
            key="nav_historico_site",
            use_container_width=True,
            type="primary" if st.session_state.pagina_app == "historico" else "secondary",
        ):
            st.session_state.pagina_app = "historico"
            st.rerun()

# =============================================================================
# PÁGINA: CATÁLOGO
# =============================================================================
if st.session_state.pagina_app == "catalogo":

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
        input_ambiente = st.sidebar.selectbox("UNIDADE:", ["Externa", "Interna"], key=f"ambiente_{key_suffix}")
        input_codigo = st.sidebar.text_input("CÓDIGO:", key=f"codigo_{key_suffix}").strip().upper()

        if st.sidebar.button("💾 Enviar Direto para o Sistema", key=f"btn_enviar_{key_suffix}"):
            if input_serie and input_modelo and input_codigo and URL_PLANILHA:
                with st.spinner("Enviando foto para o Drive..."):
                    bytes_imagem_envio = foto_com_dados.getvalue()
                    dados_envio = {
                        "acao": "criar",
                        "serie": input_serie,
                        "modelo": input_modelo,
                        "ambiente": input_ambiente,
                        "codigo": input_codigo,
                        "imagem": f"data:image/jpeg;base64,{base64.b64encode(bytes_imagem_envio).decode('utf-8')}",
                        "usuario": usuario_logado,
                    }
                    sucesso, msg = enviar_para_backend(dados_envio)
                    if sucesso:
                        st.sidebar.success("✅ Salvo com sucesso!")
                        st.session_state.form_counter += 1
                        st.rerun()
                    else:
                        st.sidebar.error(f"⚠️ {msg}")
            else:
                st.sidebar.warning("Preencha Série, Modelo e Código antes de enviar.")

    # --- CAIXA DE EDIÇÃO (aparece quando um item foi clicado para editar) ---
    if st.session_state.editando_codigo is not None:
        dados = st.session_state.get("editando_dados", {})
        st.markdown('<div id="formulario-edicao"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="caixa-acao caixa-editar"><h4>✏️ Editando item — Código atual: {st.session_state.editando_codigo}</h4>'
            f'<p>Altere os campos abaixo. Se não escolher uma nova foto, a foto atual é mantida.</p></div>',
            unsafe_allow_html=True
        )
        with st.form("form_editar_item", clear_on_submit=False):
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
            with col_e1:
                edit_serie = st.text_input("Série", value=dados.get("Série", "")).strip().upper()
            with col_e2:
                edit_modelo = st.text_input("Modelo", value=dados.get("Modelo", "")).strip().upper()
            with col_e3:
                ambientes = ["Externa", "Interna"]
                idx_amb = ambientes.index(dados.get("Ambiente")) if dados.get("Ambiente") in ambientes else 0
                edit_ambiente = st.selectbox("Ambiente", ambientes, index=idx_amb)
            with col_e4:
                edit_codigo = st.text_input("Código", value=dados.get("Código", "")).strip().upper()

            edit_nova_foto = st.file_uploader("Nova foto (opcional — deixe em branco para manter a atual)", type=["jpg", "jpeg", "png", "webp"], key="edit_nova_foto")

            col_botoes_e1, col_botoes_e2 = st.columns(2)
            with col_botoes_e1:
                salvar_edicao = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            with col_botoes_e2:
                cancelar_edicao = st.form_submit_button("✖️ Cancelar", use_container_width=True)

        if st.session_state.get("rolar_para_acao") == "editar":
            st.session_state.pop("rolar_para_acao", None)
            rolar_para_formulario("formulario-edicao")

        if cancelar_edicao:
            st.session_state.editando_codigo = None
            st.session_state.editando_dados = None
            st.rerun()

        if salvar_edicao:
            if edit_serie and edit_modelo and edit_codigo:
                payload_edicao = {
                    "acao": "editar",
                    "codigo_original": st.session_state.editando_codigo,
                    "serie": edit_serie,
                    "modelo": edit_modelo,
                    "ambiente": edit_ambiente,
                    "codigo": edit_codigo,
                    "usuario": usuario_logado,
                }
                if edit_nova_foto is not None:
                    payload_edicao["imagem"] = f"data:image/jpeg;base64,{base64.b64encode(edit_nova_foto.getvalue()).decode('utf-8')}"
                sucesso, msg = enviar_para_backend(payload_edicao)
                if sucesso:
                    st.success("✅ Item atualizado com sucesso!")
                    st.session_state.editando_codigo = None
                    st.session_state.editando_dados = None
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"⚠️ {msg}")
            else:
                st.warning("Preencha Série, Modelo e Código antes de salvar.")

    # --- CAIXA DE EXCLUSÃO (aparece quando um item foi clicado para excluir) ---
    if st.session_state.excluindo_codigo is not None:
        dados_exc = st.session_state.get("excluindo_dados", {})
        st.markdown('<div id="formulario-exclusao"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="caixa-acao caixa-excluir"><h4>🗑️ Excluir item — Código: {st.session_state.excluindo_codigo}</h4>'
            f'<p>Série: <b>{dados_exc.get("Série","")}</b> · Modelo: <b>{dados_exc.get("Modelo","")}</b>. '
            f'Essa ação não pode ser desfeita. Informe o motivo da exclusão.</p></div>',
            unsafe_allow_html=True
        )
        with st.form("form_excluir_item", clear_on_submit=False):
            motivo_exclusao = st.text_input("Motivo da exclusão *", placeholder="Ex: item duplicado, foto errada, componente descartado...")
            col_botoes_x1, col_botoes_x2 = st.columns(2)
            with col_botoes_x1:
                confirmar_exclusao = st.form_submit_button("🗑️ Confirmar Exclusão", use_container_width=True)
            with col_botoes_x2:
                cancelar_exclusao = st.form_submit_button("✖️ Cancelar", use_container_width=True)

        if st.session_state.get("rolar_para_acao") == "excluir":
            st.session_state.pop("rolar_para_acao", None)
            rolar_para_formulario("formulario-exclusao")

        if cancelar_exclusao:
            st.session_state.excluindo_codigo = None
            st.session_state.excluindo_dados = None
            st.rerun()

        if confirmar_exclusao:
            if not motivo_exclusao.strip():
                st.warning("⚠️ O motivo da exclusão é obrigatório.")
            else:
                payload_exclusao = {
                    "acao": "excluir",
                    "codigo": st.session_state.excluindo_codigo,
                    "serie": dados_exc.get("Série", ""),
                    "modelo": dados_exc.get("Modelo", ""),
                    "ambiente": dados_exc.get("Ambiente", ""),
                    "motivo": motivo_exclusao.strip(),
                    "usuario": usuario_logado,
                }
                sucesso, msg = enviar_para_backend(payload_exclusao)
                if sucesso:
                    st.success("✅ Item excluído com sucesso!")
                    st.session_state.excluindo_codigo = None
                    st.session_state.excluindo_dados = None
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"⚠️ {msg}")

    with st.container(border=True):
        st.markdown('<h3>🔍 Filtros de Busca</h3>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1: busca_s = st.text_input("Filtrar por Série", placeholder="Ex: CASSETE, INVERTER...").upper()
        with col2: busca_m = st.text_input("Buscar por Modelo", placeholder="Ex: CF100, CB601...").upper()
        with col3: busca_a = st.selectbox("UNIDADE", ["Todos", "Interna", "Externa"])
        with col4: busca_c = st.text_input("Buscar por Código", placeholder="Digitar código...").upper()

    try:
        from streamlit_gsheets import GSheetsConnection

        col_titulo, col_refresh = st.columns([6, 1])
        with col_refresh:
            forcar_refresh = st.button("🔄 Atualizar", use_container_width=True)

        ttl_planilha = "0s" if forcar_refresh else "60s"
        conexao = st.connection("gsheets", type=GSheetsConnection)
        df_dados = conexao.read(ttl=ttl_planilha)
        df_dados.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]
        df_filtrado = df_dados.copy()
        if busca_s: df_filtrado = df_filtrado[df_filtrado['Série'].str.upper().str.contains(busca_s, na=False)]
        if busca_m: df_filtrado = df_filtrado[df_filtrado['Modelo'].str.upper().str.contains(busca_m, na=False)]
        if busca_a != "Todos":
            # Ignora espaços extras e diferenças entre maiúsculas/minúsculas
            # vindas da planilha antes de comparar a unidade selecionada.
            unidade_planilha = df_filtrado['Ambiente'].astype(str).str.strip().str.casefold()
            unidade_filtro = busca_a.strip().casefold()
            df_filtrado = df_filtrado[unidade_planilha == unidade_filtro]
        if busca_c: df_filtrado = df_filtrado[df_filtrado['Código'].astype(str).str.contains(busca_c, na=False)]

        total_itens = len(df_filtrado)

        # ---------------------------------------------------------------------
        # EXPORTAÇÃO: os arquivos incluem os dados e a imagem de cada código.
        # "Tudo" ignora os filtros; "por modelo" cria um Excel independente
        # para cada modelo e reúne todos em um único download ZIP.
        # ---------------------------------------------------------------------
        with st.expander("📥 Exportar catálogo para Excel", expanded=False):
            st.write(
                "As fotos são incorporadas no Excel ao lado de cada código. "
                "Os filtros da tela não alteram estas exportações: elas sempre "
                "consideram todo o catálogo."
            )
            col_exportar_tudo, col_exportar_modelo = st.columns(2)
            with col_exportar_tudo:
                if st.button("📄 Preparar Excel com tudo", key="preparar_excel_tudo", use_container_width=True):
                    with st.spinner("Baixando fotos e montando o Excel completo..."):
                        st.session_state.arquivo_excel_completo = criar_excel_catalogo_completo(df_dados)
                if st.session_state.get("arquivo_excel_completo"):
                    st.download_button(
                        "⬇️ Baixar Excel completo",
                        data=st.session_state.arquivo_excel_completo,
                        file_name=f"catalogo_completo_{datetime.datetime.now():%Y-%m-%d}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="baixar_excel_tudo",
                        use_container_width=True,
                    )
            with col_exportar_modelo:
                if st.button("🗂️ Preparar Excel por modelo", key="preparar_excel_modelo", use_container_width=True):
                    with st.spinner("Baixando fotos e montando os arquivos por modelo..."):
                        st.session_state.arquivos_excel_por_modelo = criar_zip_excel_por_modelo(df_dados)
                if st.session_state.get("arquivos_excel_por_modelo"):
                    st.download_button(
                        "⬇️ Baixar ZIP por modelo",
                        data=st.session_state.arquivos_excel_por_modelo,
                        file_name=f"catalogos_por_modelo_{datetime.datetime.now():%Y-%m-%d}.zip",
                        mime="application/zip",
                        key="baixar_excel_modelo",
                        use_container_width=True,
                    )

        if total_itens > 0:
            ITENS_POR_PAGINA = 20
            total_paginas = max(1, (total_itens - 1) // ITENS_POR_PAGINA + 1)

            if "pagina_atual" not in st.session_state:
                st.session_state.pagina_atual = 1
            if st.session_state.pagina_atual > total_paginas:
                st.session_state.pagina_atual = 1

            st.markdown(
                f'<div class="contador-resultados">📊 {total_itens} item(ns) encontrado(s)</div>',
                unsafe_allow_html=True
            )

            inicio = (st.session_state.pagina_atual - 1) * ITENS_POR_PAGINA
            fim = inicio + ITENS_POR_PAGINA
            df_pagina = df_filtrado.reset_index(drop=True).iloc[inicio:fim]

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

            # Grade em st.columns(4): cada card precisa de botões reais de
            # Editar/Excluir (não dá pra clicar em algo dentro de um bloco
            # HTML puro), então voltamos a usar componentes nativos por
            # item. Como a página já está limitada a 20 itens, o custo
            # continua baixo (20 cards x 2 botões).
            linhas_pagina = list(df_pagina.iterrows())
            for inicio_linha in range(0, len(linhas_pagina), 4):
                colunas = st.columns(4)
                bloco = linhas_pagina[inicio_linha:inicio_linha + 4]
                for coluna, (idx, linha) in zip(colunas, bloco):
                    with coluna:
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

                        card_html = (
                            f'<div class="card-wrapper">{html_foto}<div class="card-info">'
                            f'<div class="linha"><span>Série</span><b>{linha["Série"]}</b></div>'
                            f'<div class="linha"><span>Modelo</span><b>{linha["Modelo"]}</b></div>'
                            f'<div class="linha"><span>Ambiente</span><b>{linha["Ambiente"]}</b></div>'
                            f'<div class="linha"><span>Código</span><b>{linha["Código"]}</b></div>'
                            f'</div></div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

                        chave_item = f"{slug(linha['Código'])}_{idx}"
                        col_btn_editar, col_btn_excluir = st.columns(2)
                        with col_btn_editar:
                            st.markdown('<div class="btn-editar">', unsafe_allow_html=True)
                            if st.button("✏️ Editar", key=f"editar_{chave_item}", use_container_width=True):
                                st.session_state.editando_codigo = linha["Código"]
                                st.session_state.editando_dados = linha.to_dict()
                                st.session_state.excluindo_codigo = None
                                st.session_state.excluindo_dados = None
                                st.session_state.rolar_para_acao = "editar"
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_btn_excluir:
                            st.markdown('<div class="btn-excluir">', unsafe_allow_html=True)
                            if st.button("🗑️ Excluir", key=f"excluir_{chave_item}", use_container_width=True):
                                st.session_state.excluindo_codigo = linha["Código"]
                                st.session_state.excluindo_dados = linha.to_dict()
                                st.session_state.editando_codigo = None
                                st.session_state.editando_dados = None
                                st.session_state.rolar_para_acao = "excluir"
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

            if total_paginas > 1:
                st.divider()
                col_pag_esq, col_pag_meio, col_pag_dir = st.columns([1, 1.2, 1])
                with col_pag_meio:
                    st.number_input(
                        f"Página (1 a {total_paginas})",
                        min_value=1,
                        max_value=total_paginas,
                        step=1,
                        key="pagina_atual",
                        label_visibility="collapsed",
                        on_change=marcar_subida_de_pagina,
                    )
                    st.caption(f"Página {st.session_state.pagina_atual} de {total_paginas}")

                if st.session_state.pop("rolar_para_inicio_catalogo", False):
                    rolar_para_topo()
        else:
            st.info("💡 Nenhum item encontrado.")
    except Exception:
        st.info("💡 Planilha aguardando dados.")

# =============================================================================
# PÁGINA: HISTÓRICO
# =============================================================================
else:
    st.subheader("🕓 Histórico de Ações")
    st.caption("Registro de criações, edições e exclusões realizadas no catálogo.")

    with st.container(border=True):
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            filtro_acao = st.selectbox("Tipo de ação", ["Todas", "Criação", "Edição", "Exclusão"])
        with col_h2:
            filtro_usuario = st.text_input("Filtrar por usuário", placeholder="Ex: joao.silva").strip().lower()
        with col_h3:
            filtro_codigo_h = st.text_input("Filtrar por código", placeholder="Digitar código...").strip().upper()

    try:
        # Para uma conexão pública, streamlit_gsheets espera o GID numérico da
        # aba. Esta URL do Google aceita o nome da aba e evita o HTTP 400 que
        # ocorria ao enviar "Historico" como GID.
        url_historico = (
            f"{URL_BASE_DADOS}/gviz/tq?tqx=out:csv&sheet={quote('Historico')}"
        )
        resposta_historico = requests.get(url_historico, timeout=30)
        resposta_historico.raise_for_status()
        df_historico = pd.read_csv(io.StringIO(resposta_historico.text))

        colunas_esperadas = ["Data/Hora", "Usuário", "Ação", "Série", "Modelo", "Ambiente", "Código", "Motivo"]

        # A conexão pode devolver colunas extras vazias ou pequenas diferenças
        # de espaço no cabeçalho. Mantemos somente as oito colunas do histórico
        # e padronizamos seus nomes sem causar erro de tamanho no DataFrame.
        df_historico = df_historico.iloc[:, :len(colunas_esperadas)].copy()
        df_historico.columns = [str(coluna).strip() for coluna in df_historico.columns]

        if len(df_historico.columns) < len(colunas_esperadas):
            raise ValueError(
                "A aba Historico precisa ter as colunas: "
                + " | ".join(colunas_esperadas)
            )

        df_historico.columns = colunas_esperadas
        df_historico = df_historico.dropna(how="all")

        if filtro_acao != "Todas":
            mapa_acao = {"Criação": "criar", "Edição": "editar", "Exclusão": "excluir"}
            alvo = mapa_acao[filtro_acao]
            df_historico = df_historico[df_historico["Ação"].astype(str).str.lower().str.contains(alvo[:-1], na=False)]
        if filtro_usuario:
            df_historico = df_historico[df_historico["Usuário"].astype(str).str.lower().str.contains(filtro_usuario, na=False)]
        if filtro_codigo_h:
            df_historico = df_historico[df_historico["Código"].astype(str).str.upper().str.contains(filtro_codigo_h, na=False)]

        # mais recente primeiro
        try:
            df_historico = df_historico.iloc[::-1]
        except Exception:
            pass

        if len(df_historico) == 0:
            st.info("💡 Nenhum registro encontrado para esse filtro.")
        else:
            st.markdown(f'<div class="contador-resultados">📊 {len(df_historico)} registro(s)</div>', unsafe_allow_html=True)

            HIST_POR_PAGINA = 30
            total_paginas_h = max(1, (len(df_historico) - 1) // HIST_POR_PAGINA + 1)
            if "pagina_historico" not in st.session_state:
                st.session_state.pagina_historico = 1
            if st.session_state.pagina_historico > total_paginas_h:
                st.session_state.pagina_historico = 1

            if total_paginas_h > 1:
                st.session_state.pagina_historico = st.number_input(
                    f"Página (1 a {total_paginas_h})", min_value=1, max_value=total_paginas_h,
                    value=st.session_state.pagina_historico, step=1
                )

            ini_h = (st.session_state.pagina_historico - 1) * HIST_POR_PAGINA
            fim_h = ini_h + HIST_POR_PAGINA
            df_pagina_h = df_historico.iloc[ini_h:fim_h]

            linhas_html = ['<div class="hist-linha hist-cabecalho">'
                           '<div>Data/Hora</div><div>Usuário</div><div>Ação</div><div>Série</div>'
                           '<div>Modelo</div><div>Ambiente</div><div>Código</div><div>Motivo</div></div>']

            classe_tag = {"criar": "tag-criacao", "editar": "tag-edicao", "excluir": "tag-exclusao"}
            rotulo_tag = {"criar": "Criação", "editar": "Edição", "excluir": "Exclusão"}

            for _, linha_h in df_pagina_h.iterrows():
                acao_bruta = str(linha_h.get("Ação", "")).strip().lower()
                classe = classe_tag.get(acao_bruta, "tag-edicao")
                rotulo = rotulo_tag.get(acao_bruta, linha_h.get("Ação", ""))
                linhas_html.append(
                    '<div class="hist-linha">'
                    f'<div>{linha_h.get("Data/Hora", "")}</div>'
                    f'<div>{linha_h.get("Usuário", "")}</div>'
                    f'<div><span class="tag-acao {classe}">{rotulo}</span></div>'
                    f'<div>{linha_h.get("Série", "")}</div>'
                    f'<div>{linha_h.get("Modelo", "")}</div>'
                    f'<div>{linha_h.get("Ambiente", "")}</div>'
                    f'<div>{linha_h.get("Código", "")}</div>'
                    f'<div>{linha_h.get("Motivo", "") or "—"}</div>'
                    '</div>'
                )

            st.markdown(f'<div class="hist-tabela">{"".join(linhas_html)}</div>', unsafe_allow_html=True)

            if total_paginas_h > 1:
                st.caption(f"Página {st.session_state.pagina_historico} de {total_paginas_h}")

    except Exception as erro:
        st.error("Não foi possível carregar o histórico da planilha.")
        st.caption(f"Detalhe técnico: {type(erro).__name__}: {erro}")
