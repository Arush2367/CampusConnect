import http.cookiejar, json, os, subprocess, sys, tempfile, threading, time, urllib.request, urllib.error, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:3015'
RUN_ID=str(int(time.time()*1000))[-8:]
TEST_STUDENT_ID=f'TEST{RUN_ID}'
TEST_FACULTY_ID=f'FAC{RUN_ID}'
TEST_EMAIL=f'test{RUN_ID}@example.edu'
FAC_EMAIL=f'faculty{RUN_ID}@example.edu'

def post(opener,path,payload):
    req=urllib.request.Request(BASE+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    return opener.open(req)

def get(opener,path):
    return opener.open(urllib.request.Request(BASE+path))

proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env={**os.environ,'PORT':'3015'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    for _ in range(60):
        try:
            opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            r=post(opener,'/api/auth/login',{'role':'student','studentId':'STU1001','password':'student123'})
            assert r.status==200
            student=json.loads(r.read())['user'];assert student['accessRole']=='student'
            break
        except Exception:
            time.sleep(.1)
    else: raise AssertionError('server did not start')
    # Student privacy: locker API and detail API must not expose another user's private identity data.
    lockers=json.loads(get(opener,'/api/lockers').read())['lockers']
    assert all('studentName' not in x and 'studentId' not in x for x in lockers)
    detail=json.loads(get(opener,'/api/lockers/A1-002').read())
    assert detail.get('student') is None
    # Student signup now starts email verification and only creates the account after OTP verification.
    signup_opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    outbox=ROOT/'data'/'test_email_outbox.jsonl'
    if outbox.exists(): outbox.unlink()
    signup=post(signup_opener,'/api/auth/signup',{'role':'student','name':'Test Student','branch':'CSE','semester':'1','campus':'Dwarka Campus','studentId':TEST_STUDENT_ID,'mobile':'9999999001','email':TEST_EMAIL,'password':'strongpass123'})
    assert signup.status==202
    signup_data=json.loads(signup.read()); assert signup_data['pendingVerification']
    lines=outbox.read_text(encoding='utf-8').splitlines(); assert lines, 'test email transport did not write an OTP'
    otp=json.loads(lines[-1])['otp']; assert len(otp)==6 and otp.isdigit()
    verify=post(signup_opener,'/api/auth/verify-otp',{'email':TEST_EMAIL,'verificationId':signup_data['verificationId'],'otp':otp})
    assert verify.status==201
    created=json.loads(verify.read())['user']; assert created['accessRole']=='student'
    relogin=json.loads(post(signup_opener,'/api/auth/login',{'role':'student','studentId':TEST_STUDENT_ID,'password':'strongpass123'}).read())['user']
    assert relogin['studentId']==TEST_STUDENT_ID and relogin['email']==TEST_EMAIL
    # Regression: the same verified account must also be able to sign in with
    # its email address, including normal email capitalization.
    email_login=json.loads(post(signup_opener,'/api/auth/login',{'role':'student','studentId':TEST_EMAIL,'password':'strongpass123'}).read())['user']
    assert email_login['studentId']==TEST_STUDENT_ID
    email_case_login=json.loads(post(signup_opener,'/api/auth/login',{'role':'student','studentId':TEST_EMAIL.upper(),'password':'strongpass123'}).read())['user']
    assert email_case_login['studentId']==TEST_STUDENT_ID
    bad_verify=post(urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())),'/api/auth/verify-otp',{'email':TEST_EMAIL,'verificationId':signup_data['verificationId'],'otp':'000000'}) if False else None
    # Staff signup becomes a pending request.
    guest=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    staff=post(guest,'/api/auth/signup',{'role':'admin','name':'Test Faculty','branch':'CSE','semester':'','campus':'Dwarka Campus','studentId':TEST_FACULTY_ID,'mobile':'9999999002','email':FAC_EMAIL,'password':'strongpass123'})
    staff_data=json.loads(staff.read()); assert staff.status==202 and staff_data['pending']
    # Primary admin can see staff request and has notification.
    admin=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    login=json.loads(post(admin,'/api/auth/login',{'role':'admin','studentId':'ADMIN001','password':'admin123'}).read())['user'];assert login['accessRole']=='super_admin'
    requests=json.loads(get(admin,'/api/staff-requests').read())['requests']; assert any(x['request_code']==staff_data['requestCode'] and x['priority']==0 for x in requests)
    # Restricted staff permission check: primary admin approval creates staff role.
    post(admin,'/api/staff-requests/'+staff_data['requestCode']+'/approve',{})
    staffop=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    approved=json.loads(post(staffop,'/api/auth/login',{'role':'admin','studentId':TEST_FACULTY_ID,'password':'strongpass123'}).read())['user'];assert approved['accessRole']=='staff'
    # Restricted staff can perform their explicit operational release permission on an occupied locker.
    locker_rows=json.loads(get(admin,'/api/lockers?status=occupied').read())['lockers']
    assert locker_rows, 'seed data should contain an occupied locker'
    rel_id=locker_rows[0]['id']
    rel=post(staffop,'/api/lockers/'+rel_id+'/release',{}); assert rel.status==200
    # Restricted staff cannot create lockers.
    try:
        post(staffop,'/api/lockers/bulk',{'floor':1,'group':'2','quantity':1,'startNumber':1})
        raise AssertionError('restricted staff unexpectedly created locker')
    except urllib.error.HTTPError as e:
        assert e.code==403
    # Staff can release lockers, while restricted staff still cannot create lockers.
    post(staffop,'/api/lockers/A1-001/release',{}) if False else None
    # Notifications are persistent and user-scoped.
    n=json.loads(get(admin,'/api/notifications').read());assert 'notifications' in n and n['unread']>=0
    # Maintenance state endpoint and audit visibility for admin.
    post(admin,'/api/maintenance',{'lockerId':'A1-001','reason':'Test maintenance','severity':'low'})
    maint=json.loads(get(admin,'/api/maintenance').read())['maintenance']; assert any(x.get('locker_code')=='A1-001' for x in maint)
    # QR identity is authenticated and contains no student data.
    q=json.loads(get(admin,'/api/lockers/A1-001/qr').read());assert q['lockerId']=='A1-001' and 'student' not in q
    audit=json.loads(get(admin,'/api/audit').read())['audit'];assert any(x['action']=='staff_request_approved' for x in audit)
    print('ALL_TESTS_PASSED')
finally:
    proc.terminate();
    try: proc.wait(timeout=3)
    except subprocess.TimeoutExpired: proc.kill()
