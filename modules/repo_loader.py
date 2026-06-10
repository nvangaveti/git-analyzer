import os
import shutil
from git import Repo
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go',
    '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.md'
}

IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    'env', '.env', 'dist', 'build', '.idea', '.vscode'
}

def clone_repo(github_url: str, dest: str = "./repo_cache") -> Repo:
    """Clone a GitHub repo to local directory."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    print(f"Cloning {github_url}...")
    repo = Repo.clone_from(github_url, dest)
    print(f"Cloned successfully.")
    return repo

def get_code_files(repo_path: str) -> list[dict]:
    """Walk repo and return all supported code files with metadata."""
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for filename in filenames:
            ext = Path(filename).suffix
            if ext in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, repo_path)
                try:
                    with open(full_path, 'r', errors='ignore') as f:
                        content = f.read()
                    files.append({
                        "filename": filename,
                        "relative_path": relative_path,
                        "extension": ext,
                        "content": content,
                        "size": len(content)
                    })
                except Exception as e:
                    print(f"Skipping {filename}: {e}")
    print(f"Found {len(files)} code files.")
    return files

def extract_git_history(repo: Repo) -> list[dict]:
    """Extract commit history with metadata."""
    commits = []
    for commit in repo.iter_commits():
        try:
            commits.append({
                "sha": commit.hexsha[:8],
                "author": commit.author.name,
                "email": commit.author.email,
                "date": commit.authored_datetime,
                "message": commit.message.strip(),
                "files_changed": len(commit.stats.files),
                "insertions": commit.stats.total["insertions"],
                "deletions": commit.stats.total["deletions"],
            })
        except Exception:
            continue
    print(f"Extracted {len(commits)} commits.")
    return commits