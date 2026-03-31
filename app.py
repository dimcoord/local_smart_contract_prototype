from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
import os
import uuid
import threading
import queue
import sqlite3
import json
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import ollama
from fpdf import FPDF  # type: ignore[import-not-found]

from utils import extract_text_from_pdf
from analyzer import analyze_contract, add_risk_score, MODEL
from generator import generate_contract

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-this")

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
GENERATED_CONTRACTS_FOLDER = "generated_contracts"
DATABASE = "users.db"
ALLOWED_EXTENSIONS = {"pdf"}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(GENERATED_CONTRACTS_FOLDER):
    os.makedirs(GENERATED_CONTRACTS_FOLDER)

# In-memory job store
jobs = {}

# Job queue for sequential processing (FIFO)
job_queue = queue.Queue()
job_worker_running = False

# Contract generation queue for sequential processing (FIFO)
contract_queue = queue.Queue()
contract_worker_running = False

SUPPORTED_LANGUAGES = {"en", "id"}

TRANSLATIONS = {
    "en": {
        "app_name": "LexivaAI",
        "dashboard": "Dashboard",
        "analyze_contract": "Analyze Contract",
        "generate_contract": "Generate Contract",
        "logout": "Logout",
        "login": "Login",
        "register": "Register",
        "signed_in_as": "Signed in as",
        "welcome_back": "Welcome back",
        "total_analysis_jobs": "Total Analysis Jobs",
        "completed_jobs": "Completed Jobs",
        "processing_jobs": "Processing Jobs",
        "start_new_analysis": "Start New Analysis",
        "generate_new_contract": "Generate New Contract",
        "your_analysis_jobs": "Your Analysis Jobs",
        "job_id": "Job ID",
            "your_analysis_generation_jobs": "Your Analysis & Generation Jobs",
        "status": "Status",
        "started": "Started",
        "completed": "Completed",
        "action": "Action",
        "view_result": "View Result",
        "still_processing": "Still processing...",
        "no_jobs": "No analysis jobs yet. Start one from Analyze Contract.",
        "upload_contract_pdf": "Upload Contract (PDF)",
        "select_pdf_contract": "Select your PDF contract",
        "start_analysis": "Start Analysis",
        "analyze_help": "After upload, you will be redirected to the processing screen automatically.",
        "describe_contract": "Describe the contract you want to generate",
        "generate": "Generate",
        "generated_contract": "Generated Contract",
        "contract_title": "Contract Title",
        "contract_title_hint": "Example: Service Agreement, NDA, Software License, etc.",
        "generating_hint": "Example: Create a one-year software development agreement with monthly payments and IP ownership clauses.",
        "processing_title": "Processing...",
        "analyzing_contract": "Analyzing Contract...",
        "ai_evaluating": "AI is evaluating clauses and risks.",
        "home": "Home",
        "risk_score": "Risk Score",
        "contract_details": "Contract Details",
        "type": "Type",
        "parties": "Parties",
        "effective_date": "Effective Date",
        "governing_law": "Governing Law",
        "risk_level": "Risk Level",
        "risk_analysis": "Risk Analysis",
        "termination_clause_summary": "Termination Clause Summary",
        "payment_terms": "Payment Terms",
        "analyze_another": "Analyze Another",
        "prototype": "LexivaAI Prototype",
        "logged_in_as": "Logged in as",
        "do_not_have_account": "Do not have an account?",
        "already_have_account": "Already have an account?",
        "username": "Username",
        "password": "Password",
        "switch_language": "Bahasa Indonesia",
        "registration_successful": "Registration successful.",
        "login_successful": "Login successful.",
        "invalid_credentials": "Invalid username or password.",
        "logged_out": "Logged out.",
        "username_password_required": "Username and password are required.",
        "username_exists": "Username already exists.",
        "choose_pdf": "Please choose a PDF file.",
        "pdf_only": "Only PDF files are allowed.",
        "prompt_required": "Prompt is required.",
        "download_pdf": "Download PDF",
        "contract_saved_pdf": "Contract saved as PDF.",
        "recent_generated_contracts": "Recent Generated Contracts",
        "created_at": "Created At",
        "no_generated_contracts": "No generated contracts yet.",
        "contract_language": "Contract Language",
        "english": "English",
        "bahasa_indonesia": "Bahasa Indonesia",
        "your_generated_contracts": "Your Generated Contracts",
        "in_queue": "In Queue",
        "in_job": "In Job",
        "finished": "Finished",
        "no_generated_contracts_dashboard": "No generated contracts yet.",
    },
    "id": {
        "app_name": "LexivaAI",
        "dashboard": "Dasbor",
        "analyze_contract": "Analisis Kontrak",
        "generate_contract": "Buat Kontrak",
        "logout": "Keluar",
        "login": "Masuk",
        "register": "Daftar",
        "signed_in_as": "Masuk sebagai",
        "welcome_back": "Selamat datang kembali",
        "total_analysis_jobs": "Total Pekerjaan Analisis",
        "completed_jobs": "Pekerjaan Selesai",
        "processing_jobs": "Pekerjaan Diproses",
        "start_new_analysis": "Mulai Analisis Baru",
        "generate_new_contract": "Buat Kontrak Baru",
        "your_analysis_jobs": "Pekerjaan Analisis Anda",
        "job_id": "ID Pekerjaan",
        "your_analysis_generation_jobs": "Pekerjaan Analisis & Generate Anda",
        "status": "Status",
        "started": "Dimulai",
        "completed": "Selesai",
        "action": "Aksi",
        "view_result": "Lihat Hasil",
        "still_processing": "Masih diproses...",
        "no_jobs": "Belum ada pekerjaan analisis. Mulai dari menu Analisis Kontrak.",
        "upload_contract_pdf": "Unggah Kontrak (PDF)",
        "select_pdf_contract": "Pilih file kontrak PDF",
        "start_analysis": "Mulai Analisis",
        "analyze_help": "Setelah unggah, Anda akan diarahkan ke halaman pemrosesan secara otomatis.",
        "describe_contract": "Jelaskan kontrak yang ingin Anda buat",
        "generate": "Buat",
        "generated_contract": "Kontrak Hasil Generate",
        "contract_title": "Judul Kontrak",
        "contract_title_hint": "Contoh: Perjanjian Layanan, NDA, Lisensi Perangkat Lunak, dll.",
        "generating_hint": "Contoh: Buat kontrak pengembangan software satu tahun dengan pembayaran bulanan dan klausul kepemilikan HKI.",
        "processing_title": "Memproses...",
        "analyzing_contract": "Menganalisis Kontrak...",
        "ai_evaluating": "AI sedang mengevaluasi klausul dan risiko.",
        "home": "Beranda",
        "risk_score": "Skor Risiko",
        "contract_details": "Detail Kontrak",
        "type": "Jenis",
        "parties": "Para Pihak",
        "effective_date": "Tanggal Berlaku",
        "governing_law": "Hukum yang Berlaku",
        "risk_level": "Tingkat Risiko",
        "risk_analysis": "Analisis Risiko",
        "termination_clause_summary": "Ringkasan Klausul Pengakhiran",
        "payment_terms": "Ketentuan Pembayaran",
        "analyze_another": "Analisis Lagi",
        "prototype": "Prototipe LexivaAI",
        "logged_in_as": "Masuk sebagai",
        "do_not_have_account": "Belum punya akun?",
        "already_have_account": "Sudah punya akun?",
        "username": "Nama pengguna",
        "password": "Kata sandi",
        "switch_language": "English",
        "registration_successful": "Registrasi berhasil.",
        "login_successful": "Login berhasil.",
        "invalid_credentials": "Nama pengguna atau kata sandi tidak valid.",
        "logged_out": "Berhasil keluar.",
        "username_password_required": "Nama pengguna dan kata sandi wajib diisi.",
        "username_exists": "Nama pengguna sudah ada.",
        "choose_pdf": "Silakan pilih file PDF.",
        "pdf_only": "Hanya file PDF yang diizinkan.",
        "prompt_required": "Prompt wajib diisi.",
        "download_pdf": "Unduh PDF",
        "contract_saved_pdf": "Kontrak disimpan sebagai PDF.",
        "recent_generated_contracts": "Kontrak Terbaru yang Dibuat",
        "created_at": "Dibuat Pada",
        "no_generated_contracts": "Belum ada kontrak yang dibuat.",
        "contract_language": "Bahasa Kontrak",
        "english": "Bahasa Inggris",
        "bahasa_indonesia": "Bahasa Indonesia",
        "your_generated_contracts": "Kontrak Yang Dibuat",
        "in_queue": "Antri",
        "in_job": "Sedang Dibuat",
        "finished": "Selesai",
        "no_generated_contracts_dashboard": "Belum ada kontrak yang dibuat.",
    },
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generated_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            prompt TEXT NOT NULL,
            content TEXT,
            pdf_filename TEXT,
            status TEXT DEFAULT 'pending',
            language TEXT DEFAULT 'en',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def job_worker():
    """Background worker thread that processes jobs one at a time from the queue."""
    while True:
        try:
            job_id, file_path = job_queue.get()
            if job_id is None:  # Sentinel value to stop worker
                break
            
            # Process the job
            text = extract_text_from_pdf(file_path)
            result = analyze_contract(text)
            
            if "error" not in result:
                result = add_risk_score(result)
            
            # Update job status
            job = jobs.get(job_id, {})
            job["status"] = "completed"
            job["result"] = result
            job["completed_at"] = datetime.utcnow().isoformat(timespec="seconds")
            jobs[job_id] = job
            
        except Exception as e:
            # Handle errors gracefully
            if job_id in jobs:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = str(e)
                jobs[job_id]["completed_at"] = datetime.utcnow().isoformat(timespec="seconds")
        finally:
            job_queue.task_done()


def contract_worker():
    """Background worker thread that generates contracts one at a time from the queue."""
    while True:
        try:
            contract_id = contract_queue.get()
            if contract_id is None:  # Sentinel value to stop worker
                break
            
            conn = get_db_connection()
            contract = conn.execute(
                "SELECT id, user_id, title, prompt, language FROM generated_contracts WHERE id = ?",
                (contract_id,)
            ).fetchone()
            conn.close()
            
            if not contract:
                continue
            
            try:
                # Update status to "in job"
                conn = get_db_connection()
                conn.execute(
                    "UPDATE generated_contracts SET status = ? WHERE id = ?",
                    ("in job", contract_id)
                )
                conn.commit()
                conn.close()
                
                # Generate the contract
                result = generate_contract(contract["prompt"], language=contract["language"])
                
                # Create PDF
                created_at = datetime.utcnow().isoformat(timespec="seconds")
                pdf_filename = f"contract_{contract['user_id']}_{uuid.uuid4().hex}.pdf"
                pdf_path = os.path.join(GENERATED_CONTRACTS_FOLDER, pdf_filename)
                create_contract_pdf(result, pdf_path, title=contract["title"])
                
                # Update database with completed status
                conn = get_db_connection()
                conn.execute(
                    """
                    UPDATE generated_contracts
                    SET status = ?, content = ?, pdf_filename = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    ("finished", result, pdf_filename, created_at, contract_id)
                )
                conn.commit()
                conn.close()
                
            except Exception as e:
                # Mark contract as failed
                conn = get_db_connection()
                conn.execute(
                    "UPDATE generated_contracts SET status = ? WHERE id = ?",
                    ("error", contract_id)
                )
                conn.commit()
                conn.close()
                
        finally:
            contract_queue.task_done()


def start_job_worker():
    """Start the background job worker thread."""
    global job_worker_running
    if not job_worker_running:
        job_worker_running = True
        worker_thread = threading.Thread(target=job_worker, daemon=True)
        worker_thread.start()


def start_contract_worker():
    """Start the background contract worker thread."""
    global contract_worker_running
    if not contract_worker_running:
        contract_worker_running = True
        worker_thread = threading.Thread(target=contract_worker, daemon=True)
        worker_thread.start()


def sanitize_text_for_pdf(text):
    """Remove emoji and other characters not supported by courier font."""
    import re
    import unicodedata
    
    # First, replace smart quotes and dashes with ASCII equivalents
    text = re.sub(r'["""]', '"', text)  # curly double quotes -> straight
    text = re.sub(r"[''']", "'", text)  # curly/single quotes -> straight
    text = text.replace('–', '-')      # en dash -> hyphen
    text = text.replace('—', '--')     # em dash -> double hyphen
    
    # Common emoji and symbol replacements
    replacements = {
        "✅": "[OK]",
        "❌": "[FAIL]",
        "⚠️": "[WARNING]",
        "✓": "[OK]",
        "✗": "[X]",
        "●": "*",
        "○": "o",
        "→": "->",
        "←": "<-",
        "•": "*",
    }
    
    result = text
    for emoji, replacement in replacements.items():
        result = result.replace(emoji, replacement)
    
    # Keep only ASCII printable characters and basic whitespace
    # This is safe for courier font
    cleaned = []
    for char in result:
        code = ord(char)
        # Keep ASCII printable (32-126) and whitespace (9, 10, 13)
        if (32 <= code <= 126) or code in (9, 10, 13):
            cleaned.append(char)
    
    return ''.join(cleaned)


def create_contract_pdf(contract_text, output_path, title=None):
    # Sanitize text to remove emoji and unsupported Unicode before rendering
    contract_text = sanitize_text_for_pdf(contract_text)
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("courier", "B", 16)
    title_text = title if title else "Generated Contract"
    pdf.cell(0, 10, title_text, new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("courier", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(
        0,
        8,
        f"Created: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    for raw_line in contract_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
            continue

        is_heading = (
            line.isupper()
            or (line[0].isdigit() and "." in line[:4])
            or line.endswith(":")
        )

        if is_heading:
            pdf.set_font("courier", "B", 12)
            pdf.multi_cell(0, 7, line, wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        else:
            pdf.set_font("courier", "", 11)
            pdf.multi_cell(0, 6, line, wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_language():
    lang = session.get("lang", "en")
    if lang not in SUPPORTED_LANGUAGES:
        return "en"
    return lang


def tr(key):
    lang = get_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(
        key, TRANSLATIONS["en"].get(key, key)
    )


def translate_result_with_ollama(result_payload, target_lang):
    if target_lang == "en":
        return result_payload

    prompt = (
        "Translate this legal analysis JSON to Indonesian. "
        "Return STRICT JSON only with the exact same keys and translated values.\n\n"
        f"JSON:\n{json.dumps(result_payload, ensure_ascii=False)}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a precise legal translator. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.1, "top_p": 0.9},
    )

    translated_text = response["message"]["content"].strip()
    if translated_text.startswith("```"):
        translated_text = translated_text.split("```")[1].strip()

    parsed = json.loads(translated_text)
    if isinstance(parsed, dict):
        return parsed
    return result_payload


def localize_result(job, lang):
    if lang == "en":
        return job.get("result", {})

    localized = job.setdefault("localized_results", {})
    if lang in localized:
        return localized[lang]

    base_result = job.get("result", {})
    translated = dict(base_result)

    risk_level_map = {"Low": "Rendah", "Medium": "Sedang", "High": "Tinggi"}
    if translated.get("risk_level") in risk_level_map:
        translated["risk_level"] = risk_level_map[translated["risk_level"]]

    try:
        translated = translate_result_with_ollama(base_result, lang)
        if translated.get("risk_level") in risk_level_map:
            translated["risk_level"] = risk_level_map[translated["risk_level"]]
    except Exception:
        # Fall back to the partially translated payload if model translation fails.
        pass

    localized[lang] = translated
    return translated


@app.context_processor
def inject_i18n():
    current_lang = get_language()
    return {
        "t": tr,
        "current_lang": current_lang,
        "toggle_lang": "id" if current_lang == "en" else "en",
    }


@app.route("/set-language/<lang>")
def set_language(lang):
    if lang in SUPPORTED_LANGUAGES:
        session["lang"] = lang
    next_url = request.args.get("next") or request.referrer or url_for("home")
    return redirect(next_url)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash(tr("username_password_required"), "error")
            return redirect(url_for("register"))

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash(tr("username_exists"), "error")
            conn.close()
            return redirect(url_for("register"))

        user = conn.execute(
            "SELECT id, username FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash(tr("registration_successful"), "success")
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(tr("login_successful"), "success")
            return redirect(url_for("home"))

        flash(tr("invalid_credentials"), "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash(tr("logged_out"), "success")
    return redirect(url_for("login"))

@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    analysis_jobs = []
    for job_id, job in jobs.items():
        if job.get("user_id") != session["user_id"]:
            continue

        analysis_jobs.append(
            {
                "job_id": job_id,
                "type": "analysis",
                "status": job.get("status", "processing"),
                "created_at": job.get("created_at"),
                "completed_at": job.get("completed_at"),
            }
        )

    analysis_jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    
    # Fetch generated contracts from database
    conn = get_db_connection()
    generated_contracts = conn.execute(
        """
        SELECT id, title, status, created_at, completed_at
        FROM generated_contracts
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    
    generation_jobs = []
    for contract in generated_contracts:
        generation_jobs.append(
            {
                "contract_id": contract["id"],
                "title": contract["title"] or "Untitled Contract",
                "status": contract["status"],
                "created_at": contract["created_at"],
                "completed_at": contract["completed_at"],
            }
        )
    generation_jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)

    completed_jobs = sum(1 for job in analysis_jobs if job.get("status") == "completed")
    processing_jobs = sum(1 for job in analysis_jobs if job.get("status") == "processing")
    
    return render_template(
        "dashboard.html",
        total_jobs=len(analysis_jobs),
        completed_jobs=completed_jobs,
        processing_jobs=processing_jobs,
        analysis_jobs=analysis_jobs,
        generation_jobs=generation_jobs,
    )


# -------------------------------
# Upload and create async job
# -------------------------------
@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    if request.method == "POST":
        file = request.files["contract"]
        if not file or file.filename == "":
            flash(tr("choose_pdf"), "error")
            return redirect(url_for("analyze"))

        if not allowed_file(file.filename):
            flash(tr("pdf_only"), "error")
            return redirect(url_for("analyze"))

        safe_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4()}_{safe_name}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(file_path)

        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "status": "processing",
            "user_id": session["user_id"],
            "created_at": datetime.utcnow().isoformat(timespec="seconds"),
            "completed_at": None,
        }

        # Add job to queue instead of spawning a thread directly
        job_queue.put((job_id, file_path))

        return redirect(url_for("processing", job_id=job_id))

    return render_template("analyze.html")


@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        title = request.form.get("title", "").strip()
        contract_lang = request.form.get("contract_lang", "en").strip()
        if not prompt:
            flash(tr("prompt_required"), "error")
            return redirect(url_for("generate"))

        created_at = datetime.utcnow().isoformat(timespec="seconds")
        
        # Create database record with "pending" status
        conn = get_db_connection()
        cursor = conn.execute(
            """
            INSERT INTO generated_contracts (user_id, title, prompt, status, language, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session["user_id"], title, prompt, "pending", contract_lang, created_at),
        )
        conn.commit()
        generated_contract_id = cursor.lastrowid
        conn.close()
        
        # Update status to "in queue"
        conn = get_db_connection()
        conn.execute(
            "UPDATE generated_contracts SET status = ? WHERE id = ?",
            ("in queue", generated_contract_id)
        )
        conn.commit()
        conn.close()

        # Add to contract generation queue
        contract_queue.put(generated_contract_id)
        
        flash(tr("contract_saved_pdf"), "success")
        return redirect(url_for("generate"))

    conn = get_db_connection()
    recent_contracts = conn.execute(
        """
        SELECT id, title, pdf_filename, status, created_at, completed_at
        FROM generated_contracts
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "generate.html",
        recent_contracts=recent_contracts,
    )


@app.route("/generated-contract/<int:contract_id>/download")
@login_required
def download_generated_contract(contract_id):
    conn = get_db_connection()
    contract = conn.execute(
        """
        SELECT id, user_id, pdf_filename
        FROM generated_contracts
        WHERE id = ?
        """,
        (contract_id,),
    ).fetchone()
    conn.close()

    if not contract or contract["user_id"] != session["user_id"]:
        return redirect(url_for("generate"))

    return send_from_directory(
        GENERATED_CONTRACTS_FOLDER,
        contract["pdf_filename"],
        as_attachment=True,
    )


# -------------------------------
# Processing page
# -------------------------------
@app.route("/processing/<job_id>")
@login_required
def processing(job_id):
    job = jobs.get(job_id)
    if not job or job.get("user_id") != session["user_id"]:
        return redirect(url_for("home"))
    return render_template("loading.html", job_id=job_id)


# -------------------------------
# Job status API
# -------------------------------
@app.route("/status/<job_id>")
@login_required
def status(job_id):
    job = jobs.get(job_id)
    if not job or job.get("user_id") != session["user_id"]:
        return jsonify({"status": "not_found"})
    return jsonify(job)


# -------------------------------
# Result page
# -------------------------------
@app.route("/result/<job_id>")
@login_required
def result(job_id):
    job = jobs.get(job_id)

    if (
        not job
        or job.get("user_id") != session["user_id"]
        or job["status"] != "completed"
    ):
        return redirect(url_for("home"))

    localized_result = localize_result(job, get_language())
    return render_template("result.html", result=localized_result)


init_db()
start_job_worker()
start_contract_worker()


if __name__ == "__main__":
    app.run(debug=True)