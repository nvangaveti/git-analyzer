import os
import ast
import json
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

REVIEW_PROMPT = """You are a senior software engineer doing a thorough code review.
Analyze this function and return ONLY a valid JSON object with these exact keys:
{{
    "function_name": "name of the function",
    "file": "file path",
    "bugs": ["list of potential bugs with line references"],
    "code_smells": ["list of code smells like long function, magic numbers, etc"],
    "security_issues": ["list of security vulnerabilities if any"],
    "refactor_suggestion": "one concrete refactoring suggestion",
    "severity": "low or medium or high",
    "overall_score": "score out of 10"
}}

Function name: {function_name}
File: {file_path}

Code:
{code}

Return ONLY the JSON object, no markdown, no explanation."""

def extract_functions_for_review(code_files: list[dict]) -> list[dict]:
    """Extract all functions from Python files for review."""
    functions = []
    for file_info in code_files:
        if file_info['extension'] != '.py':
            continue
        try:
            tree = ast.parse(file_info['content'])
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_code = ast.get_source_segment(
                        file_info['content'], node
                    )
                    if func_code and len(func_code) > 50:
                        functions.append({
                            "function_name": node.name,
                            "file_path": file_info['relative_path'],
                            "code": func_code,
                            "lineno": node.lineno
                        })
        except SyntaxError:
            continue
    return functions

def review_function(llm: ChatGroq, func: dict) -> dict:
    """Review a single function using LLM."""
    prompt = REVIEW_PROMPT.format(
        function_name=func['function_name'],
        file_path=func['file_path'],
        code=func['code']
    )
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        # Clean up markdown if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        result['lineno'] = func['lineno']
        return result
    except Exception as e:
        return {
            "function_name": func['function_name'],
            "file": func['file_path'],
            "bugs": [],
            "code_smells": [],
            "security_issues": [],
            "refactor_suggestion": "Could not analyze",
            "severity": "unknown",
            "overall_score": "N/A",
            "lineno": func['lineno'],
            "error": str(e)
        }

def run_code_review(code_files: list[dict], max_functions: int = 20) -> list[dict]:
    """Run LLM code review on all extracted functions."""
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0
    )

    functions = extract_functions_for_review(code_files)

    # Limit to avoid rate limits
    functions = functions[:max_functions]
    print(f"Reviewing {len(functions)} functions...")

    results = []
    for i, func in enumerate(functions):
        print(f"Reviewing {i+1}/{len(functions)}: {func['function_name']}")
        result = review_function(llm, func)
        results.append(result)

    return results

def get_review_summary(reviews: list[dict]) -> dict:
    """Summarize code review results."""
    if not reviews:
        return {}

    severity_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    total_bugs = 0
    total_smells = 0
    total_security = 0

    for r in reviews:
        sev = r.get("severity", "unknown").lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        total_bugs += len(r.get("bugs", []))
        total_smells += len(r.get("code_smells", []))
        total_security += len(r.get("security_issues", []))

    return {
        "total_functions_reviewed": len(reviews),
        "severity_breakdown": severity_counts,
        "total_bugs_found": total_bugs,
        "total_code_smells": total_smells,
        "total_security_issues": total_security,
        "high_severity_functions": [
            r for r in reviews if r.get("severity") == "high"
        ]
    }