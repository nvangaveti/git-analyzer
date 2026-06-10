import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

from modules.repo_loader import clone_repo, get_code_files, extract_git_history
from modules.history_analyzer import get_full_analysis
from modules.rag_engine import build_vector_store, get_rag_chain, query_codebase
from modules.code_reviewer import run_code_review, get_review_summary

load_dotenv()

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Git Analyzer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 GitHub Repository Analyzer")
st.caption("AI-powered codebase analysis — RAG Q&A · Git History · Code Review")

# ─── Session State ─────────────────────────────────────────────────────────────
if "repo_loaded" not in st.session_state:
    st.session_state.repo_loaded = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Repository Setup")
    github_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repo"
    )
    max_functions = st.slider("Max functions to review", 5, 30, 15)

    analyze_btn = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)

    if st.session_state.repo_loaded:
        st.success("✅ Repository loaded")
        st.info(f"📁 {st.session_state.get('file_count', 0)} files found")
        st.info(f"📝 {st.session_state.get('commit_count', 0)} commits extracted")

# ─── Load Repository ───────────────────────────────────────────────────────────
if analyze_btn and github_url:
    with st.spinner("Cloning repository..."):
        try:
            repo = clone_repo(github_url)
            st.session_state.repo = repo
        except Exception as e:
            st.error(f"Failed to clone repo: {e}")
            st.stop()

    with st.spinner("Reading code files..."):
        code_files = get_code_files("./repo_cache")
        st.session_state.code_files = code_files
        st.session_state.file_count = len(code_files)

    with st.spinner("Extracting git history..."):
        commits = extract_git_history(repo)
        st.session_state.commits = commits
        st.session_state.commit_count = len(commits)

    with st.spinner("Building vector store for RAG..."):
        vectorstore = build_vector_store(code_files)
        chain, retriever = get_rag_chain(vectorstore)
        st.session_state.chain = chain
        st.session_state.retriever = retriever

    with st.spinner("Running git history analysis..."):
        analysis = get_full_analysis(commits, repo)
        st.session_state.analysis = analysis

    with st.spinner(f"Running LLM code review on up to {max_functions} functions..."):
        reviews = run_code_review(code_files, max_functions=max_functions)
        st.session_state.reviews = reviews
        st.session_state.review_summary = get_review_summary(reviews)

    st.session_state.repo_loaded = True
    st.rerun()

