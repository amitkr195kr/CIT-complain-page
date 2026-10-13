# CIT One — AI Campus Grievance & Infrastructure Transparency

A local, demonstrable Flask + SQLite prototype for a proposed student pilot at Central Institute of Technology Kokrajhar. It is **not an official CIT system** and is not connected to CIT identity services, official email, government grievance portals, or institutional finance systems.

## Features

- Student registration and login (passwords are hashed).
- Private complaint submission with optional image evidence.
- Unique reference IDs and personal complaint tracking.
- Rule-based AI-style category/severity suggestions (transparent prototype heuristic, not a trained ML model).
- Admin queue, assignment, status updates, and update history.
- Email draft generator (copy-only; it does not send email).
- Public aggregate dashboard and anonymised issue summaries.
- Private evidence images; only the complaint owner or an admin can access them.
- Responsive layout suitable for desktop and mobile.

## Requirements

- Python 3.10+ recommended
- macOS, Windows or Linux
- Internet is not required for the backend. The optional Google Fonts import in `static/style.css` falls back to system fonts if offline.

## Run on a MacBook Air M1

1. Extract `cit_one_project.zip` into a folder.
2. Open Terminal and move into the project folder, for example:

   ```bash
   cd ~/Downloads/cit_one
   ```

3. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install packages:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   python app.py
   ```

6. Open `http://127.0.0.1:5000` in your browser.

The SQLite database `cit_one.db` is created automatically the first time the app starts. Uploaded evidence is stored in `uploads/`.

## Demo accounts — local demonstration only

- Student: `student@example.com` / `Student123!`
- Administrator: `admin@example.com` / `Admin123!`

Change/remove demo accounts before sharing the application. The prototype creates these accounts only when the database has no users. To reset demo data, stop the app and delete `cit_one.db`; that deletes all local records. Do not do this if you need to retain submissions.

## Quick test plan

1. Log in as the demo student and submit a test report, e.g. “Pothole near the main gate”, location “Main gate road”.
2. Note the generated `CIT-XXXXXX` reference.
3. Open **My complaints** and confirm the report is visible to its owner.
4. Log out and open the public overview. Confirm the dashboard shows summary information, not the report's full description or student identity.
5. Log in as the demo administrator and open **Admin**.
6. Open the report, assign a responsible team, add an update note, and change its status.
7. Log back in as the student and confirm the status and history update.
8. As admin, use **Generate email draft**. Confirm it produces a copyable draft and does not send it.
9. Test that a student cannot open another student's private complaint URL or evidence image.

## Architecture

- `app.py`: Flask routes, session authentication, SQLite access, heuristic triage and admin workflow.
- `templates/`: Jinja HTML views.
- `static/style.css`: responsive interface styling.
- `schema.sql`: database schema reference.
- `uploads/`: private evidence uploads (created automatically).

### Database tables

- `users`: account name, unique email, password hash and role.
- `complaints`: private complaint record, category, location, severity suggestion, status, assigned team, image name and timestamps.
- `updates`: audit-style status history with actor, note and timestamp.

## Important prototype limitations

This is an educational MVP, not a production deployment. Before a college-wide pilot, work with the faculty supervisor and authorised institute officials to:

- obtain written approval and nominate a data owner / complaint-handling team;
- use official institutional authentication or verified student emails;
- set a strong secret key through `CIT_ONE_SECRET` and disable debug mode;
- deploy behind HTTPS on an approved host, add CSRF protection, rate limits, backups, logging and security testing;
- set retention, consent, privacy, moderation, accessibility and incident-response procedures;
- validate file uploads and malware-scan evidence; store uploads outside a public web root;
- replace the demo administrator mechanism with approved role provisioning and least privilege;
- implement real email only after authorisation, with reviewed recipient lists, audit logs and rate limits;
- have a human verify AI labels, safety flags, proposed budgets and all public resolution claims.

For local testing, Flask's development server is used. Do not expose it directly to the public internet. The rule-based classifier can miss issues and is not an emergency response service. Students must contact campus security or emergency services directly for immediate danger.

## Suggested next-stage enhancements

1. Institutional SSO / verified CIT email.
2. CSRF protection, audit events and admin MFA.
3. Department queues and response-time service levels.
4. Safe map pinning and duplicate clustering.
5. Resolution evidence and reporter confirmation.
6. Export of anonymised statistics to CSV/PDF.
7. Reviewed project proposal generator with itemised estimates, source/date for rates, and clear approval status.
8. Optional email integration using an authorised provider API; never send unattended mass email.
