from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import bcrypt
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "freshhire123"

def get_db():
    conn = sqlite3.connect("freshhire.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.context_processor
def inject_globals():
    notif_count = 0
    if "user_id" in session:
        try:
            conn = get_db()
            notif_count = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
                (session["user_id"],)
            ).fetchone()[0]
            conn.close()
        except:
            pass
    return {"notif_count": notif_count}

@app.route("/")
def home():
    conn = get_db()
    keyword  = request.args.get("keyword", "")
    location = request.args.get("location", "")
    query  = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if keyword.strip():
        query += " AND (job_title LIKE ? OR required_skills LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if location.strip():
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    query += " ORDER BY id DESC"
    jobs = conn.execute(query, params).fetchall()
    try:
        reviews = conn.execute("""
            SELECT reviews.*, users.first_name FROM reviews
            JOIN users ON reviews.reviewer_id = users.id
            ORDER BY reviews.id DESC LIMIT 6
        """).fetchall()
    except:
        reviews = []
    conn.close()
    return render_template("index.html", jobs=jobs, reviews=reviews)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name   = request.form.get("first_name", "").strip()
        last_name    = request.form.get("last_name", "").strip()
        email        = request.form.get("email", "").strip()
        phone        = request.form.get("phone", "").strip()
        username     = request.form.get("username", "").strip()
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm_password", "")
        role         = request.form.get("role", "fresher")
        login_method = request.form.get("login_method", "email")

        if not first_name or not username or not password:
            flash("Please fill all required fields!", "error")
            return render_template("signup.html")
        if login_method == "phone" and not phone:
            flash("Please enter your mobile number!", "error")
            return render_template("signup.html")
        if login_method == "email" and not email:
            flash("Please enter your email address!", "error")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match!", "error")
            return render_template("signup.html")

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn = get_db()
        # Add phone column if it doesn't exist yet
        try:
            conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            conn.commit()
        except:
            pass
        try:
            conn.execute(
                "INSERT INTO users (first_name, last_name, email, phone, username, password, role) VALUES (?,?,?,?,?,?,?)",
                (first_name, last_name, email or None, phone or None, username, hashed, role)
            )
            conn.commit()
            if email:
                user_id = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]
            else:
                user_id = conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()[0]
            session["user_id"] = user_id
            session["name"]    = first_name
            session["role"]    = role
            flash(f"Welcome to FreshHire, {first_name}! 🎉", "success")
            return redirect(url_for("home"))
        except:
            flash("Email, phone or username already exists!", "error")
        finally:
            conn.close()
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_method = request.form.get("login_method", "email")
        identifier   = request.form.get("identifier", "").strip()
        password     = request.form.get("password", "")
        conn = get_db()
        # Add phone column if it doesn't exist yet
        try:
            conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            conn.commit()
        except:
            pass
        if login_method == "phone":
            user = conn.execute("SELECT * FROM users WHERE phone=?", (identifier,)).fetchone()
        else:
            user = conn.execute("SELECT * FROM users WHERE email=?", (identifier,)).fetchone()
        conn.close()
        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            session["user_id"] = user["id"]
            session["name"]    = user["first_name"]
            session["role"]    = user["role"] if user["role"] else "fresher"
            flash(f"Welcome, {user['first_name']}! 👋", "success")
            return redirect(url_for("home"))
        else:
            flash("Wrong credentials or account not found!", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("home"))

@app.route("/jobs")
def jobs():
    q        = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    skill    = request.args.get("skill", "").strip()
    conn     = get_db()

    sql    = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if q:
        sql += " AND (job_title LIKE ? OR company LIKE ? OR description LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    if skill:
        sql += " AND required_skills LIKE ?"
        params.append(f"%{skill}%")
    if location:
        sql += " AND location LIKE ?"
        params.append(f"%{location}%")
    sql += " ORDER BY id DESC"
    jobs = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("jobs.html", jobs=jobs, query=q, location=location, skill=skill)

