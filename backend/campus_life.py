from backend.utils import DatabaseIntegrityError, DatabaseOperationalError
"""Campus Buddy — Clubs and Events Module (Full-featured upgrade)."""
import json, sqlite3, secrets
from backend.utils import conn, now, get_permissions, audit, notify


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _is_club_leader(c, club_id, user_id):
    """Return True if user_id is an active leader (only) of club_id."""
    row = c.execute(
        "SELECT 1 FROM club_members WHERE club_id=? AND user_id=? "
        "AND status='active' AND role='leader'",
        (club_id, user_id)
    ).fetchone()
    return bool(row)

def _is_club_leadership(c, club_id, user_id):
    """Return True if user_id is an active leader OR co-leader of club_id.

    Leaders and co-leaders share day-to-day management abilities
    (creating events/meetings, moderating the gallery, reviewing join
    requests). Only the leader role itself can reassign roles."""
    row = c.execute(
        "SELECT 1 FROM club_members WHERE club_id=? AND user_id=? "
        "AND status='active' AND role IN('leader','co-leader')",
        (club_id, user_id)
    ).fetchone()
    return bool(row)

def _is_club_staff_or_admin(user):
    return user['access_role'] in ('super_admin', 'staff', 'locker_manager')


# ══════════════════════════════════════════════════════════════
# CLUBS — LIST
# ══════════════════════════════════════════════════════════════

