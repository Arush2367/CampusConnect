from backend.utils import DatabaseIntegrityError, DatabaseOperationalError
"""Campus Buddy — CampusLock locker endpoints."""
import secrets, re, uuid, sqlite3
from urllib.parse import urlparse, parse_qs, unquote

from backend.config import FLOOR_CODES, PORT, PUBLIC_BASE_URL
from backend.utils import (
    conn, now, later, audit, notify, locker_event, get_permissions,
)
from backend.database import expire_requests

try:
    import qrcode
except ImportError:
    qrcode = None

REQUEST_DAYS = 7


def handle_dashboard(handler):
    """GET /api/dashboard"""
    r = handler.auth()
    if not r:
        return
    c = conn()
    expire_requests(c)

    counts = dict(c.execute(
        "SELECT COUNT(*) total,"
        "COALESCE(SUM(status='available'),0) available,"
        "COALESCE(SUM(status='occupied'),0) occupied,"
        "COALESCE(SUM(status='pending'),0) pending,"
        "COALESCE(SUM(status='maintenance'),0) maintenance "
        "FROM lockers"
    ).fetchone())
    counts['staff_pending'] = c.execute(
        "SELECT COUNT(*) FROM staff_requests WHERE status='pending'"
    ).fetchone()[0]
    counts['unresolved_maintenance'] = c.execute(
        "SELECT COUNT(*) FROM maintenance_records WHERE status<>'resolved'"
    ).fetchone()[0]

    floors = [dict(x) for x in c.execute(
        "SELECT f.floor_number,f.code,COUNT(l.id) total,"
        "COALESCE(SUM(l.status='available'),0) available,"
        "COALESCE(SUM(l.status='occupied'),0) occupied,"
        "COALESCE(SUM(l.status='pending'),0) pending,"
        "COALESCE(SUM(l.status='maintenance'),0) maintenance "
        "FROM floors f LEFT JOIN locker_rooms rr ON rr.floor_id=f.id "
        "LEFT JOIN lockers l ON l.room_id=rr.id "
        "GROUP BY f.id ORDER BY f.floor_number"
    ).fetchall()]

    my_locker = my_request = None
    if r['access_role'] == 'student':
        z = c.execute(
            "SELECT l.locker_id,l.status,l.assigned_at,rr.room_code,"
            "f.floor_number FROM lockers l "
            "JOIN locker_rooms rr ON rr.id=l.room_id "
            "JOIN floors f ON f.id=rr.floor_id "
            "WHERE l.student_user_id=? AND l.status='occupied'",
            (r['id'],)
        ).fetchone()
        my_locker = dict(z) if z else None
        z = c.execute(
            "SELECT lr.request_code,lr.status,l.locker_id,lr.created_at,"
            "lr.reviewed_at,lr.rejection_reason,lr.expires_at "
            "FROM locker_requests lr JOIN lockers l ON l.id=lr.locker_id "
            "WHERE lr.student_user_id=? ORDER BY lr.id DESC LIMIT 1",
            (r['id'],)
        ).fetchone()
        my_request = dict(z) if z else None

    from datetime import datetime, timezone, timedelta
    acts = [dict(x) for x in c.execute(
        "SELECT ae.action,ae.entity_type,ae.entity_id,ae.created_at,"
        "COALESCE(u.full_name,'System') actor FROM audit_events ae "
        "LEFT JOIN users u ON u.id=ae.actor_id "
        "ORDER BY ae.id DESC LIMIT 10"
    ).fetchall()]

    trends = [dict(x) for x in c.execute(
        "SELECT substr(created_at,1,10) day,"
        "SUM(action='request_submitted') requests,"
        "SUM(action='request_approved') approvals "
        "FROM audit_events WHERE created_at>=? "
        "GROUP BY substr(created_at,1,10) ORDER BY day",
        ((datetime.now(timezone.utc) - timedelta(days=13)).isoformat(
            timespec='seconds'),)
    ).fetchall()]

    alerts = [dict(x) for x in c.execute(
        "SELECT id,status,severity,reason,reported_at "
        "FROM maintenance_records WHERE status<>'resolved' "
        "ORDER BY CASE severity WHEN 'high' THEN 0 "
        "WHEN 'medium' THEN 1 ELSE 2 END,id DESC LIMIT 6"
    ).fetchall()]

    c.close()
    util = round(
        ((counts.get('occupied') or 0) / (counts.get('total') or 1)) * 100, 1
    )
    handler.send_json({
        'counts': counts, 'utilization': util, 'floors': floors,
        'myLocker': my_locker, 'myRequest': my_request,
        'activities': acts, 'trends': trends, 'alerts': alerts,
    })


def handle_lockers(handler):
    """GET /api/lockers"""
    r = handler.auth('view_lockers')
    if not r:
        return
    q = parse_qs(urlparse(handler.path).query)
    floor = q.get('floor', ['all'])[0]
    room = q.get('room', ['all'])[0]
    status = q.get('status', ['all'])[0]
    term = q.get('q', [''])[0].strip()
    w = []
    a = []
    if floor != 'all':
        w.append('f.floor_number=?'); a.append(int(floor))
    if room != 'all':
        w.append('rr.room_code=?'); a.append(room)
    if status != 'all':
        w.append('l.status=?'); a.append(status)
    if term:
        w.append('(l.locker_id LIKE ? OR rr.room_code LIKE ?)')
        t = f'%{term}%'
        a += [t, t]
    where = ' WHERE ' + ' AND '.join(w) if w else ''
    c = conn()
    expire_requests(c)
    rows = c.execute(
        f"SELECT l.id,l.locker_id,l.status,l.assigned_at,f.floor_number,"
        f"f.code floor_code,rr.room_code,rr.room_name FROM lockers l "
        f"JOIN locker_rooms rr ON rr.id=l.room_id "
        f"JOIN floors f ON f.id=rr.floor_id{where} "
        f"ORDER BY f.floor_number,CAST(rr.room_code AS INTEGER),l.locker_id",
        a
    ).fetchall()
    out = []
    for x in rows:
        z = {
            'id': x['locker_id'], 'floor': x['floor_number'],
            'floorCode': x['floor_code'], 'group': x['room_code'],
            'roomCode': x['room_code'], 'roomName': x['room_name'],
            'status': x['status'], 'assignedAt': x['assigned_at'],
            'isMine': False,
        }
        if x['status'] == 'occupied':
            z['isMine'] = c.execute(
                'SELECT 1 FROM lockers WHERE id=? AND student_user_id=?',
                (x['id'], r['id'])
            ).fetchone() is not None
        if r['access_role'] != 'student':
            s = c.execute(
                'SELECT full_name,student_id FROM users '
                'WHERE id=(SELECT student_user_id FROM lockers WHERE id=?)',
                (x['id'],)
            ).fetchone()
            z['studentName'] = s['full_name'] if s else None
            z['studentId'] = s['student_id'] if s else None
        out.append(z)
    c.close()
    handler.send_json({'lockers': out})


