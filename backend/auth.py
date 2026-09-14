from backend.utils import DatabaseIntegrityError, DatabaseOperationalError
"""Campus Buddy — Authentication endpoints (login, signup, logout, me)."""
import secrets, re, sqlite3, hashlib, hmac, smtplib
from backend.config import CAMPUSES, PERMISSIONS, PRIMARY_ADMIN_LOGIN, USE_POSTGRES
from backend.utils import (
    conn, hpw, vpw, now, later, audit, notify,
    get_permissions, make_cookie, public_user,
)
from datetime import datetime, timezone, timedelta
from backend.mailer import send_otp_email


def handle_login(handler):
    """POST /api/auth/login"""
    d = handler.body()
    portal = d.get('role')
    ident = str(d.get('studentId', '')).strip()
    pw = str(d.get('password', ''))
    ip = handler.client_address[0]

    if portal not in ('student', 'admin') or not ident or not pw:
        return handler.send_json(
            {'error': 'Role, ID and password are required.'}, 400
        )

    c = conn()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(
        timespec='seconds'
    )
    fails = c.execute(
        "SELECT COUNT(*) n FROM audit_events "
        "WHERE action='login_failed' AND metadata_json LIKE ? "
        "AND created_at>?",
        (f'%\\"ip\\":\\"{ip}\\"%', cutoff),
    ).fetchone()['n']
    if fails >= 20:
        c.close()
        return handler.send_json(
            {'error': 'Too many login attempts. Try again shortly.'}, 429
        )

    # Login identifiers are intentionally flexible: students may use their
    # college/student ID, generated login ID, or verified email address.
    # Email matching is case-insensitive, and IDs are matched case-insensitively
    # as well so that browser autofill/capitalization cannot cause false
    # 'Invalid credentials' errors. Do not use a single-row lookup here: an
    # email can be shared by multiple legacy/demo records, so the password and
    # portal role must be used to select the correct account.
    candidates = c.execute(
        'SELECT * FROM users WHERE active=1 AND '
        "(LOWER(COALESCE(student_id,''))=LOWER(?) OR "
        " LOWER(username)=LOWER(?) OR LOWER(COALESCE(email,''))=LOWER(?))", 
        (ident, ident, ident),
    ).fetchall()

    r = None
    for candidate in candidates:
        role_ok = (
            (portal == 'student' and candidate['account_type'] == 'student')
            or (portal == 'admin' and candidate['role'] == 'admin')
        )
        if role_ok and vpw(pw, candidate['password_hash']):
            r = candidate
            break

    if r is None:
        audit(c, None, None, 'login_failed', 'auth', ident, meta={'ip': ip})
        c.commit()
        c.close()
        return handler.send_json({'error': 'Invalid credentials.'}, 401)

    audit(
        c, r['id'], r['access_role'], 'login_success', 'user',
        str(r['id']), meta={'ip': ip}
    )
    c.commit()
    c.close()

    sid = handler.create_session(r['id'])
    handler.send_json(
        {'user': public_user(r, True)},
        headers={'Set-Cookie': make_cookie(sid)},
    )


OTP_TTL_MINUTES=5
OTP_RESEND_SECONDS=45
OTP_MAX_ATTEMPTS=5

def _otp_hash(email, otp):
    return hmac.new(hashlib.sha256(email.lower().encode()).digest(), otp.encode(), hashlib.sha256).hexdigest()

def _iso_in(minutes=0, seconds=0):
    return (datetime.now(timezone.utc)+timedelta(minutes=minutes,seconds=seconds)).isoformat(timespec='seconds')

