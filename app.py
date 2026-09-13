import streamlit as st
import requests
from Bio import Entrez
from deep_translator import GoogleTranslator

# Configuração do Entrez NCBI
Entrez.email = "fisioterapeuta_app@dominio.com"

# Configuração visual da página
st.set_page_config(
    page_title="PhysioSearch - Evidências & Imagens",
    page_icon="🦴",
    layout="wide"
)

# ---------------------------------------------------------
# FUNÇÕES DE BUSCA E PROCESSAMENTO
# ---------------------------------------------------------

def traduzir_termo(texto_pt):
    """Traduz o relato clínico de PT para EN gratuitamente."""
    try:
        tradutor = GoogleTranslator(source='pt', target='en')
        return tradutor.translate(texto_pt)
    except Exception as e:
        st.error(f"Erro na tradução: {e}")
        return texto_pt

def buscar_pubmed(termo_en, max_results=4):
    """Busca ensaios clínicos e revisões no PubMed."""
    query = (
        f"({termo_en}) AND "
        f"(\"Orthopedics\"[MeSH Terms] OR \"Musculoskeletal Diseases\"[MeSH Terms] OR \"Physical Therapy Modalities\"[MeSH Terms]) AND "
        f"(\"Clinical Trial\"[Publication Type] OR \"Systematic Review\"[Publication Type]) AND "
        f"ffrft[Filter]"  # Apenas texto completo grátis
    )
    
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="pub_date")
        search_results = Entrez.read(handle)
        handle.close()
        
        id_list = search_results["IdList"]
        if not id_list:
            return []

        handle = Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="xml", retmode="xml")
        records = Entrez.read(handle)
        handle.close()

        artigos = []
        for article in records['PubmedArticle']:
            medline = article['MedlineCitation']
            article_data = medline['Article']
            
            titulo = article_data.get('ArticleTitle', 'Sem título')
            abstract_list = article_data.get('Abstract', {}).get('AbstractText', [])
            abstract_text = " ".join(abstract_list) if abstract_list else "Resumo não disponível."
            
            # Traduz o resumo de volta para o Português
            abstract_pt = GoogleTranslator(source='en', target='pt').translate(abstract_text[:1000])

            artigos.append({
                'pmid': str(medline['PMID']),
                'titulo': titulo,
                'resumo_pt': abstract_pt,
                'link': f"https://pubmed.ncbi.nlm.org/{medline['PMID']}/"
            })
        return artigos
    except Exception as e:
        st.error(f"Erro ao acessar PubMed: {e}")
        return []

def buscar_imagens_europe_pmc(termo_en, max_images=6):
    """Busca imagens e figuras de artigos de acesso aberto via Europe PMC API."""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"
    
    # Query buscando termos de exercício/mobilidade com licença Open Access
    query = f"({termo_en}) AND (HAS_FT:y) AND (OPEN_ACCESS:y)"
    
    payload = {
        'query': query,
        'format': 'json',
        'pageSize': '10',
        'resultType': 'core'
    }
    
    imagens = []
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            data = response.json()
            for result in data.get('resultList', {}).get('result', []):
                pmcid = result.get('pmcid')
                title = result.get('title', '')
                
                # Se houver PMCID, buscamos a estrutura de figuras cadastradas
                if pmcid:
                    img_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/"
                    # Adiciona referências visuais de artigos OA
                    imagens.append({
                        'article_title': title,
                        'pmcid': pmcid,
                        'link_artigo': f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
                    })
    except Exception as e:
        st.warning(f"Não foi possível carregar algumas imagens do Europe PMC: {e}")
        
    return imagens

# ---------------------------------------------------------
# INTERFACE GRÁFICA (STREAMLIT)
# ---------------------------------------------------------

st.title("🦴 PhysioSearch - Buscador Clínico")
st.caption("Fisioterapia Ortopédica | Evidências (PubMed) & Imagens Clínicas (Europe PMC)")

# Entrada do caso clínico
caso_pt = st.text_area(
    "Descreva o caso clínico da paciente:",
    value="Paciente com luxação no dedo anelar pós-redução, dor ao dobrar e limitação da amplitude de movimento em flexão da articulação interfalangiana proximal.",
    height=100
)

if st.button("🔎 Buscar Evidências e Imagens", type="primary"):
    with st.spinner("Traduzindo termo, consultando PubMed e filtrando imagens..."):
        # 1. Tradução
        termo_en = traduzir_termo(caso_pt)
        st.info(f"**Termos traduzidos para busca em bases internacionais:** `{termo_en}`")
        
        # Criação de abas para organizar a informação
        tab1, tab2 = st.tabs(["📚 Artigos & Evidências", "🖼️ Figuras & Diagramas Clínicos"])
        
        # ABA 1: ARTIGOS DO PUBMED
        with tab1:
            artigos = buscar_pubmed(termo_en)
            if artigos:
                for art in artigos:
                    with st.expander(f"📌 {art['titulo']}"):
                        st.write(f"**Resumo em Português:** {art['resumo_pt']}")
                        st.markdown(f"[🔗 Abrir artigo completo no PubMed]({art['link']})")
            else:
                st.warning("Nenhum artigo encontrado com os critérios exatos.")

        # ABA 2: IMAGENS E DIAGRAMAS (EUROPE PMC)
        with tab2:
            st.subheader("Imagens & Ilustrações de Artigos Científicos (Open Access)")
            imagens = buscar_imagens_europe_pmc(termo_en)
            
            if imagens:
                for img in imagens:
                    st.markdown(f"📖 **Artigo:** {img['article_title']}")
                    st.markdown(f"[👉 Visualizar Figuras e Texto Completo no PMC]({img['link_artigo']})")
                    st.divider()
            else:
                st.info("Nenhuma imagem com licença aberta encontrada para os termos exatos.")