def handle_locker_detail(handler, lid):
    """GET /api/lockers/{lockerId}"""
    r = handler.auth('view_lockers')
    if not r:
        return
    c = conn()
    x = c.execute(
        "SELECT l.id,l.locker_id,l.status,l.assigned_at,l.qr_token,"
        "f.floor_number,f.code floor_code,rr.room_code group_code,"
        "rr.room_name,u.id uid,u.full_name,u.branch,u.course,u.year,"
        "u.semester,u.student_id,u.mobile,u.joined_at FROM lockers l "
        "JOIN locker_rooms rr ON rr.id=l.room_id "
        "JOIN floors f ON f.id=rr.floor_id "
        "LEFT JOIN users u ON u.id=l.student_user_id "
        "WHERE l.locker_id=?", (lid,)
    ).fetchone()
    if not x:
        c.close()
        return handler.send_json({'error': 'Locker not found.'}, 404)

    is_admin = r['access_role'] != 'student'
    owns = x['uid'] == r['id']
    student = None
    if x['uid'] and (is_admin or owns):
        student = {
            'name': x['full_name'], 'branch': x['branch'] or x['course'] or '\u2014',
            'year': x['year'] or '\u2014', 'semester': x['semester'] or '\u2014',
            'studentId': x['student_id'] or 'Not assigned',
            'mobile': x['mobile'] or '\u2014',
            'joinedAt': x['joined_at'] or '\u2014',
        }

    events = []
    maintenance = []
    if is_admin or owns:
        events = [dict(e) for e in c.execute(
            "SELECT le.event_type,le.previous_state,le.new_state,le.notes,"
            "le.request_code,le.created_at,COALESCE(u.full_name,'System') actor "
            "FROM locker_events le LEFT JOIN users u ON u.id=le.actor_user_id "
            "WHERE le.locker_id=? ORDER BY le.id DESC LIMIT 50", (x['id'],)
        ).fetchall()]
        maintenance = [dict(m) for m in c.execute(
            "SELECT mr.id,mr.status,mr.severity,mr.reason,mr.notes,"
            "mr.reported_at,mr.resolved_at,"
            "COALESCE(u.full_name,'System') reporter "
            "FROM maintenance_records mr "
            "LEFT JOIN users u ON u.id=mr.reporter_id "
            "WHERE mr.locker_id=? ORDER BY mr.id DESC", (x['id'],)
        ).fetchall()]

    qr = f'{PUBLIC_BASE_URL}/q/{x["qr_token"]}' if PUBLIC_BASE_URL else f'{PUBLIC_BASE_URL}/q/{x["qr_token"]}' if PUBLIC_BASE_URL else f'http://localhost:{PORT}/q/{x["qr_token"]}'
    c.close()
    handler.send_json({
        'locker': {
            'id': x['locker_id'], 'status': x['status'],
            'assignedAt': x['assigned_at'], 'floor': x['floor_number'],
            'floorCode': x['floor_code'], 'group': x['group_code'],
            'roomName': x['room_name'], 'qrUrl': qr,
        },
        'student': student, 'events': events, 'maintenance': maintenance,
    })


def handle_rooms(handler):
    """GET /api/rooms"""
    r = handler.auth('view_lockers')
    if not r:
        return
    c = conn()
    rows = [dict(x) for x in c.execute(
        "SELECT rr.id,rr.room_code,rr.room_name,f.floor_number,f.code,"
        "count(l.id) locker_count FROM locker_rooms rr "
        "JOIN floors f ON f.id=rr.floor_id "
        "LEFT JOIN lockers l ON l.room_id=rr.id "
        "GROUP BY rr.id ORDER BY f.floor_number,"
        "CAST(rr.room_code AS INTEGER)"
    ).fetchall()]
    c.close()
    handler.send_json({'rooms': rows})


