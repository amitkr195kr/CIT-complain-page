import os, re, sqlite3, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'cit_one.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app = Flask(__name__)
app.secret_key = os.environ.get('CIT_ONE_SECRET', 'dev-only-change-this-secret-before-deployment')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

CATEGORIES = ['Roads & pathways', 'Electricity', 'Water & drainage', 'Hostel & sanitation', 'Classrooms & labs', 'Wi-Fi & IT', 'Safety concern', 'Other']
STATUSES = ['Submitted', 'Under review', 'Assigned', 'In progress', 'Resolved', 'Closed']

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'student',
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS complaints (
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
CREATE TABLE IF NOT EXISTS updates (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 complaint_id INTEGER NOT NULL,
 actor TEXT NOT NULL,
 status TEXT NOT NULL,
 note TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(complaint_id) REFERENCES complaints(id)
);
'''

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    # Demo accounts are created only on an empty database. Change passwords immediately.
    if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        now = datetime.now().isoformat(timespec='seconds')
        conn.execute('INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)', ('Demo Student','student@example.com',generate_password_hash('Student123!'),'student',now))
        conn.execute('INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)', ('Demo Administrator','admin@example.com',generate_password_hash('Admin123!'),'admin',now))
        conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def classify(text):
    t = text.lower()
    rules = {
      'Roads & pathways': ['road','pothole','pathway','pavement','footpath','asphalt','repaving'],
      'Electricity': ['electric','power cut','light','wire','transformer','voltage','switch'],
      'Water & drainage': ['water','drain','leak','tap','sewage','flood'],
      'Hostel & sanitation': ['hostel','mess','toilet','bathroom','garbage','sanitation','clean'],
      'Classrooms & labs': ['classroom','laboratory','lab ','projector','bench','equipment'],
      'Wi-Fi & IT': ['wifi','wi-fi','internet','network','computer','printer'],
      'Safety concern': ['fire','shock','exposed wire','unsafe','accident','emergency','collapse']
    }
    scores = {cat: sum(1 for word in words if word in t) for cat, words in rules.items()}
    category = max(scores, key=scores.get) if scores and max(scores.values()) else 'Other'
    high = any(w in t for w in ['fire','electric shock','exposed wire','collapse','live wire','emergency'])
    severity = 'High' if high else ('Medium' if any(w in t for w in ['broken','damaged','leak','pothole','not working','blocked']) else 'Low')
    note = 'Rule-based suggestion only; staff must verify category and urgency.'
    if high: note += ' Potential safety risk detected: review promptly and follow campus emergency procedures.'
    return category, severity, note

def public_code():
    return 'CIT-' + secrets.token_hex(3).upper()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_globals():
    return {'categories': CATEGORIES, 'statuses': STATUSES, 'current_user': session.get('name'), 'current_role': session.get('role')}

@app.route('/')
def index():
    conn = db()
    totals = conn.execute("SELECT COUNT(*) n FROM complaints").fetchone()['n']
    resolved = conn.execute("SELECT COUNT(*) n FROM complaints WHERE status IN ('Resolved','Closed')").fetchone()['n']
    open_count = conn.execute("SELECT COUNT(*) n FROM complaints WHERE status NOT IN ('Resolved','Closed')").fetchone()['n']
    high_count = conn.execute("SELECT COUNT(*) n FROM complaints WHERE severity='High' AND status NOT IN ('Resolved','Closed')").fetchone()['n']
    recent = conn.execute("SELECT public_id,title,category,location,severity,status,created_at,updated_at FROM complaints ORDER BY created_at DESC LIMIT 8").fetchall()
    by_cat = conn.execute('SELECT category, COUNT(*) n FROM complaints GROUP BY category ORDER BY n DESC').fetchall()
    return render_template('index.html', totals=totals, resolved=resolved, open_count=open_count, high_count=high_count, recent=recent, by_cat=by_cat)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not name or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email) or len(password) < 8:
            flash('Enter your name, a valid email, and a password of at least 8 characters.', 'error')
            return render_template('register.html')
        try:
            db().execute('INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)', (name,email,generate_password_hash(password),'student',datetime.now().isoformat(timespec='seconds')))
            db().commit()
        except sqlite3.IntegrityError:
            flash('That email is already registered.', 'error')
            return render_template('register.html')
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = db().execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear(); session['user_id'] = user['id']; session['name'] = user['name']; session['role'] = user['role']
            dest = request.args.get('next')
            return redirect(dest if dest and dest.startswith('/') else url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); flash('You have been logged out.', 'info'); return redirect(url_for('index'))

@app.route('/report', methods=['GET','POST'])
@login_required
def report():
    if request.method == 'POST':
        title = request.form.get('title','').strip()[:120]
        description = request.form.get('description','').strip()[:4000]
        location = request.form.get('location','').strip()[:200]
        category_input = request.form.get('category','Other')
        if not title or len(description) < 10 or not location:
            flash('Add a title, at least 10 characters of detail, and a location.', 'error')
            return render_template('report.html')
        suggested, severity, ai_note = classify(title + ' ' + description)
        category = category_input if category_input in CATEGORIES else suggested
        if category_input == 'AI suggestion': category = suggested
        image_name = ''
        file = request.files.get('photo')
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Photo must be PNG, JPG, JPEG or WEBP.', 'error')
                return render_template('report.html')
            image_name = secrets.token_hex(8) + '_' + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))
        now = datetime.now().isoformat(timespec='seconds')
        conn = db(); code = public_code()
        while conn.execute('SELECT 1 FROM complaints WHERE public_id=?',(code,)).fetchone(): code = public_code()
        cur = conn.execute('''INSERT INTO complaints(public_id,user_id,title,description,category,location,severity,status,image_name,ai_note,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(code,session['user_id'],title,description,category,location,severity,'Submitted',image_name,ai_note,now,now))
        conn.execute('INSERT INTO updates(complaint_id,actor,status,note,created_at) VALUES(?,?,?,?,?)',(cur.lastrowid,session['name'],'Submitted','Complaint submitted by student.',now))
        conn.commit(); flash('Complaint submitted. Your ID is ' + code, 'success')
        return redirect(url_for('my_complaints'))
    return render_template('report.html')

@app.route('/dashboard')
@login_required
def dashboard():
    rows = db().execute('SELECT * FROM complaints WHERE user_id=? ORDER BY created_at DESC',(session['user_id'],)).fetchall()
    return render_template('dashboard.html', rows=rows)

@app.route('/complaint/<public_id>')
@login_required
def complaint_detail(public_id):
    row = db().execute('SELECT c.*,u.name AS reporter FROM complaints c JOIN users u ON u.id=c.user_id WHERE c.public_id=?',(public_id,)).fetchone()
    if not row: abort(404)
    if row['user_id'] != session['user_id'] and session.get('role') != 'admin': abort(403)
    updates = db().execute('SELECT * FROM updates WHERE complaint_id=? ORDER BY created_at DESC',(row['id'],)).fetchall()
    return render_template('detail.html', row=row, updates=updates)

@app.route('/my-complaints')
@login_required
def my_complaints(): return redirect(url_for('dashboard'))

@app.route('/admin')
@admin_required
def admin():
    rows = db().execute('SELECT c.*,u.name AS reporter,u.email FROM complaints c JOIN users u ON u.id=c.user_id ORDER BY CASE c.severity WHEN "High" THEN 0 WHEN "Medium" THEN 1 ELSE 2 END, c.created_at DESC').fetchall()
    return render_template('admin.html', rows=rows)

@app.route('/admin/complaint/<public_id>', methods=['POST'])
@admin_required
def update_complaint(public_id):
    conn = db(); row = conn.execute('SELECT * FROM complaints WHERE public_id=?',(public_id,)).fetchone()
    if not row: abort(404)
    status = request.form.get('status','Submitted')
    if status not in STATUSES: abort(400)
    assigned = request.form.get('assigned_to','').strip()[:120]
    note = request.form.get('admin_note','').strip()[:1500]
    now = datetime.now().isoformat(timespec='seconds')
    resolved_at = now if status in ('Resolved','Closed') else ''
    conn.execute('UPDATE complaints SET status=?,assigned_to=?,admin_note=?,updated_at=?,resolved_at=? WHERE id=?',(status,assigned,note,now,resolved_at,row['id']))
    conn.execute('INSERT INTO updates(complaint_id,actor,status,note,created_at) VALUES(?,?,?,?,?)',(row['id'],session['name'],status,note or ('Status changed to ' + status),now))
    conn.commit(); flash('Complaint updated.', 'success')
    return redirect(url_for('complaint_detail', public_id=public_id))

@app.route('/admin/email-draft/<public_id>')
@admin_required
def email_draft(public_id):
    row = db().execute('SELECT c.*,u.name AS reporter FROM complaints c JOIN users u ON u.id=c.user_id WHERE c.public_id=?',(public_id,)).fetchone()
    if not row: abort(404)
    body = f"Respected Sir/Madam,\n\nA campus issue has been reported through the CIT One pilot.\n\nComplaint ID: {row['public_id']}\nTitle: {row['title']}\nCategory: {row['category']}\nLocation: {row['location']}\nPriority suggestion: {row['severity']} (AI-assisted; please verify)\nCurrent status: {row['status']}\n\nDescription: {row['description']}\n\nKindly review this report and advise on the appropriate action. This draft has not been sent and must be reviewed by an authorised person before use.\n\nRegards,\nCIT One Campus Pilot"
    return render_template('email_draft.html', row=row, body=body)


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    # Evidence is private: only the owner of the complaint or an administrator can access it.
    safe = os.path.basename(filename)
    row = db().execute('SELECT user_id FROM complaints WHERE image_name=?', (safe,)).fetchone()
    if not row: abort(404)
    if row['user_id'] != session['user_id'] and session.get('role') != 'admin': abort(403)
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe)

@app.errorhandler(403)
def forbidden(_e): return render_template('message.html', title='Access restricted', message='You do not have permission to view this page.'),403
@app.errorhandler(404)
def missing(_e): return render_template('message.html', title='Not found', message='The requested page or complaint was not found.'),404

if __name__ == '__main__':
    init_db()
    app.run(debug=os.environ.get('CIT_ONE_DEBUG','0') == '1', host='127.0.0.1', port=int(os.environ.get('PORT','5000')))
