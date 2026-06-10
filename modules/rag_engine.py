import os
import ast
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "./chroma_db"

def extract_functions_from_file(file_info: dict) -> list[Document]:
    """Extract individual functions from Python files using AST."""
    docs = []
    if file_info['extension'] != '.py':
        docs.append(Document(
            page_content=file_info['content'],
            metadata={
                "source": file_info['relative_path'],
                "filename": file_info['filename'],
                "type": "file"
            }
        ))
        return docs

    try:
        tree = ast.parse(file_info['content'])
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_code = ast.get_source_segment(file_info['content'], node)
                if func_code:
                    docs.append(Document(
                        page_content=func_code,
                        metadata={
                            "source": file_info['relative_path'],
                            "filename": file_info['filename'],
                            "function_name": node.name,
                            "lineno": node.lineno,
                            "type": "function"
                        }
                    ))
    except SyntaxError:
        docs.append(Document(
            page_content=file_info['content'],
            metadata={
                "source": file_info['relative_path'],
                "filename": file_info['filename'],
                "type": "file"
            }
        ))
    return docs

def build_vector_store(code_files: list[dict]) -> Chroma:
    """Build ChromaDB vector store from code files."""
    print("Building vector store...")
    all_docs = []

    for file_info in code_files:
        docs = extract_functions_from_file(file_info)
        all_docs.extend(docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    final_docs = []
    for doc in all_docs:
        if len(doc.page_content) > 1500:
            chunks = splitter.split_documents([doc])
            final_docs.extend(chunks)
        else:
            final_docs.append(doc)

    print(f"Total chunks to embed: {len(final_docs)}")

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vectorstore = Chroma.from_documents(
        documents=final_docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    print("Vector store built successfully.")
    return vectorstore

def load_vector_store() -> Chroma:
    """Load existing ChromaDB vector store."""
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

def get_rag_chain(vectorstore: Chroma):
    """Build RAG chain with Groq LLM."""
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    prompt = ChatPromptTemplate.from_template("""
You are an expert code analyst. Use the following code context to answer the question.
Always mention the file name and function name when referencing specific code.
If you don't know the answer, say so clearly.

Context:
{context}

Question: {question}

Answer:""")

    def format_docs(docs):
        return "\n\n".join([
            f"File: {doc.metadata.get('source', 'unknown')}\n"
            f"Function: {doc.metadata.get('function_name', 'N/A')}\n"
            f"Code:\n{doc.page_content}"
            for doc in docs
        ])

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain, retriever

def query_codebase(chain, question: str) -> dict:
    """Query the codebase using RAG chain."""
    answer = chain.invoke(question)
    return {"answer": answer}