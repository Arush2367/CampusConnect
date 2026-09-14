from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parent.parent
BAD_FILES = {'.env'}
SECRET_PATTERNS = [
    re.compile(r'AIza[0-9A-Za-z_-]{20,}'),
    re.compile(r'(?i)\bsk-[A-Za-z0-9]{20,}'),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}'),
    re.compile(r'(?i)\b(xox[baprs]-[A-Za-z0-9-]{10,})'),
    re.compile(r'-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----'),
]
ALLOWED_ENV_EXAMPLE = ROOT / '.env.example'
errors = []
for path in ROOT.rglob('*'):
    if not path.is_file() or '.git' in path.parts or path.name in {'campusbuddy.db', 'test_email_outbox.jsonl'}:
        continue
    rel = path.relative_to(ROOT)
    if path.name in BAD_FILES:
        errors.append(f'forbidden secret file present: {rel}')
        continue
    if path == ALLOWED_ENV_EXAMPLE:
        continue
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for rx in SECRET_PATTERNS:
        if rx.search(text):
            errors.append(f'possible secret pattern in {rel}')
            break

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('SECURITY_CHECK_PASSED')
