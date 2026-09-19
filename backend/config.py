"""Campus Buddy — Centralized configuration and constants."""
import os
import tempfile
from pathlib import Path


def _load_dotenv_file(path):
    """Load simple KEY=VALUE pairs from a local .env file if present.

    No third-party dependency is required. Existing process environment
    values always win, so production/CI environment variables remain safe.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


# Load local environment overrides before backend modules read configuration.
# Process environment values always win; local files are for development/demo only.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_load_dotenv_file(PROJECT_ROOT / '.env')
_load_dotenv_file(PROJECT_ROOT / '.env.local')

# Runtime mode
ENV_NAME = os.environ.get('CAMPUSCONNECT_ENV', 'development').strip().lower()
IS_PRODUCTION = ENV_NAME in {'production', 'prod'}
IS_VERCEL = os.environ.get('VERCEL', '').strip() == '1'
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRES = bool(DATABASE_URL)

# Paths
ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / 'public'
# Vercel Functions have ephemeral writable storage only under /tmp. Database
# records and sessions must use PostgreSQL in production.
_default_data_dir = (
    str(Path(tempfile.gettempdir()) / 'campusconnect') if IS_VERCEL
    else ('/var/data' if IS_PRODUCTION else str(ROOT / 'data'))
)
DATA_DIR = Path(os.environ.get('CAMPUSCONNECT_DATA_DIR', _default_data_dir)).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = DATA_DIR / 'uploads'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DB = Path(os.environ.get('CAMPUSCONNECT_DB_PATH', str(DATA_DIR / 'campusbuddy.db'))).expanduser()
DB.parent.mkdir(parents=True, exist_ok=True)

# Server
PORT = int(os.environ.get('PORT', '3005'))
HOST = os.environ.get('CAMPUSCONNECT_HOST', '0.0.0.0' if IS_PRODUCTION else '127.0.0.1')
_vercel_url = os.environ.get('VERCEL_URL', '').strip().rstrip('/')
if _vercel_url and not _vercel_url.startswith(('http://', 'https://')):
    _vercel_url = f'https://{_vercel_url}'
PUBLIC_BASE_URL = (
    os.environ.get('CAMPUSCONNECT_PUBLIC_URL', '').strip().rstrip('/')
    or os.environ.get('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
    or _vercel_url
)
PRIMARY_ADMIN_LOGIN = os.environ.get('CAMPUSCONNECT_PRIMARY_ADMIN', 'ADMIN001')
SESSION_DAYS = 8
REQUEST_DAYS = 7
SEED_DEMO = os.environ.get('CAMPUSCONNECT_SEED_DEMO', '0' if IS_PRODUCTION else '1').strip() == '1'
BOOTSTRAP_ADMIN_NAME = os.environ.get('CAMPUSCONNECT_BOOTSTRAP_ADMIN_NAME', 'Campus Connect Admin').strip()
BOOTSTRAP_ADMIN_EMAIL = os.environ.get('CAMPUSCONNECT_BOOTSTRAP_ADMIN_EMAIL', '').strip().lower()
BOOTSTRAP_ADMIN_PASSWORD = os.environ.get('CAMPUSCONNECT_BOOTSTRAP_ADMIN_PASSWORD', '')
BOOTSTRAP_ADMIN_MOBILE = os.environ.get('CAMPUSCONNECT_BOOTSTRAP_ADMIN_MOBILE', '0000000000').strip()
MAX_REQUEST_BYTES = int(os.environ.get('CAMPUSCONNECT_MAX_REQUEST_BYTES', str(5 * 1024 * 1024)))
HTTPS = os.environ.get('CAMPUSCONNECT_HTTPS', '1' if IS_PRODUCTION else '0') == '1'
COOKIE_SAMESITE = 'Strict' if IS_PRODUCTION else 'Lax'

# Campus hierarchy
FLOOR_CODES = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
CAMPUSES = ('Dwarka Campus', 'G.B Pant', 'Shakarpur', 'Bhai Premanand')

# Max upload size in bytes (2 MB)
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

# RBAC permission matrix
PERMISSIONS = {
    'super_admin': {
        'view_students', 'view_private_student_data', 'view_lockers',
        'create_lockers', 'modify_lockers', 'approve_locker_requests',
        'release_lockers', 'manage_maintenance', 'review_staff_requests',
        'manage_staff', 'view_audit_logs', 'manage_system_settings',
        'view_notifications',
        # Campus Buddy additions
        'manage_clubs', 'manage_events', 'manage_lost_found',
        'manage_problems', 'manage_calendar',
    },
    'locker_manager': {
        'view_students', 'view_private_student_data', 'view_lockers',
        'create_lockers', 'modify_lockers', 'approve_locker_requests',
        'release_lockers', 'manage_maintenance', 'view_audit_logs',
        'view_notifications',
    },
    'staff': {
        'view_students', 'view_private_student_data', 'view_lockers',
        'approve_locker_requests', 'release_lockers', 'manage_maintenance',
        'view_notifications',
        # Staff can manage clubs/events they are assigned to
        'manage_clubs', 'manage_events', 'manage_problems',
    },
    'student': {
        'view_lockers', 'release_lockers', 'view_notifications',
    },
}
