from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from rule_engine import analyze_clause_rules
from chatgpt_service import run_model
from github_service import GitHubService
import json
import PyPDF2
import docx
import os
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["GET","POST"])
def analyze():
    if request.method == "POST":
        text = request.form.get("contract_text")
        ai_result = run_model(text)
        
        return render_template("report.html", 
            ai_result=ai_result,
            rule_result=analyze_clause_rules(text), 
        )
    else:
        return render_template("analyze.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/dashboard")
def dashboard():
    ...

if __name__ == '__main__':
    app.run(debug=True)
