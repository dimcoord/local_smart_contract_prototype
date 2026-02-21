from flask import Flask, render_template, request
import os
from utils import extract_text_from_pdf
from analyzer import analyze_contract
from generator import generate_contract

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    result = None

    if request.method == "POST":
        file = request.files["contract"]
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        text = extract_text_from_pdf(file_path)
        result = analyze_contract(text)

    return render_template("analyze.html", result=result)


@app.route("/generate", methods=["GET", "POST"])
def generate():
    result = None

    if request.method == "POST":
        prompt = request.form["prompt"]
        result = generate_contract(prompt)

    return render_template("generate.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)