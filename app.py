import re
import inspect
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import json
import io
import zipfile
import requests
import datetime
import unicodedata
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# ATENÇÃO — BACKEND (Google Apps Script) PRECISA SER ATUALIZADO
# =============================================================================
# Este app agora envia 3 tipos de ação para o webhook (URL_PLANILHA), no
# campo "acao" do JSON:
#
#   "acao": "criar"   -> comportamento que já existia (adiciona uma linha)
#   "acao": "editar"  -> localiza pela combinação "codigo_original" +
#                         "modelo_original", sobrescreve os dados e só troca a
#                         Imagem quando o campo "imagem" vier preenchido
#   "acao": "excluir" -> remove pela combinação Código + Modelo
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
st.set_option("client.toolbarMode", "minimal")

# --- ESTILIZAÇÃO CSS PROFISSIONAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Remove as ações públicas do Streamlit Cloud (Share, editar, GitHub,
    favoritos e menu), preservando o botão que abre a sidebar no celular. */
    [data-testid="stToolbarActions"],
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"],
    [data-testid="stStatusWidget"],
    [data-testid="manage-app-button"],
    #MainMenu,
    [class*="viewerBadge"],
    [class*="ViewerBadge"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    /* Proteção visual usada somente pelo perfil Usuário. Os campos de
    formulário continuam selecionáveis para não atrapalhar a digitação. */
    body.protecao-catalogo-ativa .imagem-protegida {
        user-select: none !important;
        -webkit-user-select: none !important;
        -webkit-user-drag: none !important;
        -webkit-touch-callout: none !important;
    }
    body.protecao-catalogo-captura [data-testid="stAppViewContainer"],
    body.protecao-catalogo-captura section[data-testid="stSidebar"] {
        filter: blur(28px) brightness(0.15) !important;
        transition: none !important;
    }
    @media print {
        body.protecao-catalogo-ativa > * {
            display: none !important;
        }
        body.protecao-catalogo-ativa::after {
            content: "Impressão bloqueada para este perfil.";
            display: block !important;
            padding: 40px;
            color: #111827;
            font-family: Arial, sans-serif;
            font-size: 20px;
        }
    }

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
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
    section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] {
        background-color: #16213A !important; color: #F1F5F9 !important;
        border-radius: 8px !important; border: 1px solid #2A3752 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] *,
    section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] * {
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
    section[data-testid="stSidebar"] .stButton button,
    section[data-testid="stSidebar"] .stButton button * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stButton button:disabled,
    section[data-testid="stSidebar"] .stButton button:disabled * {
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
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
    div[data-testid="stSelectbox"] label p,
    div[data-testid="stMultiSelect"] label p {
        color: #312E81 !important; font-weight: 700 !important; font-size: 13.5px;
    }

    /* Rótulos do formulário de cadastro na barra lateral. A regra específica
    garante texto branco mesmo com o estilo dos filtros da área principal. */
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] label p,
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label p,
    section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] label p {
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

    /* Corrige contraste do expansor e dos botões na barra lateral. A regra
    geral da sidebar usa texto claro; sem estas exceções, ele some sobre
    componentes que o Streamlit desenha com fundo claro. */
    section[data-testid="stSidebar"] details,
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: #16213A !important;
        border: 1px solid #2A3752 !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] details > summary,
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background-color: #16213A !important;
        color: #F8FAFC !important;
    }
    section[data-testid="stSidebar"] details > summary *,
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary * {
        color: #F8FAFC !important;
        -webkit-text-fill-color: #F8FAFC !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] .stButton button:not(:disabled),
    section[data-testid="stSidebar"] .stButton button:not(:disabled) * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] .stButton button:disabled,
    section[data-testid="stSidebar"] .stButton button[disabled] {
        background: #CBD5E1 !important;
        border: 1px solid #94A3B8 !important;
        color: #334155 !important;
        opacity: 1 !important;
        cursor: not-allowed !important;
    }
    section[data-testid="stSidebar"] .stButton button:disabled *,
    section[data-testid="stSidebar"] .stButton button[disabled] *,
    section[data-testid="stSidebar"] .stButton button:disabled p,
    section[data-testid="stSidebar"] .stButton button[disabled] p {
        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;
        opacity: 1 !important;
    }

    /* Botões de envio dos formulários administrativos. O seletor é mais
    específico porque o Streamlit aplica estilos próprios ao botão desativado. */
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button:disabled,
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button[disabled],
    section[data-testid="stSidebar"] div[data-testid="stForm"] button:disabled,
    section[data-testid="stSidebar"] div[data-testid="stForm"] button[disabled] {
        background: #334155 !important;
        background-color: #334155 !important;
        border: 1px solid #475569 !important;
        box-shadow: none !important;
        color: #F8FAFC !important;
        -webkit-text-fill-color: #F8FAFC !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button:disabled *,
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button[disabled] *,
    section[data-testid="stSidebar"] div[data-testid="stForm"] button:disabled *,
    section[data-testid="stSidebar"] div[data-testid="stForm"] button[disabled] * {
        color: #F8FAFC !important;
        -webkit-text-fill-color: #F8FAFC !important;
        opacity: 1 !important;
    }

    /* Regra final e sem classes intermediárias: aplica-se a todos os botões
    desabilitados da lateral, inclusive aos que o Streamlit renderiza dentro
    de componentes próprios. */
    section[data-testid="stSidebar"] button:disabled,
    section[data-testid="stSidebar"] button[disabled] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        border: 1px solid #93A4BF !important;
        color: #172554 !important;
        -webkit-text-fill-color: #172554 !important;
        font-weight: 800 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] button:disabled *,
    section[data-testid="stSidebar"] button[disabled] * {
        color: #172554 !important;
        -webkit-text-fill-color: #172554 !important;
        font-weight: 800 !important;
        opacity: 1 !important;
    }

    /* Botões dos formulários: aparência visível também quando o mouse não
    está sobre eles. O Streamlit não os envolve sempre na classe .stButton. */
    section[data-testid="stSidebar"] div[data-testid="stForm"] button,
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        border: 1px solid #93C5FD !important;
        box-shadow: none !important;
        color: #1D4ED8 !important;
        -webkit-text-fill-color: #1D4ED8 !important;
        font-weight: 800 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stForm"] button *,
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button * {
        color: #1D4ED8 !important;
        -webkit-text-fill-color: #1D4ED8 !important;
        font-weight: 800 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stForm"] button:not(:disabled):hover,
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button:not(:disabled):hover {
        background: #2563EB !important;
        background-color: #2563EB !important;
        border-color: #2563EB !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stForm"] button:not(:disabled):hover *,
    section[data-testid="stSidebar"] div[data-testid="stFormSubmitButton"] button:not(:disabled):hover * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    </style>
""", unsafe_allow_html=True)


# Alguns elementos do cabeçalho são inseridos pelo Streamlit Cloud depois que
# a página já carregou. Este observador remove apenas as ações públicas e não
# toca no botão que expande a sidebar em telas pequenas.
components.html(
    """
    <script>
    (() => {
        const win = window.parent;
        const doc = win.document;

        const ocultarAcoesDoCabecalho = () => {
            const seletores = [
                '[data-testid="stToolbarActions"]',
                '[data-testid="stAppDeployButton"]',
                '[data-testid="stMainMenu"]',
                '[data-testid="stStatusWidget"]',
                '[data-testid="manage-app-button"]',
                '#MainMenu',
                '[class*="viewerBadge"]',
                '[class*="ViewerBadge"]'
            ];

            seletores.forEach(seletor => {
                doc.querySelectorAll(seletor).forEach(elemento => {
                    if (elemento.closest('[data-testid="stExpandSidebarButton"]')) return;
                    elemento.style.setProperty('display', 'none', 'important');
                    elemento.style.setProperty('visibility', 'hidden', 'important');
                    elemento.style.setProperty('pointer-events', 'none', 'important');
                });
            });

            const cabecalho = doc.querySelector('header[data-testid="stHeader"]');
            if (!cabecalho) return;

            cabecalho.querySelectorAll('button, a').forEach(elemento => {
                if (elemento.closest('[data-testid="stExpandSidebarButton"]')) return;
                const identificacao = [
                    elemento.innerText,
                    elemento.getAttribute('aria-label'),
                    elemento.getAttribute('title'),
                    elemento.getAttribute('data-testid')
                ].filter(Boolean).join(' ').toLowerCase();

                if (/(^|\\s)(share|compartilhar|star|favorite|favorito|edit|editar|github|main menu|manage app)(\\s|$)/i.test(identificacao)) {
                    elemento.style.setProperty('display', 'none', 'important');
                    elemento.style.setProperty('visibility', 'hidden', 'important');
                }
            });
        };

        if (win.__catalogoToolbarObserver) {
            win.__catalogoToolbarObserver.disconnect();
        }
        const observer = new win.MutationObserver(ocultarAcoesDoCabecalho);
        observer.observe(doc.documentElement, {childList: true, subtree: true});
        win.__catalogoToolbarObserver = observer;
        ocultarAcoesDoCabecalho();
    })();
    </script>
    """,
    height=0,
)


def configurar_protecao_navegador(bloquear: bool) -> None:
    """Ativa bloqueios de cópia/impressão/salvamento para o perfil Usuário.

    É uma proteção de interface: dificulta as ações comuns do navegador, mas
    nenhum site consegue impedir de forma absoluta uma captura feita pelo
    sistema operacional, por extensões ou pelas ferramentas de desenvolvedor.
    """
    script = """
    <script>
    (() => {
        const win = window.parent;
        const doc = win.document;

        if (win.__protecaoCatalogo) {
            win.__protecaoCatalogo.abort();
            delete win.__protecaoCatalogo;
        }

        doc.body.classList.remove('protecao-catalogo-ativa');
        doc.body.classList.remove('protecao-catalogo-captura');

        const bloquear = __BLOQUEAR__;
        if (!bloquear) return;

        const controller = new win.AbortController();
        const opcoes = {capture: true, signal: controller.signal};
        let temporizadorCaptura = null;

        const elementoEditavel = alvo =>
            alvo instanceof win.Element &&
            Boolean(alvo.closest('input, textarea, select, [contenteditable="true"]'));

        const imagemProtegida = alvo =>
            alvo instanceof win.Element &&
            Boolean(alvo.closest('.imagem-protegida, .foto-protegida'));

        const impedir = evento => {
            evento.preventDefault();
            evento.stopImmediatePropagation();
        };

        const ativarDesfoqueTemporario = () => {
            doc.body.classList.add('protecao-catalogo-captura');
            if (temporizadorCaptura) win.clearTimeout(temporizadorCaptura);
            temporizadorCaptura = win.setTimeout(
                () => doc.body.classList.remove('protecao-catalogo-captura'),
                1800
            );
        };

        doc.body.classList.add('protecao-catalogo-ativa');

        doc.addEventListener('contextmenu', evento => {
            if (!elementoEditavel(evento.target)) impedir(evento);
        }, opcoes);

        doc.addEventListener('dragstart', evento => {
            if (imagemProtegida(evento.target)) impedir(evento);
        }, opcoes);

        doc.addEventListener('selectstart', evento => {
            if (!elementoEditavel(evento.target)) impedir(evento);
        }, opcoes);

        doc.addEventListener('copy', evento => {
            if (!elementoEditavel(evento.target)) impedir(evento);
        }, opcoes);

        doc.addEventListener('cut', evento => {
            if (!elementoEditavel(evento.target)) impedir(evento);
        }, opcoes);

        doc.addEventListener('keydown', evento => {
            const tecla = String(evento.key || '').toLowerCase();
            const atalho = evento.ctrlKey || evento.metaKey;
            const capturaWindows = evento.metaKey && evento.shiftKey && tecla === 's';

            if (tecla === 'printscreen' || capturaWindows) {
                impedir(evento);
                ativarDesfoqueTemporario();
                try {
                    void win.navigator.clipboard?.writeText('').catch(() => {});
                } catch (_) {}
                return;
            }

            const bloquearAtalho =
                atalho && (
                    tecla === 'p' ||
                    tecla === 's' ||
                    ((tecla === 'c' || tecla === 'x') && !elementoEditavel(evento.target))
                );

            if (bloquearAtalho) impedir(evento);
        }, opcoes);

        win.addEventListener('blur', () => {
            doc.body.classList.add('protecao-catalogo-captura');
        }, opcoes);
        win.addEventListener('focus', () => {
            doc.body.classList.remove('protecao-catalogo-captura');
        }, opcoes);
        win.addEventListener('beforeprint', ativarDesfoqueTemporario, opcoes);
        win.addEventListener('afterprint', () => {
            doc.body.classList.remove('protecao-catalogo-captura');
        }, opcoes);

        win.__protecaoCatalogo = controller;
    })();
    </script>
    """.replace("__BLOQUEAR__", json.dumps(bool(bloquear)))
    components.html(script, height=0)

# --- AUTENTICAÇÃO (usuário e senha) ---
URL_PLANILHA = ""
if "connections" in st.secrets and "google_script_url" in st.secrets["connections"]:
    URL_PLANILHA = st.secrets["connections"]["google_script_url"]

USUARIOS_VALIDOS = {}
if "auth" in st.secrets and "usuarios" in st.secrets["auth"]:
    USUARIOS_VALIDOS = dict(st.secrets["auth"]["usuarios"])

USAR_GESTAO_USUARIOS = bool(st.secrets.get("auth", {}).get("gerenciar_usuarios", False))
ADMINISTRADORES = set(st.secrets.get("auth", {}).get("administradores", []))
ENGENHEIROS = set(st.secrets.get("auth", {}).get("engenheiros", []))
CHAVE_ADMIN = st.secrets.get("auth", {}).get("admin_api_key", "")


def autenticar_no_backend(usuario, senha):
    """Autentica no Apps Script quando a gestão dinâmica de contas está ativa."""
    if not URL_PLANILHA:
        return False, "A URL do Apps Script não foi configurada.", None
    try:
        resposta = requests.post(
            URL_PLANILHA,
            data=json.dumps({"acao": "login", "usuario": usuario, "senha": senha}),
            headers={"Content-Type": "application/json"}, timeout=30,
        )
        dados = resposta.json()
        if resposta.status_code == 200 and dados.get("sucesso"):
            return True, "", dados.get("perfil", "usuario")
        return False, dados.get("mensagem", "Usuário ou senha incorretos."), None
    except Exception:
        return False, "Não foi possível validar o acesso no servidor.", None

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    # Garante que uma proteção da sessão anterior não permaneça ativa na tela
    # de login após o logout ou a troca de perfil.
    configurar_protecao_navegador(False)
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
            if USAR_GESTAO_USUARIOS:
                sucesso, mensagem, perfil = autenticar_no_backend(usuario_input.strip(), senha_input)
                if sucesso:
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = usuario_input.strip()
                    st.session_state.perfil_usuario = perfil
                    st.rerun()
                else:
                    st.error(mensagem)
            elif not USUARIOS_VALIDOS:
                st.error("⚠️ Nenhum usuário configurado ainda nos Secrets do Streamlit Cloud.")
            elif usuario_input in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario_input] == senha_input:
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                if usuario_input in ADMINISTRADORES:
                    st.session_state.perfil_usuario = "admin"
                elif usuario_input in ENGENHEIROS:
                    st.session_state.perfil_usuario = "engenharia"
                else:
                    st.session_state.perfil_usuario = "usuario"
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()  # impede que o resto do app (catálogo) seja renderizado


URL_PLANILHA = ""
if "connections" in st.secrets and "google_script_url" in st.secrets["connections"]:
    URL_PLANILHA = st.secrets["connections"]["google_script_url"]

# URL pública de leitura da planilha. A aba Historico é acessada pelo nome,
# pois a conexão pública do streamlit_gsheets exige GID numérico para abas
# secundárias e não aceita o texto "Historico" como identificador.
URL_BASE_DADOS = "https://docs.google.com/spreadsheets/d/1C5bL1iEyNdjPJBEPgCTW4ZWIDBSmo8Dj6vOLvunpMmg"

PADRAO_ID_DRIVE = re.compile(r"[-\w]{25,}")
# Compatibilidade com implantações antigas do Apps Script que ainda validam
# Série, Modelo ou Unidade como obrigatórios. A versão nova do backend converte
# este marcador em vazio, e o Streamlit também o remove de toda exibição.
VALOR_VAZIO_BACKEND_LEGADO = "__CAMPO_OPCIONAL_VAZIO__"
MARCADORES_VAZIOS_BACKEND = ("\u200b", VALOR_VAZIO_BACKEND_LEGADO)

def normalizar_perfil(valor: str) -> str:
    """Padroniza os nomes de perfil recebidos do backend ou dos Secrets."""
    perfil = str(valor or "usuario").strip().casefold()
    aliases = {
        "admin": "admin",
        "administrador": "admin",
        "engenharia": "engenharia",
        "engenheiro": "engenharia",
        "usuario": "usuario",
        "usuário": "usuario",
    }
    return aliases.get(perfil, "usuario")


def limpar_campo_opcional(valor) -> str:
    """Converte valores vazios/NaN e o marcador legado em texto realmente vazio."""
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass
    texto = str(valor)
    for marcador in MARCADORES_VAZIOS_BACKEND:
        texto = texto.replace(marcador, "")
    return texto.strip()


def campo_opcional_para_backend_legado(valor) -> str:
    """Envia um marcador apenas quando o campo opcional está vazio."""
    texto = limpar_campo_opcional(valor)
    return texto if texto else VALOR_VAZIO_BACKEND_LEGADO


def texto_sem_acentos(valor) -> str:
    """Normaliza mensagens do backend para comparar validações antigas."""
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", str(valor or ""))
        if not unicodedata.combining(caractere)
    ).casefold()


@st.cache_data(show_spinner=False, ttl=300)
def carregar_modelos_existentes():
    """Lê somente a coluna Modelo para preencher o cadastro.

    Se a leitura falhar, o campo continua aceitando um modelo digitado.
    """
    try:
        consulta = quote("select B where B is not null")
        url_modelos = f"{URL_BASE_DADOS}/gviz/tq?tqx=out:csv&tq={consulta}"
        resposta = requests.get(url_modelos, timeout=20)
        resposta.raise_for_status()
        dados_modelos = pd.read_csv(io.StringIO(resposta.text))
        if dados_modelos.empty or len(dados_modelos.columns) == 0:
            return []
        modelos = set()
        for valor in dados_modelos.iloc[:, 0].dropna():
            modelo = limpar_campo_opcional(valor).upper()
            if modelo:
                modelos.add(modelo)
        return sorted(modelos, key=str.casefold)
    except Exception:
        return []


def extrair_id_drive(valor: str):
    m = PADRAO_ID_DRIVE.search(valor)
    return m.group(0) if m else valor

def montar_url_drive(valor: str, tamanho: int = 400) -> str:
    file_id = extrair_id_drive(valor)
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w{tamanho}"


def montar_urls_drive_original(valor: str) -> list[str]:
    """Retorna URLs que entregam o arquivo original armazenado no Drive."""
    file_id = quote(extrair_id_drive(valor), safe="")
    return [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}",
    ]


def slug(valor: str) -> str:
    """Deixa o texto seguro para usar em nome de arquivo / id de HTML / key do Streamlit."""
    valor = str(valor or "item")
    return re.sub(r"[^A-Za-z0-9_-]+", "_", valor).strip("_") or "item"

def arquivo_para_data_uri(arquivo) -> str:
    """Converte JPG, PNG ou WebP mantendo o MIME real do arquivo."""
    tipo = str(getattr(arquivo, "type", "") or "image/jpeg").strip().lower()
    if not tipo.startswith("image/"):
        tipo = "image/jpeg"
    conteudo = base64.b64encode(arquivo.getvalue()).decode("utf-8")
    return f"data:{tipo};base64,{conteudo}"

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


@st.cache_data(show_spinner=False, ttl=3600, max_entries=200)
def baixar_imagem_para_excel(valor):
    """Baixa e valida os bytes originais da foto para incorporá-los ao Excel."""
    if valor is None or valor == "PENDENTE_UPLOAD_DRIVE":
        return None
    valor = str(valor).strip()
    if not valor:
        return None

    def imagem_valida(conteudo):
        if not conteudo:
            return False
        try:
            from PIL import Image

            with Image.open(io.BytesIO(conteudo)) as imagem:
                largura, altura = imagem.size
                imagem.verify()
            return largura > 0 and altura > 0
        except Exception:
            return False

    try:
        if valor.startswith("data:image"):
            conteudo = base64.b64decode(valor.split(",", 1)[1], validate=True)
            return conteudo if imagem_valida(conteudo) else None

        # Cada URL é tentada separadamente. Assim, uma falha no primeiro
        # endpoint não impede o uso do segundo endereço de download original.
        for url_original in montar_urls_drive_original(valor):
            try:
                resposta = requests.get(
                    url_original,
                    timeout=60,
                    allow_redirects=True,
                    headers={"Accept": "image/*,application/octet-stream;q=0.9,*/*;q=0.5"},
                )
                resposta.raise_for_status()
            except requests.RequestException:
                continue

            if imagem_valida(resposta.content):
                return resposta.content

        # Último recurso: pede ao Drive a maior prévia disponível, nunca a
        # miniatura de 400 px usada no mosaico da tela.
        file_id = quote(extrair_id_drive(valor), safe="")
        try:
            resposta = requests.get(
                f"https://drive.google.com/thumbnail?id={file_id}&sz=w8192",
                timeout=60,
                allow_redirects=True,
                headers={"Accept": "image/*,*/*;q=0.5"},
            )
            resposta.raise_for_status()
            if imagem_valida(resposta.content):
                return resposta.content
        except requests.RequestException:
            pass

        return None
    except Exception:
        return None


FOTO_EXCEL_CAIXA_PX = 512
FOTO_EXCEL_MARGEM_PX = 6


FORMATOS_NATIVOS_EXCEL = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "BMP": ".bmp",
}


def preparar_imagem_excel(
    conteudo,
    caixa_px: int = FOTO_EXCEL_CAIXA_PX,
    margem_px: int = FOTO_EXCEL_MARGEM_PX,
):
    """Preserva os pixels originais e calcula a maior escala nativa possível.

    JPEG, PNG, GIF e BMP são incorporados com os mesmos bytes recebidos. WebP
    e formatos não nativos são convertidos para PNG sem reduzir as dimensões.
    A imagem é centralizada numa célula grande, sem ampliar além dos pixels
    existentes no arquivo original.
    """
    if not conteudo:
        return None
    try:
        from PIL import Image

        bytes_excel = conteudo
        with Image.open(io.BytesIO(conteudo)) as imagem:
            formato = str(imagem.format or "").upper()
            largura, altura = imagem.size
            dpi = imagem.info.get("dpi", (96, 96))

            try:
                dpi_x = float(dpi[0]) if float(dpi[0]) > 0 else 96.0
                dpi_y = float(dpi[1]) if float(dpi[1]) > 0 else 96.0
            except (TypeError, ValueError, IndexError):
                dpi_x = dpi_y = 96.0

            if formato not in FORMATOS_NATIVOS_EXCEL:
                # PNG é sem perdas e mantém todos os pixels do arquivo recebido.
                convertido = io.BytesIO()
                imagem.convert("RGBA").save(
                    convertido,
                    format="PNG",
                    dpi=(dpi_x, dpi_y),
                )
                bytes_excel = convertido.getvalue()
                formato = "PNG"

        largura_visual = largura * 96.0 / dpi_x
        altura_visual = altura * 96.0 / dpi_y
        escala_para_caber = min(
            caixa_px / max(largura_visual, 1.0),
            caixa_px / max(altura_visual, 1.0),
        )
        # O XlsxWriter/Excel considera 96 DPI na tela. Esta escala permite
        # aproveitar imagens com DPI alto até o limite de seus pixels reais,
        # sem criar pixels artificiais por ampliação.
        escala_pixel_nativo = min(dpi_x / 96.0, dpi_y / 96.0)
        escala = min(escala_para_caber, escala_pixel_nativo)

        largura_renderizada = largura_visual * escala
        altura_renderizada = altura_visual * escala
        x_offset = margem_px + max(0, round((caixa_px - largura_renderizada) / 2))
        y_offset = margem_px + max(0, round((caixa_px - altura_renderizada) / 2))

        fluxo = io.BytesIO(bytes_excel)
        fluxo.seek(0)
        return (
            fluxo,
            FORMATOS_NATIVOS_EXCEL[formato],
            escala,
            x_offset,
            y_offset,
        )
    except Exception:
        return None


def desativar_compressao_imagens_excel(conteudo_xlsx):
    """Marca o XLSX para o Excel não recomprimir as fotos ao salvar.

    O XlsxWriter incorpora JPEG/PNG sem alterar os bytes, mas o padrão do
    formato permite que o Excel comprima as imagens num salvamento posterior.
    Esta rotina ajusta somente a propriedade do workbook e preserva todas as
    mídias já armazenadas no arquivo.
    """
    if not conteudo_xlsx:
        return conteudo_xlsx

    origem = io.BytesIO(conteudo_xlsx)
    destino = io.BytesIO()

    def ajustar_workbook_pr(correspondencia):
        tag = correspondencia.group(0)
        padrao_atributo = re.compile(
            rb"\bautoCompressPictures\s*=\s*([\"'])[^\"']*\1"
        )
        if padrao_atributo.search(tag):
            return padrao_atributo.sub(
                b'autoCompressPictures="0"',
                tag,
                count=1,
            )

        fechamento = b"/>" if tag.endswith(b"/>") else b">"
        return tag[:-len(fechamento)] + b' autoCompressPictures="0"' + fechamento

    with zipfile.ZipFile(origem, "r") as zip_entrada:
        with zipfile.ZipFile(destino, "w", allowZip64=True) as zip_saida:
            zip_saida.comment = zip_entrada.comment
            for informacao in zip_entrada.infolist():
                dados = zip_entrada.read(informacao.filename)
                if informacao.filename == "xl/workbook.xml":
                    dados, alteracoes = re.subn(
                        rb"<workbookPr\b[^>]*>",
                        ajustar_workbook_pr,
                        dados,
                        count=1,
                    )
                    if alteracoes == 0:
                        dados = re.sub(
                            rb"(<workbook\b[^>]*>)",
                            rb'\1<workbookPr autoCompressPictures="0"/>',
                            dados,
                            count=1,
                        )
                zip_saida.writestr(informacao, dados)

    return destino.getvalue()


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
        planilha.set_column_pixels(
            4,
            4,
            FOTO_EXCEL_CAIXA_PX + 2 * FOTO_EXCEL_MARGEM_PX,
        )
        planilha.freeze_panes(2, 0)
        planilha.autofilter(1, 0, len(dados_modelo) + 1, 4)

        for linha_excel, (indice, item) in enumerate(dados_modelo.iterrows(), start=2):
            planilha.set_row_pixels(
                linha_excel,
                FOTO_EXCEL_CAIXA_PX + 2 * FOTO_EXCEL_MARGEM_PX,
            )
            for coluna, campo in enumerate(cabecalhos[:4]):
                valor = item.get(campo, "")
                planilha.write(linha_excel, coluna, "" if pd.isna(valor) else str(valor), estilo_texto)
            foto_preparada = preparar_imagem_excel(imagens.get(indice))
            if foto_preparada:
                foto, extensao, escala, x_offset, y_offset = foto_preparada
                planilha.write_blank(linha_excel, 4, None, estilo_texto)
                planilha.insert_image(
                    linha_excel,
                    4,
                    f"imagem_{linha_excel}{extensao}",
                    {
                        "image_data": foto,
                        "x_scale": escala,
                        "y_scale": escala,
                        "x_offset": x_offset,
                        "y_offset": y_offset,
                        "object_position": 1,
                    },
                )
            else:
                planilha.write(linha_excel, 4, "Imagem indisponível", estilo_aviso)
    return desativar_compressao_imagens_excel(arquivo.getvalue())


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


def criar_excel_de_um_modelo(modelo, dados_modelo):
    """Cria o Excel do modelo selecionado no menu de exportação."""
    imagens = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {
            executor.submit(baixar_imagem_para_excel, item["Imagem"]): indice
            for indice, item in dados_modelo.iterrows()
        }
        for futuro in as_completed(futuros):
            imagens[futuros[futuro]] = futuro.result()
    return criar_excel_modelo(modelo, dados_modelo, imagens)


def extrair_codigos(texto):
    """Aceita códigos separados por linha, espaço, vírgula ou ponto e vírgula."""
    codigos = []
    codigos_vistos = set()
    for codigo in re.split(r"[\s,;]+", texto or ""):
        codigo = codigo.strip().upper()
        if codigo and codigo.casefold() not in codigos_vistos:
            codigos.append(codigo)
            codigos_vistos.add(codigo.casefold())
    return codigos


def criar_excel_por_codigos(codigos, dados):
    """Exporta todos os modelos encontrados para cada código informado.

    Um mesmo código pode aparecer em várias linhas, desde que pertença a
    modelos diferentes. O Excel usa Código, Modelo e Foto para deixar cada
    ocorrência claramente identificada.
    """
    dados = dados.copy()
    dados["_codigo_normalizado"] = (
        dados["Código"].fillna("").astype(str).str.strip().str.upper()
    )
    dados["_modelo_normalizado"] = (
        dados["Modelo"].fillna("").astype(str).str.strip().str.upper()
    )

    # Mantém a ordem digitada e inclui todas as ocorrências do código.
    por_codigo = {}
    for indice, item in dados.iterrows():
        codigo_normalizado = item["_codigo_normalizado"]
        if codigo_normalizado:
            por_codigo.setdefault(codigo_normalizado, []).append((indice, item))

    registros_exportacao = []
    for codigo in codigos:
        encontrados = por_codigo.get(codigo, [])
        if encontrados:
            for indice, item in encontrados:
                registros_exportacao.append((codigo, indice, item))
        else:
            registros_exportacao.append((codigo, None, None))

    imagens = {}
    registros_com_foto = [
        (indice, item)
        for _, indice, item in registros_exportacao
        if item is not None
    ]
    with ThreadPoolExecutor(
        max_workers=min(8, max(1, len(registros_com_foto)))
    ) as executor:
        futuros = {}
        for indice, item in registros_com_foto:
            futuros[
                executor.submit(baixar_imagem_para_excel, item.get("Imagem"))
            ] = indice
        for futuro in as_completed(futuros):
            imagens[futuros[futuro]] = futuro.result()

    arquivo = io.BytesIO()
    with pd.ExcelWriter(
        arquivo,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_formulas": False, "strings_to_urls": False}},
    ) as escritor:
        workbook = escritor.book
        planilha = workbook.add_worksheet("Fotos")
        escritor.sheets["Fotos"] = planilha

        estilo_cabecalho = workbook.add_format({
            "bold": True,
            "font_color": "FFFFFF",
            "bg_color": "4338CA",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })
        estilo_codigo = workbook.add_format({
            "border": 1,
            "border_color": "E2E8F0",
            "valign": "vcenter",
        })
        estilo_foto = workbook.add_format({
            "border": 1,
            "border_color": "E2E8F0",
            "align": "center",
            "valign": "vcenter",
        })
        estilo_aviso = workbook.add_format({
            "border": 1,
            "border_color": "E2E8F0",
            "font_color": "991B1B",
            "italic": True,
            "align": "center",
            "valign": "vcenter",
        })

        planilha.write(0, 0, "Código", estilo_cabecalho)
        planilha.write(0, 1, "Modelo", estilo_cabecalho)
        planilha.write(0, 2, "Foto", estilo_cabecalho)
        planilha.set_row(0, 24)
        planilha.set_column("A:A", 24)
        planilha.set_column("B:B", 28)
        planilha.set_column_pixels(
            2,
            2,
            FOTO_EXCEL_CAIXA_PX + 2 * FOTO_EXCEL_MARGEM_PX,
        )
        planilha.freeze_panes(1, 0)
        planilha.autofilter(0, 0, len(registros_exportacao), 2)

        for linha_excel, (codigo, indice, item) in enumerate(
            registros_exportacao,
            start=1,
        ):
            planilha.set_row_pixels(
                linha_excel,
                FOTO_EXCEL_CAIXA_PX + 2 * FOTO_EXCEL_MARGEM_PX,
            )
            planilha.write_string(linha_excel, 0, codigo, estilo_codigo)

            if item is not None:
                modelo = limpar_campo_opcional(item.get("Modelo", ""))
                planilha.write(
                    linha_excel,
                    1,
                    modelo or "SEM MODELO",
                    estilo_codigo,
                )
                foto_preparada = preparar_imagem_excel(imagens.get(indice))
            else:
                modelo = ""
                planilha.write_blank(linha_excel, 1, None, estilo_codigo)
                foto_preparada = None

            if foto_preparada:
                foto, extensao, escala, x_offset, y_offset = foto_preparada
                planilha.write_blank(linha_excel, 2, None, estilo_foto)
                planilha.insert_image(
                    linha_excel,
                    2,
                    f"{slug(codigo)}_{slug(modelo or 'SEM_MODELO')}{extensao}",
                    {
                        "image_data": foto,
                        "x_scale": escala,
                        "y_scale": escala,
                        "x_offset": x_offset,
                        "y_offset": y_offset,
                        "object_position": 1,
                    },
                )
            elif item is not None:
                planilha.write(
                    linha_excel,
                    2,
                    "Imagem indisponível",
                    estilo_aviso,
                )
            else:
                planilha.write(
                    linha_excel,
                    2,
                    "Código não encontrado",
                    estilo_aviso,
                )

    return desativar_compressao_imagens_excel(arquivo.getvalue())


def _postar_no_backend(payload: dict) -> tuple:
    """Executa uma única requisição ao Apps Script."""
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
            except ValueError:
                # Compatibilidade com versões antigas que devolvem texto puro.
                texto_retorno = resposta.text.strip()
                texto_normalizado = texto_sem_acentos(texto_retorno)
                if any(
                    marcador in texto_normalizado
                    for marcador in ("erro", "falha", "preencha", "obrigatori")
                ):
                    return False, texto_retorno or "O backend recusou a operação."
                return True, "ok"

            if isinstance(retorno, dict):
                status = texto_sem_acentos(retorno.get("status", ""))
                falhou = (
                    retorno.get("ok") is False
                    or retorno.get("sucesso") is False
                    or status in {"erro", "error", "falha"}
                )
                if falhou:
                    return False, retorno.get("mensagem", "O backend recusou a operação.")
            return True, "ok"
        return False, f"Erro ao salvar: {resposta.status_code}"
    except Exception as e:
        return False, f"Erro de conexão: {e}"


def enviar_para_backend(payload: dict) -> tuple:
    """Envia a ação e contorna a validação antiga dos campos opcionais.

    A primeira tentativa sempre envia Série, Modelo e Unidade realmente vazios.
    Se um Apps Script antigo responder que algum desses campos é obrigatório,
    o app refaz uma única vez usando um marcador invisível. Assim Código + Foto
    já funcionam agora, sem exibir conteúdo falso nos cards ou nos arquivos.
    """
    sucesso, mensagem = _postar_no_backend(payload)
    if sucesso:
        return sucesso, mensagem

    acao = str(payload.get("acao", "")).strip().casefold()
    mensagem_normalizada = texto_sem_acentos(mensagem)
    menciona_opcional = any(
        campo in mensagem_normalizada
        for campo in ("serie", "modelo", "ambiente", "unidade")
    )
    parece_validacao = any(
        termo in mensagem_normalizada
        for termo in ("preencha", "obrigatori", "informe", "necessari")
    )

    if acao in {"criar", "editar"} and menciona_opcional and parece_validacao:
        payload_compatibilidade = dict(payload)
        alterou_payload = False
        for campo in ("serie", "modelo", "ambiente"):
            if not limpar_campo_opcional(payload_compatibilidade.get(campo)):
                payload_compatibilidade[campo] = campo_opcional_para_backend_legado("")
                alterou_payload = True

        if alterou_payload:
            return _postar_no_backend(payload_compatibilidade)

    return sucesso, mensagem


if "form_counter" not in st.session_state: st.session_state.form_counter = 0
if "pagina_app" not in st.session_state: st.session_state.pagina_app = "catalogo"
if "editando_codigo" not in st.session_state: st.session_state.editando_codigo = None
if "excluindo_codigo" not in st.session_state: st.session_state.excluindo_codigo = None
key_suffix = st.session_state.form_counter

usuario_logado = st.session_state.get('usuario_logado', '')
perfil_usuario = normalizar_perfil(st.session_state.get("perfil_usuario", "usuario"))

# Perfis: admin administra contas; engenharia pode alterar o catálogo;
# usuario apenas consulta o catálogo e o histórico.
pode_gerenciar_catalogo = perfil_usuario in {"admin", "engenharia"}

# Permissão separada para evitar que uma futura mudança na edição do catálogo
# libere, por engano, exportações ou download de fotos.
pode_baixar_arquivos = perfil_usuario in {"admin", "engenharia"}

# Usuário comum recebe as proteções de interface. Engenharia e Administrador
# mantêm os downloads autorizados e removem eventuais listeners da sessão.
configurar_protecao_navegador(perfil_usuario == "usuario")

if USAR_GESTAO_USUARIOS and perfil_usuario == "admin":
    st.sidebar.divider()
    st.sidebar.subheader("Administracao de usuarios")
    with st.sidebar.expander("Gerenciar contas", expanded=False):
        st.caption("Somente administradores podem criar contas, alterar permissoes ou redefinir senhas.")

        with st.form("form_criar_usuario", clear_on_submit=True):
            novo_usuario = st.text_input("Novo usuario").strip()
            nova_senha = st.text_input("Senha inicial", type="password")
            novo_perfil = st.selectbox(
                "Permissao", ["usuario", "engenharia", "admin"],
                format_func=lambda p: {"admin": "Administrador", "engenharia": "Engenharia", "usuario": "Usuário"}[p],
            )
            criar_usuario = st.form_submit_button("Criar conta", use_container_width=True)
        if criar_usuario:
            if not novo_usuario or not nova_senha:
                st.warning("Informe o nome de usuario e a senha inicial.")
            elif len(nova_senha) < 8:
                st.warning("A senha inicial deve ter pelo menos 8 caracteres.")
            else:
                sucesso, mensagem = enviar_para_backend({"acao": "criar_usuario", "usuario_alvo": novo_usuario, "senha": nova_senha, "perfil": novo_perfil, "administrador": usuario_logado, "chave_admin": CHAVE_ADMIN})
                (st.success if sucesso else st.error)("Conta criada com sucesso." if sucesso else mensagem)

        with st.form("form_alterar_perfil", clear_on_submit=True):
            usuario_perfil = st.text_input("Usuario para alterar permissao").strip()
            perfil_novo = st.selectbox(
                "Nova permissao", ["usuario", "engenharia", "admin"],
                format_func=lambda p: {"admin": "Administrador", "engenharia": "Engenharia", "usuario": "Usuário"}[p],
                key="perfil_novo",
            )
            salvar_perfil = st.form_submit_button("Salvar permissao", use_container_width=True)
        if salvar_perfil:
            if not usuario_perfil:
                st.warning("Informe o usuario que recebera a nova permissao.")
            else:
                sucesso, mensagem = enviar_para_backend({"acao": "alterar_perfil_usuario", "usuario_alvo": usuario_perfil, "perfil": perfil_novo, "administrador": usuario_logado, "chave_admin": CHAVE_ADMIN})
                (st.success if sucesso else st.error)("Permissao atualizada." if sucesso else mensagem)

        with st.form("form_redefinir_senha", clear_on_submit=True):
            usuario_senha = st.text_input("Usuario para redefinir senha").strip()
            senha_redefinida = st.text_input("Nova senha", type="password")
            salvar_senha = st.form_submit_button("Redefinir senha", use_container_width=True)
        if salvar_senha:
            if not usuario_senha or not senha_redefinida:
                st.warning("Informe o usuario e a nova senha.")
            elif len(senha_redefinida) < 8:
                st.warning("A nova senha deve ter pelo menos 8 caracteres.")
            else:
                sucesso, mensagem = enviar_para_backend({"acao": "redefinir_senha_usuario", "usuario_alvo": usuario_senha, "senha": senha_redefinida, "administrador": usuario_logado, "chave_admin": CHAVE_ADMIN})
                (st.success if sucesso else st.error)("Senha redefinida com sucesso." if sucesso else mensagem)
st.sidebar.markdown(f"👤 Logado como **{usuario_logado}**")
if st.sidebar.button("🚪 Sair", key="btn_logout"):
    # Remove também perfil, arquivos Excel gerados e estados administrativos.
    st.session_state.clear()
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

col_espaco, col_nav1_site, col_nav2_site = st.columns([6.2, 1.35, 1.35])
with col_nav1_site:
    if st.button("📦 Catálogo", key="nav_catalogo_site", use_container_width=True,
                 type="primary" if st.session_state.pagina_app == "catalogo" else "secondary"):
        st.session_state.pagina_app = "catalogo"
        st.rerun()
with col_nav2_site:
    if st.button("🕓 Histórico", key="nav_historico_site", use_container_width=True,
                 type="primary" if st.session_state.pagina_app == "historico" else "secondary"):
        st.session_state.pagina_app = "historico"
        st.rerun()

st.markdown('<div class="assinatura">Desenvolvido por Zellic Araújo</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="header-box">
        <h1>📦 Sistema de Catalogação e Inventário de Imagens</h1>
        <p>Registre, organize e consulte fotos de componentes em tempo real</p>
    </div>
""", unsafe_allow_html=True)

# =============================================================================
# PÁGINA: CATÁLOGO
# =============================================================================
if st.session_state.pagina_app == "catalogo":

    if not pode_gerenciar_catalogo:
        st.sidebar.info("👁️ Perfil de consulta: você pode apenas visualizar o catálogo.")

    if pode_gerenciar_catalogo:
        st.sidebar.header("📸 Adicionar Novo Item")
        origem = st.sidebar.radio(
            "Selecione o método:",
            ["Tirar Foto (Celular/PC)", "Subir da Galeria de Fotos"],
            key=f"origem_{key_suffix}",
        )

        foto_com_dados = None
        if origem == "Tirar Foto (Celular/PC)":
            parametros_camera = {"key": f"camera_{key_suffix}"}
            try:
                if "resolution" in inspect.signature(st.camera_input).parameters:
                    parametros_camera["resolution"] = "1080p"
            except (TypeError, ValueError):
                pass
            foto_com_dados = st.sidebar.camera_input(
                "Aponte a câmera para o componente",
                **parametros_camera,
            )
            st.sidebar.caption(
                "⚠️ Se a câmera não aparecer: o navegador precisa da sua permissão. "
                "Clique no ícone de cadeado/câmera na barra de endereço e escolha "
                "'Permitir'. Isso só funciona em endereços com HTTPS (o Streamlit "
                "Cloud já usa HTTPS por padrão)."
            )
        else:
            foto_com_dados = st.sidebar.file_uploader(
                "Escolha a imagem",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"upload_{key_suffix}",
            )

        if foto_com_dados is not None:
            st.sidebar.subheader("📝 Informações de Registro")
            st.sidebar.caption("Campos obrigatórios: Foto e Código.")

            input_serie = st.sidebar.text_input(
                "SÉRIE (opcional):",
                key=f"serie_{key_suffix}",
            ).strip().upper()

            input_modelos_brutos = st.sidebar.multiselect(
                "MODELO(S) (opcional):",
                options=carregar_modelos_existentes(),
                placeholder="Escolha ou digite um ou vários modelos",
                accept_new_options=True,
                key=f"modelo_{key_suffix}",
            )
            input_modelos = []
            modelos_vistos = set()
            for modelo_bruto in input_modelos_brutos:
                modelo_normalizado = str(modelo_bruto or "").strip().upper()
                if (
                    modelo_normalizado
                    and modelo_normalizado.casefold() not in modelos_vistos
                ):
                    input_modelos.append(modelo_normalizado)
                    modelos_vistos.add(modelo_normalizado.casefold())
            st.sidebar.caption(
                "O mesmo Código será cadastrado uma vez para cada modelo selecionado."
            )

            input_ambiente = st.sidebar.selectbox(
                "UNIDADE (opcional):",
                ["Painel", "Interna", "Externa"],
                index=None,
                placeholder="Selecione a unidade",
                key=f"ambiente_{key_suffix}",
            ) or ""

            input_codigo = st.sidebar.text_input(
                "CÓDIGO *:",
                key=f"codigo_{key_suffix}",
            ).strip().upper()

            if st.sidebar.button(
                "💾 Enviar Direto para o Sistema",
                key=f"btn_enviar_{key_suffix}",
                disabled=not bool(input_codigo),
            ):
                if not URL_PLANILHA:
                    st.sidebar.error("⚠️ A URL do sistema não foi configurada.")
                else:
                    with st.spinner("Enviando foto para o Drive..."):
                        modelos_backend = [
                            campo_opcional_para_backend_legado(modelo)
                            for modelo in input_modelos
                        ] or [campo_opcional_para_backend_legado("")]
                        dados_envio = {
                            "acao": "criar",
                            # O marcador garante compatibilidade até com uma
                            # implantação antiga que ainda exige estes campos.
                            "serie": campo_opcional_para_backend_legado(input_serie),
                            "modelo": modelos_backend[0],
                            "modelos": modelos_backend,
                            "ambiente": campo_opcional_para_backend_legado(input_ambiente),
                            "codigo": input_codigo,
                            "imagem": arquivo_para_data_uri(foto_com_dados),
                            "usuario": usuario_logado,
                        }
                        sucesso, msg = enviar_para_backend(dados_envio)
                        if sucesso:
                            quantidade_modelos = max(1, len(input_modelos))
                            st.sidebar.success(
                                f"✅ {quantidade_modelos} registro(s) salvo(s)!"
                            )
                            st.session_state.form_counter += 1
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            mensagem_normalizada = texto_sem_acentos(msg)
                            if "preencha serie" in mensagem_normalizada:
                                st.sidebar.error(
                                    "⚠️ O site está conectado a uma implantação antiga "
                                    "do Google Apps Script."
                                )
                                st.sidebar.caption(
                                    "Publique uma nova versão do backend e confirme que "
                                    "google_script_url aponta para a URL /exec atual."
                                )
                            else:
                                st.sidebar.error(f"⚠️ {msg}")

    # --- CAIXA DE EDIÇÃO (aparece quando um item foi clicado para editar) ---
    if pode_gerenciar_catalogo and st.session_state.editando_codigo is not None:
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
                edit_serie = st.text_input("Série (opcional)", value=dados.get("Série", "")).strip().upper()
            with col_e2:
                edit_modelo = st.text_input("Modelo (opcional)", value=dados.get("Modelo", "")).strip().upper()
            with col_e3:
                ambientes = ["", "Painel", "Interna", "Externa"]
                ambiente_atual = str(dados.get("Ambiente", "") or "").strip()
                idx_amb = ambientes.index(ambiente_atual) if ambiente_atual in ambientes else 0
                edit_ambiente = st.selectbox(
                    "Unidade (opcional)",
                    ambientes,
                    index=idx_amb,
                    format_func=lambda valor: valor or "Não informado",
                )
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
            if edit_codigo:
                payload_edicao = {
                    "acao": "editar",
                    "codigo_original": st.session_state.editando_codigo,
                    "modelo_original": campo_opcional_para_backend_legado(
                        dados.get("Modelo", "")
                    ),
                    "serie": campo_opcional_para_backend_legado(edit_serie),
                    "modelo": campo_opcional_para_backend_legado(edit_modelo),
                    "ambiente": campo_opcional_para_backend_legado(edit_ambiente),
                    "codigo": edit_codigo,
                    "usuario": usuario_logado,
                }
                if edit_nova_foto is not None:
                    payload_edicao["imagem"] = arquivo_para_data_uri(edit_nova_foto)
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
                st.warning("Informe o Código antes de salvar.")

    # --- CAIXA DE EXCLUSÃO (aparece quando um item foi clicado para excluir) ---
    if pode_gerenciar_catalogo and st.session_state.excluindo_codigo is not None:
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
        with col3: busca_a = st.selectbox("UNIDADE", ["Todos", "Painel", "Interna", "Externa"])
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

        # Como Série, Modelo e Unidade agora são opcionais, normalizamos as
        # células vazias para evitar "nan" nos cards e falhas nos filtros.
        df_dados = df_dados.fillna("")
        for coluna_opcional in ["Série", "Modelo", "Ambiente"]:
            df_dados[coluna_opcional] = df_dados[coluna_opcional].map(
                limpar_campo_opcional
            )
        for coluna_texto in ["Código", "Imagem"]:
            df_dados[coluna_texto] = (
                df_dados[coluna_texto].astype(str).str.strip()
            )

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

        # Exportações são renderizadas somente para Engenharia e Administrador.
        # O perfil Usuário não consegue nem preparar o arquivo em memória.
        if pode_baixar_arquivos:
            # -----------------------------------------------------------------
            # EXPORTAÇÃO POR LISTA DE CÓDIGOS: inclui todos os modelos ligados
            # a cada código e mantém a ordem em que os códigos foram informados.
            # -----------------------------------------------------------------
            with st.expander("📸 Exportar fotos por códigos", expanded=True):
                st.write(
                    "Cole 10, 20 ou mais códigos abaixo, separados por linha, espaço, "
                    "vírgula ou ponto e vírgula. O Excel terá Código, Modelo e a "
                    "foto original incorporada. Códigos usados em vários modelos "
                    "aparecerão em várias linhas."
                )
                texto_codigos = st.text_area(
                    "Códigos para exportar",
                    height=170,
                    placeholder="Exemplo:\nCOD001\nCOD002\nCOD003",
                    key="codigos_para_excel",
                )
                codigos_exportacao = extrair_codigos(texto_codigos)
                st.caption(f"{len(codigos_exportacao)} código(s) válido(s) informado(s).")

                if st.button(
                    "📄 Preparar Excel com as fotos",
                    key="preparar_excel_por_codigos",
                    use_container_width=True,
                    disabled=not codigos_exportacao,
                ):
                    with st.spinner(
                        f"Localizando {len(codigos_exportacao)} código(s), baixando as fotos e montando o Excel..."
                    ):
                        st.session_state.arquivo_excel_codigos = criar_excel_por_codigos(
                            codigos_exportacao, df_dados
                        )
                        st.session_state.codigos_excel_gerado = tuple(codigos_exportacao)

                if (
                    st.session_state.get("arquivo_excel_codigos")
                    and st.session_state.get("codigos_excel_gerado") == tuple(codigos_exportacao)
                ):
                    st.download_button(
                        "⬇️ Baixar Excel com código e foto",
                        data=st.session_state.arquivo_excel_codigos,
                        file_name=f"fotos_por_codigos_{datetime.datetime.now():%Y-%m-%d}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="baixar_excel_por_codigos",
                        use_container_width=True,
                    )

            # -----------------------------------------------------------------
            # EXPORTAÇÃO POR MODELO: baixa apenas o modelo escolhido, com dados
            # e foto incorporada ao lado de cada código.
            # -----------------------------------------------------------------
            with st.expander("📥 Exportar catálogo para Excel", expanded=False):
                st.write(
                    "Escolha o modelo desejado. O Excel terá Série, Modelo, Ambiente, "
                    "Código e a foto incorporada em cada linha."
                )
                modelos_normalizados = (
                    df_dados["Modelo"]
                    .fillna("SEM MODELO")
                    .astype(str)
                    .str.strip()
                    .replace("", "SEM MODELO")
                )
                opcoes_modelo = sorted(modelos_normalizados.unique(), key=str.casefold)
                modelo_exportacao = st.selectbox(
                    "Modelo para exportar",
                    opcoes_modelo,
                    key="modelo_para_exportar",
                )
                dados_do_modelo = df_dados[modelos_normalizados == modelo_exportacao]
                st.caption(f"{len(dados_do_modelo)} item(ns) serão incluídos neste Excel.")

                if st.button(
                    "📄 Preparar Excel do modelo",
                    key="preparar_excel_modelo_escolhido",
                    use_container_width=True,
                ):
                    with st.spinner(f"Baixando fotos e montando o Excel de {modelo_exportacao}..."):
                        st.session_state.arquivo_excel_modelo = criar_excel_de_um_modelo(
                            modelo_exportacao,
                            dados_do_modelo,
                        )
                        st.session_state.modelo_excel_gerado = modelo_exportacao

                if (
                    st.session_state.get("arquivo_excel_modelo")
                    and st.session_state.get("modelo_excel_gerado") == modelo_exportacao
                ):
                    st.download_button(
                        "⬇️ Baixar Excel do modelo",
                        data=st.session_state.arquivo_excel_modelo,
                        file_name=f"catalogo_{slug(modelo_exportacao)}_{datetime.datetime.now():%Y-%m-%d}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="baixar_excel_modelo_escolhido",
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
                        nome_arquivo = (
                            f"{slug(linha['Modelo'] or 'SEM_MODELO')}_"
                            f"{slug(linha['Código'])}.jpg"
                        )
                        data_uri = resultados_imagens.get(idx)

                        if data_uri:
                            if pode_baixar_arquivos:
                                html_foto = f'''
                                    <div class="foto-frame">
                                        <a href="{data_uri}" download="{nome_arquivo}" title="Clique para baixar a foto">
                                            <img src="{data_uri}" loading="lazy">
                                        </a>
                                    </div>
                                '''
                            else:
                                html_foto = f'''
                                    <div class="foto-frame foto-protegida"
                                         oncontextmenu="return false;">
                                        <img class="imagem-protegida"
                                             src="{data_uri}" loading="lazy"
                                             draggable="false"
                                             oncontextmenu="return false;"
                                             ondragstart="return false;"
                                             onselectstart="return false;"
                                             style="cursor: default; -webkit-user-drag: none; user-select: none;">
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
                            if st.button(
                                "✏️ Editar", key=f"editar_{chave_item}",
                                use_container_width=True, disabled=not pode_gerenciar_catalogo,
                            ):
                                st.session_state.editando_codigo = linha["Código"]
                                st.session_state.editando_dados = linha.to_dict()
                                st.session_state.excluindo_codigo = None
                                st.session_state.excluindo_dados = None
                                st.session_state.rolar_para_acao = "editar"
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_btn_excluir:
                            st.markdown('<div class="btn-excluir">', unsafe_allow_html=True)
                            if st.button(
                                "🗑️ Excluir", key=f"excluir_{chave_item}",
                                use_container_width=True, disabled=not pode_gerenciar_catalogo,
                            ):
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
        df_historico = df_historico.fillna("")
        for coluna_opcional in ["Série", "Modelo", "Ambiente"]:
            df_historico[coluna_opcional] = df_historico[coluna_opcional].map(
                limpar_campo_opcional
            )

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
