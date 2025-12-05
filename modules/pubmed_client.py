import streamlit as st
from Bio import Entrez
import google.generativeai as genai
import os

# Ideally, set your email here or via environment variable to be a good citizen
Entrez.email = "your_email@example.com" 

def expand_query(query):
    """
    Uses Gemini to expand the search query with synonyms and related terms.
    Returns a boolean search string for PubMed.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return query
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""You are a helpful medical research assistant. 
    Generate a boolean search query for PubMed that improves the user's search.
    
    Original Term: "{query}"
    
    Rules:
    1. PRESERVE the user's core phrases. Do not split specific medical terms.
    2. Add synonyms ONLY for the *core medical condition* or *drug* (e.g., "Heart Attack" -> "Myocardial Infarction").
    3. DO NOT expand generic terms like "treatment", "therapy", "diagnosis", "options", "strategies". Leave them as is or remove them if redundant.
    4. Use OR for synonyms, AND for distinct concepts.
    5. Return ONLY the query string.
    
    Example Input: heart attack treatment
    Example Output: ("heart attack" OR "myocardial infarction") AND treatment
    
    Example Input: Ulcerative Colitis Advanced Therapy treatments
    Example Output: ("Ulcerative Colitis" OR UC) AND "Advanced Therapy" AND treatments
    
    Output:"""
    
    try:
        response = model.generate_content(prompt)
        expanded_query = response.text.strip()
        # Basic validation to ensure it's not empty or an error message
        if len(expanded_query) > len(query):
            return expanded_query
        return query
    except Exception as e:
        print(f"Error expanding query: {e}")
        return query 

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

                # Extract Publication Type
                pub_type_list = medline.get('PublicationTypeList', [])
                pub_types = [pt for pt in pub_type_list]
                pub_type_str = ", ".join(pub_types) if pub_types else "Journal Article"

                articles.append({
                    'pubmed_id': article['MedlineCitation']['PMID'],
                    'title': title,
                    'abstract': abstract,
                    'year': year,
                    'authors': author_str,
                    'publication_type': pub_type_str,
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{article['MedlineCitation']['PMID']}/"
                })
            except Exception as e:
                continue # Skip malformed articles
                
        return articles
    except Exception as e:
        st.error(f"Error fetching details: {e}")
        return []
