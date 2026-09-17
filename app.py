
from flask import Flask, request, render_template, session, redirect, send_file
from dotenv import load_dotenv
from supabase import create_client
from cryptography.fernet import Fernet
import hashlib
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import io
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("login.html")

# --------------------------------------------------
# LOGIN
# --------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            user = response.user
            auth_session = response.session

            # Store login information
            session["user_id"] = user.id
            session["email"] = user.email
            session["access_token"] = auth_session.access_token
            session["refresh_token"] = auth_session.refresh_token

            return redirect("/profile")

        except Exception as e:

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

    return render_template("login.html")


@app.route("/profile")
def profile():

    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")

    if not access_token or not refresh_token:
        return redirect("/login")

    try:

        # Set authenticated Supabase session
        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        response = (
            supabase.table("profiles")
            .select("id, full_name, role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = response.data

        if not profile:
            return "Profile not found."

        return render_template(
            "profile.html",
               profile=profile,
            email=session.get("email")
               )

    except Exception as e:

        return f"Could not load profile: {e}"


# --------------------------------------------------
# QUESTION PAPER UPLOAD
# --------------------------------------------------

@app.route("/upload", methods=["GET", "POST"])
def upload_paper():

    # Check login
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    # Get Supabase tokens
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")

    if not access_token or not refresh_token:
        return redirect("/login")

    try:

        # Set authenticated Supabase session
        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        # Check user's role
        profile_response = (
            supabase.table("profiles")
            .select("role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = profile_response.data

        if not profile:
            return "Profile not found."

        if profile["role"] != "question_setter":
            return "Access denied. Only Question Setters can upload papers."

    except Exception as e:

        return f"Could not verify user role: {e}"

    # Show upload form
    if request.method == "GET":

        return render_template("upload.html")

    # Get uploaded file and form data
    paper = request.files.get("paper")

    title = request.form.get("title")
    exam_date = request.form.get("exam_date")
    release_at = request.form.get("release_at")

    # Validate file
    if not paper:
        return "No file selected."

    # Validate fields
    if not title or not exam_date or not release_at:
        return "All fields are required."
    # release_at comes from the form as India time (IST)
    release_local = datetime.fromisoformat(release_at)

# Tell Python that this time is IST
    release_local = release_local.replace(
    tzinfo=ZoneInfo("Asia/Kolkata")
)

# Convert IST to UTC for Supabase
    release_utc = release_local.astimezone(
    timezone.utc
    ).isoformat()

    # Only PDF allowed
    if not paper.filename.lower().endswith(".pdf"):
        return "Only PDF files are allowed."

    try:

        # ------------------------------------------
        # READ ORIGINAL PDF
        # ------------------------------------------

        original_data = paper.read()

        if not original_data:
            return "The uploaded file is empty."

        # ------------------------------------------
        # SHA-256 HASH
        # ------------------------------------------

        sha256_hash = hashlib.sha256(
            original_data
        ).hexdigest()

        # ------------------------------------------
        # GET ENCRYPTION KEY
        # ------------------------------------------

        encryption_key = os.getenv("ENCRYPTION_KEY")

        if not encryption_key:
            return "Encryption key is missing."

        # ------------------------------------------
        # ENCRYPT PDF
        # ------------------------------------------

        cipher = Fernet(
            encryption_key.encode()
        )

        encrypted_data = cipher.encrypt(
            original_data
        )

        # ------------------------------------------
        # CREATE UNIQUE FILE NAME
        # ------------------------------------------

        file_name = f"{uuid.uuid4()}.enc"

        storage_path = f"papers/{file_name}"

        # ------------------------------------------
        # UPLOAD ENCRYPTED FILE
        # ------------------------------------------

        supabase.storage.from_(
            "question-papers"
        ).upload(
            storage_path,
            encrypted_data,
            {
                "content-type":
                "application/octet-stream"
            }
        )

        # ------------------------------------------
        # SAVE DATABASE RECORD
        # ------------------------------------------

        supabase.table(
            "question_papers"
        ).insert({

            "title": title,

            "exam_date": exam_date,

            "release_at": release_utc,

            "storage_path": storage_path,

            "sha256_hash": sha256_hash,

            "status": "pending",

            "uploaded_by": user_id

        }).execute()

        return render_template("upload_success.html")

    except Exception as e:

        return f"Upload failed: {e}"


# --------------------------------------------------
# ADMINISTRATOR DASHBOARD
# --------------------------------------------------

@app.route("/admin")
def admin_dashboard():

    user_id = session.get("user_id")

    # Check login
    if not user_id:
        return redirect("/login")

    # Get tokens
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")

    if not access_token or not refresh_token:
        return redirect("/login")

    try:

        # Set authenticated Supabase session
        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        # ------------------------------------------
        # CHECK ADMIN ROLE
        # ------------------------------------------

        profile_response = (
            supabase.table("profiles")
            .select("role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = profile_response.data

        if not profile:
            return "Profile not found."

        if profile["role"] != "administrator":

            return """
                <h2>Access Denied</h2>
                <p>Only administrators can access this page.</p>
                <br>
                <a href="/">Go Home</a>
            """

        # ------------------------------------------
        # GET PENDING QUESTION PAPERS
        # ------------------------------------------

        papers_response = (
            supabase.table("question_papers")
            .select(
                "id, title, exam_date, release_at, "
                "status, uploaded_by"
            )
            .eq("status", "pending")
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        papers = papers_response.data

        # ------------------------------------------
        # SHOW ADMIN DASHBOARD
        # ------------------------------------------

        return render_template(
            "admin.html",
            papers=papers
        )

    except Exception as e:

        return f"Could not verify administrator: {e}"
# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    try:
        # Sign out from Supabase
        supabase.auth.sign_out()
    except Exception:
        pass

    # Clear Flask session
    session.clear()

    # Go back to login page
    return redirect("/")

# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

@app.route("/admin/approve/<paper_id>")
def approve_paper(paper_id):

    if "user_id" not in session:
        return redirect("/login")

    try:
        access_token = session.get("access_token")
        refresh_token = session.get("refresh_token")

        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        # Approve paper using secure database function
        supabase.rpc(
            "approve_question_paper",
            {"paper_id": paper_id}
        ).execute()

        return redirect("/admin")

    except Exception as e:
        return f"Approval failed: {e}"


@app.route("/admin/reject/<paper_id>")
def reject_paper(paper_id):

    if "user_id" not in session:
        return redirect("/login")

    try:
        access_token = session.get("access_token")
        refresh_token = session.get("refresh_token")

        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        # Reject paper using secure database function
        supabase.rpc(
            "reject_question_paper",
            {"paper_id": paper_id}
        ).execute()

        return redirect("/admin")

    except Exception as e:
        return f"Rejection failed: {e}"
@app.route("/view-paper/<paper_id>")
def view_paper(paper_id):

    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")

    if not access_token or not refresh_token:
        return redirect("/login")

    try:

        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        # Check Centre role
        profile_response = (
            supabase.table("profiles")
            .select("role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = profile_response.data

        if not profile or profile["role"] != "exam_centre":
            return "Access denied."

        # Get paper
        paper_response = (
            supabase.table("question_papers")
            .select(
                "id, title, release_at, storage_path, status"
            )
            .eq("id", paper_id)
            .single()
            .execute()
        )

        paper = paper_response.data

        if not paper:
            return "Question paper not found."

        # Must be approved
        if paper["status"] != "approved":
            return "This question paper has not been approved."

        # Check release time
        release_time = datetime.fromisoformat(
            paper["release_at"].replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)

        if now < release_time:
            return """
                <h2>Question Paper Locked</h2>
                <p>This question paper has not been released yet.</p>
            """

        # Download encrypted file
        
        storage = supabase.storage.from_("question-papers")

        encrypted_data = storage.download(
        paper["storage_path"]
        )

        print("Downloading:", paper["storage_path"])
        print("Downloaded successfully")
        # Decrypt
        encryption_key = os.getenv("ENCRYPTION_KEY")

        if not encryption_key:
            return "Encryption key is missing."

        cipher = Fernet(
            encryption_key.encode()
        )

        decrypted_data = cipher.decrypt(
            encrypted_data
        )

        # Open PDF in browser
        return send_file(
            io.BytesIO(decrypted_data),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"{paper['title']}.pdf"
        )

    except Exception as e:

        return f"Could not open question paper: {e}"
@app.route("/centre")
def centre_dashboard():
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")

    if not access_token or not refresh_token:
        return redirect("/login")

    try:
        supabase.auth.set_session(
            access_token,
            refresh_token
        )

        profile_response = (
            supabase.table("profiles")
            .select("full_name, role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = profile_response.data

        if not profile:
            return "Profile not found."

        if profile["role"] != "exam_centre":
            return "Access denied. Only Exam Centres can access this page."

        papers_response = (
            supabase.table("question_papers")
            .select(
                "id, title, exam_date, release_at, status"
            )
            .eq("status", "approved")
            .order("created_at", desc=True)
            .execute()
        )

        papers = papers_response.data or []

        # Calculate release status
        now = datetime.now(timezone.utc)

        for paper in papers:
            release_time = datetime.fromisoformat(
                paper["release_at"].replace("Z", "+00:00")
            )

            if now >= release_time:
                paper["release_status"] = "released"
            else:
                paper["release_status"] = "scheduled"

        return render_template(
            "centre.html",
            profile=profile,
            papers=papers
        )

    except Exception as e:
        return f"Could not load Exam Centre dashboard: {e}"

if __name__ == "__main__":

    app.run(debug=True)

