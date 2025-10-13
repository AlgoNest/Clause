from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import uuid
import io
import threading
import queue
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PyPDF2 import PdfReader
from docx import Document
from rule_engine import analyze_clause_rules
from chatgpt_service import analyze_clause_with_chatgpt
from github_service import GitHubService
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global error log storage (in production, use a database)
error_logs = []

# Processing queue for managing concurrent analyses
analysis_queue = queue.Queue(maxsize=10)  # Limit concurrent analyses
active_analyses = {}  # Track active analysis status

# Settings storage (in production, use a database or secure config)
settings = {
    'openai_key': os.getenv('OPENAI_API_KEY', ''),
    'github_token': os.getenv('GITHUB_TOKEN', ''),
    'github_owner': os.getenv('GITHUB_REPO_OWNER', ''),
    'github_repo': os.getenv('GITHUB_REPO_NAME', '')
}

# Initialize services
github_service = None
if all(settings[k] for k in ['github_token', 'github_owner', 'github_repo']):
    try:
        github_service = GitHubService(settings['github_token'], settings['github_owner'], settings['github_repo'])
    except Exception as e:
        logger.error(f"Failed to initialize GitHub service: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"GitHub service initialization failed: {str(e)}"
        })

def extract_text_from_file(file):
    """Extract text from uploaded file (PDF, DOCX, or TXT)."""
    filename = file.filename.lower()

    if filename.endswith('.pdf'):
        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()

    elif filename.endswith('.docx'):
        # Extract text from DOCX
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()

    elif filename.endswith('.txt'):
        # Read text file
        return file.read().decode('utf-8').strip()

    else:
        raise ValueError("Unsupported file format. Please upload PDF, DOCX, or TXT files.")

