"""Campus Buddy — Services Module (Lost & Found, Problem Reports)."""
import sqlite3
from datetime import datetime
from backend.utils import conn, now, get_permissions, audit, notify

def _is_staff(user):
    return user['access_role'] != 'student'

def handle_get_lost_found(handler):
    """GET /api/lostfound — students only see their own reports; staff see all."""
    user = handler.auth()
    if not user: return

    c = conn()
    if _is_staff(user):
        items = c.execute('''
            SELECT lf.id, lf.report_type, lf.item_name, lf.category, lf.description,
                   lf.location, lf.date_occurred, lf.time_occurred, lf.status, lf.created_at,
                   u.full_name as reporter_name
            FROM lost_found_items lf
            JOIN users u ON lf.reporter_user_id = u.id
            ORDER BY lf.created_at DESC
        ''').fetchall()
    else:
        items = c.execute('''
            SELECT lf.id, lf.report_type, lf.item_name, lf.category, lf.description,
                   lf.location, lf.date_occurred, lf.time_occurred, lf.status, lf.created_at,
                   u.full_name as reporter_name
            FROM lost_found_items lf
            JOIN users u ON lf.reporter_user_id = u.id
            WHERE lf.reporter_user_id = ?
            ORDER BY lf.created_at DESC
        ''', (user['id'],)).fetchall()
    c.close()
    handler.send_json({'items': [dict(x) for x in items]})


def handle_get_lost_found_detail(handler, item_id):
    """GET /api/lostfound/<id> — staff (or the reporter) can see reporter contact info."""
    user = handler.auth()
    if not user: return

    c = conn()
    try:
        item = c.execute('''
            SELECT lf.*, u.full_name as reporter_name, u.student_id as reporter_student_id,
                   u.mobile as reporter_mobile, u.email as reporter_email
            FROM lost_found_items lf JOIN users u ON lf.reporter_user_id = u.id
            WHERE lf.id=?
        ''', (item_id,)).fetchone()
        if not item:
            return handler.send_json({'error': 'Report not found'}, 404)
        if not _is_staff(user) and item['reporter_user_id'] != user['id']:
            return handler.send_json({'error': 'Not authorized'}, 403)
        handler.send_json({'item': dict(item)})
    finally:
        c.close()


