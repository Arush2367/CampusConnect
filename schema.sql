PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id TEXT UNIQUE,
 username TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL,
 full_name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN('student','admin')),
 course TEXT, branch TEXT, year TEXT, semester TEXT, campus TEXT,
 mobile TEXT, email TEXT, profile_photo TEXT,
 account_type TEXT NOT NULL DEFAULT 'student',
 access_role TEXT NOT NULL DEFAULT 'student',
 is_primary_admin INTEGER NOT NULL DEFAULT 0,
 active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 joined_at TEXT
);
CREATE TABLE IF NOT EXISTS floors(id INTEGER PRIMARY KEY AUTOINCREMENT,floor_number INTEGER UNIQUE NOT NULL,name TEXT NOT NULL,code TEXT UNIQUE,building_id INTEGER);
CREATE TABLE IF NOT EXISTS locker_rooms(id INTEGER PRIMARY KEY AUTOINCREMENT,floor_id INTEGER NOT NULL,room_code TEXT NOT NULL,room_name TEXT NOT NULL,UNIQUE(floor_id,room_code),FOREIGN KEY(floor_id) REFERENCES floors(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS lockers(id INTEGER PRIMARY KEY AUTOINCREMENT,locker_id TEXT UNIQUE NOT NULL,room_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'available' CHECK(status IN('available','pending','occupied','maintenance')),student_user_id INTEGER,assigned_at TEXT,qr_token TEXT UNIQUE,FOREIGN KEY(room_id) REFERENCES locker_rooms(id) ON DELETE CASCADE,FOREIGN KEY(student_user_id) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS locker_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,request_code TEXT UNIQUE NOT NULL,locker_id INTEGER NOT NULL,student_user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN('pending','approved','rejected','cancelled','expired','assigned')),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,reviewed_at TEXT,reviewed_by INTEGER,rejection_reason TEXT,expires_at TEXT,FOREIGN KEY(locker_id) REFERENCES lockers(id) ON DELETE CASCADE,FOREIGN KEY(student_user_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,actor_user_id INTEGER,action TEXT NOT NULL,target TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS staff_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,request_code TEXT UNIQUE NOT NULL,requested_login_id TEXT,password_hash TEXT NOT NULL,full_name TEXT NOT NULL,branch TEXT,semester TEXT,campus TEXT NOT NULL,mobile TEXT NOT NULL,email TEXT,profile_photo TEXT,assigned_admin_id INTEGER,priority INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN('pending','approved','rejected')),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,reviewed_at TEXT,reviewed_by INTEGER,rejection_reason TEXT,FOREIGN KEY(assigned_admin_id) REFERENCES users(id) ON DELETE SET NULL,FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS role_permissions(access_role TEXT NOT NULL,permission TEXT NOT NULL,PRIMARY KEY(access_role,permission));
CREATE TABLE IF NOT EXISTS pending_email_verifications(
  email TEXT PRIMARY KEY,
  verification_id TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'student' CHECK(role='student'),
  name TEXT NOT NULL,
  branch TEXT NOT NULL,
  semester TEXT NOT NULL,
  campus TEXT NOT NULL,
  student_id TEXT,
  mobile TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  profile_photo TEXT,
  otp_hash TEXT NOT NULL,
  otp_expires_at TEXT NOT NULL,
  otp_attempts INTEGER NOT NULL DEFAULT 0,
  last_sent_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pending_verification_expiry
  ON pending_email_verifications(otp_expires_at);

CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,last_seen_at TEXT NOT NULL,ip TEXT,user_agent TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,type TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,entity_type TEXT,entity_id TEXT,read_at TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS locker_events(id INTEGER PRIMARY KEY AUTOINCREMENT,locker_id INTEGER NOT NULL,actor_user_id INTEGER,event_type TEXT NOT NULL,previous_state TEXT,new_state TEXT,request_code TEXT,notes TEXT,correlation_id TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(locker_id) REFERENCES lockers(id) ON DELETE CASCADE,FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS maintenance_records(id INTEGER PRIMARY KEY AUTOINCREMENT,locker_id INTEGER NOT NULL,reporter_id INTEGER,reported_at TEXT NOT NULL,reason TEXT NOT NULL,severity TEXT NOT NULL DEFAULT 'medium',status TEXT NOT NULL DEFAULT 'reported' CHECK(status IN('reported','acknowledged','in_repair','resolved')),notes TEXT,resolver_id INTEGER,resolved_at TEXT,FOREIGN KEY(locker_id) REFERENCES lockers(id) ON DELETE CASCADE,FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE SET NULL,FOREIGN KEY(resolver_id) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,actor_id INTEGER,actor_role TEXT,action TEXT NOT NULL,entity_type TEXT,entity_id TEXT,previous_state TEXT,new_state TEXT,correlation_id TEXT,request_id TEXT,metadata_json TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS campuses(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,name TEXT UNIQUE NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS buildings(id INTEGER PRIMARY KEY AUTOINCREMENT,campus_id INTEGER NOT NULL,name TEXT NOT NULL,code TEXT NOT NULL,UNIQUE(campus_id,code),FOREIGN KEY(campus_id) REFERENCES campuses(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_users_student_id ON users(student_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_access_role ON users(access_role);
CREATE INDEX IF NOT EXISTS idx_lockers_status ON lockers(status);
CREATE INDEX IF NOT EXISTS idx_lockers_room ON lockers(room_id);
CREATE INDEX IF NOT EXISTS idx_lockers_qr ON lockers(qr_token);
CREATE INDEX IF NOT EXISTS idx_req_status ON locker_requests(status);
CREATE INDEX IF NOT EXISTS idx_req_student ON locker_requests(student_user_id);
CREATE INDEX IF NOT EXISTS idx_notif_user_unread ON notifications(user_id,read_at,created_at);
CREATE INDEX IF NOT EXISTS idx_events_locker ON locker_events(locker_id,created_at);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(created_at);
CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_records(status);
