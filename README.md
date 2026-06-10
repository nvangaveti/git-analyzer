# 🔍 GitHub Repository Analyzer

An AI-powered developer tool that analyzes any GitHub repository using RAG, Git history analytics, and LLM-based code review — all in a single Streamlit dashboard.

## 🚀 Live Demo
[Add Streamlit Cloud link here after deployment]

## 📸 Features

### 💬 Chat with Codebase (RAG)
- Ask natural language questions about any part of the code
- Function-level chunking using Python AST for precise retrieval
- Answers include file name and function references
- Powered by ChromaDB + HuggingFace embeddings + Groq LLaMA 3

### 📊 Git History Analytics
- Commit activity timeline
- Contributor breakdown (commits, insertions, deletions)
- Merge conflict detection from commit message patterns
- File collision risk — files touched by multiple contributors

### 🔎 LLM Code Review
- Automated bug detection per function
- Code smell identification
- Security issue flagging
- Refactor suggestions with severity scoring (low / medium / high)

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| LLM | Groq LLaMA 3.3 70B |
| Embeddings | HuggingFace all-MiniLM-L6-v2 |
| Vector DB | ChromaDB |
| Orchestration | LangChain |
| Git Analysis | GitPython |
| Visualization | Plotly |
| UI | Streamlit |

## ⚙️ Setup

**1. Clone the repo**
```bash
git clone https://github.com/nvangaveti/git-analyzer.git
cd git-analyzer
```

**2. Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your API key**
```bash
cp .env.example .env
# Edit .env and add your Groq API key
# Get free key at console.groq.com
```

**5. Run the app**
```bash
streamlit run app.py
```

## 📁 Project Structure

## 💡 Example Questions to Ask

- *"What does this codebase do?"*
- *"Who wrote the authentication logic?"*
- *"Where are the database queries?"*
- *"Which functions handle error cases?"*
- *"What does the main function do?"*

## 📊 Results on Sample Repos

Tested on `realpython/reader`:
- 7 files analyzed, 48 commits extracted
- 15 functions reviewed, 17 bugs detected
- 3 contributors tracked with full timeline

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Free API key from console.groq.com |