def handle_add_lockers(handler):
    """POST /api/lockers/bulk"""
    r = handler.auth('create_lockers')
    if not r:
        return
    d = handler.body()
    floor = int(d.get('floor', 0))
    group = str(d.get('group', '')).strip()
    qty = int(d.get('quantity', 0))
    start = int(d.get('startNumber', 0))
    if (floor not in FLOOR_CODES or not re.fullmatch(r'[1-9]\d?', group)
            or qty not in (1, 5) or not 1 <= start <= 999):
        return handler.send_json(
            {'error': 'Choose a valid floor, locker group, quantity '
                      '(1 or 5), and starting number (001\u2013999).'}, 400
        )
    c = conn()
    c.execute('BEGIN IMMEDIATE')
    try:
        fid = c.execute(
            'SELECT id FROM floors WHERE floor_number=?', (floor,)
        ).fetchone()[0]
        room = c.execute(
            'SELECT * FROM locker_rooms WHERE floor_id=? AND room_code=?',
            (fid, group)
        ).fetchone()
        rid = room['id'] if room else None
        if not room:
            c.execute(
                'INSERT INTO locker_rooms(floor_id,room_code,room_name) '
                'VALUES(?,?,?)', (fid, group, f'Locker Group {group}')
            )
            rid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        created = []
        for i in range(start, start + qty):
            if i > 999:
                raise ValueError('Locker number cannot exceed 999.')
            lid = f'{FLOOR_CODES[floor]}{int(group)}-{i:03d}'
            c.execute(
                "INSERT INTO lockers(locker_id,room_id,status,qr_token) "
                "VALUES(?,?,'available',?)",
                (lid, rid, secrets.token_urlsafe(18)),
            )
            li = c.execute('SELECT last_insert_rowid()').fetchone()[0]
            locker_event(
                c, li, r['id'], 'created', None, 'available',
                notes='Locker created'
            )
            created.append(lid)
        audit(
            c, r['id'], r['access_role'], 'lockers_created',
            'locker_group', f'{FLOOR_CODES[floor]}{group}',
            meta={'count': qty, 'codes': created},
        )
        c.commit()
        c.close()
        handler.send_json({'created': created})
    except DatabaseIntegrityError:
        c.rollback()
        c.close()
        handler.send_json(
            {'error': 'One or more locker codes already exist.'}, 409
        )
    except Exception as e:
        c.rollback()
        c.close()
        handler.send_json({'error': str(e)}, 400)


def handle_request_locker(handler, lid):
    """POST /api/lockers/{lockerId}/request"""
    r = handler.auth('view_lockers')
    if not r:
        return
    if r['access_role'] != 'student':
        return handler.send_json(
            {'error': 'Only students can request lockers.'}, 403
        )
    c = conn()
    expire_requests(c)
    try:
        c.execute('BEGIN IMMEDIATE')
        l = c.execute(
            'SELECT * FROM lockers WHERE locker_id=?', (lid,)
        ).fetchone()
        if not l or l['status'] != 'available':
            raise ValueError('That locker is no longer available.')
        if c.execute(
            "SELECT 1 FROM lockers WHERE student_user_id=? "
            "AND status='occupied'", (r['id'],)
        ).fetchone():
            raise ValueError('You already have a locker assigned.')
        if c.execute(
            "SELECT 1 FROM locker_requests WHERE student_user_id=? "
            "AND status='pending'", (r['id'],)
        ).fetchone():
            raise ValueError('You already have a request under review.')
        code = 'REQ' + secrets.token_hex(4).upper()
        cor = str(uuid.uuid4())
        exp = later(REQUEST_DAYS)
        c.execute(
            'INSERT INTO locker_requests(request_code,locker_id,'
            'student_user_id,status,expires_at) VALUES(?,?,?,?,?)',
            (code, l['id'], r['id'], 'pending', exp),
        )
        if c.execute(
            "UPDATE lockers SET status='pending' WHERE id=? "
            "AND status='available'", (l['id'],)
        ).rowcount != 1:
            raise ValueError('Locker changed. Refresh and try again.')
        locker_event(
            c, l['id'], r['id'], 'request_submitted', 'available',
            'pending', code, correlation_id=cor
        )
        audit(
            c, r['id'], 'student', 'request_submitted', 'locker', lid,
            'available', 'pending', cor, code
        )
        notify(
            c, r['id'], 'request_submitted', 'Locker request submitted',
            f'Request {code} is under review.', 'request', code
        )
        c.commit()
        c.close()
        handler.send_json({'ok': True, 'requestCode': code, 'expiresAt': exp})
    except ValueError as e:
        c.rollback()
        c.close()
        handler.send_json({'error': str(e)}, 409)
    except Exception:
        c.rollback()
        c.close()
        handler.send_json(
            {'error': 'The locker changed before your request was saved. '
                      'Refresh and choose again.'}, 409
        )


def handle_release_locker(handler, lid):
    """POST /api/lockers/{lockerId}/release"""
    r = handler.auth('release_lockers')
    if not r:
        return
    c = conn()
    c.execute('BEGIN IMMEDIATE')
    l = c.execute(
        'SELECT * FROM lockers WHERE locker_id=?', (lid,)
    ).fetchone()
    if not l:
        c.rollback()
        c.close()
        return handler.send_json({'error': 'Locker not found.'}, 404)
    allowed = (
        (r['access_role'] == 'student' and l['student_user_id'] == r['id'])
        or 'release_lockers' in get_permissions(r)
    )
    if not allowed:
        c.rollback()
        c.close()
        return handler.send_json(
            {'error': 'You cannot release this locker.'}, 403
        )
    if l['status'] != 'occupied':
        c.rollback()
        c.close()
        return handler.send_json(
            {'error': 'Locker is not currently occupied.'}, 409
        )
    student_id = l['student_user_id']
    old = 'occupied'
    c.execute(
        "UPDATE lockers SET status='available',student_user_id=NULL,"
        "assigned_at=NULL WHERE id=?", (l['id'],)
    )
    c.execute(
        "UPDATE locker_requests SET status='cancelled',reviewed_at=?,"
        "reviewed_by=? WHERE locker_id=? "
        "AND status IN ('pending','approved')",
        (now(), r['id'], l['id']),
    )
    locker_event(
        c, l['id'], r['id'], 'release', old, 'available',
        notes='Locker released'
    )
    audit(
        c, r['id'], r['access_role'], 'locker_released', 'locker',
        lid, old, 'available'
    )
    if student_id and student_id != r['id']:
        notify(
            c, student_id, 'locker_released', 'Locker released',
            f'Your locker {lid} was released by staff.', 'locker', lid
        )
    c.commit()
    c.close()
    handler.send_json({'ok': True})