def generate_pdf_report(analysis_data):
    """Generate a professional PDF report from analysis data."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center
    )

    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        textColor=colors.blue
    )

    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph("Contract Clause Analysis Report", title_style))
    story.append(Spacer(1, 12))

    # Timestamp and ID
    timestamp = datetime.fromisoformat(analysis_data['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Analysis ID: {analysis_data.get('analysis_id', 'N/A')}", normal_style))
    story.append(Paragraph(f"Generated: {timestamp}", normal_style))
    story.append(Spacer(1, 20))

    # Executive Summary
    story.append(Paragraph("Executive Summary", section_style))

    rule_summary = analysis_data.get('rule_based', {}).get('summary', 'No rule-based analysis available')
    ai_summary = analysis_data.get('ai_based', {}).get('summary', 'No AI analysis available')

    summary_text = f"This contract clause analysis combines rule-based and AI-powered insights. {rule_summary}"
    if not ai_summary.startswith('AI analysis'):
        summary_text += f" AI analysis reveals: {ai_summary}"

    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 15))

    # Risk Assessment
    story.append(Paragraph("Risk Assessment", section_style))

    rule_risk = analysis_data.get('rule_based', {}).get('risk_score', 0)
    ai_risk = analysis_data.get('ai_based', {}).get('risk_level', 'Unknown')

    risk_data = [
        ['Analysis Type', 'Risk Level', 'Score/Details'],
        ['Rule-Based', f"{rule_risk}/10", 'Numerical risk score'],
        ['AI-Based', ai_risk, 'Categorical risk assessment']
    ]

    risk_table = Table(risk_data)
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(risk_table)
    story.append(Spacer(1, 15))

    # Key Findings
    story.append(Paragraph("Key Findings", section_style))

    # Rule-based findings
    rule_flags = analysis_data.get('rule_based', {}).get('flags', [])
    if rule_flags:
        story.append(Paragraph("Rule-Based Analysis Flags:", styles['Heading3']))
        for flag in rule_flags:
            story.append(Paragraph(f"• {flag}", normal_style))

    # AI findings
    ai_terms = analysis_data.get('ai_based', {}).get('key_terms', [])
    ai_recommendations = analysis_data.get('ai_based', {}).get('recommendations', [])

    if ai_terms:
        story.append(Paragraph("Key Terms Identified:", styles['Heading3']))
        terms_text = ", ".join(ai_terms)
        story.append(Paragraph(terms_text, normal_style))

    if ai_recommendations:
        story.append(Paragraph("AI Recommendations:", styles['Heading3']))
        for rec in ai_recommendations:
            story.append(Paragraph(f"• {rec}", normal_style))

    story.append(Spacer(1, 15))

    # Detailed Analysis
    story.append(Paragraph("Detailed Analysis", section_style))

    # Rule-based details
    story.append(Paragraph("Rule-Based Analysis Details:", styles['Heading3']))
    rule_clause_type = analysis_data.get('rule_based', {}).get('clause_type', 'Unknown')
    story.append(Paragraph(f"Clause Type: {rule_clause_type}", normal_style))
    story.append(Paragraph(f"Risk Score: {rule_risk}/10", normal_style))

    # AI details
    story.append(Paragraph("AI Analysis Details:", styles['Heading3']))
    ai_clause_type = analysis_data.get('ai_based', {}).get('clause_type', 'Unknown')
    story.append(Paragraph(f"Clause Type: {ai_clause_type}", normal_style))
    story.append(Paragraph(f"Risk Level: {ai_risk}", normal_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze")
def analyze():
    return render_template("analyze.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/dashboard")
def dashboard():
    try:
        if not github_service:
            return render_template("dashboard.html", analyses=[], error="GitHub service not configured")

        analyses = github_service.list_analyses_with_data()
        return render_template("dashboard.html", analyses=analyses)
    except Exception as e:
        logger.error(f"Failed to load dashboard: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"Dashboard error: {str(e)}"
        })
        return render_template("dashboard.html", analyses=[], error=f"Failed to load analyses: {str(e)}")

def process_analysis_task(analysis_id, clause_text, input_method):
    """Background task to process analysis with progress tracking."""
    try:
        active_analyses[analysis_id] = {
            'status': 'processing',
            'progress': 0,
            'stage': 'Initializing analysis...',
            'start_time': datetime.now()
        }

        # Track processing start time
        processing_start = datetime.now()

        # Step 1: Run rule-based analysis (fast)
        active_analyses[analysis_id].update({
            'progress': 10,
            'stage': 'Running rule-based analysis...'
        })

        logger.info(f"Starting rule-based analysis for analysis_id: {analysis_id}")
        rule_start = datetime.now()
        rule_result = json.loads(analyze_clause_rules(clause_text))
        rule_duration = (datetime.now() - rule_start).total_seconds() * 1000
        logger.info(f"Rule-based analysis completed in {rule_duration:.2f}ms")

        active_analyses[analysis_id].update({
            'progress': 50,
            'stage': 'Rule-based analysis completed. Starting AI analysis...'
        })

        # Step 2: Run AI analysis (slower, with timeout and retry logic)
        ai_result = None
        ai_duration = 0

        try:
            if not settings.get('openai_key'):
                ai_result = {
                    "error": "OpenAI API key not configured",
                    "clause_type": "Unknown",
                    "key_terms": [],
                    "risk_level": "Unknown",
                    "summary": "AI analysis unavailable - please configure OpenAI API key in settings",
                    "recommendations": ["Configure OpenAI API key to enable AI analysis"]
                }
            else:
                logger.info(f"Starting AI analysis for analysis_id: {analysis_id}")
                ai_start = datetime.now()

                active_analyses[analysis_id].update({
                    'progress': 60,
                    'stage': 'Analyzing with AI...'
                })

                # Implement retry logic with exponential backoff
                max_retries = 3
                base_delay = 1  # seconds

                for attempt in range(max_retries):
                    try:
                        # Temporarily set the API key for this request
                        import openai
                        original_key = openai.api_key
                        openai.api_key = settings['openai_key']

                        # Set a reasonable timeout for the API call
                        openai.timeout = 30  # 30 seconds timeout

                        try:
                            ai_result = analyze_clause_with_chatgpt(clause_text)
                            ai_duration = (datetime.now() - ai_start).total_seconds() * 1000
                            logger.info(f"AI analysis completed in {ai_duration:.2f}ms on attempt {attempt + 1}")
                            break  # Success, exit retry loop
                        finally:
                            openai.api_key = original_key

                    except Exception as e:
                        logger.warning(f"AI analysis attempt {attempt + 1} failed: {e}")

                        if attempt < max_retries - 1:  # Not the last attempt
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            active_analyses[analysis_id].update({
                                'progress': 60 + (attempt + 1) * 5,
                                'stage': f'AI analysis failed, retrying in {delay} seconds...'
                            })
                            logger.info(f"Retrying AI analysis in {delay} seconds...")
                            import time
                            time.sleep(delay)
                        else:
                            # All retries exhausted
                            raise e

        except Exception as e:
            logger.error(f"AI analysis failed after {max_retries} attempts: {e}")
            error_logs.append({
                'timestamp': datetime.now().isoformat(),
                'message': f"AI analysis error: {str(e)}"
            })
            ai_result = {
                "error": f"AI analysis failed after retries: {str(e)}",
                "clause_type": "Unknown",
                "key_terms": [],
                "risk_level": "Unknown",
                "summary": "AI analysis encountered an error after multiple attempts",
                "recommendations": ["Try again later or check API configuration"]
            }
            ai_duration = (datetime.now() - ai_start).total_seconds() * 1000 if 'ai_start' in locals() else 0

        active_analyses[analysis_id].update({
            'progress': 90,
            'stage': 'Generating final report...'
        })

        # Calculate total processing time
        total_duration = (datetime.now() - processing_start).total_seconds() * 1000

        # Combine results with enhanced metadata
        combined_result = {
            "rule_based": rule_result,
            "ai_based": ai_result,
            "clause_text": clause_text,
            "timestamp": datetime.now().isoformat(),
            "analysis_id": analysis_id,
            "input_method": input_method,
            "text_length": len(clause_text),
            "processing_time_ms": total_duration,
            "rule_processing_time_ms": rule_duration,
            "ai_processing_time_ms": ai_duration
        }

        # Mark as completed
        active_analyses[analysis_id].update({
            'status': 'completed',
            'progress': 100,
            'stage': 'Analysis completed successfully',
            'result': combined_result
        })

        logger.info(f"Analysis {analysis_id} completed in {total_duration:.2f}ms (Rule: {rule_duration:.2f}ms, AI: {ai_duration:.2f}ms)")

    except Exception as e:
        logger.error(f"Analysis task failed for {analysis_id}: {e}")
        active_analyses[analysis_id] = {
            'status': 'failed',
            'progress': 0,
            'stage': f'Analysis failed: {str(e)}',
            'error': str(e)
        }

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    try:
        clause_text = None
        input_method = "unknown"

        # Check if file was uploaded
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400

            # Validate file before processing
            filename = file.filename.lower()
            if not (filename.endswith('.pdf') or filename.endswith('.docx') or filename.endswith('.txt')):
                return jsonify({"error": "Unsupported file format. Please upload PDF, DOCX, or TXT files."}), 400

            if file.content_length and file.content_length > 10 * 1024 * 1024:  # 10MB limit
                return jsonify({"error": "File size exceeds 10MB limit"}), 400

            try:
                clause_text = extract_text_from_file(file)
                input_method = "file"
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"File processing error: {e}")
                return jsonify({"error": f"Failed to process file: {str(e)}"}), 400

        # Check for text input (JSON or form data)
        elif request.is_json:
            data = request.get_json()
            if not data or 'clause_text' not in data:
                return jsonify({"error": "Missing 'clause_text' in request body"}), 400
            clause_text = data['clause_text'].strip()
            input_method = "json"
        elif 'clause_text' in request.form:
            clause_text = request.form['clause_text'].strip()
            input_method = "form"
        else:
            return jsonify({"error": "No clause text provided. Use 'clause_text' field or upload a file."}), 400

        # Sanitize and validate text input
        if not clause_text:
            return jsonify({"error": "Clause text cannot be empty"}), 400

        # Remove excessive whitespace and normalize
        clause_text = ' '.join(clause_text.split())

        if len(clause_text) > 10000:  # Reasonable limit
            return jsonify({"error": "Clause text is too long (max 10,000 characters)"}), 400

        if len(clause_text) < 10:  # Minimum length check
            return jsonify({"error": "Clause text is too short. Please provide at least 10 characters."}), 400

        # Track processing start time
        processing_start = datetime.now()

        # Step 1: Run rule-based analysis (fast)
        logger.info(f"Starting rule-based analysis for analysis_id: {analysis_id}")
        rule_start = datetime.now()
        rule_result = json.loads(analyze_clause_rules(clause_text))
        rule_duration = (datetime.now() - rule_start).total_seconds() * 1000
        logger.info(f"Rule-based analysis completed in {rule_duration:.2f}ms")

        # Step 2: Run AI analysis (slower, with timeout and retry logic)
        ai_result = None
        ai_duration = 0

        try:
            if not settings.get('openai_key'):
                ai_result = {
                    "error": "OpenAI API key not configured",
                    "clause_type": "Unknown",
                    "key_terms": [],
                    "risk_level": "Unknown",
                    "summary": "AI analysis unavailable - please configure OpenAI API key in settings",
                    "recommendations": ["Configure OpenAI API key to enable AI analysis"]
                }
            else:
                logger.info(f"Starting AI analysis for analysis_id: {analysis_id}")
                ai_start = datetime.now()

                # Implement retry logic with exponential backoff
                max_retries = 3
                base_delay = 1  # seconds

                for attempt in range(max_retries):
                    try:
                        # Temporarily set the API key for this request
                        import openai
                        original_key = openai.api_key
                        openai.api_key = settings['openai_key']

                        # Set a reasonable timeout for the API call
                        openai.timeout = 30  # 30 seconds timeout

                        try:
                            ai_result = analyze_clause_with_chatgpt(clause_text)
                            ai_duration = (datetime.now() - ai_start).total_seconds() * 1000
                            logger.info(f"AI analysis completed in {ai_duration:.2f}ms on attempt {attempt + 1}")
                            break  # Success, exit retry loop
                        finally:
                            openai.api_key = original_key

                    except Exception as e:
                        logger.warning(f"AI analysis attempt {attempt + 1} failed: {e}")

                        if attempt < max_retries - 1:  # Not the last attempt
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logger.info(f"Retrying AI analysis in {delay} seconds...")
                            import time
                            time.sleep(delay)
                        else:
                            # All retries exhausted
                            raise e

        except Exception as e:
            logger.error(f"AI analysis failed after {max_retries} attempts: {e}")
            error_logs.append({
                'timestamp': datetime.now().isoformat(),
                'message': f"AI analysis error: {str(e)}"
            })
            ai_result = {
                "error": f"AI analysis failed after retries: {str(e)}",
                "clause_type": "Unknown",
                "key_terms": [],
                "risk_level": "Unknown",
                "summary": "AI analysis encountered an error after multiple attempts",
                "recommendations": ["Try again later or check API configuration"]
            }
            ai_duration = (datetime.now() - ai_start).total_seconds() * 1000 if 'ai_start' in locals() else 0

        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())

        # Calculate total processing time
        total_duration = (datetime.now() - processing_start).total_seconds() * 1000

        # Combine results with enhanced metadata
        combined_result = {
            "rule_based": rule_result,
            "ai_based": ai_result,
            "clause_text": clause_text,
            "timestamp": datetime.now().isoformat(),
            "analysis_id": analysis_id,
            "input_method": input_method,
            "text_length": len(clause_text),
            "processing_time_ms": total_duration,
            "rule_processing_time_ms": rule_duration,
            "ai_processing_time_ms": ai_duration
        }

        logger.info(f"Analysis {analysis_id} completed in {total_duration:.2f}ms (Rule: {rule_duration:.2f}ms, AI: {ai_duration:.2f}ms)")

        return jsonify(combined_result), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in request body"}), 400
    except UnicodeDecodeError:
        return jsonify({"error": "Invalid text encoding. Please ensure your text is properly encoded."}), 400
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"Analysis error: {str(e)}"
        })
        # Provide more user-friendly error messages
        error_message = str(e)
        if "rate limit" in error_message.lower():
            error_message = "API rate limit exceeded. Please wait a moment and try again."
        elif "timeout" in error_message.lower():
            error_message = "Request timed out. Please try again."
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            error_message = "Network error. Please check your connection and try again."
        elif "openai" in error_message.lower():
            error_message = "AI service temporarily unavailable. Analysis completed with rule-based results only."

        return jsonify({"error": error_message}), 500

@app.route("/api/analyses", methods=["GET"])
def api_list_analyses():
    try:
        if not github_service:
            return jsonify({"error": "GitHub service not configured"}), 503

        analyses = github_service.list_analyses()
        return jsonify({"analyses": analyses}), 200
    except Exception as e:
        logger.error(f"Failed to list analyses: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"List analyses error: {str(e)}"
        })
        return jsonify({"error": f"Failed to list analyses: {str(e)}"}), 500

@app.route("/api/save", methods=["POST"])
def api_save_analysis():
    try:
        if not github_service:
            return jsonify({"error": "GitHub service not configured"}), 503

        data = request.get_json()
        if not data or 'analysis_data' not in data:
            return jsonify({"error": "Missing 'analysis_data' in request body"}), 400

        analysis_data = data['analysis_data']
        analysis_id = github_service.save_analysis(analysis_data)
        return jsonify({"analysis_id": analysis_id, "message": "Analysis saved successfully"}), 201
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"Save analysis error: {str(e)}"
        })
        return jsonify({"error": f"Failed to save analysis: {str(e)}"}), 500

@app.route("/api/generate-pdf", methods=["POST"])
def api_generate_pdf():
    try:
        data = request.get_json()
        if not data or 'analysis_data' not in data:
            return jsonify({"error": "Missing 'analysis_data' in request body"}), 400

        analysis_data = data['analysis_data']

        # Generate PDF
        pdf_buffer = generate_pdf_report(analysis_data)

        # Return PDF as downloadable file
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"clause_analysis_{analysis_data.get('analysis_id', 'report')}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"PDF generation error: {str(e)}"
        })
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500

@app.route("/api/analysis/<analysis_id>", methods=["GET"])
def api_get_analysis(analysis_id):
    try:
        if not github_service:
            return jsonify({"error": "GitHub service not configured"}), 503

        analysis_data = github_service.get_analysis(analysis_id)
        return jsonify(analysis_data), 200
    except Exception as e:
        logger.error(f"Failed to get analysis {analysis_id}: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"Get analysis error: {str(e)}"
        })
        return jsonify({"error": f"Failed to get analysis: {str(e)}"}), 500

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    try:
        # Check service status
        ai_operational = bool(settings.get('openai_key'))
        github_operational = bool(github_service and settings.get('github_token') and settings.get('github_owner') and settings.get('github_repo'))

        return jsonify({
            "openai_configured": bool(settings.get('openai_key')),
            "github_configured": bool(settings.get('github_token')),
            "github_owner": settings.get('github_owner', ''),
            "github_repo": settings.get('github_repo', ''),
            "ai_service_status": "Operational" if ai_operational else "Not Configured",
            "ai_service_operational": ai_operational,
            "github_service_status": "Operational" if github_operational else "Not Configured",
            "github_service_operational": github_operational,
            "error_logs": error_logs[-10:]  # Last 10 errors
        }), 200
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        return jsonify({"error": f"Failed to get settings: {str(e)}"}), 500

@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No settings data provided"}), 400

        # Update settings
        for key, value in data.items():
            if key in settings:
                settings[key] = value

        # Reinitialize GitHub service if settings changed
        if any(k in data for k in ['github_token', 'github_owner', 'github_repo']):
            global github_service
            if all(settings[k] for k in ['github_token', 'github_owner', 'github_repo']):
                try:
                    github_service = GitHubService(settings['github_token'], settings['github_owner'], settings['github_repo'])
                except Exception as e:
                    logger.error(f"Failed to reinitialize GitHub service: {e}")
                    error_logs.append({
                        'timestamp': datetime.now().isoformat(),
                        'message': f"GitHub service reinitialization failed: {str(e)}"
                    })
                    return jsonify({"error": f"Failed to update GitHub settings: {str(e)}"}), 400

        return jsonify({"message": "Settings updated successfully"}), 200
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        error_logs.append({
            'timestamp': datetime.now().isoformat(),
            'message': f"Settings update error: {str(e)}"
        })
        return jsonify({"error": f"Failed to update settings: {str(e)}"}), 500

@app.route("/api/settings/clear-errors", methods=["POST"])
def api_clear_errors():
    try:
        global error_logs
        error_logs = []
        return jsonify({"message": "Error logs cleared successfully"}), 200
    except Exception as e:
        logger.error(f"Failed to clear errors: {e}")
        return jsonify({"error": f"Failed to clear errors: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
        if analysis_id not in active_analyses:
            return jsonify({"error": "Analysis not found"}), 404

        status_data = active_analyses[analysis_id].copy()
