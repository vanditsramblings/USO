"""Auto-detection engine — inspects script content to extract parameters and metadata."""

import ast
import re

from .models import DetectedParam, DetectionResult

# Patterns for shell variable detection
_SHELL_VAR_RE = re.compile(r'\$\{?([A-Z_][A-Z0-9_]*)\}?')
_SHELL_SECRET_HINTS = {"PASSWORD", "SECRET", "TOKEN", "KEY", "API_KEY", "CREDENTIAL", "AUTH"}

# Python os.environ patterns
_PY_ENVIRON_RE = re.compile(
    r'''os\.environ(?:\.get)?\s*[\(\[]\s*['"]([ A-Z_][A-Z0-9_]*)['"]'''
)
_PY_GETENV_RE = re.compile(r'''os\.getenv\s*\(\s*['"]([A-Z_][A-Z0-9_]*)['"]''')


def _detect_shell(content: str) -> DetectionResult:
    """Detect parameters and description from shell scripts."""
    params: dict[str, DetectedParam] = {}
    description = ""

    # Extract description from first comment block
    lines = content.splitlines()
    desc_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#!"):
            continue
        if stripped.startswith("#"):
            desc_lines.append(stripped.lstrip("# "))
        elif stripped:
            break
    description = " ".join(desc_lines).strip()

    # Find environment variable references
    for match in _SHELL_VAR_RE.finditer(content):
        key = match.group(1)
        if key in ("PATH", "HOME", "USER", "SHELL", "PWD", "TERM"):
            continue
        is_secret = any(hint in key for hint in _SHELL_SECRET_HINTS)
        params[key] = DetectedParam(key=key, is_secret=is_secret, source="shell_var")

    tags = []
    lower = content.lower()
    if any(w in lower for w in ("curl", "wget", "http", "api")):
        tags.append("API")
    if any(w in lower for w in ("docker", "kubectl", "helm")):
        tags.append("DevOps")
    if any(w in lower for w in ("pg_dump", "mysql", "sqlite", "psql")):
        tags.append("Database")

    return DetectionResult(
        description=description, parameters=list(params.values()), tags=tags
    )


def _detect_python(content: str) -> DetectionResult:
    """Detect parameters and description from Python scripts."""
    params: dict[str, DetectedParam] = {}
    description = ""
    tags = []

    # Extract module-level docstring via AST
    try:
        tree = ast.parse(content)
        if tree.body and isinstance(tree.body[0], ast.Expr):
            node = tree.body[0].value
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                description = node.value.strip().split("\n")[0]
    except SyntaxError:
        pass

    # os.environ / os.getenv patterns
    for match in _PY_ENVIRON_RE.finditer(content):
        key = match.group(1)
        is_secret = any(hint in key for hint in _SHELL_SECRET_HINTS)
        params[key] = DetectedParam(key=key, is_secret=is_secret, source="environ")

    for match in _PY_GETENV_RE.finditer(content):
        key = match.group(1)
        is_secret = any(hint in key for hint in _SHELL_SECRET_HINTS)
        params[key] = DetectedParam(key=key, is_secret=is_secret, source="environ")

    # argparse detection
    argparse_re = re.compile(
        r'''add_argument\s*\(\s*['"]--([a-zA-Z_][a-zA-Z0-9_-]*)['"]'''
    )
    for match in argparse_re.finditer(content):
        key = match.group(1).upper().replace("-", "_")
        if key not in params:
            params[key] = DetectedParam(key=key, is_secret=False, source="argparse")

    # Tag heuristics
    lower = content.lower()
    if any(w in lower for w in ("pandas", "dataframe", "csv", "parquet")):
        tags.append("ETL")
    if any(w in lower for w in ("requests", "httpx", "aiohttp", "urllib")):
        tags.append("API")
    if any(w in lower for w in ("sqlalchemy", "psycopg", "sqlite3", "pymongo")):
        tags.append("Database")
    if any(w in lower for w in ("graphql", "gql")):
        tags.append("GraphQL")
    if "schedule" in lower or "cron" in lower:
        tags.append("Automation")

    return DetectionResult(
        description=description, parameters=list(params.values()), tags=tags
    )


def _detect_javascript(content: str) -> DetectionResult:
    """Detect parameters and description from JavaScript scripts."""
    params: dict[str, DetectedParam] = {}
    description = ""

    # Extract description from first JSDoc or comment block
    lines = content.splitlines()
    desc_lines = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("/**"):
            in_block = True
            text = stripped.lstrip("/**").rstrip("*/").strip()
            if text:
                desc_lines.append(text)
            continue
        if in_block:
            if stripped.startswith("*/"):
                break
            desc_lines.append(stripped.lstrip("* "))
            continue
        if stripped.startswith("//"):
            desc_lines.append(stripped.lstrip("/ "))
        elif stripped:
            break
    description = " ".join(desc_lines).strip()

    # process.env detection
    env_re = re.compile(r'process\.env\.([A-Z_][A-Z0-9_]*)')
    env_bracket_re = re.compile(r'''process\.env\[['"]([A-Z_][A-Z0-9_]*)['"]\]''')

    for match in env_re.finditer(content):
        key = match.group(1)
        is_secret = any(hint in key for hint in _SHELL_SECRET_HINTS)
        params[key] = DetectedParam(key=key, is_secret=is_secret, source="environ")

    for match in env_bracket_re.finditer(content):
        key = match.group(1)
        is_secret = any(hint in key for hint in _SHELL_SECRET_HINTS)
        params[key] = DetectedParam(key=key, is_secret=is_secret, source="environ")

    tags = []
    lower = content.lower()
    if any(w in lower for w in ("fetch", "axios", "http")):
        tags.append("API")
    if "graphql" in lower or "gql" in lower:
        tags.append("GraphQL")

    return DetectionResult(
        description=description, parameters=list(params.values()), tags=tags
    )


_DETECTORS = {
    "py": _detect_python,
    "sh": _detect_shell,
    "js": _detect_javascript,
}

# Header comment pattern — matches `# key: value` in the first 20 lines
_HEADER_META_RE = re.compile(r'^#\s*(\w+):\s*(.+)$')


def extract_header_meta(content: str) -> dict:
    """Parse script header comments for UI hints.

    Supported fields (first 20 lines only, no code execution):
        # icon: 💾
        # depends_on: init_env.py, setup.sh
        # tags: database, backup

    Returns a dict with keys: icon, depends_on, tags.
    """
    icon: str | None = None
    depends_on: list[str] = []
    tags: list[str] = []

    for line in content.splitlines()[:20]:
        m = _HEADER_META_RE.match(line.strip())
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2).strip()
        if key == 'icon':
            # Accept only emoji / short safe strings (no HTML)
            safe = re.sub(r'[<>&"\'\\]', '', value)[:8]
            icon = safe or None
        elif key == 'depends_on':
            depends_on = [s.strip() for s in value.split(',') if s.strip()]
        elif key == 'tags':
            tags = [s.strip() for s in value.split(',') if s.strip()]

    return {'icon': icon, 'depends_on': depends_on, 'tags': tags}


def detect(content: str, runtime: str) -> DetectionResult:
    """Inspect script content and return detected parameters, description, and tags."""
    detector = _DETECTORS.get(runtime)
    if not detector:
        return DetectionResult(description="", parameters=[], tags=[])
    return detector(content)
