import streamlit as st
import requests
import time
from Bio import Entrez
from deep_translator import GoogleTranslator

# Configuração de e-mail para Entrez
Entrez.email = "fisioterapeuta_app@dominio.com"

st.set_page_config(
    page_title="PhysioSearch - Multi-Bases & Exercícios Visuais",
    page_icon="🦴",
    layout="wide"
)

# ---------------------------------------------------------
# FUNÇÕES DE TRADUÇÃO E BUSCA
# ---------------------------------------------------------

def traduzir_termo(texto):
    """Traduz do Português para o Inglês com segurança."""
    try:
        time.sleep(0.2)
        tradutor = GoogleTranslator(source='auto', target='en')
        resultado = tradutor.translate(texto)
        return resultado if resultado else texto
    except Exception:
        return texto

@st.cache_data(ttl=3600)
def buscar_multibases(termo_en, base_selecionada, max_results=5):
    """
    Busca direcionada por periódico/base de alta relevância:
    - JOSPT
    - The Lancet
    - Foco PEDro (Ensaios Clínicos / Revisões Sistemáticas)
    - Todas as anteriores
    """
    filtro_journal = ""
    if base_selecionada == "JOSPT":
        filtro_journal = ' AND ("J Orthop Sports Phys Ther"[Journal] OR "Journal of Orthopaedic & Sports Physical Therapy"[Journal])'
    elif base_selecionada == "The Lancet":
        filtro_journal = ' AND ("Lancet"[Journal] OR "Lancet Phys Med Rehabil"[Journal])'
    elif base_selecionada == "Foco PEDro (RCTs & Revisões)":
        filtro_journal = ' AND ("Randomized Controlled Trial"[pt] OR "Controlled Clinical Trial"[pt] OR "Systematic Review"[pt])'
    else:
        # Busca Ampla
        filtro_journal = ' AND ("J Orthop Sports Phys Ther"[Journal] OR "Lancet"[Journal] OR "Phys Ther"[Journal] OR "Randomized Controlled Trial"[pt])'

    query = f"({termo_en}){filtro_journal} AND ffrft[Filter]"

    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="pub_date")
        search_results = Entrez.read(handle)
        handle.close()

        id_list = search_results.get("IdList", [])
        if not id_list:
            return []

        handle = Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="xml", retmode="xml")
        records = Entrez.read(handle)
        handle.close()

        artigos = []
        for article in records.get('PubmedArticle', []):
            medline = article['MedlineCitation']
            article_data = medline['Article']
            
            titulo = article_data.get('ArticleTitle', 'Sem título')
            journal = article_data.get('Journal', {}).get('Title', 'Periódico N/A')
            
            # Busca do PMCID para recuperar imagens do PMC
            pmcid = None
            for article_id in medline.get('ArticleIds', []):
                if article_id.attributes.get('IdType') == 'pmc':
                    pmcid = str(article_id)

            abstract_list = article_data.get('Abstract', {}).get('AbstractText', [])
            abstract_text = " ".join(abstract_list) if abstract_list else "Resumo não disponível."

            artigos.append({
                'pmid': str(medline['PMID']),
                'pmcid': pmcid,
                'titulo': titulo,
                'journal': journal,
                'resumo_en': abstract_text,
                'link_pubmed': f"https://pubmed.ncbi.nlm.org/{medline['PMID']}/"
            })
        return artigos
    except Exception as e:
        st.error(f"Erro ao consultar as bases: {e}")
        return []

