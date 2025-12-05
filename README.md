# PubMed RAG Assistant

A comprehensive research assistant that allows users to search PubMed, ingest articles into a local vector database, and perform advanced analysis using Retrieval-Augmented Generation (RAG) powered by Google's Gemini model.

## Features

### 🔍 Search & Ingest
- **Smart Search**: Automatically expands queries with synonyms (e.g., "heart attack" -> "myocardial infarction") for better recall.
- **Topic Clustering**: Categorizes search results by publication type (e.g., Clinical Trial, Review).
- **Data Export**: Download search results as CSV.

### 🧠 Advanced RAG & Analysis
- **Chat with Knowledge Base**: Ask natural language questions grounded in your ingested articles.
- **Automatic Summarization**: Gemini generates a **one-sentence TL;DR** and **Category** for every article.
- **PICO Analysis**: Automatically extracts **Population**, **Intervention**, **Comparison**, and **Outcome** from clinical abstracts.
- **Podcast Mode**: Generates a 2-minute **Audio Summary** of your knowledge base using text-to-speech.

### 🕸️ Discovery & Visualization
- **Knowledge Graph**: Interactive network graph visualizing connections between articles and authors.
- **More Like This**: Instantly find semantically similar papers with one click.

### ⚙️ Architecture
- **Hybrid Search**: Combines **Vector Search** (Semantic) and **Keyword Search** (BM25) for optimal retrieval.
- **Reranking**: Uses a Cross-Encoder to re-score top candidates for high precision.
- **Models**:
  - Embedding: `all-mpnet-base-v2` (768 dim)
  - Reranking: `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - Generation: `gemini-2.5-flash`

```mermaid
graph TD
    User[User / Streamlit UI]
    subgraph "Data Acquisition"
        PubMed[PubMed API]
        Gemini_Exp[Gemini (Query Expansion)]
    end
    subgraph "Storage & Retrieval"
        Embed[Sentence Transformer]
        LDB[(LanceDB Vector DB)]
        Rerank[Cross-Encoder Reranker]
        Graph[Knowledge Graph Builder]
    end
    subgraph "Generation & Analysis"
        Gemini[Gemini 2.5 Flash]
        TTS[gTTS (Podcast)]
    end

    User -- "1. Query" --> Gemini_Exp
    Gemini_Exp -- "2. Expanded Query" --> PubMed
    PubMed -- "3. Articles" --> User
    User -- "4. Ingest" --> Gemini
    Gemini -- "5. Metadata (Summary/PICO)" --> LDB
    Embed -- "6. Vectors" --> LDB
    User -- "7. Ask Question" --> Embed
    Embed -- "8. Hybrid Retrieval" --> LDB
    LDB -- "9. Candidates" --> Rerank
    Rerank -- "10. Top Context" --> Gemini
    Gemini -- "11. Answer" --> User
    LDB -- "12. Graph Data" --> Graph
    Graph --> User
    LDB -- "13. Podcast Script" --> Gemini
    Gemini --> TTS
    TTS -- "14. Audio" --> User
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd pubmed_rag_app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**:
   Create a `.env` file in the root directory and add your Google API Key:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```

## Usage

1. **Run the Streamlit app**:
   ```bash
   streamlit run app.py
   ```

2. **Navigate**:
   - **Search & Ingest**: Build your knowledge base.
   - **Chat**: 
     - **Chat Tab**: Ask questions, view PICO analysis, and generate Podcasts.
     - **Knowledge Graph Tab**: Explore connections visually.

## Requirements

- Python 3.9+
- Streamlit
- LanceDB
- Google Generative AI SDK
- Biopython
- Sentence Transformers
- Streamlit Agraph
- gTTS