# ─── Main Tabs ─────────────────────────────────────────────────────────────────
if st.session_state.repo_loaded:
    tab1, tab2, tab3 = st.tabs([
        "💬 Chat with Codebase",
        "📊 History Analytics",
        "🔎 Code Review"
    ])

    # ── Tab 1: RAG Chat ─────────────────────────────────────────────────────
    with tab1:
        st.subheader("💬 Ask anything about the codebase")
        st.caption("e.g. Who wrote the authentication logic? Where are database queries? What does X function do?")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if question := st.chat_input("Ask a question about the codebase..."):
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Searching codebase..."):
                    result = query_codebase(st.session_state.chain, question)
                    answer = result["answer"]
                st.write(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # ── Tab 2: History Analytics ────────────────────────────────────────────
    with tab2:
        st.subheader("📊 Git History Analytics")
        analysis = st.session_state.analysis

        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Commits", analysis["total_commits"])
        col2.metric("Contributors", analysis["total_authors"])
        col3.metric("Conflict Commits", len(analysis["conflict_commits"]))
        col4.metric("High Risk Files", len([
            f for f, d in analysis["collision_risk"].items()
            if d["risk_level"] == "High"
        ]))

        # Commit timeline
        st.subheader("📈 Commit Activity Over Time")
        if not analysis["timeline"].empty:
            fig = px.line(
                analysis["timeline"],
                x="date_only",
                y="commit_count",
                title="Commits Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Contributor stats
        st.subheader("👥 Contributor Breakdown")
        if not analysis["contributors"].empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    analysis["contributors"].head(10),
                    x="author",
                    y="commits",
                    title="Top Contributors by Commits"
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(
                    analysis["contributors"].head(10),
                    x="author",
                    y=["insertions", "deletions"],
                    title="Lines Added vs Deleted",
                    barmode="group"
                )
                st.plotly_chart(fig, use_container_width=True)

        # Merge conflict analysis
        st.subheader("⚠️ Merge Conflict Analysis")
        conflict_commits = analysis["conflict_commits"]
        if conflict_commits:
            st.warning(f"Found {len(conflict_commits)} conflict-related commits")
            conflict_df = pd.DataFrame(conflict_commits)[
                ["sha", "author", "date", "message"]
            ]
            st.dataframe(conflict_df, use_container_width=True)
        else:
            st.success("No conflict-related commits detected.")

        # File collision risk
        st.subheader("🔥 High Collision Risk Files")
        collision_risk = analysis["collision_risk"]
        if collision_risk:
            risk_data = [
                {
                    "file": f,
                    "contributors": d["contributor_count"],
                    "touches": d["total_touches"],
                    "risk": d["risk_level"],
                    "authors": ", ".join(d["contributors"])
                }
                for f, d in collision_risk.items()
            ]
            risk_df = pd.DataFrame(risk_data)
            st.dataframe(
                risk_df.style.map(
    lambda x: "background-color: #ffcccc" if x == "High"
    else "background-color: #fff3cc" if x == "Medium" else "",
    subset=["risk"]
),
                use_container_width=True
            )
        else:
            st.info("No high collision risk files detected.")

    # ── Tab 3: Code Review ──────────────────────────────────────────────────
    with tab3:
        st.subheader("🔎 LLM Code Review Report")
        summary = st.session_state.review_summary
        reviews = st.session_state.reviews

        if summary:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Functions Reviewed", summary["total_functions_reviewed"])
            col2.metric("Bugs Found", summary["total_bugs_found"])
            col3.metric("Code Smells", summary["total_code_smells"])
            col4.metric("Security Issues", summary["total_security_issues"])

            # Severity breakdown
            sev = summary["severity_breakdown"]
            fig = px.pie(
                values=list(sev.values()),
                names=list(sev.keys()),
                title="Severity Breakdown",
                color_discrete_map={
                    "high": "#ff4444",
                    "medium": "#ffaa00",
                    "low": "#44bb44",
                    "unknown": "#aaaaaa"
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        # Individual function reviews
        st.subheader("📋 Function-level Review")
        for review in reviews:
            severity = review.get("severity", "unknown")
            color = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
            with st.expander(
                f"{color} {review.get('function_name', 'Unknown')} "
                f"— {review.get('file', '')} "
                f"(Score: {review.get('overall_score', 'N/A')}/10)"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🐛 Bugs**")
                    bugs = review.get("bugs", [])
                    if bugs:
                        for b in bugs:
                            st.write(f"• {b}")
                    else:
                        st.write("No bugs found")

                    st.markdown("**🔒 Security Issues**")
                    sec = review.get("security_issues", [])
                    if sec:
                        for s in sec:
                            st.write(f"• {s}")
                    else:
                        st.write("No security issues")

                with col2:
                    st.markdown("**👃 Code Smells**")
                    smells = review.get("code_smells", [])
                    if smells:
                        for sm in smells:
                            st.write(f"• {sm}")
                    else:
                        st.write("No code smells")

                    st.markdown("**💡 Refactor Suggestion**")
                    st.info(review.get("refactor_suggestion", "N/A"))

else:
    st.info("👈 Enter a GitHub repository URL in the sidebar and click **Analyze Repository** to get started.")
    st.markdown("""
    ### What this tool does:
    - **💬 Chat with codebase** — Ask questions about any part of the code using RAG
    - **📊 History analytics** — Visualize commits, contributors, conflict risk
    - **🔎 Code review** — AI-powered bug detection and refactor suggestions
    """)