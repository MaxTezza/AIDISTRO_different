#!/usr/bin/env python3
"""
AI Distro — File Intelligence

Semantic search over the user's home directory. Indexes filenames, paths,
and text content with TF-IDF for natural language queries like "that PDF
about taxes from last week."

Architecture:
  - Background indexer crawls ~/Documents, ~/Downloads, ~/Desktop, etc.
  - Extracts text from PDF, TXT, MD, HTML, DOCX, and code files
  - Builds a TF-IDF search index with SQLite persistence
  - Supports metadata filters: file type, date range, size
  - Incremental re-indexing via modification time tracking

Usage:
  python3 file_intelligence.py search "taxes PDF last week"
  python3 file_intelligence.py index               # Full re-index
  python3 file_intelligence.py index --incremental  # Update changed files only
  python3 file_intelligence.py recent [n]           # Recently modified files
  python3 file_intelligence.py stats                # Index statistics
  python3 file_intelligence.py find <pattern>       # Glob search
"""
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

INDEX_DB = Path(os.path.expanduser("~/.cache/ai-distro/file_index.db"))
HOME = Path.home()

# Directories to index
INDEX_DIRS = [
    HOME / "Documents",
    HOME / "Downloads",
    HOME / "Desktop",
    HOME / "Pictures",
    HOME / "Music",
    HOME / "Videos",
    HOME / "Projects",
    HOME / "Code",
    HOME / "src",
    HOME / "dev",
]

# File types to index content from
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".org", ".log", ".csv", ".tsv", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".rb",
    ".sh", ".bash", ".zsh", ".fish", ".ps1",
    ".html", ".htm", ".xml", ".css", ".scss",
    ".sql", ".r", ".jl", ".lua", ".php", ".swift", ".kt",
    ".tex", ".bib",
}

PDF_EXTENSION = ".pdf"
DOCX_EXTENSION = ".docx"

# Skip patterns
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".cache", ".local",
             "venv", ".venv", ".tox", "target", "build", "dist", ".next"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_CONTENT_CHARS = 50000

STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could i me my we our you your he she it they them "
    "this that these those am to in for on with at by from of and but or not no "
    "so if then else than too very just about also how what when where which who "
    "all each every both few more most other some such".split()
)


