from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
import os
import uuid
import logging
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
from analyzer import analyze_contract, MODEL
from generator import generate_contract

logger = logging.getLogger(__name__)

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

# Global job queue for sequential processing (FIFO) across all users and job types
job_queue = queue.Queue()
job_worker_running = False

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
        "total_jobs": "Total Jobs",
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
        "prototype": "LexivaAI",
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
        "contract_monitoring": "Contract Monitoring",
        "created_at": "Created At",
        "no_generated_contracts": "No generated contracts yet.",
        "no_contracts": "No contracts yet.",
        "contract_language": "Contract Language",
        "contract_template": "Contract Template",
        "choose_contract_template": "Choose the contract purpose",
        "general_contract": "General Contract",
        "surat_perjanjian": "Agreement Letter",
        "kontrak_kerja": "Employment Contract",
        "nda": "Non-Disclosure Agreement",
        "service_agreement": "Service Agreement",
        "software_license": "Software License Agreement",
        "english": "English",
        "bahasa_indonesia": "Bahasa Indonesia",
        "your_generated_contracts": "Your Generated Contracts",
        "in_queue": "In Queue",
        "in_job": "In Job",
        "finished": "Finished",
        "processing": "Processing",
        "review_status": "Review Status",
        "pending_review": "Pending Review",
        "accepted": "Accepted",
        "rejected": "Rejected",
        "accept": "Accept",
        "reject": "Reject",
        "edit_acceptance": "Edit",
        "delete_contract": "Delete Contract",
        "save_changes": "Save Changes",
        "contract_accepted": "Contract accepted.",
        "contract_rejected": "Contract rejected.",
        "changes_saved": "Changes saved.",
        "contract_deleted": "Contract deleted.",
        "review_note": "Review Note",
        "contract_title_edit": "Contract Title",
        "acceptance_editor": "Editor",
        "source_type": "Source Type",
        "analysis": "Analysis",
        "generation": "Generation",
        "contract_queued": "Contract queued for monitoring.",
        "monitoring": "Monitoring",
        "no_generated_contracts_dashboard": "No generated contracts yet.",
        "legal_assistance": "Legal Assistance",
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
        "total_jobs": "Total Pekerjaan",
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
        "contract_monitoring": "Monitoring Kontrak",
        "created_at": "Dibuat Pada",
        "no_generated_contracts": "Belum ada kontrak yang dibuat.",
        "no_contracts": "Belum ada kontrak.",
        "contract_language": "Bahasa Kontrak",
        "contract_template": "Template Kontrak",
        "choose_contract_template": "Pilih tujuan kontrak",
        "general_contract": "Kontrak Umum",
        "surat_perjanjian": "Surat Perjanjian",
        "kontrak_kerja": "Kontrak Kerja",
        "nda": "Perjanjian Kerahasiaan",
        "service_agreement": "Perjanjian Jasa",
        "software_license": "Perjanjian Lisensi Perangkat Lunak",
        "english": "Bahasa Inggris",
        "bahasa_indonesia": "Bahasa Indonesia",
        "your_generated_contracts": "Kontrak Yang Dibuat",
        "in_queue": "Antri",
        "in_job": "Sedang Dibuat",
        "finished": "Selesai",
        "processing": "Diproses",
        "review_status": "Status Review",
        "pending_review": "Menunggu Review",
        "accepted": "Diterima",
        "rejected": "Ditolak",
        "accept": "Setujui",
        "reject": "Tolak",
        "edit_acceptance": "Edit",
        "delete_contract": "Hapus Kontrak",
        "save_changes": "Simpan Perubahan",
        "contract_accepted": "Kontrak diterima.",
        "contract_rejected": "Kontrak ditolak.",
        "changes_saved": "Perubahan disimpan.",
        "contract_deleted": "Kontrak dihapus.",
        "review_note": "Catatan Review",
        "contract_title_edit": "Judul Kontrak",
        "acceptance_editor": "Editor",
        "source_type": "Sumber",
        "analysis": "Analisis",
        "generation": "Generate",
        "contract_queued": "Kontrak masuk antrean monitoring.",
        "monitoring": "Monitoring",
        "no_generated_contracts_dashboard": "Belum ada kontrak yang dibuat.",
        "legal_assistance": "Bantuan Hukum",
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
            template_type TEXT DEFAULT 'general',
            source_type TEXT DEFAULT 'generation',
            source_name TEXT,
            source_path TEXT,
            analysis_json TEXT,
            review_status TEXT DEFAULT 'pending',
            review_note TEXT,
            review_updated_at TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(generated_contracts)").fetchall()
    }
    schema_updates = {
        "source_type": "TEXT DEFAULT 'generation'",
        "template_type": "TEXT DEFAULT 'general'",
        "source_name": "TEXT",
        "source_path": "TEXT",
        "analysis_json": "TEXT",
        "review_status": "TEXT DEFAULT 'pending'",
        "review_note": "TEXT",
        "review_updated_at": "TEXT",
    }
    for column_name, column_definition in schema_updates.items():
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE generated_contracts ADD COLUMN {column_name} {column_definition}"
            )

    conn.execute(
        "UPDATE generated_contracts SET source_type = 'generation' WHERE source_type IS NULL OR source_type = ''"
    )
    conn.execute(
        "UPDATE generated_contracts SET review_status = 'pending' WHERE review_status IS NULL OR review_status = ''"
    )
    conn.commit()
    conn.close()


