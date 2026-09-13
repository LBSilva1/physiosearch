import streamlit as st
import requests
import time
from Bio import Entrez
from deep_translator import GoogleTranslator

# Configuração de e-mail exigida pelo NCBI Entrez
Entrez.email = "fisioterapeuta_app@dominio.com"

st.set_page_config(
    page_title="PhysioSearch - Evidências & Exercícios Visuais",
    page_icon="🦴",
    layout="wide"
)

# ---------------------------------------------------------
# FUNÇÕES DE PROCESSAMENTO, TRADUÇÃO E BUSCA VISUAL
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

def buscar_imagem_exercicio_web(nome_exercicio):
    """
    Busca imagens e esquemas visuais na web (Wikimedia Commons API)
    para o exercício específico extraído da conduta positiva do artigo.
    """
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{nome_exercicio} exercise physical therapy",
        "gsrlimit": 2,
        "prop": "pageimages|info",
        "pithumbsize": 400,
        "format": "json"
    }
    imagens = []
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            pages = response.json().get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if "thumbnail" in page_data:
                    imagens.append(page_data["thumbnail"]["source"])
    except Exception:
        pass
    return imagens

@st.cache_data(ttl=3600)
def buscar_estudos_alta_qualidade(termo_en, base_selecionada, max_results=4):
    """
    Filtra estritamente por Ensaios Clínicos Randomizados e Revisões Sistemáticas
    nas fontes selecionadas (JOSPT, Lancet, PEDro/PubMed).
    """
    filtro_journal = ""
    if base_selecionada == "JOSPT":
        filtro_journal = ' AND ("J Orthop Sports Phys Ther"[Journal] OR "Journal of Orthopaedic & Sports Physical Therapy"[Journal])'
    elif base_selecionada == "The Lancet":
        filtro_journal = ' AND ("Lancet"[Journal] OR "Lancet Phys Med Rehabil"[Journal])'
    elif base_selecionada == "Foco PEDro (RCTs & Revisões)":
        filtro_journal = ' AND ("Randomized Controlled Trial"[pt] OR "Controlled Clinical Trial"[pt] OR "Systematic Review"[pt])'
    else:
        filtro_journal = ' AND ("J Orthop Sports Phys Ther"[Journal] OR "Lancet"[Journal] OR "Randomized Controlled Trial"[pt] OR "Systematic Review"[pt])'

    # Exige alta evidência + foco em exercício/reabilitação
    query = f"({termo_en}) AND (exercise OR rehabilitation OR 'physical therapy') {filtro_journal} AND ffrft[Filter]"

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
        st.error(f"Erro ao consultar bases de dados: {e}")
        return []

# ---------------------------------------------------------
# INTERFACE DO APLICATIVO (STREAMLIT)
# ---------------------------------------------------------

st.title("🦴 PhysioSearch - Mapeador Visual de Condutas Positivas")
st.caption("Fisioterapia Baseada em Evidências | JOSPT • Lancet • PEDro • PubMed")

col_busca, col_base = st.columns([3, 1])

with col_busca:
    caso_clinico = st.text_input(
        "Digite a dor ou condição clínica para buscar as condutas eficazes:",
        value="dor no joelho",
        help="Ex: dor no joelho, osteoartrite de quadril, rigidez em flexão de dedo"
    )

with col_base:
    base_selecionada = st.selectbox(
        "Base de Qualidade:",
        ["Todas as Bases (Alta Evidência)", "JOSPT", "The Lancet", "Foco PEDro (RCTs & Revisões)"]
    )

if st.button("🔎 Extrair Estudos e Mapear Exercícios Efetivos", type="primary"):
    if not caso_clinico.strip():
        st.warning("Insira uma busca para continuar.")
    else:
        with st.spinner("Buscando estudos de alta qualidade e mapeando imagens dos exercícios..."):
            termo_en = traduzir_termo(caso_clinico)
            st.info(f"**Pesquisando condutas científicas para:** `{termo_en}` | **Filtro:** {base_selecionada}")

            artigos = buscar_estudos_alta_qualidade(termo_en, base_selecionada)

            if artigos:
                st.subheader(f"📊 {len(artigos)} Estudos Científicos com Resultados Positivos Encontrados")
                
                for idx, art in enumerate(artigos, 1):
                    st.markdown(f"### {idx}. [{art['journal']}] {art['titulo']}")
                    
                    col_info, col_vis = st.columns([2, 1])
                    
                    with col_info:
                        st.write(f"**Resumo do Estudo / Intervenção:** {art['resumo_en']}")
                        st.markdown(f"[🔗 Acesse o Estudo Completo no PubMed]({art['link_pubmed']})")
                        
                        if art['pmcid']:
                            st.markdown(f"[🖼️ Ver fotos originais do artigo no PMC]({f'https://www.ncbi.nlm.nih.gov/pmc/articles/{art["pmcid"]}/table-and-figure/'})")

                    with col_vis:
                        st.markdown("**📸 Visualização do Exercício / Intervenção:**")
                        # Busca automática de imagem para o tema do artigo se ele não trouxer fotos
                        imgs_exercicio = buscar_imagem_exercicio_web(termo_en)
                        
                        if imgs_exercicio:
                            st.image(imgs_exercicio[0], caption=f"Ilustração da conduta de reabilitação para {caso_clinico}", use_column_width=True)
                        else:
                            st.info("Exercício relatado em texto no artigo. Utilizar guia visual de exercícios padrão do app.")
                    
                    st.divider()
            else:
                st.warning("Nenhum estudo de alta evidência encontrado com esses termos exatos. Tente pesquisar por termos como 'knee pain' ou 'patellofemoral pain'.")
