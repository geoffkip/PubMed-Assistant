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
    for i, article in enumerate(articles):
        context += f"Article {i+1}: {article['title']}\nSummary: {article.get('summary', 'No summary')}\n\n"
    
    prompt = f"""You are a charismatic podcast host named Dr. Alex. Create a short, engaging 2-minute script summarizing the latest medical research based on the following articles.
    
    CRITICAL INSTRUCTIONS:
    1. Write ONLY the spoken words. 
    2. DO NOT include any stage directions like [cue music], [applause], (fade out), or *music plays*.
    3. DO NOT use speaker labels like "Host:" or "Alex:".
    4. Use a natural, conversational tone. Use contractions (it's, we're) and simple language.
    5. Start directly with the content, e.g., "Hello and welcome back..."
    
    Articles:
    {context}
    
    Script:"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating script: {e}"

import re

import asyncio
import edge_tts

async def _generate_audio(text, filename, voice="en-US-ChristopherNeural"):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def create_audio(text, filename="podcast.mp3"):
    """
    Converts text to audio using edge-tts for a more natural voice.
    """
    try:
        # Clean text to remove stage directions and markdown
        # Remove text in brackets []
        clean_text = re.sub(r'\[.*?\]', '', text)
        # Remove text in parentheses ()
        clean_text = re.sub(r'\(.*?\)', '', clean_text)
        # Remove text between asterisks *...*
        clean_text = re.sub(r'\*.*?\*', '', clean_text)
        # Remove potential speaker labels like "Host:" or "Dr. Alex:" at start of lines
        clean_text = re.sub(r'^[A-Za-z\s]+:\s*', '', clean_text, flags=re.MULTILINE)
        # Remove markdown bold/italic markers if any remain
        clean_text = clean_text.replace('**', '').replace('__', '')
        
        if not clean_text.strip():
            return None

        # Run async function synchronously
        asyncio.run(_generate_audio(clean_text, filename))
        return filename
    except Exception as e:
        print(f"Error creating audio: {e}")
        return None
