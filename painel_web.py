import smtplib
from email.mime.text import MIMEText
import streamlit as st
import streamlit_authenticator as stauth
import sqlite3
import pandas as pd
from fpdf import FPDF
from docx import Document
import io
import requests
from bs4 import BeautifulSoup
import pdfplumber
import openai
import re
import datetime

# --- BANCO DE DADOS: SQLite ---
conn = sqlite3.connect("ambiclean.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS prestadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    servico TEXT,
    contato TEXT
)
""")
conn.commit()

def cadastrar_prestador(nome, servico, contato):
    cursor.execute("INSERT INTO prestadores (nome, servico, contato) VALUES (?, ?, ?)", (nome, servico, contato))
    conn.commit()

def listar_prestadores():
    cursor.execute("SELECT nome, servico, contato FROM prestadores")
    return cursor.fetchall()

# --- AUTENTICAÇÃO ---
names = ['Usuário1', 'Usuário2']
usernames = ['user1', 'user2']
passwords = ['senha1', 'senha2']  # Use hashes em produção!
hashed_passwords = stauth.Hasher(passwords).generate()
authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    'ambiclean_dashboard', 'abcdef', cookie_expiry_days=1)

with st.sidebar:
    st.markdown("# Acesso Restrito")
    name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status is False:
    st.error('Usuário ou senha incorretos')
elif authentication_status is None:
    st.warning('Digite usuário e senha')
elif authentication_status:
    st.set_page_config(page_title="Painel Compliance AmbiClean", layout="wide")
    st.markdown("<h1 style='color:#2E8B57;'>AmbiClean | Plataforma de Gestão de Licitações</h1>", unsafe_allow_html=True)
    st.caption("Powered by Rafael Neves + IA")
    st.success(f"Bem-vindo, {name}!")

    st.markdown("""
        <style>
        .main {background-color: #f7f9fa;}
        .stApp {background-color: #f7f9fa;}
        h1, h2, h3 {color: #2E8B57;}
        .stButton>button {background-color: #2E8B57; color: white; border-radius:8px;}
        .stTextInput>div>input {border-radius:8px;}
        .stTextArea>div>textarea {border-radius:8px;}
        .stSelectbox>div>div>div {border-radius:8px;}
        .stDataFrame {background-color: #fff; border-radius:8px;}
        .stMarkdown {font-size: 1.1em;}
        .stDivider {margin-top: 1em; margin-bottom: 1em;}
        .stTabs [data-baseweb="tab-list"] {background: #eaf5ef; border-radius: 8px;}
        .stTabs [data-baseweb="tab"] {font-size: 1.1em;}
        </style>
    """, unsafe_allow_html=True)

    abas_labels = [
        "🏢 CNPJ/Receita",
        "📄 Análise de Edital IA",
        "⚖️ Advogado Digital",
        "🔍 Busca Prestadores",
        "💼 Investidores & Parcerias",
        "📢 Oportunidades de Licitação",
        "📄 Certidões & Documentos",
        "⚠️ Compliance & Riscos",
        "🤖 Chatbot de Dúvidas",
        "🛒 Marketplace de Prestadores"
    ]
    abas = st.tabs(abas_labels)

    # --------- ABA 1: CNPJ/Receita ---------
    with abas[0]:
        st.markdown("<h2>🔎 Consulta CNPJ na Receita Federal</h2>", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns([2,3])
        with col1:
            cnpj = st.text_input("Digite o CNPJ (somente números)", max_chars=14)
            consultar_btn = st.button("Consultar Receita Federal", use_container_width=True)
        with col2:
            st.markdown("Consulte dados oficiais de qualquer empresa.")
        st.divider()
        if consultar_btn:
            if len(cnpj) != 14 or not cnpj.isdigit():
                st.warning("CNPJ inválido! Digite 14 números.")
            else:
                with st.spinner("Consultando Receita Federal..."):
                    resultado = consultar_cnpj_receita(cnpj)
                    st.markdown(f"<div style='background:#fff;border-radius:8px;padding:1em;margin-top:1em;'>{resultado}</div>", unsafe_allow_html=True)

    # --------- ABA 2: Análise Edital IA -------------
    with abas[1]:
        st.markdown("#### Análise Automática de Edital (IA)")
        st.divider()
        uploaded_edital = st.file_uploader("Faça upload do PDF do Edital", type=["pdf"], key="edital")
        if uploaded_edital and st.button("Analisar Edital IA"):
            with st.spinner("Extraindo texto e analisando com IA..."):
                texto = extrair_texto_pdf(uploaded_edital)
                prompt = (
                    "Você é uma IA especialista em licitações públicas, análise de editais e identificação de riscos para pequenas empresas. "
                    "Com base no edital abaixo, responda em tópicos claros, objetivos e detalhados:\n"
                    "..."
                    "\nEDITAL:\n"
                    + texto[:6000]
                )
                resposta = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    temperature=0.3,
                )
                st.markdown(f"**Resultado da Análise:**\n\n{resposta.choices[0].message.content}", unsafe_allow_html=True)

    # --------- ABA 3: ADVOGADO DIGITAL (DEFESA IA) -------------
    with abas[2]:
        st.markdown("#### Advogado Digital (Defesa Administrativa IA)")
        st.divider()
        if "defesa_gerada" not in st.session_state:
            st.session_state["defesa_gerada"] = ""
        uploaded_oficio = st.file_uploader("Faça upload do PDF do Ofício/Notificação", type=["pdf"], key="oficio")
        contexto = st.text_area("Explique o contexto do caso (quanto mais detalhes, melhor a defesa)", height=150)
        uploaded_provas = st.file_uploader(
            "Anexe provas, prints, e-mails ou outros documentos de suporte (opcional)",
            type=["pdf", "jpg", "jpeg", "png", "docx", "doc"],
            key="provas",
            accept_multiple_files=True
        )
        provas_texto = ""
        if uploaded_provas:
            for arquivo in uploaded_provas:
                if arquivo.type == "application/pdf":
                    provas_texto += f"\n---\n[PDF: {arquivo.name}] (documento em anexo)"
                elif arquivo.type in ["image/png", "image/jpeg"]:
                    provas_texto += f"\n---\n[Imagem: {arquivo.name}] (print/foto em anexo)"
                elif arquivo.type in [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword"
                ]:
                    provas_texto += f"\n---\n[Documento Word: {arquivo.name}] (documento em anexo)"
            provas_prompt = (
                "\nAbaixo estão as provas/documentos enviados pelo cliente. Utilize essas informações para reforçar a defesa. "
                "Se for relevante, cite 'conforme print/documento/anexo em anexo' no texto da defesa.\n"
                f"{provas_texto}\n"
            )
        else:
            provas_prompt = ""
        if uploaded_oficio and st.button("Gerar Defesa Jurídica IA"):
            with st.spinner("Lendo documento e elaborando defesa jurídica com IA..."):
                texto = extrair_texto_pdf(uploaded_oficio)
                prompt = (
                    "Aja como um ADVOGADO EXPERIENTE, ...\n"
                    "CONTEXTO:\n"
                    f"{contexto}\n\n"
                    "OFÍCIO/NOTIFICAÇÃO:\n"
                    f"{texto[:6000]}\n"
                    f"{provas_prompt}"
                )
                resposta = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1200,
                    temperature=0.25,
                )
                st.session_state["defesa_gerada"] = resposta.choices[0].message.content
        if st.session_state["defesa_gerada"]:
            st.markdown(f"**Defesa Gerada:**\n\n{st.session_state['defesa_gerada']}", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Exportar Defesa em PDF", key="exportar_pdf_defesa"):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    for linha in st.session_state['defesa_gerada'].split('\n'):
                        pdf.multi_cell(0, 10, linha.encode('latin-1', 'replace').decode('latin-1'))
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_bytes,
                        file_name="defesa_IA.pdf",
                        mime="application/pdf"
                    )
            with col2:
                if st.button("Exportar Defesa em Word (.docx)", key="exportar_word_defesa"):
                    doc = Document()
                    for linha in st.session_state['defesa_gerada'].split('\n'):
                        doc.add_paragraph(linha)
                    docx_output = io.BytesIO()
                    doc.save(docx_output)
                    st.download_button(
                        "Baixar Word",
                        data=docx_output.getvalue(),
                        file_name="defesa_IA.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
        else:
            st.info("Gere a defesa para habilitar a exportação para PDF ou Word.")

    # --------- ABA 4: BUSCA PRESTADORES -------------
    with abas[3]:
        st.markdown("#### 🔍 Buscar Prestadores de Serviço/Empresas (com IA)")
        termo = st.text_input("Qual serviço/atividade está buscando? (ex: limpeza de sofá, eletricista)", key="termo_ia")
        cidade = st.text_input("Cidade", key="cidade_ia")
        estado = st.text_input("Estado (sigla, ex: MA)", max_chars=2, key="estado_ia")
        resultados = []
        if st.button("Buscar com IA"):
            if not (termo and cidade and estado):
                st.warning("Preencha todos os campos!")
            elif not GOOGLE_API_KEY:
                st.error("API Key do Google não configurada.")
            else:
                with st.spinner("Aprimorando busca com IA..."):
                    termo_otimizado = aprimorar_termo_busca_ia(termo, cidade, estado)
                    st.info(f"🔎 Buscando: **{termo_otimizado}** em {cidade} - {estado}")
                with st.spinner("Buscando prestadores via Google..."):
                    resultados = buscar_prestadores_google(termo_otimizado, cidade, estado, GOOGLE_API_KEY)
                if resultados:
                    st.dataframe(resultados)
                    st.divider()
                    st.write("💡 **Sugestão Inteligente da IA sobre os resultados:**")
                    st.caption("Essa busca é turbinada por IA. Resultados mais precisos, menos dor de cabeça!")
                    sugestao_ia = analisar_prestadores_ia(str(resultados))
                    st.success(sugestao_ia)
                else:
                    st.warning("Nenhum resultado encontrado.")

    # --------- ABA 5: INVESTIDORES & PARCERIAS -------------
    with abas[4]:
        st.markdown("#### Buscar Empresas/Investidores para Parcerias e Enviar Apresentação")
        termo_inv = st.text_input("Segmento/Tipo de empresa (ex: investidor, venture capital, startup)", key="termo_inv")
        cidade_inv = st.text_input("Cidade", key="cidade_inv")
        estado_inv = st.text_input("Estado (sigla, ex: SP)", max_chars=2, key="estado_inv")
        aprimorar = st.checkbox("Aprimorar termo de busca com IA", value=True)
        assunto_email = st.text_input("Assunto do e-mail", value="Apresentação AmbiClean", key="assunto_inv")
        mensagem_email = st.text_area("Mensagem de apresentação", value="Olá! Gostaríamos de apresentar a AmbiClean, plataforma inovadora para gestão de licitações...", key="msg_inv")
        smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com", key="smtp_inv")
        smtp_port = st.number_input("SMTP Port", value=587, key="port_inv")
        usuario = st.text_input("Seu e-mail (remetente)", key="user_inv")
        senha = st.text_input("Senha do e-mail", type="password", key="pass_inv")

        # Use session_state para guardar empresas encontradas
        if "empresas_encontradas" not in st.session_state:
            st.session_state["empresas_encontradas"] = []

        if st.button("Buscar empresas/investidores"):
            if not (termo_inv and cidade_inv and estado_inv):
                st.warning("Preencha todos os campos!")
            else:
                if aprimorar:
                    with st.spinner("Aprimorando termo de busca com IA..."):
                        termo_otimizado = aprimorar_termo_busca_ia(termo_inv, cidade_inv, estado_inv)
                        st.info(f"🔎 Termo otimizado pela IA: **{termo_otimizado}**")
                else:
                    termo_otimizado = termo_inv
                with st.spinner("Buscando empresas/investidores e extraindo e-mails..."):
                    empresas = buscar_empresas_com_email(termo_otimizado, cidade_inv, estado_inv, GOOGLE_API_KEY)
                st.session_state["empresas_encontradas"] = empresas
                if empresas:
                    st.dataframe(empresas)
                    st.success(f"{len(empresas)} empresas/investidores com e-mail encontrados.")
                else:
                    st.warning("Nenhuma empresa/investidor com e-mail encontrado.")

        # Só habilita o botão de envio se houver empresas encontradas
        if st.session_state["empresas_encontradas"]:
            if st.button("Enviar apresentação para todos"):
                with st.spinner("Enviando e-mails..."):
                    erros = []
                    for empresa in st.session_state["empresas_encontradas"]:
                        email = empresa.get("Email")
                        if email:
                            try:
                                enviar_email(email, assunto_email, mensagem_email, smtp_server, smtp_port, usuario, senha)
                            except Exception as e:
                                erros.append(f"{empresa['Nome']}: {str(e)}")
                    if not erros:
                        st.success("Apresentação enviada para todos os e-mails encontrados!")
                    else:
                        st.error(f"Alguns e-mails não foram enviados:\n" + "\n".join(erros))
        else:
            st.info("Busque empresas/investidores antes de enviar os e-mails.")

    # --------- ABA 6: Oportunidades de Licitação -------------
    with abas[5]:
        st.markdown("<h2 style='color:#2E8B57;'>📢 Oportunidades de Licitação no Brasil</h2>", unsafe_allow_html=True)
        st.markdown("Busque editais de licitação por estado e palavra-chave.")
        estados = [
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
            "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
        ]
        col1, col2 = st.columns([2, 3])
        with col1:
            estado_selecionado = st.selectbox("Selecione o Estado", estados, index=24)
            filtro = st.text_input("🔎 Palavra-chave", key="filtro_licitacao")
            buscar_btn = st.button("Buscar Licitações", use_container_width=True)
        with col2:
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            st.markdown("Selecione o estado e digite uma palavra-chave para buscar oportunidades.")

        st.markdown("---")

        if buscar_btn:
            with st.spinner("Buscando oportunidades reais no Comprasnet..."):
                resultados = buscar_licitacoes_comprasnet(estado_selecionado, filtro)
            st.markdown(f"### Resultados para **{estado_selecionado}**")
            st.dataframe(resultados, use_container_width=True)

        st.markdown("---")
        st.info("Para ampliar, integre scraping de outros portais estaduais e nacionais.")

    # --------- ABA 7: Certidões & Documentos -------------
    with abas[6]:
        st.markdown("### Gestão de Certidões")
        certidao = st.file_uploader("Envie sua certidão", type=["pdf"], key="certidao_upload")
        data_venc = st.date_input("Data de vencimento", key="certidao_venc")
        if certidao and data_venc:
            dias = (data_venc - datetime.date.today()).days
            st.success(f"Certidão enviada! Faltam {dias} dias para o vencimento.")
            if dias < 30:
                st.warning("Atenção: sua certidão está próxima do vencimento!")

    # --------- ABA 8: Compliance & Riscos -------------
    with abas[7]:
        st.markdown("### Checklist de Compliance")
        checklist = [
            "CND Federal em dia",
            "CND Estadual em dia",
            "FGTS regular",
            "Certidão Trabalhista OK"
        ]
        respostas = []
        for item in checklist:
            respostas.append(st.checkbox(item, key=item))
        if st.button("Verificar Riscos"):
            if all(respostas):
                st.success("Checklist concluído! Nenhum risco identificado.")
            else:
                st.warning("Atenção: Existem pendências de compliance!")

    # --------- ABA 9: Chatbot de Dúvidas IA -------------
    with abas[8]:
        st.markdown("### Chatbot de Dúvidas sobre Licitação")
        pergunta = st.text_input("Digite sua dúvida sobre licitação", key="chatbot_pergunta")
        if st.button("Perguntar à IA"):
            if pergunta:
                resposta = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": pergunta}],
                    max_tokens=300,
                    temperature=0.3,
                )
                st.markdown(resposta.choices[0].message.content)
            else:
                st.info("Digite uma dúvida para perguntar à IA.")

    # --------- ABA 10: Marketplace de Prestadores -------------
    with abas[9]:
        st.markdown("<h2>🛒 Marketplace de Prestadores</h2>", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns([2,3])
        with col1:
            nome = st.text_input("Nome do prestador", key="mp_nome")
            servico = st.text_input("Serviço oferecido", key="mp_servico")
            contato = st.text_input("Contato", key="mp_contato")
            cadastrar_btn = st.button("Cadastrar Prestador", use_container_width=True)
        with col2:
            st.markdown("Cadastre empresas ou profissionais para serem encontrados por quem busca serviços.")
        st.divider()
        if cadastrar_btn:
            if nome and servico and contato:
                cadastrar_prestador(nome, servico, contato)
                st.success("Prestador cadastrado!")
            else:
                st.warning("Preencha todos os campos para cadastrar.")
        st.markdown("#### Prestadores cadastrados")
        prestadores = listar_prestadores()
        if prestadores:
            df_prestadores = pd.DataFrame(prestadores, columns=["Nome", "Serviço", "Contato"])
            st.dataframe(df_prestadores, use_container_width=True)
        else:
            st.info("Nenhum prestador cadastrado ainda.")

    # --------- ABA 11: LOGIN -----------
    with st.sidebar:
        st.markdown("# Acesso Restrito")
        st.markdown("Área destinada a usuários autenticados.")

    st.write("---")
    st.caption("AmbiClean • Dashboard desenvolvido por Rafael Neves com IA")