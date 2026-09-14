PRAGMA foreign_keys=ON;

-- ══════════════════════════════════════════════════════════════
-- AUTH & USERS
-- ══════════════════════════════════════════════════════════════
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

CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  ip TEXT,
  user_agent TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS staff_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_code TEXT UNIQUE NOT NULL,
  requested_login_id TEXT,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  branch TEXT, semester TEXT,
  campus TEXT NOT NULL,
  mobile TEXT NOT NULL, email TEXT, profile_photo TEXT,
  assigned_admin_id INTEGER,
  priority INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN('pending','approved','rejected')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT, reviewed_by INTEGER, rejection_reason TEXT,
  FOREIGN KEY(assigned_admin_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS role_permissions(
  access_role TEXT NOT NULL,
  permission TEXT NOT NULL,
  PRIMARY KEY(access_role,permission)
);

-- ══════════════════════════════════════════════════════════════
-- CAMPUS HIERARCHY
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS campuses(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  name TEXT UNIQUE NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS buildings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campus_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  code TEXT NOT NULL,
  UNIQUE(campus_id,code),
  FOREIGN KEY(campus_id) REFERENCES campuses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS floors(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  floor_number INTEGER UNIQUE NOT NULL,
  name TEXT NOT NULL,
  code TEXT UNIQUE,
  building_id INTEGER
);

-- ══════════════════════════════════════════════════════════════
-- CAMPUSLOCK (Lockers)
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS locker_rooms(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  floor_id INTEGER NOT NULL,
  room_code TEXT NOT NULL,
  room_name TEXT NOT NULL,
  UNIQUE(floor_id,room_code),
  FOREIGN KEY(floor_id) REFERENCES floors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lockers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  locker_id TEXT UNIQUE NOT NULL,
  room_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'available'
    CHECK(status IN('available','pending','occupied','maintenance')),
  student_user_id INTEGER,
  assigned_at TEXT,
  qr_token TEXT UNIQUE,
  FOREIGN KEY(room_id) REFERENCES locker_rooms(id) ON DELETE CASCADE,
  FOREIGN KEY(student_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS locker_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_code TEXT UNIQUE NOT NULL,
  locker_id INTEGER NOT NULL,
  student_user_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN('pending','approved','rejected','cancelled','expired','assigned')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT, reviewed_by INTEGER, rejection_reason TEXT, expires_at TEXT,
  FOREIGN KEY(locker_id) REFERENCES lockers(id) ON DELETE CASCADE,
  FOREIGN KEY(student_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS locker_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  locker_id INTEGER NOT NULL,
  actor_user_id INTEGER,
  event_type TEXT NOT NULL,
  previous_state TEXT, new_state TEXT,
  request_code TEXT, notes TEXT, correlation_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(locker_id) REFERENCES lockers(id) ON DELETE CASCADE,
  FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS maintenance_records(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  locker_id INTEGER NOT NULL,
  reporter_id INTEGER,
  reported_at TEXT NOT NULL,
  reason TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'medium',
  status TEXT NOT NULL DEFAULT 'reported'
    CHECK(status IN('reported','acknowledged','in_repair','resolved')),
  notes TEXT,
  resolver_id INTEGER, resolved_at TEXT,
  FOREIGN KEY(locker_id) REFERENCES lockers(id) ON DELETE CASCADE,
  FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY(resolver_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ══════════════════════════════════════════════════════════════
-- CLUBS
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS clubs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  category TEXT,           -- Technical, Cultural, Sports, Creative, etc.
  department TEXT,
  logo TEXT,               -- base64 or file path
  founder_user_id INTEGER, -- the student who created it
  coordinator_user_id INTEGER,
  contact_email TEXT,
  contact_phone TEXT,
  meeting_schedule TEXT,   -- free text e.g. "Every Saturday 4pm"
  status TEXT NOT NULL DEFAULT 'pending_staff'
    CHECK(status IN('pending_staff','active','archived','rejected')),
  staff_reviewer_id INTEGER,
  staff_reviewed_at TEXT,
  staff_rejection_reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(founder_user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY(coordinator_user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY(staff_reviewer_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS club_members(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  club_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  role TEXT NOT NULL DEFAULT 'member',  -- free text: leader, co-leader, pr-leader, member, etc.
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN('pending','active','rejected')),
  joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(club_id,user_id),
  FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Club events with optional application/registration form ──
CREATE TABLE IF NOT EXISTS club_event_forms(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL UNIQUE,
  fields_json TEXT NOT NULL DEFAULT '[]', -- [{label,type,required}]
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_event_form_submissions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  answers_json TEXT NOT NULL DEFAULT '{}',
  submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(event_id, user_id),
  FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Club meetings (internal, member-facing — distinct from public Events) ──
CREATE TABLE IF NOT EXISTS club_meetings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  club_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  agenda TEXT,
  meeting_date TEXT NOT NULL,   -- YYYY-MM-DD
  start_time TEXT,
  end_time TEXT,
  location TEXT,
  meeting_mode TEXT NOT NULL DEFAULT 'offline'
    CHECK(meeting_mode IN('online','offline','hybrid')),
  online_link TEXT,
  created_by INTEGER,
  status TEXT NOT NULL DEFAULT 'scheduled'
    CHECK(status IN('scheduled','completed','cancelled')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE,
  FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS club_meeting_rsvps(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'going' CHECK(status IN('going','not_going')),
  responded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(meeting_id, user_id),
  FOREIGN KEY(meeting_id) REFERENCES club_meetings(id) ON DELETE CASCADE,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Club gallery: "Club Memories" + past-event photos ──
CREATE TABLE IF NOT EXISTS club_gallery(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  club_id INTEGER NOT NULL,
  event_id INTEGER,             -- optional: photo tied to a specific past event
  uploaded_by INTEGER,
  caption TEXT,
  image TEXT NOT NULL,          -- base64 data URL, compressed client-side
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE,
  FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE SET NULL,
  FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ══════════════════════════════════════════════════════════════
-- EVENTS
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  club_id INTEGER,          -- NULL if campus-wide / department event
  organizer_user_id INTEGER,
  event_date TEXT NOT NULL,  -- YYYY-MM-DD
  start_time TEXT,           -- HH:MM
  end_time TEXT,
  location TEXT,
  event_mode TEXT NOT NULL DEFAULT 'offline'
    CHECK(event_mode IN('online','offline','hybrid')),
  online_link TEXT,          -- for online/hybrid events
  capacity INTEGER DEFAULT 0,         -- 0 = unlimited
  registered_count INTEGER DEFAULT 0,
  event_type TEXT DEFAULT 'General',  -- Workshop, Meetup, Competition, etc.
  requires_form INTEGER NOT NULL DEFAULT 0,  -- 1 = has custom application form
  image TEXT,
  status TEXT NOT NULL DEFAULT 'upcoming'
    CHECK(status IN('draft','upcoming','ongoing','completed','cancelled')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE SET NULL,
  FOREIGN KEY(organizer_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS event_registrations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'registered'
    CHECK(status IN('registered','cancelled','attended')),
  registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(event_id,user_id),
  FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ══════════════════════════════════════════════════════════════
-- LOST & FOUND
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS lost_found_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_type TEXT NOT NULL CHECK(report_type IN('lost','found')),
  item_name TEXT NOT NULL,
  category TEXT,             -- Electronics, Documents, Clothing, etc.
  description TEXT,
  location TEXT,
  date_occurred TEXT,        -- YYYY-MM-DD
  time_occurred TEXT,
  photo TEXT,
  reporter_user_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK(status IN('open','matched','claim_pending','verified','resolved','expired','rejected')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(reporter_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lost_found_claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  claimant_user_id INTEGER NOT NULL,
  message TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN('pending','approved','rejected')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT,
  reviewed_by INTEGER,
  FOREIGN KEY(item_id) REFERENCES lost_found_items(id) ON DELETE CASCADE,
  FOREIGN KEY(claimant_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ══════════════════════════════════════════════════════════════
-- CAMPUS PROBLEM REPORTING
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS problem_reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reporter_user_id INTEGER NOT NULL,
  category TEXT NOT NULL
    CHECK(category IN('Electrical','Water','Cleanliness','Furniture',
                       'Wi-Fi','Security','Infrastructure','Other')),
  location TEXT NOT NULL,
  description TEXT NOT NULL,
  photo TEXT,
  status TEXT NOT NULL DEFAULT 'reported'
    CHECK(status IN('reported','acknowledged','assigned','in_progress','resolved','rejected')),
  assigned_to INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT,
  FOREIGN KEY(reporter_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- ══════════════════════════════════════════════════════════════
-- SYSTEM: NOTIFICATIONS & AUDIT
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  entity_type TEXT, entity_id TEXT,
  read_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_user_id INTEGER,
  action TEXT NOT NULL,
  target TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id INTEGER,
  actor_role TEXT,
  action TEXT NOT NULL,
  entity_type TEXT, entity_id TEXT,
  previous_state TEXT, new_state TEXT,
  correlation_id TEXT, request_id TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ══════════════════════════════════════════════════════════════
-- INDEXES
-- ══════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_users_student_id    ON users(student_id);
CREATE INDEX IF NOT EXISTS idx_users_role          ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_access_role   ON users(access_role);
CREATE INDEX IF NOT EXISTS idx_lockers_status       ON lockers(status);
CREATE INDEX IF NOT EXISTS idx_lockers_room         ON lockers(room_id);
CREATE INDEX IF NOT EXISTS idx_lockers_qr           ON lockers(qr_token);
CREATE INDEX IF NOT EXISTS idx_req_status           ON locker_requests(status);
CREATE INDEX IF NOT EXISTS idx_req_student          ON locker_requests(student_user_id);
CREATE INDEX IF NOT EXISTS idx_notif_user_unread    ON notifications(user_id,read_at,created_at);
CREATE INDEX IF NOT EXISTS idx_events_locker        ON locker_events(locker_id,created_at);
CREATE INDEX IF NOT EXISTS idx_audit_time           ON audit_events(created_at);
CREATE INDEX IF NOT EXISTS idx_maintenance_status   ON maintenance_records(status);

-- Campus Buddy additional indexes
CREATE INDEX IF NOT EXISTS idx_clubs_status         ON clubs(status);
CREATE INDEX IF NOT EXISTS idx_clubs_founder        ON clubs(founder_user_id);
CREATE INDEX IF NOT EXISTS idx_club_members_user    ON club_members(user_id);
CREATE INDEX IF NOT EXISTS idx_club_members_status  ON club_members(status);
CREATE INDEX IF NOT EXISTS idx_event_forms          ON club_event_forms(event_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions     ON club_event_form_submissions(event_id,user_id);
CREATE INDEX IF NOT EXISTS idx_events_date          ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_club          ON events(club_id);
CREATE INDEX IF NOT EXISTS idx_event_reg_user       ON event_registrations(user_id);
CREATE INDEX IF NOT EXISTS idx_event_reg_event      ON event_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_lf_status            ON lost_found_items(status);
CREATE INDEX IF NOT EXISTS idx_lf_reporter          ON lost_found_items(reporter_user_id);
CREATE INDEX IF NOT EXISTS idx_problems_status      ON problem_reports(status);
CREATE INDEX IF NOT EXISTS idx_problems_reporter    ON problem_reports(reporter_user_id);