def handle_maintenance_toggle(handler, lid):
    """POST /api/lockers/{lockerId}/maintenance"""
    r = handler.auth('manage_maintenance')
    if not r:
        return
    d = handler.body()
    enable = bool(d.get('maintenance'))
    c = conn()
    l = c.execute(
        'SELECT * FROM lockers WHERE locker_id=?', (lid,)
    ).fetchone()
    if not l:
        c.close()
        return handler.send_json({'error': 'Locker not found.'}, 404)

    if enable:
        if l['status'] == 'occupied':
            c.close()
            return handler.send_json(
                {'error': 'Release the locker before placing it into '
                          'maintenance.'}, 409
            )
        c.execute('BEGIN IMMEDIATE')
        reason = str(
            d.get('reason', 'Operational maintenance required')
        ).strip() or 'Operational maintenance required'
        sev = str(d.get('severity', 'medium'))
        pending = c.execute(
            "SELECT request_code,student_user_id "
            "FROM locker_requests WHERE locker_id=? AND status='pending'",
            (l['id'],)
        ).fetchall()
        c.execute(
            "UPDATE locker_requests SET status='cancelled',reviewed_at=?,"
            "reviewed_by=?,rejection_reason=? WHERE locker_id=? "
            "AND status='pending'",
            (now(), r['id'], 'Locker moved to maintenance.', l['id']),
        )
        c.execute(
            "UPDATE lockers SET status='maintenance' WHERE id=? "
            "AND status IN ('available','pending')", (l['id'],)
        )
        mid = c.execute(
            'INSERT INTO maintenance_records(locker_id,reporter_id,'
            'reported_at,reason,severity,status,notes) '
            'VALUES(?,?,?,?,?,?,?)',
            (l['id'], r['id'], now(), reason, sev, 'reported',
             d.get('notes')),
        ).lastrowid
        locker_event(
            c, l['id'], r['id'], 'maintenance_reported', l['status'],
            'maintenance', notes=reason
        )
        audit(
            c, r['id'], r['access_role'], 'maintenance_reported',
            'locker', lid, l['status'], 'maintenance'
        )
        for pr in pending:
            notify(
                c, pr['student_user_id'], 'request_cancelled',
                'Locker request cancelled',
                f"Request {pr['request_code']} was cancelled because "
                f'{lid} entered maintenance.',
                'request', pr['request_code'],
            )
            audit(
                c, r['id'], r['access_role'], 'request_cancelled',
                'request', pr['request_code'], 'pending', 'cancelled',
                meta={'reason': 'locker_maintenance'},
            )
        c.commit()
        c.close()
        handler.send_json({
            'ok': True, 'maintenanceId': mid,
            'cancelledRequests': len(pending),
        })
    else:
        c.execute('BEGIN IMMEDIATE')
        m = c.execute(
            "SELECT * FROM maintenance_records WHERE locker_id=? "
            "AND status<>'resolved' ORDER BY id DESC LIMIT 1", (l['id'],)
        ).fetchone()
        if not m:
            c.rollback()
            c.close()
            return handler.send_json(
                {'error': 'No active maintenance record.'}, 409
            )
        c.execute(
            "UPDATE maintenance_records SET status='resolved',"
            "resolver_id=?,resolved_at=? WHERE id=?",
            (r['id'], now(), m['id']),
        )
        c.execute(
            "UPDATE lockers SET status='available' WHERE id=? "
            "AND status='maintenance'", (l['id'],)
        )
        locker_event(
            c, l['id'], r['id'], 'maintenance_resolved', 'maintenance',
            'available', notes=m['reason']
        )
        audit(
            c, r['id'], r['access_role'], 'maintenance_resolved',
            'locker', lid, 'maintenance', 'available'
        )
        c.commit()
        c.close()
        handler.send_json({'ok': True})


def handle_maintenance_view(handler):
    """GET /api/maintenance"""
    r = handler.auth('manage_maintenance')
    if not r:
        return
    c = conn()
    rows = [dict(x) for x in c.execute(
        "SELECT mr.*,l.locker_id AS locker_code,"
        "COALESCE(u.full_name,'System') reporter "
        "FROM maintenance_records mr "
        "JOIN lockers l ON l.id=mr.locker_id "
        "LEFT JOIN users u ON u.id=mr.reporter_id "
        "ORDER BY CASE mr.status WHEN 'reported' THEN 0 "
        "WHEN 'acknowledged' THEN 1 WHEN 'in_repair' THEN 2 "
        "ELSE 3 END,mr.id DESC"
    ).fetchall()]
    c.close()
    handler.send_json({'maintenance': rows})


def handle_maintenance_create(handler):
    """POST /api/maintenance"""
    r = handler.auth('manage_maintenance')
    if not r:
        return
    d = handler.body()
    lid = str(d.get('lockerId', '')).strip()
    reason = str(d.get('reason', 'Operational issue')).strip()
    severity = str(d.get('severity', 'medium')).strip()
    c = conn()
    l = c.execute(
        'SELECT * FROM lockers WHERE locker_id=?', (lid,)
    ).fetchone()
    if not l:
        c.close()
        return handler.send_json({'error': 'Locker not found.'}, 404)
    if l['status'] == 'occupied':
        c.close()
        return handler.send_json(
            {'error': 'Occupied lockers must be released before '
                      'maintenance.'}, 409
        )
    c.execute('BEGIN IMMEDIATE')
    c.execute(
        "UPDATE lockers SET status='maintenance' WHERE id=?", (l['id'],)
    )
    mid = c.execute(
        'INSERT INTO maintenance_records(locker_id,reporter_id,'
        'reported_at,reason,severity,status,notes) '
        'VALUES(?,?,?,?,?,?,?)',
        (l['id'], r['id'], now(), reason or 'Operational issue',
         severity, 'reported', d.get('notes')),
    ).lastrowid
    locker_event(
        c, l['id'], r['id'], 'maintenance_reported', l['status'],
        'maintenance', notes=reason
    )
    audit(
        c, r['id'], r['access_role'], 'maintenance_reported',
        'maintenance', str(mid), l['status'], 'maintenance'
    )
    c.commit()
    c.close()
    handler.send_json({'ok': True, 'maintenanceId': mid})