def process_analysis_job(job_id, file_path, contract_id=None):
    job = jobs.get(job_id)
    if not job:
        return

    try:
        job["status"] = "in job"
        text = extract_text_from_pdf(file_path)
        
        # Get the language from the database
        language = "en"
        if contract_id:
            conn = get_db_connection()
            contract = conn.execute(
                "SELECT language FROM generated_contracts WHERE id = ?",
                (contract_id,)
            ).fetchone()
            conn.close()
            if contract:
                language = contract["language"] or "en"
                logger.info(f"Analysis job {job_id}: Using language '{language}' from contract {contract_id}")
            else:
                logger.warning(f"Analysis job {job_id}: Contract {contract_id} not found in database")
        else:
            logger.warning(f"Analysis job {job_id}: No contract_id provided, defaulting to 'en'")
        
        result = analyze_contract(text, language=language)

        job["status"] = "completed"
        job["result"] = result
        job["completed_at"] = datetime.utcnow().isoformat(timespec="seconds")

        if contract_id:
            conn = get_db_connection()
            conn.execute(
                """
                UPDATE generated_contracts
                SET status = ?, content = ?, analysis_json = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    "finished",
                    json.dumps(result, ensure_ascii=False, indent=2),
                    json.dumps(result, ensure_ascii=False),
                    job["completed_at"],
                    contract_id,
                ),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        if contract_id:
            conn = get_db_connection()
            conn.execute(
                "UPDATE generated_contracts SET status = ? WHERE id = ?",
                ("error", contract_id),
            )
            conn.commit()
            conn.close()
        job["completed_at"] = datetime.utcnow().isoformat(timespec="seconds")
        logger.exception("Failed to analyze contract %s", contract_id)


def process_contract_job(contract_id):
    conn = get_db_connection()
    contract = conn.execute(
        "SELECT id, user_id, title, prompt, language, template_type FROM generated_contracts WHERE id = ?",
        (contract_id,),
    ).fetchone()
    conn.close()

    if not contract:
        return

    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE generated_contracts SET status = ? WHERE id = ?",
            ("in job", contract_id),
        )
        conn.commit()
        conn.close()

        result = generate_contract(
            contract["prompt"],
            language=contract["language"],
            template_type=contract["template_type"] or "general",
        )

        completed_at = datetime.utcnow().isoformat(timespec="seconds")
        pdf_filename = f"contract_{contract['user_id']}_{uuid.uuid4().hex}.pdf"
        pdf_path = os.path.join(GENERATED_CONTRACTS_FOLDER, pdf_filename)
        create_contract_pdf(result, pdf_path, title=contract["title"])

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE generated_contracts
            SET status = ?, content = ?, pdf_filename = ?, completed_at = ?
            WHERE id = ?
            """,
            ("finished", result, pdf_filename, completed_at, contract_id),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.exception("Failed to generate contract %s", contract_id)
        conn = get_db_connection()
        conn.execute(
            "UPDATE generated_contracts SET status = ? WHERE id = ?",
            ("error", contract_id),
        )
        conn.commit()
        conn.close()


def get_owned_contract(contract_id):
    conn = get_db_connection()
    contract = conn.execute(
        "SELECT * FROM generated_contracts WHERE id = ? AND user_id = ?",
        (contract_id, session["user_id"]),
    ).fetchone()
    conn.close()
    return contract


def get_user_contract_items(user_id):
    conn = get_db_connection()
    contracts = conn.execute(
        """
        SELECT id, title, status, review_status, review_note, source_type, created_at, completed_at, pdf_filename
        FROM generated_contracts
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    items = []
    for contract in contracts:
        items.append(
            {
                "contract_id": contract["id"],
                "id": contract["id"],
                "title": contract["title"] or "Untitled Contract",
                "status": contract["status"],
                "review_status": contract["review_status"],
                "review_note": contract["review_note"],
                "source_type": contract["source_type"] or "generation",
                "created_at": contract["created_at"],
                "completed_at": contract["completed_at"],
                "pdf_filename": contract["pdf_filename"],
            }
        )
    return items


def get_combined_job_metrics(user_id):
    analysis_jobs = []
    for job_id, job in jobs.items():
        if job.get("user_id") != user_id:
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

    contract_items = get_user_contract_items(user_id)
    
    # Separate generation jobs from all contracts
    generation_jobs = [item for item in contract_items if item.get("source_type") == "generation"]

    total_jobs = len(contract_items)
    completed_jobs = sum(1 for job in contract_items if job.get("status") in {"completed", "finished"})
    processing_jobs = sum(
        1
        for job in contract_items
        if job.get("status") in {"processing", "in queue", "in job", "pending"}
    )

    analysis_jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    generation_jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)

    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "processing_jobs": processing_jobs,
        "analysis_jobs": analysis_jobs,
        "generation_jobs": generation_jobs,
        "contract_items": contract_items,
    }


def review_status_label(review_status):
    review_status = (review_status or "pending").lower()
    if review_status == "accepted":
        return tr("accepted")
    if review_status == "rejected":
        return tr("rejected")
    if review_status == "pending":
        return tr("pending_review")
    return review_status.replace("_", " ").title()


def status_label(status):
    status = (status or "").lower()
    if status in {"in queue", "pending"}:
        return tr("in_queue")
    if status == "in job":
        return tr("in_job")
    if status in {"finished", "completed"}:
        return tr("finished")
    if status == "error":
        return "Error"
    return status.title() if status else tr("processing")


def job_worker():
    """Single global worker that processes analysis and generation jobs one at a time."""
    while True:
        task = job_queue.get()
        try:
            if task is None:
                break

            task_type = task.get("type")
            if task_type == "analysis":
                process_analysis_job(task["job_id"], task["file_path"], contract_id=task.get("contract_id"))
            elif task_type == "generation":
                process_contract_job(task["contract_id"])
        finally:
            job_queue.task_done()


def start_job_worker():
    """Start the background job worker thread."""
    global job_worker_running
    if not job_worker_running:
        job_worker_running = True
        worker_thread = threading.Thread(target=job_worker, daemon=True)
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

    # Keep result rendering non-blocking.
    # Synchronous LLM translation here can cause the result page request to hang.
    # UI labels are already localized via translation keys, so this preserves usability.

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
    metrics = get_combined_job_metrics(session["user_id"])
    
    return render_template(
        "dashboard.html",
        total_jobs=metrics["total_jobs"],
        completed_jobs=metrics["completed_jobs"],
        processing_jobs=metrics["processing_jobs"],
        analysis_jobs=metrics["analysis_jobs"],
        generation_jobs=metrics["generation_jobs"],
    )


@app.route("/monitoring")
@login_required
def monitoring():
    metrics = get_combined_job_metrics(session["user_id"])
    return render_template(
        "monitoring.html",
        contract_items=metrics["contract_items"],
        total_jobs=metrics["total_jobs"],
        completed_jobs=metrics["completed_jobs"],
        processing_jobs=metrics["processing_jobs"],
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

        created_at = datetime.utcnow().isoformat(timespec="seconds")
        contract_title = os.path.splitext(safe_name)[0] or safe_name
        conn = get_db_connection()
        cursor = conn.execute(
            """
            INSERT INTO generated_contracts (
                user_id, title, prompt, content, status, language,
                source_type, source_name, source_path, review_status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                contract_title,
                f"Uploaded PDF: {safe_name}",
                None,
                "in queue",
                get_language(),
                "analysis",
                safe_name,
                file_path,
                "pending",
                created_at,
            ),
        )
        conn.commit()
        monitored_contract_id = cursor.lastrowid
        conn.close()

        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "status": "in queue",
            "user_id": session["user_id"],
            "created_at": created_at,
            "completed_at": None,
            "contract_id": monitored_contract_id,
        }

        # Add job to global queue (shared across all users and job types)
        job_queue.put({"type": "analysis", "job_id": job_id, "file_path": file_path, "contract_id": monitored_contract_id})

        flash(tr("contract_queued"), "success")
        return redirect(url_for("dashboard"))

    return render_template("analyze.html")


