"""Campus Connect — Main HTTP server and API router.

This is the entry point. Run with: py server.py
Then open: http://localhost:3000

All business logic lives in backend/ modules. This file handles:
- HTTP request parsing
- Session management
- API route dispatching
- Static file serving
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from pathlib import Path
import json, secrets, re, os, sqlite3, time
from collections import defaultdict, deque

# Backend modules
from backend.config import ROOT, PUBLIC, PORT, HOST, SESSION_DAYS, PERMISSIONS, MAX_REQUEST_BYTES, HTTPS
from backend.utils import conn, now, later, get_permissions, make_cookie, public_user, DatabaseError
from backend.database import seed

# Route handlers
from backend import auth as auth_routes
from backend import lockers as locker_routes
from backend import campus_life
from backend import services


class Handler(BaseHTTPRequestHandler):
    """Main HTTP request handler for Campus Connect."""

    # Small single-process abuse guard for unauthenticated email/login endpoints.
    _rate_hits = defaultdict(deque)
    _rate_rules = {
        '/api/auth/signup': (10, 600),
        '/api/auth/resend-otp': (10, 600),
        '/api/auth/login': (30, 60),
    }

    @classmethod
    def _rate_limited(cls, path, ip):
        rule = cls._rate_rules.get(path)
        if not rule:
            return False
        limit, window = rule
        now_m = time.monotonic()
        key = (path, ip)
        q = cls._rate_hits[key]
        cutoff = now_m - window
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now_m)
        return False

    def log_message(self, *args):
        pass  # Suppress default access logging

    def send_response(self, code, message=None):
        super().send_response(code, message)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        if HTTPS:
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

    # ── Response helpers ──────────────────────────────────────────────
    def send_json(self, obj, status=200, headers=None):
        """Send a JSON response with proper headers."""
        body = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        """Parse the JSON request body."""
        try:
            n = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValueError('Invalid Content-Length')
        if n > MAX_REQUEST_BYTES:
            raise ValueError('Request body too large')
        raw = self.rfile.read(n) or b'{}'
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON body')

    # ── Session management ────────────────────────────────────────────
    def get_session_id(self):
        """Extract session ID from cookie header."""
        for part in self.headers.get('Cookie', '').split(';'):
            k, _, v = part.strip().partition('=')
            if k == 'sid':
                return v
        return None

    def create_session(self, user_id):
        """Create a new session in the database and return the session ID."""
        sid = secrets.token_urlsafe(32)
        c = conn()
        c.execute('DELETE FROM sessions WHERE expires_at<?', (now(),))
        c.execute(
            'INSERT INTO sessions(id,user_id,created_at,expires_at,'
            'last_seen_at,ip,user_agent) VALUES(?,?,?,?,?,?,?)',
            (sid, user_id, now(), later(SESSION_DAYS), now(),
             self.client_address[0],
             self.headers.get('User-Agent', '')[:300]),
        )
        c.commit()
        c.close()
        return sid

    def auth(self, permission=None):
        """Authenticate the current request.

        Returns the user row if authenticated (and authorized for the
        given permission), or None if the response has already been sent
        with an error.
        """
        sid = self.get_session_id()
        if not sid:
            self.send_json({'error': 'Sign in required.'}, 401)
            return None
        c = conn()
        row = c.execute(
            'SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id '
            'WHERE s.id=? AND s.expires_at>? AND u.active=1',
            (sid, now()),
        ).fetchone()
        if not row:
            c.close()
            self.send_json(
                {'error': 'Session expired. Please sign in again.'}, 401
            )
            return None
        c.execute(
            'UPDATE sessions SET last_seen_at=? WHERE id=?', (now(), sid)
        )
        c.commit()
        c.close()
        self.sid = sid
        if permission and permission not in get_permissions(row):
            self.send_json(
                {'error': 'You do not have permission for this area.'}, 403
            )
            return None
        return row

    # ── HTTP method handlers ──────────────────────────────────────────
    def do_GET(self):
        p = unquote(urlparse(self.path).path)
        # QR PNG route must come before generic API dispatch
        if re.fullmatch(r'/api/lockers/[^/]+/qr\.png', p):
            return locker_routes.handle_qr_png(self, unquote(p.split('/')[-2]))
        if p.startswith('/api/'):
            return self.api('GET', p)
        if p.startswith('/q/'):
            return locker_routes.handle_qr_landing(self, unquote(p[3:]))
        # Static file serving
        rel = p.lstrip('/') or 'index.html'
        f = (PUBLIC / rel).resolve()
        if not str(f).startswith(str(PUBLIC.resolve())) or not f.is_file():
            f = PUBLIC / 'index.html'
        mime = {
            '.html': 'text/html', '.js': 'application/javascript',
            '.css': 'text/css', '.png': 'image/png',
            '.jpg': 'image/jpeg', '.gif': 'image/gif',
            '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
            '.woff2': 'font/woff2', '.woff': 'font/woff',
        }.get(f.suffix, 'application/octet-stream')
        data = f.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        p = urlparse(self.path).path
        if p.startswith('/api/'):
            return self.api('POST', p)
        self.send_error(404)

    def do_PATCH(self):
        p = urlparse(self.path).path
        if p.startswith('/api/'):
            return self.api('PATCH', p)
        self.send_error(404)

    # ── API Router ────────────────────────────────────────────────────
    def api(self, method, path):
        """Dispatch API requests to the appropriate handler module."""
        try:
            if method == 'GET' and path == '/api/health':
                return self.send_json({'status': 'ok'})

            if method == 'POST' and path in self._rate_rules:
                if self._rate_limited(path, self.client_address[0]):
                    return self.send_json({'error': 'Too many requests. Please try again shortly.'}, 429, {'Retry-After': '60'})
            # ─── Auth routes ──────────────────────────────────────
            routes = {
                ('POST', '/api/auth/login'): lambda: auth_routes.handle_login(self),
                ('POST', '/api/auth/signup'): lambda: auth_routes.handle_signup(self),
                ('POST', '/api/auth/resend-otp'): lambda: auth_routes.handle_resend_otp(self),
                ('POST', '/api/auth/verify-otp'): lambda: auth_routes.handle_verify_otp(self),
                ('POST', '/api/auth/logout'): lambda: auth_routes.handle_logout(self),
                ('GET', '/api/me'): lambda: auth_routes.handle_me(self),

                # ─── Locker/Dashboard routes ──────────────────────
                ('GET', '/api/dashboard'): lambda: locker_routes.handle_dashboard(self),
                ('GET', '/api/lockers'): lambda: locker_routes.handle_lockers(self),
                ('GET', '/api/rooms'): lambda: locker_routes.handle_rooms(self),
                ('GET', '/api/requests'): lambda: locker_routes.handle_requests(self),
                ('GET', '/api/staff-requests'): lambda: locker_routes.handle_staff_requests(self),
                ('GET', '/api/students'): lambda: locker_routes.handle_students(self),
                ('POST', '/api/students'): lambda: locker_routes.handle_add_student(self),
                ('POST', '/api/profile/update'): lambda: locker_routes.handle_update_profile(self),
                ('PATCH', '/api/profile/update'): lambda: locker_routes.handle_update_profile(self),
                ('GET', '/api/notifications'): lambda: locker_routes.handle_notifications(self),
                ('POST', '/api/notifications/read-all'): lambda: locker_routes.handle_mark_notifications_all(self),
                ('GET', '/api/audit'): lambda: locker_routes.handle_audit_view(self),
                ('GET', '/api/maintenance'): lambda: locker_routes.handle_maintenance_view(self),
                ('POST', '/api/maintenance'): lambda: locker_routes.handle_maintenance_create(self),
                
                # ─── Campus Life routes ───────────────────────────
                ('GET', '/api/clubs'): lambda: campus_life.handle_get_clubs(self),
                ('POST', '/api/clubs'): lambda: campus_life.handle_create_club(self),
                ('GET', '/api/events'): lambda: campus_life.handle_get_events(self),
                ('POST', '/api/events'): lambda: campus_life.handle_create_event(self),
                ('GET', '/api/my-requests'): lambda: campus_life.handle_my_requests(self),
                ('GET', '/api/clubs/requests-queue'): lambda: campus_life.handle_club_requests_queue(self),
                
                # ─── Campus Services routes ───────────────────────
                ('GET', '/api/lostfound'): lambda: services.handle_get_lost_found(self),
                ('POST', '/api/lostfound'): lambda: services.handle_create_lost_found(self),
                ('GET', '/api/problems'): lambda: services.handle_get_problems(self),
                ('POST', '/api/problems'): lambda: services.handle_create_problem(self),
                ('POST', '/api/notices/broadcast'): lambda: services.handle_broadcast_notice(self),
            }

            if (method, path) in routes:
                return routes[(method, path)]()

            # ─── Dynamic locker routes ────────────────────────────
            if method == 'GET' and re.fullmatch(r'/api/lockers/[^/]+', path):
                return locker_routes.handle_locker_detail(
                    self, unquote(path.split('/')[-1])
                )
            if method == 'GET' and re.fullmatch(r'/api/lockers/[^/]+/qr', path):
                return locker_routes.handle_locker_qr_json(
                    self, unquote(path.split('/')[-2])
                )
            if method == 'GET' and re.fullmatch(r'/api/qr/[^/]+', path):
                return locker_routes.handle_qr_info(
                    self, unquote(path.split('/')[-1])
                )
            if method == 'POST' and path == '/api/lockers/bulk':
                return locker_routes.handle_add_lockers(self)

            if method == 'POST' and re.fullmatch(
                r'/api/lockers/[^/]+/(request|release|maintenance)', path
            ):
                bits = path.split('/')
                lid = unquote(bits[3])
                action = bits[4]
                dispatch = {
                    'request': locker_routes.handle_request_locker,
                    'release': locker_routes.handle_release_locker,
                    'maintenance': locker_routes.handle_maintenance_toggle,
                }
                return dispatch[action](self, lid)

            if method == 'POST' and re.fullmatch(
                r'/api/requests/[^/]+/(approve|reject|cancel)', path
            ):
                bits = path.split('/')
                return locker_routes.handle_review(
                    self, unquote(bits[3]), bits[4]
                )

            if method == 'POST' and re.fullmatch(
                r'/api/staff-requests/[^/]+/(approve|reject)', path
            ):
                bits = path.split('/')
                return locker_routes.handle_review_staff(
                    self, unquote(bits[3]), bits[4]
                )

            if method == 'POST' and re.fullmatch(
                r'/api/notifications/\d+/read', path
            ):
                return locker_routes.handle_mark_notification(
                    self, int(path.split('/')[-2])
                )

            if method == 'POST' and re.fullmatch(
                r'/api/maintenance/\d+/(acknowledge|repair|resolve)', path
            ):
                bits = path.split('/')
                return locker_routes.handle_maintenance_transition(
                    self, int(bits[-2]), bits[-1]
                )

            # ─── Dynamic Club routes ──────────────────────────
            if method == 'GET' and re.fullmatch(r'/api/clubs/\d+', path):
                return campus_life.handle_get_club_detail(self, int(path.split('/')[-1]))

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/join', path):
                return campus_life.handle_join_club(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/leave', path):
                return campus_life.handle_leave_club(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/review/(approve|reject)', path):
                bits = path.split('/')
                return campus_life.handle_review_club(self, int(bits[3]), bits[5])

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/members/\d+/(approve|reject)', path):
                bits = path.split('/')
                return campus_life.handle_review_membership(self, int(bits[3]), int(bits[5]), bits[6])

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/members/\d+/role', path):
                bits = path.split('/')
                return campus_life.handle_assign_role(self, int(bits[3]), int(bits[5]))

            if method == 'GET' and re.fullmatch(r'/api/clubs/\d+/events', path):
                return campus_life.handle_get_club_events(self, int(path.split('/')[-2]))

            if method == 'GET' and re.fullmatch(r'/api/clubs/\d+/meetings', path):
                return campus_life.handle_get_club_meetings(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/meetings', path):
                return campus_life.handle_create_club_meeting(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/meetings/\d+/rsvp/(going|not_going)', path):
                bits = path.split('/')
                return campus_life.handle_rsvp_meeting(self, int(bits[3]), bits[5])

            if method == 'GET' and re.fullmatch(r'/api/clubs/\d+/gallery', path):
                return campus_life.handle_get_club_gallery(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/gallery', path):
                return campus_life.handle_add_gallery_photo(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/clubs/\d+/gallery/\d+/delete', path):
                bits = path.split('/')
                return campus_life.handle_delete_gallery_photo(self, int(bits[3]), int(bits[5]))

            # ─── Dynamic Event routes ─────────────────────────
            if method == 'GET' and re.fullmatch(r'/api/events/\d+', path):
                return campus_life.handle_get_event_detail(self, int(path.split('/')[-1]))

            if method == 'GET' and re.fullmatch(r'/api/lostfound/\d+', path):
                return services.handle_get_lost_found_detail(self, int(path.split('/')[-1]))

            if method == 'POST' and re.fullmatch(r'/api/lostfound/\d+/remove', path):
                return services.handle_remove_lost_found(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/events/\d+/register', path):
                return campus_life.handle_register_event(self, int(path.split('/')[-2]))

            if method == 'GET' and re.fullmatch(r'/api/events/\d+/form', path):
                return campus_life.handle_get_event_form(self, int(path.split('/')[-2]))

            if method == 'GET' and re.fullmatch(r'/api/events/\d+/registrants', path):
                return campus_life.handle_get_event_registrants(self, int(path.split('/')[-2]))

            if method == 'POST' and re.fullmatch(r'/api/events/\d+/registrants/\d+/payment/(verify|reject)', path):
                bits = path.split('/')
                return campus_life.handle_review_payment(self, int(bits[3]), int(bits[5]), bits[7])

            # ─── 404 for unmatched API routes ─────────────────────
            self.send_json({'error': 'API route not found'}, 404)

        except (sqlite3.Error, DatabaseError, ValueError, KeyError, TypeError) as e:
            self.send_json(
                {
                    'error': 'Request could not be completed.',
                    'detail': str(e) if os.environ.get('CAMPUSBUDDY_DEBUG') else None,
                },
                500,
            )


def main():
    """Start the Campus Connect server."""
    try:
        seed()
    except RuntimeError as exc:
        raise SystemExit(f'CampusConnect startup blocked: {exc}') from exc
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    public = os.environ.get('CAMPUSCONNECT_PUBLIC_URL', f'http://127.0.0.1:{PORT}')
    print(f'Campus Connect -> {public}')
    server.serve_forever()


if __name__ == '__main__':
    main()