@app.route("/job/<int:job_id>")
def job_detail(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not job:
        flash("Job not found!", "error")
        return redirect(url_for("jobs"))
    return render_template("job_detail.html", job=job)

@app.route("/post-job", methods=["GET", "POST"])
def post_job():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    if session.get("role") != "hirer":
        flash("Only hirers can post jobs!", "error")
        return redirect(url_for("home"))
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO jobs (posted_by, job_title, company, location, description, required_skills, salary, apply_link) VALUES (?,?,?,?,?,?,?,?)",
            (session["user_id"],
             request.form.get("job_title"),
             request.form.get("company"),
             request.form.get("location"),
             request.form.get("description"),
             request.form.get("required_skills"),
             request.form.get("salary"),
             request.form.get("apply_link"))
        )
        conn.commit()
        conn.close()
        flash("Job posted successfully! ✅", "success")
        return redirect(url_for("jobs"))
    return render_template("post_job.html")

@app.route("/delete-job/<int:job_id>")
def delete_job(job_id):
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM jobs WHERE id=? AND posted_by=?", (job_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Job deleted successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply_job(job_id):
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    job     = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    already = conn.execute(
        "SELECT * FROM applications WHERE user_id=? AND job_id=?",
        (session["user_id"], job_id)
    ).fetchone()
    if request.method == "POST":
        if already:
            flash("You already applied for this job!", "error")
        else:
            cover_letter = request.form.get("cover_letter", "")
            conn.execute(
                "INSERT INTO applications (user_id, job_id, cover_letter, applied_on, status) VALUES (?,?,?,?,?)",
                (session["user_id"], job_id, cover_letter,
                 datetime.now().strftime("%Y-%m-%d %H:%M"), "pending")
            )
            if job:
                conn.execute(
                    "INSERT INTO notifications (user_id, message, created_at) VALUES (?,?,?)",
                    (job["posted_by"],
                     f"Someone applied for your job: {job['job_title']}!",
                     datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
            conn.commit()
            flash("Applied successfully! 🎉", "success")
        conn.close()
        return redirect(url_for("jobs"))
    conn.close()
    return render_template("apply_job.html", job=job, already=already)

@app.route("/my-applications")
def my_applications():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    applications = conn.execute("""
        SELECT jobs.job_title, jobs.company, jobs.location,
               applications.applied_on, applications.cover_letter, applications.status
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        WHERE applications.user_id=?
        ORDER BY applications.id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("my_applications.html", applications=applications)

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    if request.method == "POST":
        photo_filename = existing["photo"] if existing and existing["photo"] else None
        if "photo" in request.files:
            photo = request.files["photo"]
            if photo and photo.filename != "":
                ext = photo.filename.rsplit(".", 1)[-1].lower()
                if ext in ["jpg", "jpeg", "png"]:
                    os.makedirs("static/photos", exist_ok=True)
                    photo_filename = f"photo_{session['user_id']}.{ext}"
                    photo.save(f"static/photos/{photo_filename}")
        data = (
            request.form.get("name"), request.form.get("email"),
            request.form.get("phone"), request.form.get("city"),
            request.form.get("bio"), request.form.get("college"),
            request.form.get("degree"), request.form.get("primary_skill"),
            request.form.get("project_title"), request.form.get("project_desc"),
            request.form.get("project_link"), photo_filename,
        )
        if existing:
            conn.execute("""UPDATE profiles SET name=?, email=?, phone=?, city=?, bio=?,
                college=?, degree=?, primary_skill=?, project_title=?, project_desc=?,
                project_link=?, photo=? WHERE user_id=?""", data + (session["user_id"],))
        else:
            conn.execute("""INSERT INTO profiles
                (name, email, phone, city, bio, college, degree, primary_skill,
                 project_title, project_desc, project_link, photo, user_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", data + (session["user_id"],))
        conn.commit()
        conn.close()
        flash("Profile saved successfully! 🎉", "success")
        return redirect(url_for("view_my_profile"))
    conn.close()
    return render_template("profile.html", profile=existing)

@app.route("/profiles")
def profiles():
    conn = get_db()
    all_profiles = conn.execute("SELECT * FROM profiles").fetchall()
    conn.close()
    return render_template("profiles.html", profiles=all_profiles)

@app.route("/my-profile")
def view_my_profile():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    my_profile = conn.execute(
        "SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    conn.close()
    if not my_profile:
        flash("Create your profile first!", "error")
        return redirect(url_for("profile"))
    return render_template("my_profile.html", profile=my_profile)

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    if request.method == "POST":
        conn.execute("""UPDATE profiles SET name=?, email=?, phone=?, city=?, bio=?,
            college=?, degree=?, primary_skill=?, project_title=?, project_desc=?, project_link=?
            WHERE user_id=?""", (
            request.form.get("name"), request.form.get("email"),
            request.form.get("phone"), request.form.get("city"),
            request.form.get("bio"), request.form.get("college"),
            request.form.get("degree"), request.form.get("primary_skill"),
            request.form.get("project_title"), request.form.get("project_desc"),
            request.form.get("project_link"), session["user_id"]
        ))
        conn.commit()
        conn.close()
        flash("Profile updated! ✅", "success")
        return redirect(url_for("view_my_profile"))
    conn.close()
    return render_template("edit_profile.html", profile=existing)

@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    if "user_id" not in session:
        return redirect(url_for("login"))
    file = request.files.get("resume")
    if file and file.filename.endswith(".pdf"):
        os.makedirs("static/resumes", exist_ok=True)
        filename = f"resume_{session['user_id']}.pdf"
        file.save(f"static/resumes/{filename}")
        conn = get_db()
        conn.execute("UPDATE profiles SET resume=? WHERE user_id=?", (filename, session["user_id"]))
        conn.commit()
        conn.close()
        flash("Resume uploaded! ✅", "success")
    else:
        flash("Only PDF files allowed!", "error")
    return redirect(url_for("dashboard"))

@app.route("/upload-photo", methods=["POST"])
def upload_photo():
    if "user_id" not in session:
        return redirect(url_for("login"))
    file = request.files.get("photo")
    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext in ["jpg", "jpeg", "png"]:
            os.makedirs("static/photos", exist_ok=True)
            filename = f"photo_{session['user_id']}.{ext}"
            file.save(f"static/photos/{filename}")
            conn = get_db()
            conn.execute("UPDATE profiles SET photo=? WHERE user_id=?", (filename, session["user_id"]))
            conn.commit()
            conn.close()
            flash("Photo uploaded! ✅", "success")
        else:
            flash("Only JPG/PNG allowed!", "error")
    return redirect(url_for("dashboard"))

@app.route("/bookmark/<int:job_id>")
def bookmark(job_id):
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    already = conn.execute(
        "SELECT * FROM bookmarks WHERE user_id=? AND job_id=?",
        (session["user_id"], job_id)
    ).fetchone()
    if already:
        conn.execute("DELETE FROM bookmarks WHERE user_id=? AND job_id=?",
                     (session["user_id"], job_id))
        flash("Bookmark removed!", "success")
    else:
        conn.execute("INSERT INTO bookmarks (user_id, job_id) VALUES (?,?)",
                     (session["user_id"], job_id))
        flash("Job bookmarked! ✅", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("jobs"))

@app.route("/bookmarks")
def my_bookmarks():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    bookmarks = conn.execute("""
        SELECT jobs.* FROM bookmarks
        JOIN jobs ON bookmarks.job_id = jobs.id
        WHERE bookmarks.user_id = ?
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("bookmarks.html", jobs=bookmarks)

@app.route("/notifications")
def notifications():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    conn.commit()
    conn.close()
    return render_template("notifications.html", notifs=notifs)

@app.route("/chat/<int:receiver_id>", methods=["GET", "POST"])
def chat(receiver_id):
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            conn.execute(
                "INSERT INTO chats (sender_id, receiver_id, message, sent_at) VALUES (?,?,?,?)",
                (session["user_id"], receiver_id, message,
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.execute(
                "INSERT INTO notifications (user_id, message, created_at, sender_id) VALUES (?,?,?,?)",
                (receiver_id,
                 f"💬 {session['name']} sent you a message!",
                 datetime.now().strftime("%Y-%m-%d %H:%M"),
                 session["user_id"])
            )
            conn.commit()
    messages = conn.execute("""
        SELECT chats.*, users.first_name FROM chats
        JOIN users ON chats.sender_id = users.id
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY id ASC
    """, (session["user_id"], receiver_id, receiver_id, session["user_id"])).fetchall()
    receiver = conn.execute("SELECT * FROM users WHERE id=?", (receiver_id,)).fetchone()
    conn.close()
    return render_template("chat.html", messages=messages, receiver=receiver, receiver_id=receiver_id)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    total_jobs     = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    total_profiles = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    total_users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    my_jobs        = conn.execute(
        "SELECT * FROM jobs WHERE posted_by=? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    my_profile     = conn.execute(
        "SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    is_admin       = conn.execute(
        "SELECT * FROM admins WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    conn.close()
    return render_template("dashboard.html",
                           total_jobs=total_jobs, total_profiles=total_profiles,
                           total_users=total_users, my_jobs=my_jobs,
                           my_profile=my_profile, is_admin=is_admin)

@app.route("/admin")
def admin():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    is_admin = conn.execute(
        "SELECT * FROM admins WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    if not is_admin:
        conn.close()
        flash("Access denied!", "error")
        return redirect(url_for("home"))
    users    = conn.execute("SELECT * FROM users").fetchall()
    jobs     = conn.execute("SELECT * FROM jobs").fetchall()
    profiles = conn.execute("SELECT * FROM profiles").fetchall()
    conn.close()
    return render_template("admin.html", users=users, jobs=jobs, profiles=profiles)

@app.route("/admin/delete-user/<int:user_id>")
def admin_delete_user(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    is_admin = conn.execute("SELECT * FROM admins WHERE user_id=?", (session["user_id"],)).fetchone()
    if not is_admin:
        conn.close()
        return redirect(url_for("home"))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted!", "success")
    return redirect(url_for("admin"))

@app.route("/admin/delete-job/<int:job_id>")
def admin_delete_job(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    is_admin = conn.execute("SELECT * FROM admins WHERE user_id=?", (session["user_id"],)).fetchone()
    if not is_admin:
        conn.close()
        return redirect(url_for("home"))
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    flash("Job deleted!", "success")
    return redirect(url_for("admin"))

@app.route("/update-status/<int:app_id>/<status>")
def update_status(app_id, status):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    conn.commit()
    conn.close()
    flash("Status updated!", "success")
    return redirect(url_for("admin"))

@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    if request.method == "POST":
        if "user_id" not in session:
            flash("Please login first!", "error")
            return redirect(url_for("login"))
        conn = get_db()
        conn.execute(
            "INSERT INTO reviews (reviewer_id, message, rating, created_at) VALUES (?,?,?,?)",
            (session["user_id"], request.form.get("message"),
             request.form.get("rating"), datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
        conn.close()
        flash("Review submitted! ✅", "success")
    return redirect(url_for("home"))

@app.route("/recommendations")
def recommendations():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    my_profile = conn.execute(
        "SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    if not my_profile or not my_profile["primary_skill"]:
        conn.close()
        flash("Create your profile first!", "error")
        return redirect(url_for("profile"))
    skills = my_profile["primary_skill"].split(",")
    recommended = []
    seen = set()
    for skill in skills:
        jobs = conn.execute(
            "SELECT * FROM jobs WHERE required_skills LIKE ?", (f"%{skill.strip()}%",)
        ).fetchall()
        for job in jobs:
            if job["id"] not in seen:
                seen.add(job["id"])
                recommended.append(job)
    conn.close()
    return render_template("recommendations.html", jobs=recommended, skill=my_profile["primary_skill"])

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Message sent successfully! ✅", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

# ================= COMPANY PROFILE ================= #
@app.route("/company/create", methods=["GET", "POST"])
def create_company():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    if session.get("role") != "hirer":
        flash("Only hirers can create company profiles!", "error")
        return redirect(url_for("home"))
    conn = get_db()
    existing = conn.execute("SELECT * FROM companies WHERE user_id=?", (session["user_id"],)).fetchone()
    if request.method == "POST":
        if existing:
            conn.execute("""UPDATE companies SET company_name=?, industry=?, location=?,
                website=?, description=?, founded=?, size=? WHERE user_id=?""",
                (request.form.get("company_name"), request.form.get("industry"),
                 request.form.get("location"), request.form.get("website"),
                 request.form.get("description"), request.form.get("founded"),
                 request.form.get("size"), session["user_id"]))
        else:
            conn.execute("""INSERT INTO companies (user_id, company_name, industry, location,
                website, description, founded, size) VALUES (?,?,?,?,?,?,?,?)""",
                (session["user_id"], request.form.get("company_name"),
                 request.form.get("industry"), request.form.get("location"),
                 request.form.get("website"), request.form.get("description"),
                 request.form.get("founded"), request.form.get("size")))
        conn.commit()
        conn.close()
        flash("Company profile saved! ✅", "success")
        return redirect(url_for("companies"))
    conn.close()
    return render_template("create_company.html", company=existing)

@app.route("/companies")
def companies():
    conn = get_db()
    all_companies = conn.execute("""
        SELECT companies.*, users.first_name FROM companies
        JOIN users ON companies.user_id = users.id
    """).fetchall()
    conn.close()
    return render_template("companies.html", companies=all_companies)

# ================= RESUME BUILDER ================= #
@app.route("/resume-builder", methods=["GET", "POST"])
def resume_builder():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    existing = conn.execute("SELECT * FROM resume_builder WHERE user_id=?", (session["user_id"],)).fetchone()
    profile = conn.execute("SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)).fetchone()
    if request.method == "POST":
        if existing:
            conn.execute("""UPDATE resume_builder SET objective=?, experience=?, education=?,
                skills=?, certifications=?, languages=? WHERE user_id=?""",
                (request.form.get("objective"), request.form.get("experience"),
                 request.form.get("education"), request.form.get("skills"),
                 request.form.get("certifications"), request.form.get("languages"),
                 session["user_id"]))
        else:
            conn.execute("""INSERT INTO resume_builder (user_id, objective, experience,
                education, skills, certifications, languages, created_at) VALUES (?,?,?,?,?,?,?,?)""",
                (session["user_id"], request.form.get("objective"),
                 request.form.get("experience"), request.form.get("education"),
                 request.form.get("skills"), request.form.get("certifications"),
                 request.form.get("languages"), datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        flash("Resume saved! ✅", "success")
        return redirect(url_for("view_resume"))
    conn.close()
    return render_template("resume_builder.html", resume=existing, profile=profile)

@app.route("/view-resume")
def view_resume():
    if "user_id" not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
    conn = get_db()
    resume = conn.execute("SELECT * FROM resume_builder WHERE user_id=?", (session["user_id"],)).fetchone()
    profile = conn.execute("SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)).fetchone()
    conn.close()
    if not resume:
        flash("Please build your resume first!", "error")
        return redirect(url_for("resume_builder"))
    return render_template("view_resume.html", resume=resume, profile=profile)

if __name__ == "__main__":
    app.run(debug=True)