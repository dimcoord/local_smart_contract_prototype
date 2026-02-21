from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import uuid
import threading

from utils import extract_text_from_pdf
from analyzer import analyze_contract, add_risk_score

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# In-memory job store
jobs = {}

@app.route("/")
def home():
    return render_template("index.html")


# -------------------------------
# Upload and create async job
# -------------------------------
@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    if request.method == "POST":
        file = request.files["contract"]
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "processing"}

        thread = threading.Thread(target=process_contract, args=(job_id, file_path))
        thread.start()

        return redirect(url_for("processing", job_id=job_id))

    return render_template("analyze.html")


def process_contract(job_id, file_path):
    text = extract_text_from_pdf(file_path)
    result = analyze_contract(text)

    if "error" not in result:
        result = add_risk_score(result)

    jobs[job_id] = {
        "status": "completed",
        "result": result
    }


# -------------------------------
# Processing page
# -------------------------------
@app.route("/processing/<job_id>")
def processing(job_id):
    return render_template("loading.html", job_id=job_id)


# -------------------------------
# Job status API
# -------------------------------
@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(jobs.get(job_id, {"status": "not_found"}))


# -------------------------------
# Result page
# -------------------------------
@app.route("/result/<job_id>")
def result(job_id):
    job = jobs.get(job_id)

    if not job or job["status"] != "completed":
        return redirect(url_for("home"))

    return render_template("result.html", result=job["result"])


if __name__ == "__main__":
    app.run(debug=True)