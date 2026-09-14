"""Campus Buddy — Database schema, migration, and seeding."""
import secrets, re
from backend.config import (
    ROOT, DB, PRIMARY_ADMIN_LOGIN, REQUEST_DAYS,
    FLOOR_CODES, PERMISSIONS, SEED_DEMO, BOOTSTRAP_ADMIN_NAME,
    BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD, BOOTSTRAP_ADMIN_MOBILE,
)
from backend.utils import (
    conn, hpw, now, later, ensure_column, audit, notify, locker_event,
)
from backend.config import IS_PRODUCTION


def migrate():
    """Apply the full schema and run forward-compatible migrations."""
    c = conn()

    using_postgres = bool(__import__('os').environ.get('DATABASE_URL', '').strip())

    # SQLite-only legacy introspection is skipped on fresh PostgreSQL deployments.
    if not using_postgres:
        existing_users = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if existing_users:
            for name, ddl in [
                ('access_role', "TEXT NOT NULL DEFAULT 'student'"),
                ('account_type', "TEXT NOT NULL DEFAULT 'student'"),
                ('is_primary_admin', 'INTEGER NOT NULL DEFAULT 0'),
            ]:
                ensure_column(c, 'users', name, ddl)

        if c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lockers'"
        ).fetchone():
            ensure_column(c, 'lockers', 'qr_token', 'TEXT')

    # Apply full schema (CREATE IF NOT EXISTS)
    c.executescript((ROOT / 'database' / 'schema.sql').read_text(encoding='utf-8'))

    # Ensure all user columns exist (forward-compat)
    for name, ddl in [
        ('is_primary_admin', 'INTEGER NOT NULL DEFAULT 0'),
        ('branch', 'TEXT'), ('semester', 'TEXT'), ('campus', 'TEXT'),
        ('profile_photo', 'TEXT'),
        ('account_type', "TEXT NOT NULL DEFAULT 'student'"),
        ('joined_at', 'TEXT'), ('year', 'TEXT'), ('course', 'TEXT'),
        ('mobile', 'TEXT'), ('email', 'TEXT'),
        ('access_role', "TEXT NOT NULL DEFAULT 'student'"),
    ]:
        ensure_column(c, 'users', name, ddl)

    ensure_column(c, 'floors', 'building_id', 'INTEGER')

    # Forward-compat: new clubs columns
    for name, ddl in [
        ('founder_user_id', 'INTEGER'),
        ('contact_email', 'TEXT'),
        ('contact_phone', 'TEXT'),
        ('meeting_schedule', 'TEXT'),
        ('staff_reviewer_id', 'INTEGER'),
        ('staff_reviewed_at', 'TEXT'),
        ('staff_rejection_reason', 'TEXT'),
    ]:
        ensure_column(c, 'clubs', name, ddl)

    # Forward-compat: new events columns
    for name, ddl in [
        ('event_mode', "TEXT NOT NULL DEFAULT 'offline'"),
        ('online_link', 'TEXT'),
        ('requires_form', 'INTEGER NOT NULL DEFAULT 0'),
        ('is_paid', 'INTEGER NOT NULL DEFAULT 0'),
        ('price', 'REAL NOT NULL DEFAULT 0'),
        ('payment_qr_image', 'TEXT'),
    ]:
        ensure_column(c, 'events', name, ddl)

    # Forward-compat: new event_registrations columns (paid-event payment proof)
    for name, ddl in [
        ('payment_status', 'TEXT'),      # NULL, 'pending', 'verified', 'rejected'
        ('payment_proof', 'TEXT'),       # base64 screenshot uploaded by student
        ('payment_note', 'TEXT'),        # optional transaction reference
    ]:
        ensure_column(c, 'event_registrations', name, ddl)

    # Forward-compat: new club_members columns
    ensure_column(c, 'club_members', 'status', "TEXT NOT NULL DEFAULT 'active'")

    # Migrate old club status values
    c.execute("UPDATE clubs SET status='active' WHERE status='approved'")
    c.execute("UPDATE clubs SET status='pending_staff' WHERE status='pending'")

    # Migrate legacy locker_requests only for SQLite legacy databases. Fresh PostgreSQL
    # installs receive the current schema directly.
    req_row = None
    if not using_postgres:
        req_row = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='locker_requests'"
        ).fetchone()
    if req_row:
        request_sql = req_row[0]
        if request_sql and 'assigned' not in request_sql:
            c.execute('ALTER TABLE locker_requests RENAME TO locker_requests_legacy')
            for idx in c.execute('PRAGMA index_list(locker_requests_legacy)').fetchall():
                idx_name = idx[1]
                if idx_name.startswith('idx_'):
                    c.execute(f'DROP INDEX IF EXISTS {idx_name}')
            c.executescript((ROOT / 'database' / 'schema.sql').read_text(encoding='utf-8'))
            old = c.execute('SELECT * FROM locker_requests_legacy').fetchall()
            for r in old:
                status = (
                    'assigned' if r['status'] == 'approved'
                    else (r['status'] if r['status'] in
                          {'pending', 'rejected', 'cancelled', 'expired', 'assigned'}
                          else 'pending')
                )
                c.execute(
                    'INSERT INTO locker_requests(request_code,locker_id,'
                    'student_user_id,status,created_at,reviewed_at,reviewed_by,'
                    'rejection_reason,expires_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (r['request_code'], r['locker_id'], r['student_user_id'],
                     status, r['created_at'], r['reviewed_at'], r['reviewed_by'],
                     None, later(REQUEST_DAYS))
                )
            c.execute('DROP TABLE locker_requests_legacy')

    # Normalize legacy role data
    c.execute(
        "UPDATE users SET account_type=CASE WHEN role='admin' THEN 'staff' "
        "ELSE 'student' END WHERE account_type IS NULL OR account_type=''"
    )
    c.execute(
        "UPDATE users SET access_role=CASE WHEN role='student' THEN 'student' "
        "WHEN is_primary_admin=1 THEN 'super_admin' ELSE 'staff' END "
        "WHERE access_role IS NULL OR access_role=''"
    )
    c.execute('UPDATE users SET joined_at=COALESCE(joined_at, created_at)')
    c.execute(
        "UPDATE users SET campus='Dwarka Campus' "
        "WHERE campus IS NULL OR campus=''"
    )

    # Seed campuses and buildings
    for code, name in [
        ('DWK', 'Dwarka Campus'), ('GBP', 'G.B Pant'),
        ('SHA', 'Shakarpur'), ('BPR', 'Bhai Premanand'),
    ]:
        c.execute(
            'INSERT OR IGNORE INTO campuses(code,name,active) VALUES(?,?,?)',
            (code, name, 1 if name == 'Dwarka Campus' else 0)
        )
    dw = c.execute(
        "SELECT id FROM campuses WHERE name='Dwarka Campus'"
    ).fetchone()[0]
    c.execute(
        'INSERT OR IGNORE INTO buildings(campus_id,name,code) VALUES(?,?,?)',
        (dw, 'Main Academic Block', 'MAB')
    )
    bid = c.execute(
        "SELECT id FROM buildings WHERE campus_id=? AND code='MAB'", (dw,)
    ).fetchone()[0]
    c.execute(
        'UPDATE floors SET building_id=? WHERE building_id IS NULL', (bid,)
    )
    for f, code in FLOOR_CODES.items():
        c.execute(
            'UPDATE floors SET code=?,name=? WHERE floor_number=?',
            (code, f'Floor {f}', f)
        )

    # Normalize locker display codes
    rows = c.execute(
        'SELECT l.id,l.locker_id,f.floor_number FROM lockers l '
        'JOIN locker_rooms rr ON rr.id=l.room_id '
        'JOIN floors f ON f.id=rr.floor_id'
    ).fetchall()
    for r in rows:
        m = re.fullmatch(r'F(\d+)-R[^/]+-L(\d+)', r['locker_id'] or '')
        if m:
            f, num = int(m.group(1)), int(m.group(2))
            c.execute(
                'UPDATE lockers SET locker_id=? WHERE id=?',
                (f'{FLOOR_CODES.get(f, "A")}1-{num:03d}', r['id'])
            )

    for f in range(1, 5):
        c.execute(
            "UPDATE locker_rooms SET room_code='1',room_name='Locker Group 1' "
            "WHERE floor_id=(SELECT id FROM floors WHERE floor_number=?)", (f,)
        )
    for r in c.execute(
        "SELECT id FROM lockers WHERE qr_token IS NULL OR qr_token=''"
    ).fetchall():
        c.execute(
            'UPDATE lockers SET qr_token=? WHERE id=?',
            (secrets.token_urlsafe(18), r['id'])
        )

    # Primary admin setup
    c.execute("UPDATE users SET is_primary_admin=0 WHERE role='admin'")
    primary = c.execute(
        "SELECT id FROM users WHERE username=? AND role='admin' AND active=1",
        (PRIMARY_ADMIN_LOGIN,)
    ).fetchone()
    if not primary:
        primary = c.execute(
            "SELECT id FROM users WHERE role='admin' AND active=1 "
            "ORDER BY id LIMIT 1"
        ).fetchone()
    if primary:
        c.execute(
            "UPDATE users SET is_primary_admin=1,access_role='super_admin',"
            "account_type='staff' WHERE id=?", (primary['id'],)
        )
    c.execute(
        "UPDATE users SET access_role='staff' WHERE role='admin' "
        "AND is_primary_admin=0 AND (access_role IS NULL OR "
        "access_role='student' OR access_role='super_admin')"
    )

    # Demo/test credentials are created only by seed() when SEED_DEMO=1.
    # Production bootstraps exactly one administrator from environment variables.
    if not SEED_DEMO:
        admin = c.execute("SELECT id FROM users WHERE role='admin' AND active=1 ORDER BY is_primary_admin DESC, id LIMIT 1").fetchone()
        if not admin:
            if not BOOTSTRAP_ADMIN_PASSWORD or len(BOOTSTRAP_ADMIN_PASSWORD) < 12:
                raise RuntimeError('No active administrator exists. Set CAMPUSCONNECT_BOOTSTRAP_ADMIN_PASSWORD to a long random password before first production start.')
            if not BOOTSTRAP_ADMIN_EMAIL or '@' not in BOOTSTRAP_ADMIN_EMAIL:
                raise RuntimeError('No production administrator email configured. Set CAMPUSCONNECT_BOOTSTRAP_ADMIN_EMAIL before first production start.')
            login = PRIMARY_ADMIN_LOGIN
            c.execute(
                'INSERT INTO users(student_id,username,password_hash,full_name,role,branch,mobile,email,account_type,access_role,is_primary_admin,campus,joined_at,active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)',
                (login, login, hpw(BOOTSTRAP_ADMIN_PASSWORD), BOOTSTRAP_ADMIN_NAME, 'admin', 'Administration', BOOTSTRAP_ADMIN_MOBILE, BOOTSTRAP_ADMIN_EMAIL, 'staff', 'super_admin', 1, 'Dwarka Campus', now())
            )
        else:
            c.execute("UPDATE users SET is_primary_admin=0 WHERE role='admin'")
            c.execute("UPDATE users SET is_primary_admin=1,access_role='super_admin',account_type='staff' WHERE id=?", (admin['id'],))
    c.commit()
    c.close()


