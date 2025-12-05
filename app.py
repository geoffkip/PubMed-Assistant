import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from modules.pubmed_client import search_pubmed, fetch_details, expand_query
from modules.rag_engine import RAGEngine
from modules.utils import init_session_state, build_knowledge_graph
from streamlit_agraph import agraph, Node, Edge, Config

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

    st.title("🧬 PubMed RAG Assistant")

    # Sidebar for Navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio("Go to:", ["Search & Ingest", "Chat"])
        
        st.markdown("---")
        st.header("Configuration")
        
        # Auto-load API Key from .env if available
        env_api_key = os.getenv("GOOGLE_API_KEY")
        api_key = st.text_input("Gemini API Key", type="password", value=env_api_key if env_api_key else "")
        
        if api_key:
            if st.session_state.rag_engine is None:
                st.session_state.rag_engine = RAGEngine(api_key)
                st.success("RAG Engine Initialized!")
        else:
            st.warning("Please enter your Gemini API Key.")

    # Page: Search & Ingest
    if page == "Search & Ingest":
        st.header("Search & Ingest Articles")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Enter search query (e.g., 'immunotherapy for lung cancer')")
            use_expansion = st.checkbox("Enable Smart Query Expansion", value=True, help="Automatically adds synonyms to your search.")
        with col2:
            max_results = st.slider("Max Results", 5, 100, 10)
        
        search_btn = st.button("Search PubMed")
        
        if search_btn and query:
            final_query = query
            if use_expansion:
                with st.spinner("Expanding query..."):
                    expanded_query = expand_query(query)
                    if expanded_query != query:
                        st.info(f"Expanded Query: **{expanded_query}**")
                        final_query = expanded_query
            
            with st.spinner(f"Searching PubMed for top {max_results} articles..."):
                ids = search_pubmed(final_query, max_results=max_results)
                articles = fetch_details(ids)
                if not articles:
                    st.warning("No articles found.")
                else:
                    st.session_state.articles = articles
                    st.success(f"Found {len(articles)} articles.")
        
        if st.session_state.articles:
            st.markdown("### Search Results")
            
            # Export Search Results
            df_search = pd.DataFrame(st.session_state.articles)
            if not df_search.empty:
                csv_search = df_search.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Search Results (CSV)",
                    data=csv_search,
                    file_name='pubmed_search_results.csv',
                    mime='text/csv',
                )

            # Display Articles
            
            # Select All Logic
            def toggle_select_all():
                select_all = st.session_state.select_all
                for i in range(len(st.session_state.articles)):
                    st.session_state[f"select_{i}"] = select_all

            st.checkbox("Select All", key="select_all", on_change=toggle_select_all)
            
            selected_indices = []
            for i, article in enumerate(st.session_state.articles):
                with st.expander(f"{article['title']} ({article['year']})"):
                    st.markdown(f"**Authors:** {article['authors']}")
                    st.markdown(f"**Type:** {article.get('publication_type', 'Journal Article')}")
                    st.markdown(f"**Abstract:** {article['abstract']}")
                    st.markdown(f"[Read on PubMed]({article['url']})")
                    
                    # Ensure key exists in session state if not already
                    if f"select_{i}" not in st.session_state:
                        st.session_state[f"select_{i}"] = False
                        
                    if st.checkbox("Select for Ingestion", key=f"select_{i}"):
                        selected_indices.append(i)
            
            if st.button("Ingest Selected Articles"):
                if not selected_indices:
                    st.warning("Please select at least one article.")
                elif st.session_state.rag_engine:
                    selected_articles = [st.session_state.articles[i] for i in selected_indices]
                    with st.spinner("Ingesting and Generating Summaries (this may take a moment)..."):
                        success = st.session_state.rag_engine.ingest_articles(selected_articles)
                        if success:
                            st.success(f"Successfully ingested {len(selected_articles)} articles!")
                        else:
                            st.error("Failed to ingest articles.")
                else:
                    st.error("Please configure the API Key first.")

    # Page: Chat
    elif page == "Chat":
        st.header("Chat with Knowledge Base")
        
        # Tabs for different views
        tab1, tab2 = st.tabs(["💬 Chat", "🕸️ Knowledge Graph"])
        
        with tab1:
            # Knowledge Base View
            with st.expander("📚 View Knowledge Base"):
                if st.session_state.rag_engine:
                    try:
                        tbl = st.session_state.rag_engine.db.open_table(st.session_state.rag_engine.table_name)
                        df_kb = tbl.to_pandas()
                        if not df_kb.empty:
                            # Podcast Generation
                            if st.button("🎙️ Generate Podcast Summary"):
                                with st.spinner("Writing script and generating audio..."):
                                    articles_list = df_kb.to_dict('records')
                                    script = generate_podcast_script(articles_list, api_key)
                                    if script:
                                        audio_file = create_audio(script)
                                        if audio_file:
                                            st.audio(audio_file)
                                            st.success("Podcast generated!")
                            
                            st.dataframe(df_kb[['title', 'year', 'category', 'summary']])
                            
                            # Export Knowledge Base
                            csv_kb = df_kb.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Export Knowledge Base (CSV)",
                                data=csv_kb,
                                file_name='knowledge_base.csv',
                                mime='text/csv',
                            )
                            
                            st.markdown("### Explore Articles")
                            for index, row in df_kb.iterrows():
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.markdown(f"**{row['title']}**")
                                    if 'pico' in row and row['pico']:
                                        with st.expander("🔬 PICO Analysis"):
                                            st.text(row['pico'])
                                with col2:
                                    if st.button("More Like This", key=f"sim_{row['pubmed_id']}"):
                                        similar = st.session_state.rag_engine.find_similar_articles(row['pubmed_id'])
                                        if similar:
                                            st.session_state.similar_articles = similar
                                            st.toast(f"Found {len(similar)} similar articles!", icon="🔍")
                                        else:
                                            st.toast("No similar articles found.", icon="⚠️")

                            # Display Similar Articles if found
                            if "similar_articles" in st.session_state and st.session_state.similar_articles:
                                st.markdown("#### 🔍 Similar Articles Found")
                                for sim in st.session_state.similar_articles:
                                    with st.expander(f"{sim['title']} ({sim['year']})"):
                                        st.markdown(f"**Abstract:** {sim['abstract']}")
                                        st.markdown(f"[Read on PubMed]({sim['url']})")
                                if st.button("Clear Similar Results"):
                                    del st.session_state.similar_articles
                                    st.rerun()

                        else:
                            st.info("Knowledge base is empty.")
                    except:
                        st.info("Knowledge base not initialized yet.")

            st.markdown("---")
            
            # Initialize chat history
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display chat messages from history on app rerun
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # React to user input
            if prompt := st.chat_input("Ask a question..."):
                # Display user message in chat message container
                st.chat_message("user").markdown(prompt)
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})

                if st.session_state.rag_engine:
                    with st.spinner("Thinking..."):
                        # Pass chat history to RAG engine
                        answer, references = st.session_state.rag_engine.query_rag(prompt, chat_history=st.session_state.messages)
                        
                        # Display assistant response in chat message container
                        with st.chat_message("assistant"):
                            st.markdown(answer)
                            if references:
                                st.markdown("### References")
                                for ref in references:
                                    st.markdown(f"- **{ref['title']}** ({ref['year']})")
                                    if 'summary' in ref:
                                        st.caption(f"Summary: {ref['summary']}")
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error("Please configure the API Key first.")

        with tab2:
            st.header("Knowledge Graph")
            if st.session_state.rag_engine:
                try:
                    tbl = st.session_state.rag_engine.db.open_table(st.session_state.rag_engine.table_name)
                    articles = tbl.to_pandas().to_dict('records')
                    if articles:
                        nodes, edges = build_knowledge_graph(articles)
                        
                        config = Config(width=700, 
                                        height=500, 
                                        directed=True, 
                                        physics=True, 
                                        hierarchical=False,
                                        nodeHighlightBehavior=True, 
                                        highlightColor="#F7A7A6",
                                        collapsible=True)
                        
                        return_value = agraph(nodes=nodes, 
                                              edges=edges, 
                                              config=config)
                    else:
                        st.info("No articles to visualize.")
                except Exception as e:
                    st.error(f"Error building graph: {e}")
            else:
                st.info("Initialize RAG Engine to view graph.")

if __name__ == "__main__":
    main()