def handle_get_clubs(handler):
    """GET /api/clubs"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        if _is_club_staff_or_admin(user):
            # Staff sees all clubs including pending
            clubs = c.execute('''
                SELECT cl.id, cl.name, cl.category, cl.description, cl.logo,
                       cl.department, cl.contact_email, cl.meeting_schedule,
                       cl.status, cl.created_at,
                       u.full_name AS founder_name,
                       (SELECT COUNT(*) FROM club_members cm WHERE cm.club_id = cl.id AND cm.status='active') AS member_count,
                       (SELECT role FROM club_members cm WHERE cm.club_id=cl.id AND cm.user_id=? AND cm.status='active') AS my_role,
                       (SELECT status FROM club_members cm WHERE cm.club_id=cl.id AND cm.user_id=?) AS my_status
                FROM clubs cl
                LEFT JOIN users u ON u.id = cl.founder_user_id
                ORDER BY cl.status, cl.name
            ''', (user['id'], user['id'])).fetchall()
        else:
            clubs = c.execute('''
                SELECT cl.id, cl.name, cl.category, cl.description, cl.logo,
                       cl.department, cl.contact_email, cl.meeting_schedule,
                       cl.status, cl.created_at,
                       u.full_name AS founder_name,
                       (SELECT COUNT(*) FROM club_members cm WHERE cm.club_id = cl.id AND cm.status='active') AS member_count,
                       (SELECT role FROM club_members cm WHERE cm.club_id=cl.id AND cm.user_id=? AND cm.status='active') AS my_role,
                       (SELECT status FROM club_members cm WHERE cm.club_id=cl.id AND cm.user_id=?) AS my_status
                FROM clubs cl
                LEFT JOIN users u ON u.id = cl.founder_user_id
                WHERE cl.status = 'active'
                ORDER BY cl.name
            ''', (user['id'], user['id'])).fetchall()
        handler.send_json({'clubs': [dict(x) for x in clubs]})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — DETAIL (with members list)
# ══════════════════════════════════════════════════════════════

def handle_get_club_detail(handler, club_id):
    """GET /api/clubs/<club_id>"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        club = c.execute('''
            SELECT cl.*, u.full_name AS founder_name,
                   (SELECT role FROM club_members cm WHERE cm.club_id=cl.id AND cm.user_id=? AND cm.status='active') AS my_role,
                   (SELECT status FROM club_members cm WHERE cm.club_id=cl.id AND cm.user_id=?) AS my_membership_status
            FROM clubs cl
            LEFT JOIN users u ON u.id = cl.founder_user_id
            WHERE cl.id=?
        ''', (user['id'], user['id'], club_id)).fetchone()

        if not club:
            return handler.send_json({'error': 'Club not found'}, 404)

        # Only show pending clubs to staff/admin or the founder
        if club['status'] == 'pending_staff' and not _is_club_staff_or_admin(user) and club['founder_user_id'] != user['id']:
            return handler.send_json({'error': 'Club not found'}, 404)

        # Members list
        members = c.execute('''
            SELECT cm.id, cm.user_id, cm.role, cm.status, cm.joined_at,
                   u.full_name, u.student_id, u.branch, u.year
            FROM club_members cm
            JOIN users u ON u.id = cm.user_id
            WHERE cm.club_id=?
            ORDER BY CASE cm.role WHEN 'leader' THEN 0 WHEN 'co-leader' THEN 1 ELSE 9 END, cm.joined_at
        ''', (club_id,)).fetchall()

        # Pending membership requests (only visible to leader/co-leader/staff)
        is_leader = _is_club_leadership(c, club_id, user['id'])
        pending_requests = []
        if is_leader or _is_club_staff_or_admin(user):
            pending_requests = c.execute('''
                SELECT cm.id, cm.user_id, cm.joined_at,
                       u.full_name, u.student_id, u.branch, u.year
                FROM club_members cm
                JOIN users u ON u.id = cm.user_id
                WHERE cm.club_id=? AND cm.status='pending'
                ORDER BY cm.joined_at
            ''', (club_id,)).fetchall()

        handler.send_json({
            'club': dict(club),
            'members': [dict(m) for m in members],
            'pendingRequests': [dict(r) for r in pending_requests],
            'isLeader': is_leader,
            'isStaff': _is_club_staff_or_admin(user),
        })
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — CREATE (goes to staff for approval)
# ══════════════════════════════════════════════════════════════

def handle_create_club(handler):
    """POST /api/clubs"""
    user = handler.auth()
    if not user: return

    body = handler.body()
    name = (body.get('name') or '').strip()
    if not name:
        return handler.send_json({'error': 'Club name is required'}, 400)

    c = conn()
    try:
        existing = c.execute("SELECT 1 FROM clubs WHERE name=?", (name,)).fetchone()
        if existing:
            return handler.send_json({'error': 'A club with this name already exists'}, 400)

        c.execute('''
            INSERT INTO clubs(name, description, category, department, logo,
                contact_email, contact_phone, meeting_schedule,
                founder_user_id, status, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            name,
            (body.get('description') or '').strip(),
            (body.get('category') or 'General').strip(),
            (body.get('department') or '').strip(),
            body.get('logo') or None,
            (body.get('contactEmail') or '').strip(),
            (body.get('contactPhone') or '').strip(),
            (body.get('meetingSchedule') or '').strip(),
            user['id'],
            'pending_staff',
            now()
        ))
        club_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Auto-add founder as leader (pending until club is approved)
        c.execute('''
            INSERT INTO club_members(club_id, user_id, role, status, joined_at)
            VALUES(?, ?, 'leader', 'active', ?)
        ''', (club_id, user['id'], now()))

        # Notify all staff/admin users
        staff_users = c.execute(
            "SELECT id FROM users WHERE access_role IN ('super_admin','staff') AND active=1"
        ).fetchall()
        for su in staff_users:
            notify(c, su['id'], 'club_pending',
                   f'New club proposal: {name}',
                   f'{user["full_name"]} has proposed a new club "{name}". Review and approve in Clubs management.',
                   'club', str(club_id))

        audit(c, user['id'], user['access_role'], 'club_proposed', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': f'Club proposal submitted for staff review.', 'clubId': club_id})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — STAFF REVIEW (approve/reject)
# ══════════════════════════════════════════════════════════════

def handle_review_club(handler, club_id, action):
    """POST /api/clubs/<club_id>/review"""
    user = handler.auth()
    if not user: return

    if not _is_club_staff_or_admin(user):
        return handler.send_json({'error': 'Staff access required'}, 403)

    body = handler.body()
    c = conn()
    try:
        club = c.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
        if not club:
            return handler.send_json({'error': 'Club not found'}, 404)
        if club['status'] != 'pending_staff':
            return handler.send_json({'error': 'Club is not pending review'}, 400)

        if action == 'approve':
            c.execute('''
                UPDATE clubs SET status='active', staff_reviewer_id=?, staff_reviewed_at=?
                WHERE id=?
            ''', (user['id'], now(), club_id))
            # Notify founder
            if club['founder_user_id']:
                notify(c, club['founder_user_id'], 'club_approved',
                       f'Club approved: {club["name"]}',
                       f'Your club "{club["name"]}" has been approved! You are now the club leader.',
                       'club', str(club_id))
            msg = 'Club approved successfully.'
        else:
            reason = (body.get('reason') or 'Club proposal was not approved.').strip()
            c.execute('''
                UPDATE clubs SET status='rejected', staff_reviewer_id=?, staff_reviewed_at=?,
                    staff_rejection_reason=?
                WHERE id=?
            ''', (user['id'], now(), reason, club_id))
            if club['founder_user_id']:
                notify(c, club['founder_user_id'], 'club_rejected',
                       f'Club proposal rejected: {club["name"]}',
                       f'Your club proposal "{club["name"]}" was not approved. Reason: {reason}',
                       'club', str(club_id))
            msg = 'Club proposal rejected.'

        audit(c, user['id'], user['access_role'], f'club_{action}d', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': msg})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — JOIN (request membership)
# ══════════════════════════════════════════════════════════════

def handle_join_club(handler, club_id):
    """POST /api/clubs/<club_id>/join"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        club = c.execute("SELECT * FROM clubs WHERE id=? AND status='active'", (club_id,)).fetchone()
        if not club:
            return handler.send_json({'error': 'Club not found or not active'}, 404)

        existing = c.execute(
            "SELECT status FROM club_members WHERE club_id=? AND user_id=?",
            (club_id, user['id'])
        ).fetchone()

        if existing:
            if existing['status'] == 'active':
                return handler.send_json({'error': 'You are already a member'}, 400)
            elif existing['status'] == 'pending':
                return handler.send_json({'error': 'Your membership request is already pending'}, 400)
            else:
                # rejected previously — re-apply
                c.execute(
                    "UPDATE club_members SET status='pending', role='member', joined_at=? WHERE club_id=? AND user_id=?",
                    (now(), club_id, user['id'])
                )
        else:
            c.execute(
                "INSERT INTO club_members(club_id, user_id, role, status, joined_at) VALUES(?,?,'member','pending',?)",
                (club_id, user['id'], now())
            )

        # Notify club leader(s)
        leaders = c.execute(
            "SELECT user_id FROM club_members WHERE club_id=? AND role='leader' AND status='active'",
            (club_id,)
        ).fetchall()
        for l in leaders:
            notify(c, l['user_id'], 'membership_request',
                   f'New membership request — {club["name"]}',
                   f'{user["full_name"]} has requested to join {club["name"]}. Go to Club > Member Requests to approve.',
                   'club', str(club_id))

        audit(c, user['id'], user['access_role'], 'club_join_requested', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': f'Membership request sent to {club["name"]} leader.'})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — LEAVE
# ══════════════════════════════════════════════════════════════

def handle_leave_club(handler, club_id):
    """POST /api/clubs/<club_id>/leave"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        c.execute("DELETE FROM club_members WHERE club_id=? AND user_id=?", (club_id, user['id']))
        audit(c, user['id'], user['access_role'], 'left_club', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': 'Successfully left club'})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — REVIEW MEMBERSHIP REQUEST (leader action)
# ══════════════════════════════════════════════════════════════

def handle_review_membership(handler, club_id, member_id, action):
    """POST /api/clubs/<club_id>/members/<member_id>/(approve|reject)"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        # Must be leader, co-leader or staff
        if not _is_club_leadership(c, club_id, user['id']) and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Only club leader, co-leader or staff can review requests'}, 403)

        row = c.execute(
            "SELECT cm.*, u.full_name FROM club_members cm JOIN users u ON u.id=cm.user_id WHERE cm.id=? AND cm.club_id=?",
            (member_id, club_id)
        ).fetchone()
        if not row:
            return handler.send_json({'error': 'Membership request not found'}, 404)

        club = c.execute("SELECT name FROM clubs WHERE id=?", (club_id,)).fetchone()

        if action == 'approve':
            c.execute("UPDATE club_members SET status='active' WHERE id=?", (row['id'],))
            notify(c, row['user_id'], 'membership_approved',
                   f'Membership approved — {club["name"]}',
                   f'Your request to join {club["name"]} has been approved! Welcome aboard.',
                   'club', str(club_id))
            msg = 'Membership approved.'
        else:
            c.execute("UPDATE club_members SET status='rejected' WHERE id=?", (row['id'],))
            notify(c, row['user_id'], 'membership_rejected',
                   f'Membership request — {club["name"]}',
                   f'Your request to join {club["name"]} was not approved at this time.',
                   'club', str(club_id))
            msg = 'Membership request rejected.'

        audit(c, user['id'], user['access_role'], f'membership_{action}d', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': msg})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — ASSIGN ROLE (leader action)
# ══════════════════════════════════════════════════════════════

def handle_assign_role(handler, club_id, member_id):
    """POST /api/clubs/<club_id>/members/<member_id>/role"""
    user = handler.auth()
    if not user: return

    body = handler.body()
    new_role = (body.get('role') or '').strip().lower()
    if not new_role:
        return handler.send_json({'error': 'Role is required'}, 400)

    c = conn()
    try:
        if not _is_club_leader(c, club_id, user['id']) and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Only club leader or staff can assign roles'}, 403)

        row = c.execute(
            "SELECT * FROM club_members WHERE id=? AND club_id=? AND status='active'",
            (member_id, club_id)
        ).fetchone()
        if not row:
            return handler.send_json({'error': 'Active member not found'}, 404)

        c.execute("UPDATE club_members SET role=? WHERE id=?", (new_role, member_id))
        club = c.execute("SELECT name FROM clubs WHERE id=?", (club_id,)).fetchone()
        notify(c, row['user_id'], 'role_assigned',
               f'Role updated — {club["name"]}',
               f'Your role in {club["name"]} has been updated to: {new_role}.',
               'club', str(club_id))

        audit(c, user['id'], user['access_role'], 'role_assigned', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': f'Role updated to "{new_role}".'})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — LIST
# ══════════════════════════════════════════════════════════════

def handle_get_events(handler):
    """GET /api/events"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        events = c.execute('''
            SELECT e.id, e.title, e.description, e.event_date,
                   e.start_time AS time_start, e.end_time AS time_end,
                   e.location, e.event_type AS type, e.event_mode,
                   e.online_link, e.requires_form, e.capacity,
                   e.is_paid, e.price,
                   c.name AS club_name, c.id AS club_id,
                   (SELECT COUNT(*) FROM event_registrations er WHERE er.event_id=e.id AND er.status='registered') AS attendee_count,
                   (SELECT status FROM event_registrations er WHERE er.event_id=e.id AND er.user_id=?) AS my_status,
                   (SELECT payment_status FROM event_registrations er WHERE er.event_id=e.id AND er.user_id=?) AS my_payment_status,
                   (SELECT 1 FROM club_event_form_submissions fs WHERE fs.event_id=e.id AND fs.user_id=?) AS my_form_submitted
            FROM events e
            LEFT JOIN clubs c ON e.club_id = c.id
            WHERE e.status IN ('upcoming','ongoing') AND e.event_date >= date('now')
            ORDER BY e.event_date, e.start_time
        ''', (user['id'], user['id'], user['id'])).fetchall()
        handler.send_json({'events': [dict(x) for x in events]})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — CREATE (club leader)
# ══════════════════════════════════════════════════════════════

def handle_create_event(handler):
    """POST /api/events"""
    user = handler.auth()
    if not user: return

    body = handler.body()
    club_id = body.get('clubId')
    title = (body.get('title') or '').strip()
    if not title:
        return handler.send_json({'error': 'Event title is required'}, 400)
    if not body.get('eventDate'):
        return handler.send_json({'error': 'Event date is required'}, 400)

    c = conn()
    try:
        # Must be club leader, co-leader or staff
        if club_id:
            if not _is_club_leadership(c, club_id, user['id']) and not _is_club_staff_or_admin(user):
                return handler.send_json({'error': 'Only the club leader or co-leader can create events'}, 403)
        elif not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Only staff can create campus-wide events'}, 403)

        # Prevent back-dated events (server-side enforcement, not just UI)
        event_date = body.get('eventDate')
        if event_date and event_date < now()[:10]:
            return handler.send_json({'error': 'Event date cannot be in the past'}, 400)

        event_mode = body.get('eventMode', 'offline')
        if event_mode not in ('online', 'offline', 'hybrid'):
            event_mode = 'offline'

        form_fields = body.get('formFields', [])  # list of {label, type, required}
        requires_form = 1 if form_fields else 0

        is_paid = 1 if body.get('isPaid') else 0
        price = float(body.get('price') or 0) if is_paid else 0
        payment_qr = (body.get('paymentQr') or '').strip() if is_paid else ''
        if is_paid and not payment_qr:
            return handler.send_json({'error': 'Please upload a payment QR code for a paid event'}, 400)

        c.execute('''
            INSERT INTO events(title, description, club_id, organizer_user_id,
                event_date, start_time, end_time, location, event_mode, online_link,
                capacity, event_type, requires_form, is_paid, price, payment_qr_image,
                status, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            title,
            (body.get('description') or '').strip(),
            club_id or None,
            user['id'],
            event_date,
            body.get('startTime', '10:00'),
            body.get('endTime', ''),
            (body.get('location') or '').strip(),
            event_mode,
            (body.get('onlineLink') or '').strip(),
            int(body.get('capacity', 0)),
            (body.get('eventType') or 'General').strip(),
            requires_form,
            is_paid,
            price,
            payment_qr or None,
            'upcoming',
            now()
        ))
        event_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Save form fields if any
        if form_fields:
            c.execute(
                "INSERT INTO club_event_forms(event_id, fields_json) VALUES(?,?)",
                (event_id, json.dumps(form_fields))
            )

        audit(c, user['id'], user['access_role'], 'event_created', 'event', str(event_id))
        c.commit()
        handler.send_json({'message': 'Event created successfully.', 'eventId': event_id})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — SINGLE DETAIL (title, form fields, payment info in one call)
# ══════════════════════════════════════════════════════════════

def handle_get_event_detail(handler, event_id):
    """GET /api/events/<event_id> — everything the registration modal needs."""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        event = c.execute('''
            SELECT e.*, cl.name AS club_name,
                   (SELECT status FROM event_registrations er WHERE er.event_id=e.id AND er.user_id=?) AS my_status,
                   (SELECT payment_status FROM event_registrations er WHERE er.event_id=e.id AND er.user_id=?) AS my_payment_status
            FROM events e LEFT JOIN clubs cl ON cl.id = e.club_id
            WHERE e.id=?
        ''', (user['id'], user['id'], event_id)).fetchone()
        if not event:
            return handler.send_json({'error': 'Event not found'}, 404)

        form = c.execute(
            "SELECT fields_json FROM club_event_forms WHERE event_id=?", (event_id,)
        ).fetchone()

        handler.send_json({
            'event': dict(event),
            'fields': json.loads(form['fields_json']) if form else [],
        })
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — GET FORM
# ══════════════════════════════════════════════════════════════

def handle_get_event_form(handler, event_id):
    """GET /api/events/<event_id>/form"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        event = c.execute(
            "SELECT id, title, requires_form FROM events WHERE id=?", (event_id,)
        ).fetchone()
        if not event:
            return handler.send_json({'error': 'Event not found'}, 404)

        form = c.execute(
            "SELECT fields_json FROM club_event_forms WHERE event_id=?", (event_id,)
        ).fetchone()

        existing = c.execute(
            "SELECT answers_json FROM club_event_form_submissions WHERE event_id=? AND user_id=?",
            (event_id, user['id'])
        ).fetchone()

        handler.send_json({
            'eventId': event_id,
            'eventTitle': event['title'],
            'fields': json.loads(form['fields_json']) if form else [],
            'alreadySubmitted': bool(existing),
            'answers': json.loads(existing['answers_json']) if existing else {},
        })
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — REGISTER
# ══════════════════════════════════════════════════════════════

def handle_register_event(handler, event_id):
    """POST /api/events/<event_id>/register"""
    user = handler.auth()
    if not user: return

    body = handler.body()
    c = conn()
    try:
        event = c.execute(
            "SELECT * FROM events WHERE id=? AND status IN ('upcoming','ongoing')",
            (event_id,)
        ).fetchone()
        if not event:
            return handler.send_json({'error': 'Event not found'}, 404)

        # If event requires form, save form answers
        if event['requires_form']:
            answers = body.get('answers', {})
            # Validate required fields
            form = c.execute(
                "SELECT fields_json FROM club_event_forms WHERE event_id=?", (event_id,)
            ).fetchone()
            if form:
                fields = json.loads(form['fields_json'])
                for f in fields:
                    if f.get('required') and not answers.get(f['label'], '').strip():
                        return handler.send_json({'error': f'Required field missing: {f["label"]}'}, 400)

            # Upsert form submission
            existing_sub = c.execute(
                "SELECT id FROM club_event_form_submissions WHERE event_id=? AND user_id=?",
                (event_id, user['id'])
            ).fetchone()
            if existing_sub:
                c.execute(
                    "UPDATE club_event_form_submissions SET answers_json=?, submitted_at=? WHERE id=?",
                    (json.dumps(answers), now(), existing_sub['id'])
                )
            else:
                c.execute(
                    "INSERT INTO club_event_form_submissions(event_id, user_id, answers_json, submitted_at) VALUES(?,?,?,?)",
                    (event_id, user['id'], json.dumps(answers), now())
                )

        # Paid events require a payment proof screenshot before we register
        payment_proof = (body.get('paymentProof') or '').strip()
        payment_note = (body.get('paymentNote') or '').strip()
        if event['is_paid'] and not payment_proof:
            return handler.send_json({'error': 'Please upload a payment screenshot to complete registration'}, 400)
        payment_status = 'pending' if event['is_paid'] else None

        existing = c.execute(
            "SELECT status, payment_status FROM event_registrations WHERE event_id=? AND user_id=?",
            (event_id, user['id'])
        ).fetchone()

        if existing:
            if existing['status'] == 'registered' and (not event['is_paid'] or existing['payment_status'] == 'verified'):
                return handler.send_json({'error': 'You are already registered'}, 400)
            # Allow re-submitting payment proof after a rejection, or resuming a cancelled registration
            c.execute(
                "UPDATE event_registrations SET status='registered', registered_at=?, "
                "payment_status=?, payment_proof=?, payment_note=? WHERE event_id=? AND user_id=?",
                (now(), payment_status, payment_proof or None, payment_note or None, event_id, user['id'])
            )
        else:
            c.execute(
                "INSERT INTO event_registrations(event_id, user_id, payment_status, payment_proof, payment_note) "
                "VALUES(?,?,?,?,?)",
                (event_id, user['id'], payment_status, payment_proof or None, payment_note or None)
            )

        # If this is a paid club event, let the leadership know a payment needs verifying
        if event['is_paid'] and event['club_id']:
            leaders = c.execute(
                "SELECT user_id FROM club_members WHERE club_id=? AND status='active' AND role IN('leader','co-leader')",
                (event['club_id'],)
            ).fetchall()
            for l in leaders:
                notify(c, l['user_id'], 'payment_pending',
                       f'Payment to verify — {event["title"]}',
                       f'{user["full_name"]} submitted a payment proof for "{event["title"]}". Review it in Event Registrants.',
                       'event', str(event_id))

        audit(c, user['id'], user['access_role'], 'registered_event', 'event', str(event_id))
        c.commit()
        msg = f'Registered for {event["title"]}.'
        if event['is_paid']:
            msg += ' Your payment is pending verification by the club.'
        handler.send_json({'message': msg})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — VERIFY / REJECT PAYMENT (club leader / co-leader / staff)
# ══════════════════════════════════════════════════════════════

def handle_review_payment(handler, event_id, target_user_id, action):
    """POST /api/events/<event_id>/registrants/<user_id>/payment/(verify|reject)"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        event = c.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not event:
            return handler.send_json({'error': 'Event not found'}, 404)

        is_leadership = event['club_id'] and _is_club_leadership(c, event['club_id'], user['id'])
        if not is_leadership and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Not authorized to verify payments for this event'}, 403)

        reg = c.execute(
            "SELECT * FROM event_registrations WHERE event_id=? AND user_id=?",
            (event_id, target_user_id)
        ).fetchone()
        if not reg:
            return handler.send_json({'error': 'Registration not found'}, 404)

        new_status = 'verified' if action == 'verify' else 'rejected'
        c.execute(
            "UPDATE event_registrations SET payment_status=? WHERE event_id=? AND user_id=?",
            (new_status, event_id, target_user_id)
        )
        notify(c, target_user_id,
               'payment_verified' if action == 'verify' else 'payment_rejected',
               f'Payment {"verified" if action=="verify" else "not verified"} — {event["title"]}',
               f'Your payment for "{event["title"]}" was {"verified. You are confirmed for the event." if action=="verify" else "not verified. Please check your payment and re-upload proof, or contact the organizers."}',
               'event', str(event_id))

        audit(c, user['id'], user['access_role'], f'payment_{new_status}', 'event', str(event_id))
        c.commit()
        handler.send_json({'message': f'Payment marked as {new_status}.'})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# EVENTS — GET REGISTRANTS (club leader / staff)
# ══════════════════════════════════════════════════════════════

def handle_get_event_registrants(handler, event_id):
    """GET /api/events/<event_id>/registrants"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        event = c.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not event:
            return handler.send_json({'error': 'Event not found'}, 404)

        # Check permission
        is_leader = event['club_id'] and _is_club_leadership(c, event['club_id'], user['id'])
        if not is_leader and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Not authorized'}, 403)

        registrants = c.execute('''
            SELECT er.user_id, er.status, er.registered_at,
                   er.payment_status, er.payment_proof, er.payment_note,
                   u.full_name, u.student_id, u.branch, u.year, u.email, u.mobile,
                   fs.answers_json
            FROM event_registrations er
            JOIN users u ON u.id = er.user_id
            LEFT JOIN club_event_form_submissions fs ON fs.event_id=er.event_id AND fs.user_id=er.user_id
            WHERE er.event_id=? AND er.status='registered'
            ORDER BY er.registered_at
        ''', (event_id,)).fetchall()

        form = c.execute(
            "SELECT fields_json FROM club_event_forms WHERE event_id=?", (event_id,)
        ).fetchone()

        result = []
        for r in registrants:
            row = dict(r)
            row['answers'] = json.loads(r['answers_json']) if r['answers_json'] else {}
            del row['answers_json']
            result.append(row)

        handler.send_json({
            'event': dict(event),
            'registrants': result,
            'formFields': json.loads(form['fields_json']) if form else [],
        })
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — EVENTS FOR THIS CLUB (upcoming + past, for the profile page)
# ══════════════════════════════════════════════════════════════

def handle_get_club_events(handler, club_id):
    """GET /api/clubs/<club_id>/events"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        club = c.execute("SELECT id FROM clubs WHERE id=?", (club_id,)).fetchone()
        if not club:
            return handler.send_json({'error': 'Club not found'}, 404)

        events = c.execute('''
            SELECT e.id, e.title, e.description, e.event_date,
                   e.start_time AS time_start, e.end_time AS time_end,
                   e.location, e.event_type AS type, e.event_mode, e.status,
                   e.requires_form, e.is_paid, e.price,
                   (SELECT COUNT(*) FROM event_registrations er WHERE er.event_id=e.id AND er.status='registered') AS attendee_count,
                   (SELECT status FROM event_registrations er WHERE er.event_id=e.id AND er.user_id=?) AS my_status,
                   (SELECT payment_status FROM event_registrations er WHERE er.event_id=e.id AND er.user_id=?) AS my_payment_status
            FROM events e
            WHERE e.club_id=?
            ORDER BY e.event_date DESC, e.start_time DESC
        ''', (user['id'], user['id'], club_id)).fetchall()

        today = now()[:10]
        upcoming = [dict(x) for x in events if x['event_date'] >= today]
        past = [dict(x) for x in events if x['event_date'] < today]
        handler.send_json({'upcoming': upcoming, 'past': past})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — MEETINGS (internal, member-facing)
# ══════════════════════════════════════════════════════════════

def handle_get_club_meetings(handler, club_id):
    """GET /api/clubs/<club_id>/meetings"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        club = c.execute("SELECT id FROM clubs WHERE id=?", (club_id,)).fetchone()
        if not club:
            return handler.send_json({'error': 'Club not found'}, 404)

        is_member = c.execute(
            "SELECT 1 FROM club_members WHERE club_id=? AND user_id=? AND status='active'",
            (club_id, user['id'])
        ).fetchone()
        if not is_member and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Only club members can view meetings'}, 403)

        meetings = c.execute('''
            SELECT m.*, u.full_name AS created_by_name,
                   (SELECT COUNT(*) FROM club_meeting_rsvps r WHERE r.meeting_id=m.id AND r.status='going') AS going_count,
                   (SELECT status FROM club_meeting_rsvps r WHERE r.meeting_id=m.id AND r.user_id=?) AS my_rsvp
            FROM club_meetings m
            LEFT JOIN users u ON u.id = m.created_by
            WHERE m.club_id=?
            ORDER BY m.meeting_date DESC, m.start_time DESC
        ''', (user['id'], club_id)).fetchall()

        handler.send_json({'meetings': [dict(x) for x in meetings]})
    finally:
        c.close()


def handle_create_club_meeting(handler, club_id):
    """POST /api/clubs/<club_id>/meetings"""
    user = handler.auth()
    if not user: return

    body = handler.body()
    title = (body.get('title') or '').strip()
    if not title:
        return handler.send_json({'error': 'Meeting title is required'}, 400)
    if not body.get('meetingDate'):
        return handler.send_json({'error': 'Meeting date is required'}, 400)

    c = conn()
    try:
        if not _is_club_leadership(c, club_id, user['id']) and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Only club leader, co-leader or staff can schedule meetings'}, 403)

        mode = body.get('meetingMode', 'offline')
        if mode not in ('online', 'offline', 'hybrid'):
            mode = 'offline'

        c.execute('''
            INSERT INTO club_meetings(club_id, title, agenda, meeting_date, start_time,
                end_time, location, meeting_mode, online_link, created_by, status, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            club_id, title, (body.get('agenda') or '').strip(), body.get('meetingDate'),
            body.get('startTime', ''), body.get('endTime', ''),
            (body.get('location') or '').strip(), mode,
            (body.get('onlineLink') or '').strip(), user['id'], 'scheduled', now()
        ))
        meeting_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]

        club = c.execute("SELECT name FROM clubs WHERE id=?", (club_id,)).fetchone()
        members = c.execute(
            "SELECT user_id FROM club_members WHERE club_id=? AND status='active' AND user_id!=?",
            (club_id, user['id'])
        ).fetchall()
        for m in members:
            notify(c, m['user_id'], 'meeting_scheduled',
                   f'New meeting — {club["name"]}',
                   f'"{title}" is scheduled on {body.get("meetingDate")}. Check the club Meetings tab.',
                   'club', str(club_id))

        audit(c, user['id'], user['access_role'], 'meeting_scheduled', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': 'Meeting scheduled.', 'meetingId': meeting_id})
    finally:
        c.close()


def handle_rsvp_meeting(handler, meeting_id, status):
    """POST /api/meetings/<meeting_id>/rsvp/(going|not_going)"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        meeting = c.execute("SELECT * FROM club_meetings WHERE id=?", (meeting_id,)).fetchone()
        if not meeting:
            return handler.send_json({'error': 'Meeting not found'}, 404)

        is_member = c.execute(
            "SELECT 1 FROM club_members WHERE club_id=? AND user_id=? AND status='active'",
            (meeting['club_id'], user['id'])
        ).fetchone()
        if not is_member:
            return handler.send_json({'error': 'Only club members can RSVP'}, 403)

        existing = c.execute(
            "SELECT id FROM club_meeting_rsvps WHERE meeting_id=? AND user_id=?",
            (meeting_id, user['id'])
        ).fetchone()
        if existing:
            c.execute("UPDATE club_meeting_rsvps SET status=?, responded_at=? WHERE id=?",
                      (status, now(), existing['id']))
        else:
            c.execute(
                "INSERT INTO club_meeting_rsvps(meeting_id,user_id,status,responded_at) VALUES(?,?,?,?)",
                (meeting_id, user['id'], status, now())
            )
        c.commit()
        handler.send_json({'message': f'RSVP updated: {status.replace("_"," ")}.'})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# CLUBS — GALLERY / "CLUB MEMORIES" (photos of past events & moments)
# ══════════════════════════════════════════════════════════════

def handle_get_club_gallery(handler, club_id):
    """GET /api/clubs/<club_id>/gallery"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        club = c.execute("SELECT id FROM clubs WHERE id=?", (club_id,)).fetchone()
        if not club:
            return handler.send_json({'error': 'Club not found'}, 404)

        photos = c.execute('''
            SELECT g.id, g.caption, g.image, g.created_at, g.uploaded_by, g.event_id,
                   u.full_name AS uploaded_by_name, e.title AS event_title
            FROM club_gallery g
            LEFT JOIN users u ON u.id = g.uploaded_by
            LEFT JOIN events e ON e.id = g.event_id
            WHERE g.club_id=?
            ORDER BY g.created_at DESC
        ''', (club_id,)).fetchall()

        handler.send_json({'photos': [dict(x) for x in photos]})
    finally:
        c.close()


def handle_add_gallery_photo(handler, club_id):
    """POST /api/clubs/<club_id>/gallery"""
    user = handler.auth()
    if not user: return

    body = handler.body()
    image = body.get('image')
    if (not isinstance(image, str) or re.match(r'^data:image/(?:jpeg|png|webp);base64,', image, re.I) is None or len(image) > 3_500_000):
        return handler.send_json({'error': 'A valid JPEG, PNG or WebP image is required.'}, 400)

    c = conn()
    try:
        is_member = c.execute(
            "SELECT 1 FROM club_members WHERE club_id=? AND user_id=? AND status='active'",
            (club_id, user['id'])
        ).fetchone()
        if not is_member and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Only club members can add memories'}, 403)

        event_id = body.get('eventId') or None
        c.execute('''
            INSERT INTO club_gallery(club_id, event_id, uploaded_by, caption, image, created_at)
            VALUES(?,?,?,?,?,?)
        ''', (club_id, event_id, user['id'], (body.get('caption') or '').strip(), image, now()))
        photo_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]

        audit(c, user['id'], user['access_role'], 'gallery_photo_added', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': 'Memory added!', 'photoId': photo_id})
    finally:
        c.close()


def handle_delete_gallery_photo(handler, club_id, photo_id):
    """POST /api/clubs/<club_id>/gallery/<photo_id>/delete"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        photo = c.execute(
            "SELECT * FROM club_gallery WHERE id=? AND club_id=?", (photo_id, club_id)
        ).fetchone()
        if not photo:
            return handler.send_json({'error': 'Photo not found'}, 404)

        is_leader = _is_club_leadership(c, club_id, user['id'])
        if photo['uploaded_by'] != user['id'] and not is_leader and not _is_club_staff_or_admin(user):
            return handler.send_json({'error': 'Not authorized to delete this photo'}, 403)

        c.execute("DELETE FROM club_gallery WHERE id=?", (photo_id,))
        audit(c, user['id'], user['access_role'], 'gallery_photo_deleted', 'club', str(club_id))
        c.commit()
        handler.send_json({'message': 'Memory removed.'})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# "MY REQUESTS" — unified, student-facing status tracker
# (surfaced inside the Notices page so a student can see, in one
#  place, whether anything they requested is pending/approved/declined)
# ══════════════════════════════════════════════════════════════

def handle_my_requests(handler):
    """GET /api/my-requests"""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        out = []

        # 1) Clubs this user proposed
        proposals = c.execute('''
            SELECT id, name, status, created_at, staff_rejection_reason
            FROM clubs WHERE founder_user_id=?
            ORDER BY created_at DESC
        ''', (user['id'],)).fetchall()
        for p in proposals:
            status = {'pending_staff': 'pending', 'active': 'approved',
                      'rejected': 'declined', 'archived': 'archived'}.get(p['status'], p['status'])
            out.append({
                'kind': 'Club proposal', 'title': p['name'], 'status': status,
                'detail': p['staff_rejection_reason'] if status == 'declined' and p['staff_rejection_reason'] else
                          ('You are the club leader.' if status == 'approved' else 'Awaiting staff review.'),
                'created_at': p['created_at'],
            })

        # 2) Club membership (join) requests made by this user
        memberships = c.execute('''
            SELECT cm.status, cm.joined_at, cl.name AS club_name
            FROM club_members cm JOIN clubs cl ON cl.id = cm.club_id
            WHERE cm.user_id=? AND cm.role != 'leader'
            ORDER BY cm.joined_at DESC
        ''', (user['id'],)).fetchall()
        for m in memberships:
            status = {'pending': 'pending', 'active': 'approved', 'rejected': 'declined'}.get(m['status'], m['status'])
            out.append({
                'kind': 'Club join request', 'title': m['club_name'], 'status': status,
                'detail': 'Waiting for the club leader to respond.' if status == 'pending' else
                          ('You are a member of this club.' if status == 'approved' else 'Your request was not approved.'),
                'created_at': m['joined_at'],
            })

        # 3) Paid-event payment verifications
        payments = c.execute('''
            SELECT er.payment_status, er.registered_at, e.title, e.id AS event_id
            FROM event_registrations er JOIN events e ON e.id = er.event_id
            WHERE er.user_id=? AND er.payment_status IS NOT NULL
            ORDER BY er.registered_at DESC
        ''', (user['id'],)).fetchall()
        for p in payments:
            status = {'pending': 'pending', 'verified': 'approved', 'rejected': 'declined'}.get(p['payment_status'], p['payment_status'])
            out.append({
                'kind': 'Event payment', 'title': p['title'], 'status': status,
                'detail': 'Waiting for the organizers to verify your payment.' if status == 'pending' else
                          ('Payment verified — you are confirmed.' if status == 'approved' else 'Payment was not verified. Please re-check and resubmit.'),
                'created_at': p['registered_at'],
            })

        # 4) Lost & Found reports submitted by this student.
        lost_found = c.execute('''
            SELECT item_name, report_type, status, created_at, location
            FROM lost_found_items
            WHERE reporter_user_id=?
            ORDER BY created_at DESC
        ''', (user['id'],)).fetchall()
        for lf in lost_found:
            status = {'open': 'pending', 'matched': 'approved', 'claim_pending': 'pending',
                      'verified': 'approved', 'resolved': 'approved', 'expired': 'declined',
                      'rejected': 'declined'}.get(lf['status'], lf['status'])
            out.append({
                'kind': 'Lost & Found report',
                'title': lf['item_name'],
                'status': status,
                'detail': f"{lf['report_type'].title()} item · {lf['location'] or 'Location not specified'}",
                'created_at': lf['created_at'],
            })

        # 5) Campus problem reports submitted by this student.
        problems = c.execute('''
            SELECT category, status, created_at, location
            FROM problem_reports
            WHERE reporter_user_id=?
            ORDER BY created_at DESC
        ''', (user['id'],)).fetchall()
        for pr in problems:
            status = {'reported': 'pending', 'acknowledged': 'pending', 'assigned': 'pending',
                      'in_progress': 'pending', 'resolved': 'approved', 'rejected': 'declined'}.get(pr['status'], pr['status'])
            out.append({
                'kind': 'Problem report',
                'title': pr['category'],
                'status': status,
                'detail': f"{pr['location']} · {pr['status'].replace('_',' ').title()}",
                'created_at': pr['created_at'],
            })

        # 6) Locker requests (existing feature — surfaced here too)
        try:
            lockers = c.execute('''
                SELECT lr.status, lr.created_at, lr.locker_id, lr.rejection_reason
                FROM locker_requests lr WHERE lr.student_user_id=?
                ORDER BY lr.created_at DESC LIMIT 10
            ''', (user['id'],)).fetchall()
            for l in lockers:
                status = {'pending': 'pending', 'assigned': 'approved', 'approved': 'approved',
                          'rejected': 'declined', 'cancelled': 'declined', 'expired': 'declined'}.get(l['status'], l['status'])
                out.append({
                    'kind': 'Locker request', 'title': f'Locker {l["locker_id"]}', 'status': status,
                    'detail': l['rejection_reason'] or ('Awaiting admin review.' if status == 'pending' else ''),
                    'created_at': l['created_at'],
                })
        except DatabaseOperationalError:
            pass

        out.sort(key=lambda x: x['created_at'] or '', reverse=True)
        handler.send_json({'myRequests': out})
    finally:
        c.close()


# ══════════════════════════════════════════════════════════════
# STAFF — UNIFIED REQUESTS QUEUE (club proposals + membership requests)
# ══════════════════════════════════════════════════════════════

def handle_club_requests_queue(handler):
    """GET /api/clubs/requests-queue — staff-only aggregation used by the
    'Requests' page in the side menu, so staff don't have to hunt through
    every club individually to find pending items."""
    user = handler.auth()
    if not user: return
    if not _is_club_staff_or_admin(user):
        return handler.send_json({'error': 'Staff access required'}, 403)

    c = conn()
    try:
        proposals = c.execute('''
            SELECT cl.id, cl.name, cl.category, cl.description, cl.created_at,
                   u.full_name AS founder_name, u.student_id AS founder_student_id
            FROM clubs cl LEFT JOIN users u ON u.id = cl.founder_user_id
            WHERE cl.status='pending_staff'
            ORDER BY cl.created_at
        ''').fetchall()

        memberships = c.execute('''
            SELECT cm.id AS member_id, cm.club_id, cm.joined_at,
                   cl.name AS club_name,
                   u.full_name, u.student_id, u.branch, u.year
            FROM club_members cm
            JOIN clubs cl ON cl.id = cm.club_id
            JOIN users u ON u.id = cm.user_id
            WHERE cm.status='pending'
            ORDER BY cm.joined_at
        ''').fetchall()

        handler.send_json({
            'clubProposals': [dict(x) for x in proposals],
            'membershipRequests': [dict(x) for x in memberships],
        })
    finally:
        c.close()
