from flask import Flask, render_template, request, jsonify, send_file, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
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
app.secret_key = "oursupersecretkeyissimpleasmysassyouknowiknew"
CORS(app)  # Enable CORS for all routes

# Configure logging

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["GET","POST"])
def analyze():
    if request.method == "POST":
        text = request.form.get("clause_text")
        ai_result = run_model(text)
        
        return render_template("report.html", 
            ai_result=ai_result,
            rule_result=analyze_clause_rules(text), 
        )
    else:
        return render_template("analyze.html")

gh = GitHubService(
    token="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",
    repo_owner="AlgoNest",
    repo_name="ClauseDB"
)

# ---------------------------
# Signup
# ---------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        users = gh.load_users()

        # Check if email exists
        for u in users:
            if u["email"] == email:
                flash("Email already exists!")
                return redirect("/signup")

        hashed = generate_password_hash(password)

        new_user = {
            "name": name,
            "email": email,
            "password": hashed
        }

        gh.add_user(new_user)
        flash("Thanks for signup!")
        return redirect("/analyze")

    return render_template("signup.html")


# ---------------------------
# Login
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        users = gh.load_users()

        for u in users:
            if u["email"] == email and check_password_hash(u["password"], password):
                session["user_email"] = u["email"]
                session["user_name"] = u["name"]
                return redirect("/analyze")

        flash("Invalid email or password!")
        return redirect("/login")

    return render_template("login.html")


# ---------------------------
# Dashboard
# ---------------------------
@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/login")

    return f"Welcome {session['user_name']}!"


# ---------------------------
# Logout
# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == '__main__':
    app.run(debug=True)