def _init_db():
    INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(INDEX_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        extension TEXT,
        size INTEGER,
        modified REAL,
        indexed_at REAL,
        tokens TEXT,
        content_preview TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS doc_freq (
        term TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON files(path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ext ON files(extension)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_modified ON files(modified)")
    conn.commit()
    conn.close()


def _tokenize(text):
    """Tokenize text for search indexing."""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]


def _extract_text(filepath):
    """Extract searchable text content from a file."""
    ext = filepath.suffix.lower()
    try:
        if ext in TEXT_EXTENSIONS:
            with open(filepath, "r", errors="ignore") as f:
                return f.read(MAX_CONTENT_CHARS)

        elif ext == PDF_EXTENSION:
            return _extract_pdf(filepath)

        elif ext == DOCX_EXTENSION:
            return _extract_docx(filepath)

    except Exception:
        pass
    return ""


def _extract_pdf(filepath):
    """Extract text from PDF using pdftotext or fallback."""
    try:
        import subprocess
        r = subprocess.run(
            ["pdftotext", str(filepath), "-"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return r.stdout[:MAX_CONTENT_CHARS]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: try basic binary extraction
    try:
        with open(filepath, "rb") as f:
            data = f.read(MAX_FILE_SIZE)
        text_chunks = re.findall(rb"\(([^)]+)\)", data)
        return " ".join(c.decode("latin-1", errors="ignore") for c in text_chunks[:500])
    except Exception:
        return ""


def _extract_docx(filepath):
    """Extract text from DOCX (ZIP of XML)."""
    try:
        import zipfile
        with zipfile.ZipFile(filepath) as z:
            with z.open("word/document.xml") as doc:
                content = doc.read().decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", content)
                return text[:MAX_CONTENT_CHARS]
    except Exception:
        return ""


def _should_skip(path):
    """Check if a path should be skipped."""
    parts = path.parts
    return any(skip in parts for skip in SKIP_DIRS)


# ═══════════════════════════════════════════════════════════════════
# Indexing
# ═══════════════════════════════════════════════════════════════════

def index_files(incremental=True):
    """Index files in configured directories."""
    _init_db()
    conn = sqlite3.connect(str(INDEX_DB))

    # Get existing index for incremental
    existing = {}
    if incremental:
        rows = conn.execute("SELECT path, modified FROM files").fetchall()
        existing = {r[0]: r[1] for r in rows}

    indexed = 0
    skipped = 0
    errors = 0

    for base_dir in INDEX_DIRS:
        if not base_dir.exists():
            continue

        for filepath in base_dir.rglob("*"):
            if not filepath.is_file():
                continue
            if _should_skip(filepath):
                continue
            if filepath.stat().st_size > MAX_FILE_SIZE:
                continue

            path_str = str(filepath)
            mtime = filepath.stat().st_mtime

            # Skip if unchanged (incremental)
            if incremental and path_str in existing:
                if existing[path_str] and abs(existing[path_str] - mtime) < 1:
                    skipped += 1
                    continue

            try:
                # Build token set from filename + path + content
                name_tokens = _tokenize(filepath.stem)
                path_tokens = _tokenize(str(filepath.parent))
                content = _extract_text(filepath)
                content_tokens = _tokenize(content) if content else []

                all_tokens = name_tokens + path_tokens + content_tokens
                preview = content[:300] if content else ""

                # Update DB
                conn.execute(
                    "INSERT OR REPLACE INTO files "
                    "(path, filename, extension, size, modified, indexed_at, tokens, content_preview) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (path_str, filepath.name, filepath.suffix.lower(),
                     filepath.stat().st_size, mtime, datetime.now().timestamp(),
                     json.dumps(all_tokens[:500]), preview)
                )

                # Update document frequency
                for term in set(all_tokens):
                    conn.execute(
                        "INSERT INTO doc_freq (term, count) VALUES (?, 1) "
                        "ON CONFLICT(term) DO UPDATE SET count = count + 1",
                        (term,)
                    )

                indexed += 1

                if indexed % 100 == 0:
                    conn.commit()
                    print(f"  Indexed {indexed} files...", end="\r")

            except Exception:
                errors += 1

    conn.commit()
    conn.close()

    return {"indexed": indexed, "skipped": skipped, "errors": errors}


# ═══════════════════════════════════════════════════════════════════
# Search
# ═══════════════════════════════════════════════════════════════════

def search(query, top_k=20, file_type=None, days=None):
    """Semantic search over indexed files."""
    _init_db()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    conn = sqlite3.connect(str(INDEX_DB))

    # Get total doc count for IDF
    num_docs = max(conn.execute("SELECT COUNT(*) FROM files").fetchone()[0], 1)

    # Compute query TF-IDF
    query_tf = Counter(query_tokens)
    total_q = len(query_tokens)
    query_vec = {}
    for term, count in query_tf.items():
        tf = count / total_q
        df_row = conn.execute("SELECT count FROM doc_freq WHERE term = ?", (term,)).fetchone()
        idf = math.log(num_docs / (df_row[0] if df_row else 1)) + 1.0
        query_vec[term] = tf * idf

    # Build filter conditions
    conditions = []
    params = []
    if file_type:
        conditions.append("extension = ?")
        params.append(f".{file_type.lstrip('.')}")
    if days:
        cutoff = datetime.now().timestamp() - (days * 86400)
        conditions.append("modified >= ?")
        params.append(cutoff)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = conn.execute(
        f"SELECT path, filename, extension, size, modified, tokens, content_preview "
        f"FROM files {where} ORDER BY modified DESC LIMIT 1000",
        params
    ).fetchall()

    # Score each document
    scored = []
    for row in rows:
        doc_tokens = json.loads(row[5]) if row[5] else []
        if not doc_tokens:
            continue

        doc_tf = Counter(doc_tokens)
        total_d = len(doc_tokens) or 1
        doc_vec = {}
        for term, count in doc_tf.items():
            if term in query_vec:
                tf = count / total_d
                df_row = conn.execute("SELECT count FROM doc_freq WHERE term = ?", (term,)).fetchone()
                idf = math.log(num_docs / (df_row[0] if df_row else 1)) + 1.0
                doc_vec[term] = tf * idf

        if not doc_vec:
            continue

        # Cosine similarity
        common = set(query_vec.keys()) & set(doc_vec.keys())
        dot = sum(query_vec[k] * doc_vec[k] for k in common)
        mag_q = math.sqrt(sum(v ** 2 for v in query_vec.values()))
        mag_d = math.sqrt(sum(v ** 2 for v in doc_vec.values()))
        sim = dot / (mag_q * mag_d) if mag_q and mag_d else 0

        if sim > 0.02:
            scored.append({
                "path": row[0],
                "filename": row[1],
                "extension": row[2],
                "size_kb": round(row[3] / 1024, 1),
                "modified": datetime.fromtimestamp(row[4]).strftime("%Y-%m-%d %H:%M"),
                "similarity": round(sim, 4),
                "preview": row[6][:200] if row[6] else "",
            })

    conn.close()
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def find_glob(pattern):
    """Simple glob-based file search."""
    results = []
    for base_dir in INDEX_DIRS:
        if not base_dir.exists():
            continue
        for match in base_dir.rglob(pattern):
            if match.is_file():
                results.append({
                    "path": str(match),
                    "filename": match.name,
                    "size_kb": round(match.stat().st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(match.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    return results[:50]


def recent_files(n=20):
    """Get the most recently modified files."""
    _init_db()
    conn = sqlite3.connect(str(INDEX_DB))
    rows = conn.execute(
        "SELECT path, filename, extension, size, modified "
        "FROM files ORDER BY modified DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [{
        "path": r[0], "filename": r[1], "extension": r[2],
        "size_kb": round(r[3] / 1024, 1),
        "modified": datetime.fromtimestamp(r[4]).strftime("%Y-%m-%d %H:%M"),
    } for r in rows]


def stats():
    """Index statistics."""
    _init_db()
    conn = sqlite3.connect(str(INDEX_DB))
    total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    terms = conn.execute("SELECT COUNT(*) FROM doc_freq").fetchone()[0]

    by_ext = conn.execute(
        "SELECT extension, COUNT(*) as c FROM files GROUP BY extension ORDER BY c DESC LIMIT 15"
    ).fetchall()

    total_size = conn.execute("SELECT SUM(size) FROM files").fetchone()[0] or 0
    oldest = conn.execute("SELECT MIN(indexed_at) FROM files").fetchone()[0]
    conn.close()

    return {
        "total_files": total,
        "unique_terms": terms,
        "total_size_mb": round(total_size / (1024 * 1024), 1),
        "by_extension": {r[0]: r[1] for r in by_ext},
        "last_indexed": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
        "indexed_dirs": [str(d) for d in INDEX_DIRS if d.exists()],
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: file_intelligence.py <search|index|recent|stats|find>")
        return

    cmd = sys.argv[1]

    if cmd == "search":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: file_intelligence.py search <query>")
            return
        results = search(query)
        if results:
            for r in results:
                print(f"  [{r['similarity']:.3f}] {r['filename']}  ({r['size_kb']}KB, {r['modified']})")
                print(f"         {r['path']}")
                if r['preview']:
                    print(f"         {r['preview'][:100]}...")
                print()
        else:
            print("No results found.")

    elif cmd == "index":
        incremental = "--incremental" in sys.argv or "-i" in sys.argv
        print(f"Indexing files ({'incremental' if incremental else 'full'})...")
        result = index_files(incremental=incremental)
        print(json.dumps(result, indent=2))

    elif cmd == "recent":
        n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 20
        print(json.dumps(recent_files(n), indent=2))

    elif cmd == "stats":
        print(json.dumps(stats(), indent=2))

    elif cmd == "find":
        pattern = sys.argv[2] if len(sys.argv) > 2 else "*"
        print(json.dumps(find_glob(pattern), indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
