# Utility functions can go here
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

def init_session_state():
    if "rag_engine" not in st.session_state:
        st.session_state.rag_engine = None
    if "articles" not in st.session_state:
        st.session_state.articles = []

def build_knowledge_graph(articles):
    """
    Builds a knowledge graph from a list of articles.
    Nodes: Articles (Title), Authors
    Edges: Author -> Article
    """
    nodes = []
    edges = []
    
    # Sets to keep track of unique IDs
    article_ids = set()
    author_ids = set()
    
    for article in articles:
        # Article Node
        # Truncate title for display
        title_short = (article['title'][:30] + '..') if len(article['title']) > 30 else article['title']
        
        if article['pubmed_id'] not in article_ids:
            nodes.append(Node(id=article['pubmed_id'], 
                              label=title_short, 
                              size=20, 
                              color="#4CAF50", # Green for articles
                              title=article['title'])) # Tooltip
            article_ids.add(article['pubmed_id'])
        
        # Author Nodes and Edges
        if 'authors' in article and article['authors']:
            authors = article['authors'].split(', ')
            for author in authors:
                author_id = f"AUTH_{author}"
                if author_id not in author_ids:
                    nodes.append(Node(id=author_id, 
                                      label=author, 
                                      size=15, 
                                      color="#FF9800", # Orange for authors
                                      shape="dot"))
                    author_ids.add(author_id)
                
                # Edge: Author -> Article
                edges.append(Edge(source=author_id, 
                                  target=article['pubmed_id'], 
                                  color="#999999"))
    
    return nodes, edges

import google.generativeai as genai
from gtts import gTTS
import os

def generate_podcast_script(articles, api_key):
    """
    Generates a conversational podcast script from a list of articles using Gemini.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Summarize top 3 articles for the podcast
    context = ""
    for i, article in enumerate(articles[:3]):
        context += f"Article {i+1}: {article['title']}\nSummary: {article.get('summary', 'No summary')}\n\n"
    
    prompt = f"""You are a charismatic podcast host. Create a short, engaging 2-minute script summarizing the latest medical research based on the following articles.
    Make it sound like a real podcast (e.g., "Welcome back to MedDaily...").
    Keep it conversational, easy to understand, and highlight the key findings.
    
    Articles:
    {context}
    
    Script:"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating script: {e}"

def create_audio(text, filename="podcast.mp3"):
    """
    Converts text to audio using gTTS.
    """
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"Error creating audio: {e}")
        return None
