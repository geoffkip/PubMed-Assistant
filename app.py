import streamlit as st
import os
from dotenv import load_dotenv
from modules.pubmed_client import search_pubmed, fetch_details
from modules.rag_engine import RAGEngine
from modules.utils import init_session_state

# Load environment variables
load_dotenv()

# Page Config
st.set_page_config(page_title="PubMed Assistant", page_icon="🧬", layout="wide")

# Custom CSS for better aesthetics
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

def main():
    init_session_state()

    st.title("🧬 PubMed Assistant")

    # Sidebar Configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Check if API key is in env
        env_api_key = os.getenv("GOOGLE_API_KEY")
        
        if env_api_key:
            st.success("API Key loaded from environment")
            if st.session_state.rag_engine is None:
                st.session_state.rag_engine = RAGEngine(env_api_key)
        else:
            api_key = st.text_input("Gemini API Key", type="password")
            if api_key:
                os.environ["GOOGLE_API_KEY"] = api_key
                if st.session_state.rag_engine is None:
                    st.session_state.rag_engine = RAGEngine(api_key)
                    st.success("RAG Engine Initialized!")
            else:
                st.warning("Please enter your Gemini API Key to proceed.")
        
        st.markdown("---")
        page = st.radio("Navigate", ["Search & Ingest", "Chat"])

    # Page: Search & Ingest
    if page == "Search & Ingest":
        st.header("Search & Ingest")
        st.markdown("Search PubMed and add articles to your knowledge base.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Search PubMed", placeholder="e.g., 'mRNA vaccine side effects'")
        with col2:
            max_results = st.slider("Max Articles", min_value=1, max_value=50, value=10)
            
        search_btn = st.button("Search")

        if search_btn and query:
            with st.spinner(f"Searching PubMed for top {max_results} articles..."):
                ids = search_pubmed(query, max_results=max_results)
                articles = fetch_details(ids)
                st.session_state.articles = articles
                if not articles:
                    st.warning("No articles found.")
                else:
                    st.success(f"Found {len(articles)} articles.")

        if st.session_state.articles:
            st.markdown("### Search Results")
            
            # Display results in a scrollable container or just list them
            for i, article in enumerate(st.session_state.articles):
                with st.expander(f"{i+1}. {article['title']} ({article['year']})"):
                    st.write(article['abstract'])
                    st.markdown(f"[Read on PubMed]({article['url']})")
            
            if st.button("Add to Knowledge Base"):
                if st.session_state.rag_engine:
                    with st.spinner("Ingesting articles into Vector DB..."):
                        success = st.session_state.rag_engine.ingest_articles(st.session_state.articles)
                        if success:
                            st.success(f"Successfully added {len(st.session_state.articles)} articles to Knowledge Base!")
                        else:
                            st.error("Failed to add articles.")
                else:
                    st.error("Please configure the API Key first.")

    # Page: Chat
    elif page == "Chat":
        st.header("Chat with Knowledge Base")
        st.markdown("Ask questions based on the ingested articles.")
        
        user_question = st.text_input("Ask a question", placeholder="What does the literature say about...")
        ask_btn = st.button("Ask")

        if ask_btn and user_question:
            if st.session_state.rag_engine:
                with st.spinner("Thinking..."):
                    answer, references = st.session_state.rag_engine.query_rag(user_question)
                    
                    st.markdown("### Answer")
                    st.write(answer)
                    
                    if references:
                        st.markdown("### References")
                        for ref in references:
                            st.markdown(f"- **{ref['title']}** ({ref['year']})")
            else:
                st.error("Please configure the API Key first.")

if __name__ == "__main__":
    main()
