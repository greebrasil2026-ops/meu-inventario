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
    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFFFFF !important;
        font-weight: 700; border-radius: 10px; border: none; padding: 10px 0;
        width: 100%; transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF); transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }

    /* Caixa de upload / câmera legível no tema escuro */
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
    section[data-testid="stSidebar"] [data-testid="stCameraInput"] {
        background-color: #1E293B !important;
        border: 1.5px dashed #475569 !important;
        border-radius: 10px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
        color: #F1F5F9 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span {
        color: #94A3B8 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        background-color: #334155 !important; color: #F1F5F9 !important;
        border: 1px solid #475569 !important; border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {
        background-color: #1E293B !important; border-radius: 8px !important;
    }

    /* Cards do mosaico */
    .card-wrapper {
        background-color: #FFFFFF; border-radius: 14px; overflow: hidden;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease; margin-bottom: 18px;
    }
    .card-wrapper:hover {
        transform: translateY(-3px); box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
    }
    .assinatura-topo { padding: 14px 16px 26px 16px; }
    .card-info {
        background-color: #F8FAFC; padding: 14px 16px; border-top: 1px solid #E2E8F0;
        font-size: 13.5px; line-height: 1.7;
    }
    .card-info .linha { display: flex; justify-content: space-between; color: #334155; }
    .card-info .linha b { color: #0F172A; font-weight: 700; }

    [data-testid="stImage"] img {
        border-radius: 0; object-fit: cover; height: 220px !important; width: 100%;
    }

    /* Contador de resultados */
    .contador-resultados {
        font-size: 15px; font-weight: 700; color: #1E293B; margin-bottom: 16px;
    }

    /* Alinhamento dos campos de filtro, mesmo se o rótulo quebrar linha */
    div[data-testid="stHorizontalBlock"] label[data-testid="stWidgetLabel"] p {
        min-height: 32px; display: flex; align-items: flex-end; margin-bottom: 4px;
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


# --- FUNÇÃO AUXILIAR: RESOLVER O VALOR DA COLUNA "IMAGEM" ---
# A coluna "Imagem" pode conter três formatos diferentes, dependendo de como
# o Apps Script foi configurado:
#   1) Uma string base64 completa:  "data:image/jpeg;base64,......"
#   2) Um link do Google Drive:     "https://drive.google.com/file/d/ID/view"
#   3) Apenas o ID do arquivo:      "1PtTtqx7t0WsPHhSzN261sym3c8zz-0xG"
# st.image() só entende o formato (1) ou uma URL direta de imagem, então
# convertemos (2) e (3) em uma URL de thumbnail pública do Drive.
PADRAO_ID_DRIVE = re.compile(r"[-\w]{25,}")

def extrair_id_drive(valor: str):
    """Extrai o ID do arquivo de um link de Drive, ou retorna o próprio
    valor se ele já parecer ser apenas o ID."""
    m = PADRAO_ID_DRIVE.search(valor)
    return m.group(0) if m else valor

def resolver_imagem(valor):
    """Recebe o valor bruto da célula 'Imagem' e devolve algo que o
    st.image() consegue renderizar (data URI ou URL http)."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if not valor:
        return None

    # Caso 1: já é uma imagem em base64
    if valor.startswith("data:image"):
        return valor

    # Caso 2: já é uma URL http(s)
    if valor.startswith("http://") or valor.startswith("https://"):
        if "drive.google.com" in valor:
            file_id = extrair_id_drive(valor)
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
        return valor

    # Caso 3: string "solta" -> tratamos como ID de arquivo do Drive
    file_id = extrair_id_drive(valor)
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"

def baixar_bytes_imagem(valor):
    """Devolve os bytes da imagem para o botão de download,
    seja ela base64 ou hospedada no Drive."""
    valor = str(valor).strip()
    if valor.startswith("data:image"):
        return base64.b64decode(valor.split(",")[1])

    url = resolver_imagem(valor)
    resposta = requests.get(url, timeout=20)
    resposta.raise_for_status()
    return resposta.content


# --- CONTROLE DE LIMPEZA AUTOMÁTICA DO FORMULÁRIO ---
# Um contador é usado para gerar novas "keys" para os widgets sempre que um
# item é enviado com sucesso. Isso força o Streamlit a recriar os campos
# vazios, simulando a limpeza do formulário.
if "form_counter" not in st.session_state:
    st.session_state.form_counter = 0

key_suffix = st.session_state.form_counter

# --- PAINEL LATERAL: CADASTRAR/TIRAR FOTO NA HORA ---
st.sidebar.header("📸 Adicionar Novo Item")
origem = st.sidebar.radio(
    "Selecione o método:",
    ["Tirar Foto (Celular/PC)", "Subir da Galeria de Fotos"],
    key=f"origem_{key_suffix}"
)

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

    if not URL_PLANILHA:
        st.sidebar.error("⚠️ google_script_url não encontrado em st.secrets['connections']. Confira o arquivo secrets.toml no painel do Streamlit Cloud.")

    if st.sidebar.button("💾 Enviar Direto para o Sistema", key=f"btn_enviar_{key_suffix}"):
        if input_serie and input_modelo and input_codigo and URL_PLANILHA:
            with st.spinner("Registrando dados..."):
                bytes_imagem = foto_com_dados.getvalue()
                imagem_base64 = base64.b64encode(bytes_imagem).decode('utf-8')
                string_imagem_final = f"data:image/jpeg;base64,{imagem_base64}"

                dados_envio = {
                    "serie": input_serie,
                    "modelo": input_modelo,
                    "ambiente": input_ambiente,
                    "codigo": input_codigo,
                    "imagem": string_imagem_final
                }

                try:
                    resposta = requests.post(
                        URL_PLANILHA,
                        data=json.dumps(dados_envio),
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    if resposta.status_code == 200:
                        st.sidebar.success("✅ Salvo com sucesso na Planilha!")
                        # Incrementa o contador para gerar novas keys e "limpar" o formulário
                        st.session_state.form_counter += 1
                        st.rerun()
                    else:
                        st.sidebar.error(f"⚠️ Apps Script retornou status {resposta.status_code}: {resposta.text[:300]}")
                except Exception as e:
                    st.sidebar.error(f"Erro ao conectar com a planilha: {e}")
        elif not URL_PLANILHA:
            st.sidebar.warning("⚠️ O sistema está sem conexão configurada com o Google Sheets nos Secrets.")
        else:
            st.sidebar.error("⚠️ Preencha todos os campos antes de salvar.")

# --- FILTROS DE BUSCA INLINE ---
with st.container(border=True):
    st.markdown('<h3>🔍 Filtros de Busca</h3>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1: busca_s = st.text_input("Filtrar por Série", placeholder="Ex: CASSETE, INVERTER...").upper()
    with col2: busca_m = st.text_input("Buscar por Modelo", placeholder="Ex: CF100, CB601...").upper()
    with col3: busca_a = st.selectbox("Ambiente", ["Todos", "Interna", "Externa"])
    with col4: busca_c = st.text_input("Buscar por Código", placeholder="Digitar código...").upper()

# --- REQUISIÇÃO E LEITURA DE DADOS DO GOOGLE SHEETS ---
try:
    from streamlit_gsheets import GSheetsConnection
    conexao_sheets = st.connection("gsheets", type=GSheetsConnection)
    df_dados = conexao_sheets.read(ttl="5s")
except Exception:
    st.info("💡 Pronto para rodar! Adicione os Secrets no painel do Streamlit Cloud para puxar os dados da planilha.")
    st.stop()

if not df_dados.empty:
    df_dados.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]

    df_filtrado = df_dados.copy()
    if busca_s: df_filtrado = df_filtrado[df_filtrado['Série'].str.upper().str.contains(busca_s, na=False)]
    if busca_m: df_filtrado = df_filtrado[df_filtrado['Modelo'].str.upper().str.contains(busca_m, na=False)]
    if busca_a != "Todos": df_filtrado = df_filtrado[df_filtrado['Ambiente'] == busca_a]
    if busca_c: df_filtrado = df_filtrado[df_filtrado['Código'].astype(str).str.contains(busca_c, na=False)]

    if not df_filtrado.empty:
        st.markdown(f'<div class="contador-resultados">Mosaico de Itens · {len(df_filtrado)} encontrados</div>', unsafe_allow_html=True)
        colunas_mosaico = st.columns(4)

        for idx, Server_linha in df_filtrado.reset_index().iterrows():
            coluna_da_vez = colunas_mosaico[idx % 4]
            with coluna_da_vez:
                st.markdown('<div class="card-wrapper">', unsafe_allow_html=True)

                url_imagem = resolver_imagem(Server_linha['Imagem'])
                if url_imagem:
                    try:
                        st.image(url_imagem)
                    except Exception:
                        st.warning("⚠️ Não foi possível carregar esta imagem. Verifique se o arquivo no Drive está compartilhado como 'Qualquer pessoa com o link'.")
                else:
                    st.info("Sem imagem cadastrada.")

                st.markdown(f"""
                    <div class="card-info">
                        <div class="linha"><span>Série</span><b>{Server_linha['Série']}</b></div>
                        <div class="linha"><span>Modelo</span><b>{Server_linha['Modelo']}</b></div>
                        <div class="linha"><span>Ambiente</span><b>{Server_linha['Ambiente']}</b></div>
                        <div class="linha"><span>Código</span><b>{Server_linha['Código']}</b></div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                try:
                    dados_binarios = baixar_bytes_imagem(Server_linha['Imagem'])
                    st.download_button(
                        label="📥 Baixar Foto",
                        data=dados_binarios,
                        file_name=f"{Server_linha['Série']}_{Server_linha['Modelo']}_{Server_linha['Código']}.jpg",
                        mime="image/jpeg",
                        key=f"btn_dl_{idx}",
                        use_container_width=True
                    )
                except Exception:
                    pass
    else:
        st.info("💡 Nenhuma foto corresponde aos filtros aplicados.")
else:
    st.info("💡 A planilha está conectada, mas não possui nenhum registro fotográfico ainda.")