def handle_maintenance_transition(handler, mid, action):
    """POST /api/maintenance/{id}/acknowledge|repair|resolve"""
    r = handler.auth('manage_maintenance')
    if not r:
        return
    new = {
        'acknowledge': 'acknowledged', 'repair': 'in_repair',
        'resolve': 'resolved',
    }[action]
    allowed = {
        'reported': 'acknowledged', 'acknowledged': 'in_repair',
        'in_repair': 'resolved',
    }
    c = conn()
    m = c.execute(
        'SELECT * FROM maintenance_records WHERE id=?', (mid,)
    ).fetchone()
    if not m:
        c.close()
        return handler.send_json(
            {'error': 'Maintenance record not found.'}, 404
        )
    if allowed.get(m['status']) != new:
        c.close()
        return handler.send_json(
            {'error': 'Invalid maintenance state transition.'}, 409
        )
    c.execute('BEGIN IMMEDIATE')
    c.execute(
        "UPDATE maintenance_records SET status=?,resolver_id=?,"
        "resolved_at=CASE WHEN ?='resolved' THEN ? ELSE resolved_at "
        "END WHERE id=?",
        (new, r['id'], new, now() if new == 'resolved' else None, mid),
    )
    if new == 'resolved':
        c.execute(
            "UPDATE lockers SET status='available' WHERE id=? "
            "AND status='maintenance'", (m['locker_id'],)
        )
    audit(
        c, r['id'], r['access_role'], 'maintenance_' + new,
        'maintenance', str(mid), m['status'], new
    )
    c.commit()
    c.close()
    handler.send_json({'ok': True})


def handle_requests(handler):
    """GET /api/requests"""
    r = handler.auth('view_lockers')
    if not r:
        return
    c = conn()
    expire_requests(c)
    rows = c.execute(
        "SELECT lr.request_code,lr.status,lr.created_at,lr.reviewed_at,"
        "lr.rejection_reason,lr.expires_at,l.locker_id,u.student_id,"
        "u.full_name,u.branch,u.course,u.year,u.semester "
        "FROM locker_requests lr JOIN lockers l ON l.id=lr.locker_id "
        "JOIN users u ON u.id=lr.student_user_id "
        "ORDER BY CASE lr.status WHEN 'pending' THEN 0 "
        "WHEN 'approved' THEN 1 WHEN 'assigned' THEN 2 ELSE 3 END,"
        "lr.id DESC"
    ).fetchall()
    out = []
    for x in rows:
        if r['access_role'] == 'student' and x['student_id'] != r['student_id']:
            continue
        out.append(dict(x))
    staff = []
    if 'review_staff_requests' in get_permissions(r):
        staff = [dict(x) for x in c.execute(
            "SELECT sr.request_code,sr.requested_login_id,sr.full_name,"
            "sr.branch,sr.semester,sr.campus,sr.mobile,sr.email,"
            "sr.created_at,sr.status,sr.priority,sr.rejection_reason,"
            "COALESCE(a.full_name,'Unassigned') assigned_admin "
            "FROM staff_requests sr LEFT JOIN users a ON a.id=sr.assigned_admin_id "
            "ORDER BY CASE sr.status WHEN 'pending' THEN 0 ELSE 1 END,"
            "sr.priority ASC,sr.id DESC"
        ).fetchall()]
    c.close()
    handler.send_json({'requests': out, 'staffRequests': staff})


