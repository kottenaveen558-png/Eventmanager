# Event Manager App

A simple event management application with:
- Admin login
- Event creation, editing, deletion
- Student event registration
- SQL database storage (SQLite)
- Registration tracking and attendance overview

## Setup

1. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
python app.py
```

4. Open the browser at `http://127.0.0.1:5000`

## Admin credentials

- Username: `admin`
- Password: `admin123`

## Notes

- The app stores data in `events.db`
- Admin can manage events and view registrations
- Students can view available events and register for one
