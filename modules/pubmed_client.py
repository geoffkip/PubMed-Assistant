import streamlit as st
from Bio import Entrez

# Ideally, set your email here or via environment variable to be a good citizen
Entrez.email = "your_email@example.com" 

def search_pubmed(query, max_results=10):
    """
    Search PubMed for a given query and return a list of PubMed IDs.
    """
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()
        return record["IdList"]
    except Exception as e:
        st.error(f"Error searching PubMed: {e}")
        return []

def fetch_details(id_list):
    """
    Fetch details for a list of PubMed IDs.
    """
    if not id_list:
        return []
    
    ids = ",".join(id_list)
    try:
        handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        
        articles = []
        for article in records['PubmedArticle']:
            try:
                medline = article['MedlineCitation']['Article']
                title = medline['ArticleTitle']
                abstract_list = medline.get('Abstract', {}).get('AbstractText', [])
                abstract = " ".join(abstract_list) if abstract_list else "No abstract available."
                pub_date = medline.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
                year = pub_date.get('Year', 'Unknown')
                
                # Extract authors
                author_list = medline.get('AuthorList', [])
                authors = []
                for author in author_list:
                    if 'LastName' in author and 'ForeName' in author:
                        authors.append(f"{author['LastName']} {author['ForeName']}")
                author_str = ", ".join(authors)

                articles.append({
                    'pubmed_id': article['MedlineCitation']['PMID'],
                    'title': title,
                    'abstract': abstract,
                    'year': year,
                    'authors': author_str,
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{article['MedlineCitation']['PMID']}/"
                })
            except Exception as e:
                continue # Skip malformed articles
                
        return articles
    except Exception as e:
        st.error(f"Error fetching details: {e}")
        return []