def _normalize_lf_date(value):
    value = str(value or '').strip()
    if not value:
        return value
    for fmt in ('%Y-%m-%d','%y-%m-%d','%Y/%m/%d','%y/%m/%d'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return value


def _lf_words(text):
    return {w for w in (text or '').lower().split() if len(w) >= 3}

def _find_lf_match(c, new_item_id, report_type, category, item_name):
    """Very lightweight matcher: same category (if set) and at least one
    shared significant word in the item name, against the opposite report type."""
    opposite = 'found' if report_type == 'lost' else 'lost'
    candidates = c.execute('''
        SELECT id, item_name, category, reporter_user_id FROM lost_found_items
        WHERE report_type=? AND status='open' AND id != ?
    ''', (opposite, new_item_id)).fetchall()
    new_words = _lf_words(item_name)
    for cand in candidates:
        if category and cand['category'] and category.lower() != cand['category'].lower():
            continue
        if new_words & _lf_words(cand['item_name']):
            return cand
    return None


def handle_create_lost_found(handler):
    """POST /api/lostfound"""
    user = handler.auth()
    if not user: return
    
    d = handler.body()
    date_occurred = _normalize_lf_date(d.get('date'))
    if date_occurred:
        try:
            datetime.strptime(date_occurred, '%Y-%m-%d')
        except ValueError:
            return handler.send_json({'error': 'Use a valid date like 2026-09-14.'}, 400)
    c = conn()
    try:
        c.execute('''
            INSERT INTO lost_found_items(report_type, item_name, category, description, location, date_occurred, time_occurred, reporter_user_id)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ''', (d.get('type'), d.get('name'), d.get('category'), d.get('description'), d.get('location'), date_occurred, d.get('time'), user['id']))
        item_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Look for a possible match on the opposite list and notify both parties.
        match = _find_lf_match(c, item_id, d.get('type'), d.get('category'), d.get('name'))
        if match:
            c.execute("UPDATE lost_found_items SET status='matched' WHERE id IN(?,?)", (item_id, match['id']))
            notify(c, user['id'], 'lost_found_match',
                   'Possible match found!',
                   f'Your report for "{d.get("name")}" may match another report in Lost & Found. Visit the Lost & Found room to verify and collect/hand over the item.',
                   'lost_found_item', str(item_id))
            notify(c, match['reporter_user_id'], 'lost_found_match',
                   'Possible match found!',
                   f'Your report for "{match["item_name"]}" may match a new report in Lost & Found. Visit the Lost & Found room to verify and collect/hand over the item.',
                   'lost_found_item', str(match['id']))

        c.commit()
        handler.send_json({'message': 'Report submitted successfully', 'matched': bool(match)})
    finally:
        c.close()

def handle_remove_lost_found(handler, item_id):
    """POST /api/lostfound/<id>/remove — reporters can remove their own item."""
    user = handler.auth()
    if not user:
        return
    c = conn()
    try:
        item = c.execute(
            'SELECT id, reporter_user_id, item_name, status FROM lost_found_items WHERE id=?',
            (item_id,)
        ).fetchone()
        if not item:
            return handler.send_json({'error': 'Report not found'}, 404)
        if item['reporter_user_id'] != user['id'] and not _is_staff(user):
            return handler.send_json({'error': 'You can only remove your own report'}, 403)
        c.execute('DELETE FROM lost_found_items WHERE id=?', (item_id,))
        audit(c, user['id'], user['access_role'], 'lost_found_removed', 'lost_found_item', str(item_id), meta={'item_name': item['item_name']})
        c.commit()
        handler.send_json({'message': 'Lost & Found report removed.'})
    finally:
        c.close()


def handle_get_problems(handler):
    """GET /api/problems"""
    user = handler.auth()
    if not user: return
    
    c = conn()
    # Students only see their own reports. Admins/Staff see all.
    if user['access_role'] == 'student':
        items = c.execute('''
            SELECT p.id, p.category, p.location, p.description, p.photo, p.status, p.created_at
            FROM problem_reports p
            WHERE p.reporter_user_id = ?
            ORDER BY p.created_at DESC
        ''', (user['id'],)).fetchall()
    else:
        items = c.execute('''
            SELECT p.id, p.category, p.location, p.description, p.photo, p.status, p.created_at,
                   u.full_name as reporter_name
            FROM problem_reports p
            JOIN users u ON p.reporter_user_id = u.id
            ORDER BY p.created_at DESC
        ''').fetchall()
    c.close()
    handler.send_json({'problems': [dict(x) for x in items]})

def handle_create_problem(handler):
    """POST /api/problems"""
    user = handler.auth()
    if not user: return
    
    d = handler.body()
    category = str(d.get('category') or '').strip()
    location = str(d.get('location') or '').strip()
    description = str(d.get('description') or '').strip()
    photo = d.get('photo') or None
    allowed = {'Electrical','Water','Cleanliness','Furniture','Wi-Fi','Security','Infrastructure','Other'}
    if category not in allowed or not location or not description:
        return handler.send_json({'error': 'Category, location and description are required.'}, 400)
    if photo and (not isinstance(photo, str) or not re.match(r'^data:image/(?:jpeg|png|webp);base64,', photo, re.I) is not None or len(photo) > 3_500_000):
        return handler.send_json({'error': 'Problem image is too large or invalid.'}, 400)
    c = conn()
    try:
        c.execute('''
            INSERT INTO problem_reports(reporter_user_id, category, location, description, photo)
            VALUES(?, ?, ?, ?, ?)
        ''', (user['id'], category, location, description, photo))
        report_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        if not photo:
            notify(c, user['id'], 'problem_report_priority', 'Report submitted as low priority',
                   'This issue was submitted without a photo, so it will be considered lower priority during review.',
                   'problem_report', str(report_id))
        audit(c, user['id'], user['access_role'], 'problem_report_created', 'problem_report', str(report_id), meta={'has_photo': bool(photo)})
        c.commit()
        handler.send_json({'message': 'Problem reported successfully', 'lowPriority': not bool(photo)})
    finally:
        c.close()


def handle_broadcast_notice(handler):
    """POST /api/notices/broadcast — staff issue a notice to all students."""
    user = handler.auth()
    if not user: return
    if not _is_staff(user):
        return handler.send_json({'error': 'Only staff can post notices'}, 403)

    d = handler.body()
    title = (d.get('title') or '').strip()
    body = (d.get('body') or '').strip()
    if not title or not body:
        return handler.send_json({'error': 'Title and message are required'}, 400)

    c = conn()
    try:
        students = c.execute("SELECT id FROM users WHERE access_role='student'").fetchall()
        for s in students:
            notify(c, s['id'], 'staff_notice', title, body, 'notice', None)
        audit(c, user['id'], user['access_role'], 'notice_posted', 'notice', title[:60])
        c.commit()
        handler.send_json({'message': f'Notice posted to {len(students)} students.'})
    finally:
        c.close()