def seed():
    """Run migrations and initialize production or demo data safely."""
    migrate()
    c = conn()
    user_count = c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    c.close()
    if user_count:
        return
    if not SEED_DEMO:
        # Production bootstrap admin was created by migrate().
        return
    c = conn()

    c.execute('BEGIN')

    # Admin
    c.execute(
        'INSERT INTO users(student_id,username,password_hash,full_name,role,'
        'mobile,email,account_type,access_role,is_primary_admin,campus,joined_at) '
        'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
        ('ADMIN001', 'ADMIN001', hpw('admin123'), 'Priya Mehta', 'admin',
         '9876500011', 'admin@college.edu', 'staff', 'super_admin', 1,
         'Dwarka Campus', now())
    )

    # Students
    students = [
        ('STU1001', 'Aarav Sharma', 'B.Tech Computer Science', 'CSE', '3', '2nd Year', '9876501001'),
        ('STU1002', 'Riya Kapoor', 'BBA', 'Management', '2', '1st Year', '9876501002'),
        ('STU1003', 'Kabir Singh', 'B.Com', 'Commerce', '5', '3rd Year', '9876501003'),
        ('STU1004', 'Ishita Jain', 'B.Tech Information Technology', 'IT', '3', '2nd Year', '9876501004'),
        ('STU1005', 'Dev Patel', 'B.Sc Physics', 'Physics', '2', '1st Year', '9876501005'),
        ('STU1006', 'Neha Verma', 'BA English', 'English', '3', '2nd Year', '9876501006'),
        ('STU1007', 'Ananya Gupta', 'B.Tech Computer Science', 'CSE', '1', '1st Year', '9876501007'),
        ('STU1008', 'Yash Malhotra', 'BCA', 'Computer Applications', '5', '3rd Year', '9876501008'),
        ('STU1009', 'Meera Nair', 'BBA', 'Management', '4', '2nd Year', '9876501009'),
        ('STU1010', 'Arjun Rao', 'B.Tech Electronics', 'ECE', '7', '4th Year', '9876501010'),
        ('STU1011', 'Simran Kaur', 'B.Des', 'Design', '1', '1st Year', '9876501011'),
        ('STU1012', 'Aditya Mehta', 'B.Tech Mechanical', 'Mechanical', '5', '3rd Year', '9876501012'),
    ]
    for sid, name, course, branch, sem, year, mobile in students:
        c.execute(
            'INSERT INTO users(student_id,username,password_hash,full_name,'
            'role,course,branch,semester,year,mobile,email,account_type,'
            'access_role,campus,joined_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (sid, sid, hpw('student123'), name, 'student', course, branch,
             sem, year, mobile, f'{sid.lower()}@student.college.edu',
             'student', 'student', 'Dwarka Campus', now())
        )

    # Default tester students retained for local/SIH demos only.
    for sid, name, mobile in [('STU0001', 'Student-1', '9876500001'), ('STU0002', 'Student-2', '9876500002')]:
        c.execute(
            'INSERT INTO users(student_id,username,password_hash,full_name,role,branch,semester,year,course,mobile,email,account_type,access_role,campus,joined_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (sid, sid, hpw('123456789'), name, 'student', 'CSE', '1', '1st Year', 'B.Tech Computer Science', mobile, f'{sid.lower()}@student.college.edu', 'student', 'student', 'Dwarka Campus', now())
        )

    # Floors and locker rooms
    for f in range(1, 5):
        c.execute(
            'INSERT INTO floors(floor_number,name,code,building_id) '
            "VALUES(?,?,?,(SELECT id FROM buildings WHERE code='MAB'))",
            (f, f'Floor {f}', FLOOR_CODES[f])
        )
        fid = c.execute(
            'SELECT id FROM floors WHERE floor_number=?', (f,)
        ).fetchone()[0]
        c.execute(
            'INSERT INTO locker_rooms(floor_id,room_code,room_name) '
            'VALUES(?,?,?)', (fid, '1', 'Locker Group 1')
        )

    ids = [r['id'] for r in c.execute(
        "SELECT id FROM users WHERE role='student' ORDER BY id LIMIT 5"
    ).fetchall()]

    for f, code in FLOOR_CODES.items():
        rid = c.execute(
            'SELECT rr.id FROM locker_rooms rr '
            'JOIN floors ff ON ff.id=rr.floor_id '
            "WHERE ff.floor_number=? AND rr.room_code='1'", (f,)
        ).fetchone()[0]
        for i in range(1, 21):
            status = 'occupied' if i in {2, 5, 9, 14, 17} else 'available'
            uid = ids[(i + f) % len(ids)] if status == 'occupied' else None
            assigned = now() if uid else None
            lid = f'{code}1-{i:03d}'
            c.execute(
                'INSERT INTO lockers(locker_id,room_id,status,'
                'student_user_id,assigned_at,qr_token) VALUES(?,?,?,?,?,?)',
                (lid, rid, status, uid, assigned, secrets.token_urlsafe(18))
            )
            locker_pk = c.execute('SELECT last_insert_rowid()').fetchone()[0]
            if uid:
                locker_event(c, locker_pk, uid, 'assignment', None,
                             'occupied', notes='Seeded demo assignment')

    # Demo pending requests
    for rc, sid, lid in [
        ('REQ001', 'STU1007', 'A1-004'),
        ('REQ002', 'STU1012', 'C1-011'),
    ]:
        li = c.execute(
            'SELECT id FROM lockers WHERE locker_id=?', (lid,)
        ).fetchone()[0]
        uid = c.execute(
            'SELECT id FROM users WHERE student_id=?', (sid,)
        ).fetchone()[0]
        c.execute(
            'INSERT INTO locker_requests(request_code,locker_id,'
            'student_user_id,status,expires_at) VALUES(?,?,?,?,?)',
            (rc, li, uid, 'pending', later(REQUEST_DAYS))
        )
        c.execute(
            "UPDATE lockers SET status='pending' WHERE id=?", (li,)
        )
        locker_event(c, li, uid, 'request_submitted', 'available',
                     'pending', rc, 'Seeded demo request')

    # Seed demo clubs
    admin_id = c.execute(
        "SELECT id FROM users WHERE username='ADMIN001'"
    ).fetchone()[0]
    stu1_id = c.execute("SELECT id FROM users WHERE username='STU1001'").fetchone()[0]
    stu2_id = c.execute("SELECT id FROM users WHERE username='STU1002'").fetchone()[0]
    demo_clubs = [
        ('Web Development Club', 'Learn and build modern web applications together.',
         'Technical', 'CSE', stu1_id),
        ('Robotics Club', 'Explore robotics, IoT, and automation projects.',
         'Technical', 'ECE', stu2_id),
        ('Photography Club', 'Capture campus life through the lens.',
         'Creative', 'Design', admin_id),
        ('Debate Society', 'Sharpen your public speaking and argumentation skills.',
         'Cultural', 'English', admin_id),
        ('Coding Ninjas', 'Competitive programming and hackathon preparation.',
         'Technical', 'CSE', stu1_id),
    ]
    for club_name, desc, cat, dept, founder_id in demo_clubs:
        c.execute(
            'INSERT INTO clubs(name,description,category,department,'
            'founder_user_id,coordinator_user_id,status,created_at) VALUES(?,?,?,?,?,?,?,?)',
            (club_name, desc, cat, dept, founder_id, admin_id, 'active', now())
        )

    # Seed demo events
    from datetime import timedelta
    base = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    demo_events = [
        ('Web Development Workshop', 'Hands-on session covering HTML, CSS, and JS basics.',
         1, 'CSE Department', 1, 50, 'Workshop', 'offline'),
        ('Robotics Meetup', 'Monthly meetup to discuss ongoing robotics projects.',
         2, 'Robotics Lab', 0, 30, 'Meetup', 'offline'),
        ('Campus Photography Walk', 'Guided photography tour of the campus.',
         3, 'Main Gate', 0, 20, 'Activity', 'offline'),
        ('Inter-College Debate', 'Annual debate competition with guest judges.',
         4, 'Auditorium', 0, 100, 'Competition', 'offline'),
        ('Hackathon 2026', 'Build something amazing in 24 hours.',
         5, 'Computer Lab', 0, 60, 'Hackathon', 'hybrid'),
    ]
    for idx, (title, desc, club_id, loc, days_offset, cap, evt_type, evt_mode) in enumerate(demo_events):
        evt_date = base + timedelta(days=days_offset + 1)
        start_time = '10:00'
        end_time = '16:00'
        c.execute(
            'INSERT INTO events(title,description,club_id,organizer_user_id,'
            'event_date,start_time,end_time,location,event_mode,capacity,'
            'registered_count,event_type,requires_form,status,created_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (title, desc, club_id, admin_id,
             evt_date.strftime('%Y-%m-%d'), start_time, end_time,
             loc, evt_mode, cap, 0, evt_type, 0, 'upcoming', now())
        )

    # Auto-join first 3 students to Web Dev Club for demo (as active members)
    club1_id = c.execute(
        "SELECT id FROM clubs WHERE name='Web Development Club'"
    ).fetchone()[0]
    # Add founders as leaders
    club_founders = c.execute("SELECT id, founder_user_id FROM clubs WHERE founder_user_id IS NOT NULL").fetchall()
    for club_row in club_founders:
        c.execute(
            "INSERT OR IGNORE INTO club_members(club_id,user_id,role,status,joined_at) VALUES(?,?,'leader','active',?)",
            (club_row['id'], club_row['founder_user_id'], now())
        )

    for stu_id in ids[:3]:
        c.execute(
            "INSERT OR IGNORE INTO club_members(club_id,user_id,role,status,joined_at) VALUES(?,?,'member','active',?)",
            (club1_id, stu_id, now())
        )

    c.commit()
    c.close()


def expire_requests(c):
    """Expire pending locker requests past their deadline."""
    t = now()
    rows = c.execute(
        "SELECT id,request_code,locker_id,student_user_id "
        "FROM locker_requests WHERE status='pending' "
        "AND expires_at IS NOT NULL AND expires_at<?", (t,)
    ).fetchall()
    changed = False
    for r in rows:
        c.execute(
            "UPDATE locker_requests SET status='expired',reviewed_at=? "
            "WHERE id=?", (t, r['id'])
        )
        c.execute(
            "UPDATE lockers SET status='available' WHERE id=? "
            "AND status='pending'", (r['locker_id'],)
        )
        locker_event(c, r['locker_id'], None, 'request_expired',
                     'pending', 'available', r['request_code'],
                     'Request lifetime expired')
        notify(c, r['student_user_id'], 'request_expired',
               'Locker request expired',
               f"Request {r['request_code']} expired. "
               'You can request another available locker.',
               'request', r['request_code'])
        changed = True
    if changed:
        c.commit()
