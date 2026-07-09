import streamlit as st
import pandas as pd
import base64
import json
import requests

# Configuração da página para ocupar a tela inteira (layout wide para mosaico)
st.set_page_config(page_title="Sistema de Catalogação Dinâmico", layout="wide")

# Estilização CSS para manter os dados inline (lado a lado) abaixo da imagem
st.markdown("""
    <style>
    .assinatura { font-size: 13px; font-weight: 800; color: #1E3A8A; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #3B82F6; padding-bottom: 2px; margin-bottom: 15px; }
    .card-info { background-color: #F8FAFC; padding: 12px; border-radius: 0 0 12px 12px; border: 1px solid #E2E8F0; border-top: none; font-size: 13.5px; line-height: 1.6; }
    .card-info div { margin-bottom: 3px; color: #1E293B; }
    /* Força a imagem a preencher a largura do card com altura fixa */
    [data-testid="stImage"] img { border-radius: 12px 12px 0 0; object-fit: cover; height: 230px !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="assinatura">DESENVOLVIDO POR ZELLIC ARAÚJO</div>', unsafe_allow_html=True)
st.title("📦 Sistema de Catalogação e Inventário de Imagens")

# --- CONEXÃO COM O SEU GOOGLE SHEETS VIA SECRET API ---
URL_PLANILHA = ""
# CORREÇÃO: google_script_url fica DENTRO de st.secrets["connections"],
# então a checagem precisa procurar nesse dicionário aninhado, não na raiz.
if "connections" in st.secrets and "google_script_url" in st.secrets["connections"]:
    URL_PLANILHA = st.secrets["connections"]["google_script_url"]

# --- PAINEL LATERAL: CADASTRAR/TIRAR FOTO NA HORA ---
st.sidebar.header("📸 Adicionar Novo Item")
origem = st.sidebar.radio("Selecione o método:", ["Tirar Foto (Celular/PC)", "Subir da Galeria de Fotos"])

foto_com_dados = None
if origem == "Tirar Foto (Celular/PC)":
    foto_com_dados = st.sidebar.camera_input("Aponte a câmera para o componente")
else:
    foto_com_dados = st.sidebar.file_uploader("Escolha a imagem", type=["jpg", "jpeg", "png", "webp"])

if foto_com_dados is not None:
    st.sidebar.subheader("📝 Informações de Registro")

    # Campos ajustados exatamente como você pediu
    input_serie = st.sidebar.text_input("SÉRIE:").strip().upper()
    input_modelo = st.sidebar.text_input("MODELO:").strip().upper()
    input_ambiente = st.sidebar.selectbox("AMBIENTE:", ["Externa", "Interna"])
    input_codigo = st.sidebar.text_input("CÓDIGO:").strip().upper()

    # Debug opcional: mostra se a URL do Apps Script foi carregada corretamente
    if not URL_PLANILHA:
        st.sidebar.error("⚠️ google_script_url não encontrado em st.secrets['connections']. Confira o arquivo secrets.toml no painel do Streamlit Cloud.")

    if st.sidebar.button("💾 Enviar Direto para o Sistema"):
        if input_serie and input_modelo and input_codigo and URL_PLANILHA:
            with st.spinner("Registrando dados..."):
                # Transforma a imagem capturada em texto seguro (Base64) para salvar no Sheets
                bytes_imagem = foto_com_dados.getvalue()
                imagem_base64 = base64.b64encode(bytes_imagem).decode('utf-8')
                string_imagem_final = f"data:image/jpeg;base64,{imagem_base64}"

                # Monta o JSON para enviar para o Apps Script
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
                        st.rerun()
                    else:
                        st.sidebar.error(f"⚠️ Apps Script retornou status {resposta.status_code}: {resposta.text[:300]}")
                except Exception as e:
                    st.sidebar.error(f"Erro ao conectar com a planilha: {e}")
        elif not URL_PLANILHA:
            st.sidebar.warning("⚠️ O sistema está sem conexão configurada com o Google Sheets nos Secrets.")
        else:
            st.sidebar.error("⚠️ Preencha todos os campos antes de salvar.")

# --- FILTROS DE BUSCA INLINE (IGUAL AO SEU LAYOUT HTML) ---
st.subheader("🔍 Filtros de Busca")
col1, col2, col3, col4 = st.columns(4)
with col1: busca_s = st.text_input("Filtrar por Série", placeholder="Ex: CASSETE, INVERTER...").upper()
with col2: busca_m = st.text_input("Buscar por Modelo (Ex: CF100, CB601...)", placeholder="Digitar modelo...").upper()
with col3: busca_a = st.selectbox("Ambiente", ["Todos", "Interna", "Externa"])
with col4: busca_c = st.text_input("Buscar por Código", placeholder="Digitar código...").upper()

# --- REQUISIÇÃO E LEITURA DE DADOS DO GOOGLE SHEETS ---
try:
    from streamlit_gsheets import GSheetsConnection
    conexao_sheets = st.connection("gsheets", type=GSheetsConnection)
    df_dados = conexao_sheets.read(ttl="5s")  # Atualiza a cada 5 segundos para ver novas fotos rápido
except Exception:
    st.info("💡 Pronto para rodar! Adicione os Secrets no painel do Streamlit Cloud para puxar os dados da planilha.")
    st.stop()

if not df_dados.empty:
    df_dados.columns = ["Série", "Modelo", "Ambiente", "Código", "Imagem"]

    # Aplica os filtros digitados pelo usuário na galeria
    df_filtrado = df_dados.copy()
    if busca_s: df_filtrado = df_filtrado[df_filtrado['Série'].str.upper().str.contains(busca_s, na=False)]
    if busca_m: df_filtrado = df_filtrado[df_filtrado['Modelo'].str.upper().str.contains(busca_m, na=False)]
    if busca_a != "Todos": df_filtrado = df_filtrado[df_filtrado['Ambiente'] == busca_a]
    if busca_c: df_filtrado = df_filtrado[df_filtrado['Código'].astype(str).str.contains(busca_c, na=False)]

    # --- RENDERIZAÇÃO DO MOSAICO (Grid de 4 Colunas Responsivo) ---
    if not df_filtrado.empty:
        st.subheader(f"Mosaico de Itens ({len(df_filtrado)} encontrados)")
        colunas_mosaico = st.columns(4)

        for idx, Server_linha in df_filtrado.reset_index().iterrows():
            coluna_da_vez = colunas_mosaico[idx % 4]
            with coluna_da_vez:
                # Mostra a imagem vinda da planilha (Base64)
                st.image(Server_linha['Imagem'])

                # Exibe as informações inline abaixo da foto
                st.markdown(f"""
                    <div class="card-info">
                        <div><b>Série:</b> {Server_linha['Série']}</div>
                        <div><b>Mod:</b> {Server_linha['Modelo']}</div>
                        <div><b>Ambiente:</b> {Server_linha['Ambiente']}</div>
                        <div><b>Cód:</b> {Server_linha['Código']}</div>
                    </div>
                """, unsafe_allow_html=True)

                # Botão nativo para baixar a imagem original caso precise
                try:
                    dados_binarios = base64.b64decode(Server_linha['Imagem'].split(",")[1])
                    st.download_button(
                        label="📥 Baixar Foto",
                        data=dados_binarios,
                        file_name=f"{Server_linha['Série']}_{Server_linha['Modelo']}_{Server_linha['Código']}.jpg",
                        mime="image/jpeg",
                        key=f"btn_dl_{idx}"
                    )
                except Exception:
                    pass
    else:
        st.info("💡 Nenhuma foto corresponde aos filtros aplicados.")
else:
    st.info("💡 A planilha está conectada, mas não possui nenhum registro fotográfico ainda.")
