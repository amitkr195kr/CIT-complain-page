-- CIT One prototype schema. app.py creates these tables automatically.
CREATE TABLE users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'student',
 created_at TEXT NOT NULL
);
CREATE TABLE complaints (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 public_id TEXT NOT NULL UNIQUE,
 user_id INTEGER NOT NULL,
 title TEXT NOT NULL,
 description TEXT NOT NULL,
 category TEXT NOT NULL,
 location TEXT NOT NULL,
 severity TEXT NOT NULL DEFAULT 'Medium',
 status TEXT NOT NULL DEFAULT 'Submitted',
 assigned_to TEXT DEFAULT '',
 image_name TEXT DEFAULT '',
 ai_note TEXT DEFAULT '',
 admin_note TEXT DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 resolved_at TEXT DEFAULT '',
 FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE updates (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 complaint_id INTEGER NOT NULL,
 actor TEXT NOT NULL,
 status TEXT NOT NULL,
 note TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(complaint_id) REFERENCES complaints(id)
);
