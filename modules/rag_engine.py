import lancedb
import google.generativeai as genai
import pandas as pd
import os
import streamlit as st
from lancedb.pydantic import LanceModel, Vector
from sentence_transformers import SentenceTransformer

# Define the schema for LanceDB
class Article(LanceModel):
    vector: Vector(384) # Dimension for all-MiniLM-L6-v2
    text: str
    title: str
    url: str
    pubmed_id: str
    authors: str
    year: str

class RAGEngine:
    def __init__(self, api_key, db_path="data/lancedb"):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.db = lancedb.connect(db_path)
        self.table_name = "pubmed_articles_free_embed" # Changed table name to avoid conflict/schema error
        
        # Initialize embedding model
        # This will download the model the first time it runs
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def get_embedding(self, text):
        return self.embedding_model.encode(text)

    def ingest_articles(self, articles):
        """
        Ingest a list of article dictionaries into LanceDB.
        """
        data = []
        for article in articles:
            # Combine title and abstract for embedding context
            text_to_embed = f"Title: {article['title']}\nAbstract: {article['abstract']}"
            embedding = self.get_embedding(text_to_embed)
            
            data.append({
                "vector": embedding,
                "text": text_to_embed,
                "title": article['title'],
                "url": article['url'],
                "pubmed_id": str(article['pubmed_id']),
                "authors": article['authors'],
                "year": str(article['year'])
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
                return True
            except Exception as e:
                print(f"Error ingesting: {e}")
                return False
        return False

    def query_rag(self, query, k=3):
        """
        Retrieve relevant articles and generate an answer.
        """
        # Embed query using local model
        query_embedding = self.get_embedding(query)

        try:
            tbl = self.db.open_table(self.table_name)
            results = tbl.search(query_embedding).limit(k).to_pandas()
        except Exception as e:
            return f"Error searching database: {e}", []

        if results.empty:
            return "No relevant articles found in the knowledge base.", []

        # Construct context
        context = ""
        references = []
        for index, row in results.iterrows():
            context += f"Article {index+1}:\nTitle: {row['title']}\nContent: {row['text']}\n\n"
            references.append(row)

        # Generate answer using Gemini (still needs API key for generation)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""You are a helpful medical research assistant. Use the following context to answer the user's question.
        If the answer is not in the context, say you don't know.
        
        Context:
        {context}
        
        Question: {query}
        
        Answer:"""
        
        try:
            response = model.generate_content(prompt)
            return response.text, references
        except Exception as e:
            return f"Error generating answer: {e}", references