def _valid_email(email):
    return bool(re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",email))

def _student_id_taken(c,sid):
    return bool(sid and c.execute('SELECT 1 FROM users WHERE student_id=? OR username=?',(sid,sid)).fetchone())

def _email_taken(c,email):
    return bool(c.execute('SELECT 1 FROM users WHERE lower(email)=lower(?)',(email,)).fetchone())

def _cleanup_pending(c):
    c.execute("DELETE FROM pending_email_verifications WHERE datetime(otp_expires_at) < datetime('now','-1 day')")

def _validate_student_payload(p):
    if not p['name'] or not p['branch'] or not p['mobile'] or not p['password']: return 'Name, branch, mobile and password are required.'
    if not p['semester']: return 'Semester is required for student accounts.'
    if p['campus']!='Dwarka Campus': return 'Only Dwarka Campus is selectable right now.'
    if not re.fullmatch(r'\d{10}',p['mobile']): return 'Mobile number must contain 10 digits.'
    if len(p['password'])<8: return 'Password must be at least 8 characters.'
    if p['student_id'] and not re.fullmatch(r'[A-Za-z0-9_-]{3,30}',p['student_id']): return 'Student/college ID must use letters, numbers, _ or - only.'
    if not p['email'] or not _valid_email(p['email']): return 'A valid email address is required for verification.'
    if p['photo'] and (not isinstance(p['photo'],str) or not p['photo'].startswith('data:image/') or len(p['photo'])>3_500_000): return 'Profile photo is too large.'
    return None

def handle_signup(handler):
    """POST /api/auth/signup — admin/staff workflow remains unchanged; students use email OTP."""
    d=handler.body(); role=str(d.get('role','student')).strip().lower()

    if role=='admin':
        name=str(d.get('name','')).strip(); branch=str(d.get('branch','')).strip(); semester=str(d.get('semester','')).strip()
        campus=str(d.get('campus','Dwarka Campus')).strip(); sid=str(d.get('studentId','')).strip() or None
        mobile=str(d.get('mobile','')).strip(); pw=str(d.get('password','')); photo=d.get('profilePhoto') or None
        email=str(d.get('email','')).strip() or None
        if not name or not branch or not mobile or not pw: return handler.send_json({'error':'Name, branch/department, mobile and password are required.'},400)
        if campus!='Dwarka Campus': return handler.send_json({'error':'Only Dwarka Campus is selectable right now.'},400)
        if not re.fullmatch(r'\d{10}',mobile): return handler.send_json({'error':'Mobile number must contain 10 digits.'},400)
        if len(pw)<8: return handler.send_json({'error':'Password must be at least 8 characters.'},400)
        if sid and not re.fullmatch(r'[A-Za-z0-9_-]{3,30}',sid): return handler.send_json({'error':'Student/college ID must use letters, numbers, _ or - only.'},400)
        if photo and (not isinstance(photo,str) or not re.match(r'^data:image/(?:jpeg|png|webp);base64,', photo, re.I) is not None or len(photo)>3_500_000): return handler.send_json({'error':'Profile photo is too large.'},400)
        c=conn()
        try:
            if _student_id_taken(c,sid): return handler.send_json({'error':'That ID is already registered.'},409)
            admin=c.execute("SELECT id,full_name FROM users WHERE is_primary_admin=1 AND role='admin' AND active=1 LIMIT 1").fetchone() or c.execute("SELECT id,full_name FROM users WHERE role='admin' AND active=1 ORDER BY id LIMIT 1").fetchone()
            if not admin: return handler.send_json({'error':'No approving administrator is configured.'},503)
            code='SREQ'+secrets.token_hex(4).upper()
            c.execute('INSERT INTO staff_requests(request_code,requested_login_id,password_hash,full_name,branch,semester,campus,mobile,email,profile_photo,assigned_admin_id,priority,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (code,sid,hpw(pw),name,branch,semester or None,campus,mobile,email,photo,admin['id'],0,'pending'))
            notify(c,admin['id'],'staff_application','New staff access request',f'{name} submitted a staff access request for review.','staff_request',code)
            audit(c,None,None,'staff_signup_submitted','staff_request',code,request_id=code,meta={'assigned_admin_id':admin['id']})
            c.commit()
            return handler.send_json({'ok':True,'pending':True,'requestCode':code,'assignedAdmin':admin['full_name']},202)
        finally: c.close()

    p={
        'name':str(d.get('name','')).strip(),'branch':str(d.get('branch','')).strip(),
        'semester':str(d.get('semester','')).strip(),'campus':str(d.get('campus','Dwarka Campus')).strip(),
        'student_id':str(d.get('studentId','')).strip() or None,'mobile':str(d.get('mobile','')).strip(),
        'password':str(d.get('password','')),'photo':d.get('profilePhoto') or None,
        'email':str(d.get('email','')).strip().lower()
    }
    err=_validate_student_payload(p)
    if err: return handler.send_json({'error':err},400)
    c=conn()
    try:
        _cleanup_pending(c)
        if _student_id_taken(c,p['student_id']): return handler.send_json({'error':'That ID is already registered.'},409)
        if _email_taken(c,p['email']): return handler.send_json({'error':'That email is already registered. Please sign in instead.'},409)
        existing=c.execute('SELECT * FROM pending_email_verifications WHERE lower(email)=lower(?)',(p['email'],)).fetchone()
        if existing:
            elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(existing['last_sent_at'])).total_seconds()
            if elapsed<OTP_RESEND_SECONDS: return handler.send_json({'error':f'Please wait {int(OTP_RESEND_SECONDS-elapsed)} seconds before requesting another code.','retryAfter':int(OTP_RESEND_SECONDS-elapsed)},429)
        otp=f'{secrets.randbelow(1_000_000):06d}'; vid=secrets.token_urlsafe(24); expires=_iso_in(minutes=OTP_TTL_MINUTES); sent=_iso_in(); digest=_otp_hash(p['email'],otp)
        if existing:
            c.execute('UPDATE pending_email_verifications SET verification_id=?,name=?,branch=?,semester=?,campus=?,student_id=?,mobile=?,password_hash=?,profile_photo=?,otp_hash=?,otp_expires_at=?,otp_attempts=0,last_sent_at=? WHERE email=?',
                      (vid,p['name'],p['branch'],p['semester'],p['campus'],p['student_id'],p['mobile'],hpw(p['password']),p['photo'],digest,expires,sent,p['email']))
        else:
            c.execute('INSERT INTO pending_email_verifications(email,verification_id,role,name,branch,semester,campus,student_id,mobile,password_hash,profile_photo,otp_hash,otp_expires_at,otp_attempts,last_sent_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (p['email'],vid,'student',p['name'],p['branch'],p['semester'],p['campus'],p['student_id'],p['mobile'],hpw(p['password']),p['photo'],digest,expires,0,sent))
        try:
            send_otp_email(p['email'],otp)
        except (RuntimeError,smtplib.SMTPException):
            c.rollback()
            raise
        c.commit()
        return handler.send_json({'ok':True,'pendingVerification':True,'email':p['email'],'verificationId':vid,'expiresIn':300,'retryAfter':OTP_RESEND_SECONDS},202)
    except RuntimeError as e:
        return handler.send_json({'error':str(e)},503)
    except smtplib.SMTPException:
        return handler.send_json({'error':'We could not send the verification email. Please try again shortly.'},503)
    finally: c.close()

def handle_resend_otp(handler):
    d=handler.body(); email=str(d.get('email','')).strip().lower()
    if not _valid_email(email): return handler.send_json({'error':'A valid email address is required.'},400)
    c=conn()
    try:
        p=c.execute('SELECT * FROM pending_email_verifications WHERE lower(email)=lower(?)',(email,)).fetchone()
        if not p: return handler.send_json({'error':'No pending verification was found for this email.'},404)
        elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(p['last_sent_at'])).total_seconds()
        if elapsed<OTP_RESEND_SECONDS: return handler.send_json({'error':f'Please wait {int(OTP_RESEND_SECONDS-elapsed)} seconds before resending.','retryAfter':int(OTP_RESEND_SECONDS-elapsed)},429)
        otp=f'{secrets.randbelow(1_000_000):06d}'; vid=secrets.token_urlsafe(24); expires=_iso_in(minutes=OTP_TTL_MINUTES); sent=_iso_in()
        c.execute('UPDATE pending_email_verifications SET verification_id=?,otp_hash=?,otp_expires_at=?,otp_attempts=0,last_sent_at=? WHERE email=?',(vid,_otp_hash(email,otp),expires,sent,email))
        try: send_otp_email(email,otp)
        except (RuntimeError,smtplib.SMTPException): c.rollback(); raise
        c.commit()
        return handler.send_json({'ok':True,'verificationId':vid,'expiresIn':300,'retryAfter':OTP_RESEND_SECONDS})
    except RuntimeError as e: return handler.send_json({'error':str(e)},503)
    except smtplib.SMTPException: return handler.send_json({'error':'We could not send the verification email. Please try again shortly.'},503)
    finally: c.close()

def handle_verify_otp(handler):
    d=handler.body(); email=str(d.get('email','')).strip().lower(); otp=str(d.get('otp','')).strip(); vid=str(d.get('verificationId','')).strip()
    if not _valid_email(email) or not re.fullmatch(r'\d{6}',otp) or not vid: return handler.send_json({'error':'Verification email, session and 6-digit code are required.'},400)
    c=conn()
    try:
        p=c.execute('SELECT * FROM pending_email_verifications WHERE lower(email)=lower(?)',(email,)).fetchone()
        if not p or not hmac.compare_digest(p['verification_id'],vid): return handler.send_json({'error':'That verification session is no longer valid. Please request a new code.'},410)
        if datetime.fromisoformat(p['otp_expires_at'])<=datetime.now(timezone.utc):
            c.execute('DELETE FROM pending_email_verifications WHERE email=?',(email,)); c.commit()
            return handler.send_json({'error':'That code has expired. Please request a new code.'},410)
        if p['otp_attempts']>=OTP_MAX_ATTEMPTS:
            c.execute('DELETE FROM pending_email_verifications WHERE email=?',(email,)); c.commit()
            return handler.send_json({'error':'Too many incorrect attempts. Please request a new code.'},429)
        if not hmac.compare_digest(_otp_hash(email,otp),p['otp_hash']):
            c.execute('UPDATE pending_email_verifications SET otp_attempts=otp_attempts+1 WHERE email=?',(email,)); c.commit()
            return handler.send_json({'error':'Incorrect verification code.','attemptsRemaining':OTP_MAX_ATTEMPTS-p['otp_attempts']-1},401)
        if _student_id_taken(c,p['student_id']): c.execute('DELETE FROM pending_email_verifications WHERE email=?',(email,)); c.commit(); return handler.send_json({'error':'That student/college ID was registered while you were verifying.'},409)
        if _email_taken(c,email): c.execute('DELETE FROM pending_email_verifications WHERE email=?',(email,)); c.commit(); return handler.send_json({'error':'That email is already registered. Please sign in instead.'},409)
        login_id=p['student_id'] or ('STU'+secrets.token_hex(3).upper())
        c.execute('INSERT INTO users(student_id,username,password_hash,full_name,role,branch,semester,campus,mobile,email,profile_photo,account_type,access_role,joined_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (p['student_id'],login_id,p['password_hash'],p['name'],'student',p['branch'],p['semester'],p['campus'],p['mobile'],p['email'],p['profile_photo'],'student','student',now()))
        # SQLite and PostgreSQL expose inserted IDs differently. Query by the
        # unique login ID to make verification/account creation portable.
        uid_row=c.execute('SELECT id FROM users WHERE username=?',(login_id,)).fetchone()
        if not uid_row:
            raise DatabaseIntegrityError('The account could not be created. Please try again.')
        uid=uid_row['id']
        audit(c,uid,'student','account_created','user',str(uid),meta={'email_verified':True})
        audit(c,uid,'student','email_verified','user',str(uid))
        c.execute('DELETE FROM pending_email_verifications WHERE email=?',(email,)); c.commit()
        row=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        return handler.send_json({'ok':True,'loginId':login_id,'user':public_user(row,True)},201)
    except DatabaseIntegrityError:
        c.rollback(); return handler.send_json({'error':'That login/college ID is already registered. Try another.'},409)
    finally: c.close()


def handle_logout(handler):
    """POST /api/auth/logout"""
    r = handler.auth()
    if not r:
        return
    c = conn()
    audit(c, r['id'], r['access_role'], 'logout', 'user', str(r['id']))
    c.execute('DELETE FROM sessions WHERE id=?', (handler.sid,))
    c.commit()
    c.close()
    handler.send_json(
        {'ok': True}, headers={'Set-Cookie': make_cookie('', True)}
    )


def handle_me(handler):
    """GET /api/me"""
    r = handler.auth()
    if r:
        handler.send_json({'user': public_user(r, True)})
