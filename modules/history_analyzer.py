import pandas as pd
from git import Repo
from collections import defaultdict
import re

CONFLICT_KEYWORDS = [
    'merge conflict', 'fix conflict', 'resolve conflict',
    'resolved conflict', 'conflicting', 'conflict resolution'
]

COMMIT_CATEGORIES = {
    'bugfix': ['fix', 'bug', 'patch', 'resolve', 'hotfix', 'issue'],
    'feature': ['feat', 'add', 'implement', 'new', 'create', 'introduce'],
    'refactor': ['refactor', 'clean', 'restructure', 'improve', 'optimize'],
    'test': ['test', 'spec', 'coverage', 'unit', 'integration'],
    'docs': ['doc', 'readme', 'comment', 'changelog'],
    'chore': ['chore', 'bump', 'update', 'upgrade', 'dependency']
}

def classify_commit(message: str) -> str:
    """Classify commit message into category."""
    msg = message.lower()
    for category, keywords in COMMIT_CATEGORIES.items():
        if any(k in msg for k in keywords):
            return category
    return 'other'

def detect_conflict_commits(commits: list[dict]) -> list[dict]:
    """Find commits that mention merge conflicts."""
    conflict_commits = []
    for commit in commits:
        msg = commit['message'].lower()
        if any(kw in msg for kw in CONFLICT_KEYWORDS):
            conflict_commits.append(commit)
    return conflict_commits

def get_file_collision_risk(commits: list[dict], repo: Repo) -> dict:
    """Find files touched by multiple contributors — high collision risk."""
    file_authors = defaultdict(set)
    file_touch_count = defaultdict(int)

    for commit in repo.iter_commits():
        try:
            author = commit.author.name
            for filepath in commit.stats.files:
                file_authors[filepath].add(author)
                file_touch_count[filepath] += 1
        except Exception:
            continue

    collision_risk = {}
    for filepath, authors in file_authors.items():
        if len(authors) > 1:
            collision_risk[filepath] = {
                "contributors": list(authors),
                "contributor_count": len(authors),
                "total_touches": file_touch_count[filepath],
                "risk_level": "High" if len(authors) >= 4 else "Medium" if len(authors) >= 2 else "Low"
            }

    return dict(sorted(collision_risk.items(),
                key=lambda x: x[1]['contributor_count'], reverse=True)[:20])

def analyze_contributors(commits: list[dict]) -> pd.DataFrame:
    """Contributor stats — commits, insertions, deletions per author."""
    stats = defaultdict(lambda: {
        'commits': 0, 'insertions': 0,
        'deletions': 0, 'files_changed': 0
    })
    for commit in commits:
        author = commit['author']
        stats[author]['commits'] += 1
        stats[author]['insertions'] += commit['insertions']
        stats[author]['deletions'] += commit['deletions']
        stats[author]['files_changed'] += commit['files_changed']

    df = pd.DataFrame([
        {'author': author, **data}
        for author, data in stats.items()
    ])
    return df.sort_values('commits', ascending=False).reset_index(drop=True)

def analyze_commit_timeline(commits: list[dict]) -> pd.DataFrame:
    """Commits over time for timeline chart."""
    df = pd.DataFrame(commits)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date_only'] = df['date'].dt.date
    df['category'] = df['message'].apply(classify_commit)
    timeline = df.groupby('date_only').size().reset_index(name='commit_count')
    return timeline

def analyze_file_churn(commits: list[dict]) -> pd.DataFrame:
    """Most frequently changed files — churn analysis."""
    file_stats = defaultdict(lambda: {'changes': 0, 'insertions': 0, 'deletions': 0})
    for commit in commits:
        for filepath, stats in commit.get('file_details', {}).items():
            file_stats[filepath]['changes'] += 1
            file_stats[filepath]['insertions'] += stats.get('insertions', 0)
            file_stats[filepath]['deletions'] += stats.get('deletions', 0)

    df = pd.DataFrame([
        {'file': f, **s} for f, s in file_stats.items()
    ])
    if df.empty:
        return df
    return df.sort_values('changes', ascending=False).head(20).reset_index(drop=True)

def get_full_analysis(commits: list[dict], repo: Repo) -> dict:
    """Run all history analysis and return combined results."""
    return {
        "contributors": analyze_contributors(commits),
        "timeline": analyze_commit_timeline(commits),
        "conflict_commits": detect_conflict_commits(commits),
        "collision_risk": get_file_collision_risk(commits, repo),
        "total_commits": len(commits),
        "total_authors": len(set(c['author'] for c in commits)),
    }