@st.cache_data(ttl=3600)
def extrair_imagens_exercicios_europe_pmc(termo_en, max_results=6):
    """
    Busca na API do Europe PMC por artigos de acesso aberto que contêm 
    imagens/figuras de exercícios de reabilitação.
    """
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"
    
    # Correção da sintaxe com aspas simples internas no parâmetro "range of motion"
    query = f"({termo_en}) AND (exercise OR rehabilitation OR 'range of motion') AND (HAS_FT:y) AND (OPEN_ACCESS:y)"
    
    payload = {
        'query': query,
        'format': 'json',
        'pageSize': str(max_results),
        'resultType': 'core'
    }
    
    resultados_imagens = []
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for result in data.get('resultList', {}).get('result', []):
                pmcid = result.get('pmcid')
                title = result.get('title', 'Estudo sem título')
                journal = result.get('journalTitle', 'Periódico N/A')
                
                if pmcid:
                    resultados_imagens.append({
                        'title': title,
                        'journal': journal,
                        'pmcid': pmcid,
                        'link_pmc': f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/#SD1",
                        'link_figuras': f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/table-and-figure/"
                    })
    except Exception:
        pass
        
    return resultados_imagens

# ---------------------------------------------------------
# INTERFACE DO APLICATIVO (STREAMLIT)
# ---------------------------------------------------------

st.title("🦴 PhysioSearch - Multi-Bases & Exercícios Visuais")
st.caption("Pesquisa Integrada: JOSPT | The Lancet | Foco PEDro | PubMed PMC")

col_busca, col_base = st.columns([3, 1])

with col_busca:
    caso_clinico = st.text_area(
        "Descreva o caso clínico ou os exercícios desejados:",
        value="Exercícios de mobilização e flexão para rigidez pós-luxação de dedo",
        height=100
    )

with col_base:
    base_selecionada = st.selectbox(
        "Filtrar Base / Periódico:",
        ["Todas as Bases", "JOSPT", "The Lancet", "Foco PEDro (RCTs & Revisões)"]
    )

if st.button("🔎 Buscar Artigos e Imagens dos Exercícios", type="primary"):
    if not caso_clinico.strip():
        st.warning("Por favor, insira o termo de busca.")
    else:
        with st.spinner("Buscando estudos e extraindo fotos/figuras dos exercícios..."):
            termo_en = traduzir_termo(caso_clinico)
            st.info(f"**Termo traduzido para busca internacional:** `{termo_en}` | **Base selecionada:** {base_selecionada}")

            tab_artigos, tab_exercicios = st.tabs([
                "📚 Artigos (JOSPT / Lancet / PEDro / PubMed)", 
                "📷 Imagens e Fotos dos Exercícios nos Artigos"
            ])

            # TAB 1: ARTIGOS
            with tab_artigos:
                artigos = buscar_multibases(termo_en, base_selecionada)
                if artigos:
                    for art in artigos:
                        with st.expander(f"📖 [{art['journal']}] - {art['titulo']}"):
                            st.write(f"**Resumo:** {art['resumo_en']}")
                            st.markdown(f"[🔗 Ver no PubMed]({art['link_pubmed']})")
                            if art['pmcid']:
                                st.markdown(f"[🖼️ Ver Figuras do Exercício no PMC (PMCID: {art['pmcid']})]({f'https://www.ncbi.nlm.nih.gov/pmc/articles/{art["pmcid"]}/#SD1'})")
                else:
                    st.warning("Nenhum estudo encontrado para essa combinação. Tente selecionar 'Todas as Bases'.")

            # TAB 2: EXERCÍCIOS E IMAGENS
            with tab_exercicios:
                st.subheader("Fotos, Figuras e Protocolos Ilustrados de Exercícios")
                st.write("Abaixo estão os artigos de acesso aberto que contêm fotos das condutas e exercícios de reabilitação:")
                
                exercicios_imgs = extrair_imagens_exercicios_europe_pmc(termo_en)
                
                if exercicios_imgs:
                    for ex in exercicios_imgs:
                        st.markdown(f"### 🏋️ {ex['title']}")
                        st.caption(f"Periódico: {ex['journal']} | PMCID: {ex['pmcid']}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.markdown(f"[📸 **Abrir Galeria de Fotos e Exercícios do Artigo**]({ex['link_figuras']})")
                        with col_btn2:
                            st.markdown(f"[📖 **Ler Artigo Completo com Ilustrações**]({ex['link_pmc']})")
                        
                        st.divider()
                else:
                    st.info("Não foram encontradas imagens com licença livre para este termo específico. Experimente buscar por termos em inglês como `finger range of motion exercises`.")
