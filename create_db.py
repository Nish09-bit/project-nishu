import sqlite3

conn = sqlite3.connect("freshhire.db")
cursor = conn.cursor()

# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name  TEXT,
    email      TEXT UNIQUE NOT NULL,
    username   TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL
)
""")

# JOBS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    posted_by        INTEGER,
    job_title        TEXT,
    company          TEXT,
    location         TEXT,
    description      TEXT,
    required_skills  TEXT,
    salary           TEXT,
    apply_link       TEXT
)
""")

# PROFILES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER,
    name          TEXT,
    email         TEXT,
    phone         TEXT,
    city          TEXT,
    bio           TEXT,
    college       TEXT,
    degree        TEXT,
    primary_skill TEXT,
    project_title TEXT,
    project_desc  TEXT,
    project_link  TEXT
)
""")

# APPLICATIONS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    job_id     INTEGER,
    applied_on TEXT
)
""")
# BOOKMARKS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS bookmarks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    job_id     INTEGER
)
""")

# ADMIN TABLE - is mein admin user hoga
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER
)
""")
conn.commit()
conn.close()
print("Database ready!")