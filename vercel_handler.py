"""Adapter that runs the existing Campus Connect router as a Vercel Function.

Vercel owns the HTTP server process. This module exposes a request handler and
never starts ``serve_forever()``.
"""
from __future__ import annotations

import os
import threading
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.database import seed
from server import Handler


_init_lock = threading.Lock()
_initialized = False
_logger = logging.getLogger(__name__)


def _required_vercel_settings():
    """Return settings required to avoid an ephemeral SQLite deployment."""
    missing = []
    if os.environ.get('CAMPUSCONNECT_ENV', '').strip().lower() not in {'production', 'prod'}:
        missing.append('CAMPUSCONNECT_ENV')
    if not os.environ.get('DATABASE_URL', '').strip():
        missing.append('DATABASE_URL')
    return missing


def _initialize_application():
    """Migrate/seed once per warm Function instance."""
    global _initialized
    if _initialized:
        return True

    with _init_lock:
        if _initialized:
            return True
        try:
            if os.environ.get('VERCEL', '').strip() == '1':
                if _required_vercel_settings():
                    raise RuntimeError('Missing Vercel production configuration.')
            seed()
            _initialized = True
            return True
        except Exception:
            # Detailed failures remain in Vercel Function Logs only. Browser
            # responses must not reveal configuration or database information.
            _logger.exception('Campus Connect function initialization failed')
            return False


class VercelHandler(Handler):
    """Existing router with Vercel-safe initialization and errors."""

    def _ready_or_503(self):
        if _initialize_application():
            return True
        self.send_json(
            {'error': 'The service is not configured correctly. Please contact the administrator.'},
            503,
        )
        return False

    def _restore_qr_path(self):
        """Preserve the existing /q/<token> route through Vercel's API map."""
        parsed = urlsplit(self.path)
        if parsed.path.startswith('/api/q/'):
            self.path = urlunsplit((
                parsed.scheme,
                parsed.netloc,
                '/q/' + parsed.path[len('/api/q/'):],
                parsed.query,
                parsed.fragment,
            ))

    def _restore_api_path(self):
        """Recover the public API path after the Vercel router rewrite."""
        parsed = urlsplit(self.path)
        if parsed.path != '/api/router':
            return

        route = ''
        remaining_query = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if key == '__campusconnect_route' and not route:
                route = value.strip('/')
            else:
                remaining_query.append((key, value))

        api_path = '/api' if not route else f'/api/{route}'
        self.path = urlunsplit((
            parsed.scheme,
            parsed.netloc,
            api_path,
            urlencode(remaining_query),
            parsed.fragment,
        ))

    def do_GET(self):
        if self._ready_or_503():
            self._restore_api_path()
            self._restore_qr_path()
            super().do_GET()

    def do_POST(self):
        if self._ready_or_503():
            self._restore_api_path()
            super().do_POST()

    def do_PATCH(self):
        if self._ready_or_503():
            self._restore_api_path()
            super().do_PATCH()
