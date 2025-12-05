import os
import sys

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

from modules.pubmed_client import search_pubmed, fetch_details
from modules.rag_engine import RAGEngine

def test_run():
    print("1. Testing PubMed Search...")
    query = "mRNA vaccine"
    ids = search_pubmed(query, max_results=3)
    print(f"   Found {len(ids)} IDs: {ids}")
    
    if not ids:
        print("   FAILED: No IDs found.")
        return

    print("\n2. Testing Article Fetching...")
    articles = fetch_details(ids)
    print(f"   Fetched {len(articles)} articles.")
    if articles:
        print(f"   Sample Title: {articles[0]['title']}")
    else:
        print("   FAILED: No articles fetched.")
        return

    print("\n3. Testing RAG Engine Initialization (Local Embeddings)...")
    # Passing dummy key since we won't use generation in this test
    rag = RAGEngine(api_key="DUMMY_KEY") 
    print("   RAG Engine initialized.")

    print("\n4. Testing Ingestion...")
    success = rag.ingest_articles(articles)
    if success:
        print("   Ingestion successful.")
    else:
        print("   FAILED: Ingestion failed.")
        return

    print("\n5. Testing Retrieval...")
    # We expect this to work without a valid API key because it uses local embeddings
    # We will NOT call query_rag() fully because that triggers generation.
    # We will manually do the search part from query_rag to verify retrieval.
    
    query_text = "side effects"
    query_embedding = rag.get_embedding(query_text)
    
    try:
        tbl = rag.db.open_table(rag.table_name)
        results = tbl.search(query_embedding).limit(1).to_pandas()
        if not results.empty:
            print(f"   Retrieval successful. Found article: {results.iloc[0]['title']}")
        else:
            print("   Retrieval returned no results (but ran successfully).")
    except Exception as e:
        print(f"   FAILED: Retrieval error: {e}")

    print("\nTest Run Completed.")

if __name__ == "__main__":
    test_run()