def handle_review(handler, code, action):
    """POST /api/requests/{requestCode}/approve|reject|cancel"""
    r = handler.auth('approve_locker_requests')
    if not r:
        return
    c = conn()
    q = c.execute(
        'SELECT lr.*,l.locker_id,l.status locker_status '
        'FROM locker_requests lr JOIN lockers l ON l.id=lr.locker_id '
        'WHERE lr.request_code=?', (code,)
    ).fetchone()
    if not q:
        c.close()
        return handler.send_json({'error': 'Request not found.'}, 404)

    if action == 'cancel':
        if r['access_role'] != 'student' or q['student_user_id'] != r['id']:
            c.close()
            return handler.send_json(
                {'error': 'You cannot cancel this request.'}, 403
            )
        if q['status'] not in ('pending', 'approved'):
            c.close()
            return handler.send_json(
                {'error': 'Request cannot be cancelled now.'}, 409
            )
        c.execute('BEGIN IMMEDIATE')
        c.execute(
            "UPDATE locker_requests SET status='cancelled',reviewed_at=?,"
            "reviewed_by=? WHERE id=?", (now(), r['id'], q['id'])
        )
        c.execute(
            "UPDATE lockers SET status='available' WHERE id=? "
            "AND status='pending'", (q['locker_id'],)
        )
        locker_event(
            c, q['locker_id'], r['id'], 'request_cancelled',
            'pending', 'available', q['request_code']
        )
        audit(
            c, r['id'], r['access_role'], 'request_cancelled',
            'request', code, 'pending', 'cancelled'
        )
        c.commit()
        c.close()
        return handler.send_json({'ok': True})

    if q['status'] != 'pending':
        c.close()
        return handler.send_json(
            {'error': 'Request is no longer pending.'}, 409
        )

    d = handler.body() if action == 'reject' else {}
    cor = str(uuid.uuid4())
    try:
        c.execute('BEGIN IMMEDIATE')
        l = c.execute(
            'SELECT * FROM lockers WHERE id=?', (q['locker_id'],)
        ).fetchone()
        if action == 'approve':
            if not l or l['status'] != 'pending':
                raise ValueError(
                    'Locker state changed. Refresh and review again.'
                )
            if c.execute(
                "SELECT 1 FROM lockers WHERE student_user_id=? "
                "AND status='occupied'", (q['student_user_id'],)
            ).fetchone():
                raise ValueError('Student already has a locker.')
            t = now()
            c.execute(
                "UPDATE locker_requests SET status='approved',"
                "reviewed_at=?,reviewed_by=? WHERE id=?",
                (t, r['id'], q['id']),
            )
            audit(
                c, r['id'], r['access_role'], 'request_approved',
                'request', code, 'pending', 'approved', cor, code
            )
            notify(
                c, q['student_user_id'], 'request_approved',
                'Locker request approved',
                f'Request {code} is approved and assigned to '
                f'{q["locker_id"]}.', 'request', code
            )
            c.execute(
                "UPDATE locker_requests SET status='assigned' WHERE id=?",
                (q['id'],)
            )
            c.execute(
                "UPDATE lockers SET status='occupied',student_user_id=?,"
                "assigned_at=? WHERE id=? AND status='pending'",
                (q['student_user_id'], t, q['locker_id']),
            )
            locker_event(
                c, q['locker_id'], r['id'], 'assigned', 'pending',
                'occupied', code, correlation_id=cor
            )
            audit(
                c, r['id'], r['access_role'], 'request_assigned',
                'request', code, 'approved', 'assigned', cor, code
            )
            c.commit()
            c.close()
            return handler.send_json({'ok': True})

        reason = (
            str(d.get('reason', '')).strip()
            or 'Request was not approved.'
        )
        c.execute(
            "UPDATE locker_requests SET status='rejected',reviewed_at=?,"
            "reviewed_by=?,rejection_reason=? WHERE id=?",
            (now(), r['id'], reason, q['id']),
        )
        c.execute(
            "UPDATE lockers SET status='available' WHERE id=? "
            "AND status='pending'", (q['locker_id'],)
        )
        locker_event(
            c, q['locker_id'], r['id'], 'rejected', 'pending',
            'available', code, reason, cor
        )
        audit(
            c, r['id'], r['access_role'], 'request_rejected',
            'request', code, 'pending', 'rejected', cor, code,
            {'reason': reason},
        )
        notify(
            c, q['student_user_id'], 'request_rejected',
            'Locker request rejected',
            f'Request {code} was rejected. Reason: {reason}',
            'request', code,
        )
        c.commit()
        c.close()
        handler.send_json({'ok': True})
    except ValueError as e:
        c.rollback()
        c.close()
        handler.send_json({'error': str(e)}, 409)
    except Exception:
        c.rollback()
        c.close()
        handler.send_json({'error': 'Could not update request.'}, 409)


def handle_staff_requests(handler):
    """GET /api/staff-requests"""
    r = handler.auth('review_staff_requests')
    if not r:
        return
    c = conn()
    rows = [dict(x) for x in c.execute(
        "SELECT sr.request_code,sr.requested_login_id,sr.full_name,"
        "sr.branch,sr.semester,sr.campus,sr.mobile,sr.email,sr.created_at,"
        "sr.status,sr.priority,sr.rejection_reason,"
        "COALESCE(a.full_name,'Unassigned') assigned_admin "
        "FROM staff_requests sr "
        "LEFT JOIN users a ON a.id=sr.assigned_admin_id "
        "ORDER BY CASE sr.status WHEN 'pending' THEN 0 ELSE 1 END,"
        "sr.priority ASC,sr.id DESC"
    ).fetchall()]
    c.close()
    handler.send_json({'requests': rows})


def handle_review_staff(handler, code, action):
    """POST /api/staff-requests/{requestCode}/approve|reject"""
    r = handler.auth('review_staff_requests')
    if not r:
        return
    c = conn()
    q = c.execute(
        'SELECT * FROM staff_requests WHERE request_code=?', (code,)
    ).fetchone()
    if not q or q['status'] != 'pending':
        c.close()
        return handler.send_json(
            {'error': 'Staff request is no longer pending.'}, 409
        )
    if (q['assigned_admin_id'] and q['assigned_admin_id'] != r['id']
            and r['access_role'] != 'super_admin'):
        c.close()
        return handler.send_json(
            {'error': 'This request is assigned to the primary '
                      'administrator.'}, 403
        )

    d = handler.body() if action == 'reject' else {}
    try:
        c.execute('BEGIN IMMEDIATE')
        if action == 'approve':
            login_id = (
                q['requested_login_id']
                or ('STAFF' + secrets.token_hex(3).upper())
            )
            if c.execute(
                'SELECT 1 FROM users WHERE username=? OR student_id=?',
                (login_id, login_id)
            ).fetchone():
                raise ValueError(
                    'That staff/college ID is already in use.'
                )
            c.execute(
                'INSERT INTO users(student_id,username,password_hash,'
                'full_name,role,branch,semester,campus,mobile,email,'
                'profile_photo,account_type,access_role,is_primary_admin,'
                'joined_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (q['requested_login_id'], login_id, q['password_hash'],
                 q['full_name'], 'admin', q['branch'], q['semester'],
                 q['campus'], q['mobile'], q['email'],
                 q['profile_photo'], 'staff', 'staff', 0, now()),
            )
            uid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
            c.execute(
                "UPDATE staff_requests SET status='approved',"
                "reviewed_at=?,reviewed_by=?,password_hash='',"
                "rejection_reason=NULL WHERE id=?",
                (now(), r['id'], q['id']),
            )
            notify(
                c, uid, 'staff_approved', 'Staff access approved',
                'Your Campus Buddy staff account is approved.',
                'staff_request', code,
            )
            audit(
                c, r['id'], r['access_role'], 'staff_request_approved',
                'staff_request', code, 'pending', 'approved',
                request_id=code,
            )
            audit(
                c, uid, 'staff', 'account_activated', 'user', str(uid),
            )
            c.commit()
            c.close()
            return handler.send_json({'ok': True, 'loginId': login_id})

        reason = (
            str(d.get('reason', '')).strip()
            or 'Application did not meet current approval requirements.'
        )
        c.execute(
            "UPDATE staff_requests SET status='rejected',reviewed_at=?,"
            "reviewed_by=?,rejection_reason=?,password_hash='' WHERE id=?",
            (now(), r['id'], reason, q['id']),
        )
        audit(
            c, r['id'], r['access_role'], 'staff_request_rejected',
            'staff_request', code, 'pending', 'rejected',
            request_id=code, meta={'reason': reason},
        )
        c.commit()
        c.close()
        handler.send_json({'ok': True})
    except ValueError as e:
        c.rollback()
        c.close()
        handler.send_json({'error': str(e)}, 409)
    except DatabaseIntegrityError:
        c.rollback()
        c.close()
        handler.send_json(
            {'error': 'Could not approve staff request because the '
                      'login ID conflicts with an existing account.'}, 409
        )