@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        title = request.form.get("title", "").strip()
        contract_lang = request.form.get("contract_lang", "en").strip()
        template_type = request.form.get("template_type", "general").strip()
        if not prompt:
            flash(tr("prompt_required"), "error")
            return redirect(url_for("generate"))

        if template_type not in {
            "general",
            "surat_perjanjian",
            "kontrak_kerja",
            "nda",
            "service_agreement",
            "software_license",
        }:
            template_type = "general"

        created_at = datetime.utcnow().isoformat(timespec="seconds")
        conn = get_db_connection()
        cursor = conn.execute(
            """
            INSERT INTO generated_contracts (
                user_id, title, prompt, status, language, template_type, source_type, review_status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                prompt,
                "pending",
                contract_lang,
                template_type,
                "generation",
                "pending",
                created_at,
            ),
        )
        conn.commit()
        generated_contract_id = cursor.lastrowid
        conn.close()

        conn = get_db_connection()
        conn.execute(
            "UPDATE generated_contracts SET status = ? WHERE id = ?",
            ("in queue", generated_contract_id),
        )
        conn.commit()
        conn.close()

        # Add to global queue (shared across all users and job types)
        job_queue.put({"type": "generation", "contract_id": generated_contract_id})
        
        flash(tr("contract_queued"), "success")
        return redirect(url_for("generate"))

    conn = get_db_connection()
    recent_contracts = conn.execute(
        """
        SELECT id, title, pdf_filename, status, review_status, source_type, created_at, completed_at
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
    contract = get_owned_contract(contract_id)

    if not contract or contract["user_id"] != session["user_id"]:
        return redirect(url_for("generate"))

    if not contract["pdf_filename"]:
        return redirect(url_for("dashboard"))

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


@app.route("/contracts/<int:contract_id>/accept", methods=["POST"])
@login_required
def accept_contract(contract_id):
    contract = get_owned_contract(contract_id)
    if not contract:
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE generated_contracts
        SET review_status = ?, review_updated_at = ?
        WHERE id = ?
        """,
        ("accepted", datetime.utcnow().isoformat(timespec="seconds"), contract_id),
    )
    conn.commit()
    conn.close()
    flash(tr("contract_accepted"), "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/contracts/<int:contract_id>/reject", methods=["POST"])
@login_required
def reject_contract(contract_id):
    contract = get_owned_contract(contract_id)
    if not contract:
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE generated_contracts
        SET review_status = ?, review_updated_at = ?
        WHERE id = ?
        """,
        ("rejected", datetime.utcnow().isoformat(timespec="seconds"), contract_id),
    )
    conn.commit()
    conn.close()
    flash(tr("contract_rejected"), "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/contracts/<int:contract_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contract(contract_id):
    contract = get_owned_contract(contract_id)
    if not contract:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        review_status = request.form.get("review_status", "pending").strip()
        review_note = request.form.get("review_note", "").strip()

        if review_status not in {"pending", "accepted", "rejected"}:
            review_status = "pending"

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE generated_contracts
            SET title = ?, review_status = ?, review_note = ?, review_updated_at = ?
            WHERE id = ?
            """,
            (
                title or contract["title"],
                review_status,
                review_note,
                datetime.utcnow().isoformat(timespec="seconds"),
                contract_id,
            ),
        )
        conn.commit()
        conn.close()
        flash(tr("changes_saved"), "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_contract.html", contract=contract)


@app.route("/contracts/<int:contract_id>/delete", methods=["POST"])
@login_required
def delete_contract(contract_id):
    contract = get_owned_contract(contract_id)
    if not contract:
        return redirect(url_for("dashboard"))

    if contract["pdf_filename"]:
        pdf_path = os.path.join(GENERATED_CONTRACTS_FOLDER, contract["pdf_filename"])
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    if contract["source_path"] and os.path.exists(contract["source_path"]):
        os.remove(contract["source_path"])

    conn = get_db_connection()
    conn.execute("DELETE FROM generated_contracts WHERE id = ?", (contract_id,))
    conn.commit()
    conn.close()
    flash(tr("contract_deleted"), "success")
    return redirect(request.referrer or url_for("dashboard"))


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
    contract = None
    contract_id = job.get("contract_id")
    if contract_id:
        contract = get_owned_contract(contract_id)
    return render_template("result.html", result=localized_result, contract=contract)


@app.route("/contract/<int:contract_id>/result")
@login_required
def view_analysis_result(contract_id):
    contract = get_owned_contract(contract_id)
    
    if not contract or contract["source_type"] != "analysis":
        return redirect(url_for("monitoring"))
    
    # Parse the analysis_json from the database
    try:
        result = json.loads(contract["analysis_json"]) if contract["analysis_json"] else {}
    except (json.JSONDecodeError, TypeError):
        result = {}
    
    localized_result = result
    return render_template("result.html", result=localized_result, contract=contract)


init_db()
start_job_worker()


if __name__ == "__main__":
    app.run(debug=True)