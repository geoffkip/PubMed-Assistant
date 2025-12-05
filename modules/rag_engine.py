import lancedb
import google.generativeai as genai
import pandas as pd
import os
import streamlit as st
from lancedb.pydantic import LanceModel, Vector
from sentence_transformers import SentenceTransformer, CrossEncoder

# Define the schema for LanceDB
class Article(LanceModel):
    vector: Vector(768) # Dimension for all-mpnet-base-v2
    text: str
    title: str
    url: str
    pubmed_id: str
    authors: str
    year: str
    summary: str
    category: str
    pico: str # JSON string or formatted text

class RAGEngine:
    def __init__(self, api_key, db_path="data/lancedb"):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.db = lancedb.connect(db_path)
        self.table_name = "pubmed_articles_mpnet_v3" # Updated table for PICO schema
        
        # Initialize embedding model (Bi-Encoder)
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        
        # Initialize reranker (Cross-Encoder)
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def get_embedding(self, text):
        return self.embedding_model.encode(text)

    def generate_metadata(self, text):
        """
        Generates a summary, category, and PICO analysis for the article using Gemini.
        """
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Analyze the following medical article abstract and provide:
        1. A one-sentence TL;DR summary.
        2. A category (e.g., Clinical Trial, Review, Case Study, Basic Research, etc.).
        3. A PICO analysis (Population, Intervention, Comparison, Outcome).
        
        Abstract:
        {text[:2000]} # Truncate to avoid token limits
        
        Output format:
        Summary: [Summary]
        Category: [Category]
        PICO:
        P: [Population]
        I: [Intervention]
        C: [Comparison]
        O: [Outcome]
        """
        try:
            response = model.generate_content(prompt)
            content = response.text.strip()
            
            summary = "No summary available."
            category = "General"
            pico = "PICO analysis not available."
            
            # Simple parsing
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("Category:"):
                    category = line.replace("Category:", "").strip()
                elif line.startswith("PICO:"):
                    # Capture the rest as PICO
                    pico = "\n".join(lines[i+1:]).strip()
            
            return summary, category, pico
        except Exception as e:
            print(f"Error generating metadata: {e}")
            return "Error generating summary.", "Uncategorized", "Error generating PICO."

    def ingest_articles(self, articles):
        """
        Ingest a list of article dictionaries into LanceDB.
        """
        data = []
        for article in articles:
            # Combine title and abstract for embedding context
            text_to_embed = f"Title: {article['title']}\nAbstract: {article['abstract']}"
            embedding = self.get_embedding(text_to_embed)
            
            # Generate metadata
            summary, category, pico = self.generate_metadata(article['abstract'])
            
            data.append({
                "vector": embedding,
                "text": text_to_embed,
                "title": article['title'],
                "url": article['url'],
                "pubmed_id": str(article['pubmed_id']),
                "authors": article['authors'],
                "year": str(article['year']),
                "summary": summary,
                "category": category,
                "pico": pico
            })
        
        if data:
            try:
                # We use overwrite=False to append by default, or we can manage modes.
                # Since we changed the table name, let's just create or open.
                try:
                    tbl = self.db.open_table(self.table_name)
                    tbl.add(data)
                except:
                    tbl = self.db.create_table(self.table_name, data=data)
                
                # Create FTS index for hybrid search
                try:
                    tbl.create_fts_index("text", replace=True)
                except Exception as e:
                    print(f"Warning: Could not create FTS index: {e}")
                    
                return True
            except Exception as e:
                print(f"Error ingesting: {e}")
                return False
        return False

    def query_rag(self, query, chat_history=[], k=5):
        """
        Retrieve relevant articles and generate an answer.
        Uses Hybrid Search (Vector + Keyword) -> Rerank -> Top k.
        """
        # Embed query using local model
        query_embedding = self.get_embedding(query)

        try:
            tbl = self.db.open_table(self.table_name)
            
            # Hybrid Search: Retrieve candidates from both Vector and FTS
            # Note: LanceDB's hybrid search is experimental/evolving. 
            # We will fetch candidates from both and combine.
            
            # 1. Vector Search
            vector_results = tbl.search(query_embedding).limit(10).to_pandas()
            
            # 2. Keyword Search (FTS) - if index exists
            try:
                fts_results = tbl.search(query, query_type="fts").limit(10).to_pandas()
                # Combine and deduplicate
                results = pd.concat([vector_results, fts_results]).drop_duplicates(subset=['pubmed_id'])
            except:
                # Fallback to just vector if FTS fails or not indexed
                results = vector_results

        except Exception as e:
            return f"Error searching database: {e}", []

        if results.empty:
            return "No relevant articles found in the knowledge base.", []

        # Reranking
        cross_inp = [[query, row['text']] for index, row in results.iterrows()]
        cross_scores = self.reranker.predict(cross_inp)
        results['cross_score'] = cross_scores
        
        # Sort by cross_score and take top k
        results = results.sort_values(by='cross_score', ascending=False).head(k)

        # Construct context
        context = ""
        references = []
        for index, row in results.iterrows():
            context += f"Article {index+1}:\nTitle: {row['title']}\nContent: {row['text']}\n\n"
            references.append(row)

        # Construct Chat History Context
        history_context = ""
        if chat_history:
            history_context = "Chat History:\n"
            for msg in chat_history[-5:]: # Keep last 5 turns
                history_context += f"{msg['role'].capitalize()}: {msg['content']}\n"
            history_context += "\n"

        # Generate answer using Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""You are a helpful medical research assistant. Use the following context and chat history to answer the user's question.
        If the answer is not in the context, say you don't know.
        
        {history_context}
        Context:
        {context}
        
        Question: {query}
        
        Answer:"""
        
        try:
            response = model.generate_content(prompt)
            return response.text, references
        except Exception as e:
            return f"Error generating answer: {e}", references

    def find_similar_articles(self, pubmed_id, k=5):
        """
        Finds articles semantically similar to the given PubMed ID.
        """
        try:
            tbl = self.db.open_table(self.table_name)
            # Get the vector for the target article
            # Note: LanceDB filtering might be slightly different depending on version, 
            # but fetching by ID is standard.
            df = tbl.search().where(f"pubmed_id = '{pubmed_id}'").limit(1).to_pandas()
            
            if df.empty:
                return []
            
            target_vector = df.iloc[0]['vector']
            
            # Search for nearest neighbors
            results = tbl.search(target_vector).limit(k+1).to_pandas()
            
            # Filter out the article itself
            results = results[results['pubmed_id'] != pubmed_id].head(k)
            return results.to_dict('records')
        except Exception as e:
            print(f"Error finding similar articles: {e}")
            return []