def handle_students(handler):
    """GET /api/students"""
    r = handler.auth('view_students')
    if not r:
        return
    term = parse_qs(urlparse(handler.path).query).get('q', [''])[0].strip()
    t = f'%{term}%'
    c = conn()
    rows = [dict(x) for x in c.execute(
        "SELECT u.student_id,u.username,u.full_name,u.branch,u.course,"
        "u.year,u.semester,u.campus,u.mobile,u.email,u.active,u.joined_at,"
        "l.locker_id FROM users u "
        "LEFT JOIN lockers l ON l.student_user_id=u.id "
        "AND l.status='occupied' "
        "WHERE u.account_type='student' AND ("
        "COALESCE(u.student_id,'') LIKE ? OR u.username LIKE ? "
        "OR u.full_name LIKE ? OR COALESCE(u.branch,'') LIKE ?) "
        "ORDER BY u.username", (t, t, t, t)
    ).fetchall()]
    if 'view_private_student_data' not in get_permissions(r):
        for x in rows:
            x['mobile'] = None
            x['email'] = None
    c.close()
    handler.send_json({'students': rows})


def handle_add_student(handler):
    """POST /api/students"""
    r = handler.auth('manage_staff')
    if not r:
        return
    d = handler.body()
    sid = str(d.get('studentId', '')).strip()
    name = str(d.get('name', '')).strip()
    branch = str(d.get('branch', '')).strip()
    sem = str(d.get('semester', '')).strip()
    mobile = str(d.get('mobile', '')).strip()
    email = str(d.get('email', '')).strip() or None
    pw = str(d.get('password', 'student123'))
    campus = str(d.get('campus', 'Dwarka Campus'))
    if (not all((sid, name, branch, sem, mobile))
            or not re.fullmatch(r'[A-Za-z0-9_-]{3,30}', sid)
            or not re.fullmatch(r'\\d{10}', mobile)):
        return handler.send_json(
            {'error': 'Student ID, name, branch, semester and '
                      '10-digit mobile are required.'}, 400
        )
    c = conn()
    try:
        c.execute(
            'INSERT INTO users(student_id,username,password_hash,'
            'full_name,role,branch,semester,campus,mobile,email,'
            'account_type,access_role,joined_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (sid, sid, hpw(pw), name, 'student', branch, sem, campus,
             mobile, email, 'student', 'student', now()),
        )
        uid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        audit(c, r['id'], r['access_role'], 'student_added', 'user', str(uid))
        c.commit()
        c.close()
        handler.send_json({'ok': True, 'studentId': sid})
    except DatabaseIntegrityError:
        c.close()
        handler.send_json(
            {'error': 'That student ID already exists.'}, 409
        )


def handle_update_profile(handler):
    """POST /api/profile/update"""
    r = handler.auth()
    if not r:
        return
    d = handler.body()
    name = str(d.get('name', '')).strip()
    branch = str(d.get('branch', '')).strip()
    sem = str(d.get('semester', '')).strip()
    campus = str(d.get('campus', 'Dwarka Campus')).strip()
    sid = str(d.get('studentId', '')).strip() or None
    mobile = str(d.get('mobile', '')).strip()
    photo = d.get('profilePhoto')
    if (not name or not branch or not mobile
            or (r['access_role'] == 'student' and not sem)):
        return handler.send_json(
            {'error': 'Name, branch, mobile and student semester '
                      'are required.'}, 400
        )
    if campus != 'Dwarka Campus' or not re.fullmatch(r'\\d{10}', mobile):
        return handler.send_json(
            {'error': 'Only Dwarka Campus is active and mobile '
                      'must contain 10 digits.'}, 400
        )
    if sid and not re.fullmatch(r'[A-Za-z0-9_-]{3,30}', sid):
        return handler.send_json(
            {'error': 'Student/college ID must use letters, numbers, '
                      '_ or - only.'}, 400
        )
    if photo and (not isinstance(photo, str)
                  or not re.match(r'^data:image/(?:jpeg|png|webp);base64,', photo, re.I) is not None
                  or len(photo) > 3_500_000):
        return handler.send_json(
            {'error': 'Profile photo is too large.'}, 400
        )
    c = conn()
    if sid and c.execute(
        'SELECT 1 FROM users WHERE student_id=? AND id<>?', (sid, r['id'])
    ).fetchone():
        c.close()
        return handler.send_json(
            {'error': 'That student ID is already in use.'}, 409
        )
    c.execute(
        'UPDATE users SET full_name=?,branch=?,semester=?,campus=?,'
        'mobile=?,student_id=?,profile_photo=? WHERE id=?',
        (name, branch, sem, campus, mobile, sid, photo, r['id']),
    )
    audit(
        c, r['id'], r['access_role'], 'profile_updated', 'user',
        str(r['id']),
    )
    c.commit()
    nr = c.execute('SELECT * FROM users WHERE id=?', (r['id'],)).fetchone()
    c.close()
    handler.send_json({'ok': True, 'user': public_user(nr, True)})


def handle_notifications(handler):
    """GET /api/notifications"""
    r = handler.auth('view_notifications')
    if not r:
        return
    c = conn()
    rows = [dict(x) for x in c.execute(
        'SELECT id,type,title,body,entity_type,entity_id,read_at,'
        'created_at FROM notifications WHERE user_id=? '
        'ORDER BY id DESC LIMIT 100', (r['id'],)
    ).fetchall()]
    unread = sum(1 for x in rows if not x['read_at'])
    c.close()
    handler.send_json({'notifications': rows, 'unread': unread})


def handle_mark_notification(handler, nid):
    """POST /api/notifications/{id}/read"""
    r = handler.auth('view_notifications')
    if not r:
        return
    c = conn()
    c.execute(
        'UPDATE notifications SET read_at=? WHERE id=? AND user_id=?',
        (now(), nid, r['id']),
    )
    c.commit()
    c.close()
    handler.send_json({'ok': True})


def handle_mark_notifications_all(handler):
    """POST /api/notifications/read-all"""
    r = handler.auth('view_notifications')
    if not r:
        return
    c = conn()
    c.execute(
        'UPDATE notifications SET read_at=? WHERE user_id=? '
        'AND read_at IS NULL', (now(), r['id'])
    )
    c.commit()
    c.close()
    handler.send_json({'ok': True})


def handle_audit_view(handler):
    """GET /api/audit"""
    r = handler.auth('view_audit_logs')
    if not r:
        return
    c = conn()
    rows = [dict(x) for x in c.execute(
        "SELECT ae.id,ae.action,ae.entity_type,ae.entity_id,"
        "ae.previous_state,ae.new_state,ae.created_at,"
        "COALESCE(u.full_name,'System') actor,ae.actor_role,"
        "ae.correlation_id FROM audit_events ae "
        "LEFT JOIN users u ON u.id=ae.actor_id "
        "ORDER BY ae.id DESC LIMIT 200"
    ).fetchall()]
    c.close()
    handler.send_json({'audit': rows})


def handle_locker_qr_json(handler, lid):
    """GET /api/lockers/{lockerId}/qr"""
    r = handler.auth('view_lockers')
    if not r:
        return
    c = conn()
    x = c.execute(
        'SELECT locker_id,qr_token FROM lockers WHERE locker_id=?', (lid,)
    ).fetchone()
    c.close()
    if not x:
        return handler.send_json({'error': 'Locker not found.'}, 404)
    handler.send_json({
        'lockerId': x['locker_id'],
        'url': f'{PUBLIC_BASE_URL}/q/{x["qr_token"]}' if PUBLIC_BASE_URL else f'{PUBLIC_BASE_URL}/q/{x["qr_token"]}' if PUBLIC_BASE_URL else f'http://localhost:{PORT}/q/{x["qr_token"]}',
        'qrToken': x['qr_token'],
        'pngUrl': f'/api/lockers/{x["locker_id"]}/qr.png',
    })


def handle_qr_png(handler, lid):
    """GET /api/lockers/{lockerId}/qr.png"""
    r = handler.auth('view_lockers')
    if not r:
        return
    if qrcode is None:
        return handler.send_json(
            {'error': 'QR dependency is not installed. '
                      'Run pip install -r requirements.txt.'}, 503
        )
    c = conn()
    x = c.execute(
        'SELECT locker_id,qr_token FROM lockers WHERE locker_id=?', (lid,)
    ).fetchone()
    c.close()
    if not x:
        return handler.send_json({'error': 'Locker not found.'}, 404)
    img = qrcode.make(f'{PUBLIC_BASE_URL}/q/{x["qr_token"]}' if PUBLIC_BASE_URL else f'{PUBLIC_BASE_URL}/q/{x["qr_token"]}' if PUBLIC_BASE_URL else f'http://localhost:{PORT}/q/{x["qr_token"]}')
    import io
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    data = buf.getvalue()
    handler.send_response(200)
    handler.send_header('Content-Type', 'image/png')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Content-Length', str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def handle_qr_info(handler, token):
    """GET /api/qr/{token}"""
    r = handler.auth('view_lockers')
    if not r:
        return
    c = conn()
    x = c.execute(
        "SELECT l.locker_id,l.status,f.floor_number,f.code floor_code,"
        "rr.room_code,rr.room_name FROM lockers l "
        "JOIN locker_rooms rr ON rr.id=l.room_id "
        "JOIN floors f ON f.id=rr.floor_id WHERE l.qr_token=?", (token,)
    ).fetchone()
    c.close()
    if not x:
        return handler.send_json({'error': 'Invalid locker QR.'}, 404)
    handler.send_json({'locker': dict(x)})


def handle_qr_landing(handler, token):
    """GET /q/{token}"""
    html = f'''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Buddy QR</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4f6fa;margin:0;
padding:40px;color:#182033}}main{{max-width:520px;margin:auto;background:white;
border:1px solid #e5e8ef;border-radius:20px;padding:28px;
box-shadow:0 18px 48px rgba(27,35,58,.08)}}button{{border:0;border-radius:12px;
padding:12px 16px;background:#5b57f4;color:white;font-weight:800}}</style>
</head><body><main>
<p>Campus Buddy physical locker identity</p>
<h1>Locker QR detected</h1>
<p>Authentication is required. Continue to Campus Buddy to view information
allowed for your role.</p>
<button onclick="location.href='/?qr={token}'">Continue to Campus Buddy</button>
</main></body></html>'''.encode()
    handler.send_response(200)
    handler.send_header('Content-Type', 'text/html; charset=utf-8')
    handler.send_header('Content-Length', str(len(html)))
    handler.end_headers()
    handler.wfile.write(html)
