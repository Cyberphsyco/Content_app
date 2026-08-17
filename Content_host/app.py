from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from google import genai
from google.genai import types

from dotenv import load_dotenv

from functools import wraps
from datetime import datetime, timedelta

from email.message import EmailMessage

import os
import json
import re
import secrets
import smtplib


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)


# =========================================================
# DATABASE CONFIG
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is missing from your .env file"
    )

# Some hosting platforms may provide postgres://
# instead of postgresql://
if DATABASE_URL.startswith("postgres://"):

    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# GEMINI
# =========================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

if not GEMINI_API_KEY:

    raise ValueError(
        "GEMINI_API_KEY is missing from your .env file"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL = "gemini-3.6-flash"


# =========================================================
# DATABASE MODELS
# =========================================================

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    niche = db.Column(
        db.String(150),
        default=""
    )

    audience = db.Column(
        db.String(255),
        default=""
    )

    platform = db.Column(
        db.String(100),
        default=""
    )

    goal = db.Column(
        db.String(255),
        default=""
    )

    reset_code = db.Column(
        db.String(10),
        nullable=True
    )

    reset_code_expires = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    contents = db.relationship(
        "Content",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    ideas = db.relationship(
        "ContentIdea",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Content(db.Model):

    __tablename__ = "contents"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=False
    )

    hook = db.Column(
        db.Text,
        nullable=False
    )

    body = db.Column(
        db.Text,
        nullable=False
    )

    cta = db.Column(
        db.Text,
        nullable=False
    )

    platform = db.Column(
        db.String(100),
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class ContentIdea(db.Model):

    __tablename__ = "content_ideas"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=False
    )

    description = db.Column(
        db.Text,
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():

    db.create_all()


# =========================================================
# EMAIL VALIDATION
# =========================================================

def valid_email(email):

    pattern = (
        r"^[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+"
        r"\.[A-Za-z]{2,}$"
    )

    return re.match(
        pattern,
        email
    ) is not None


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:

        return None

    try:

        return db.session.get(
            User,
            int(user_id)
        )

    except (
        ValueError,
        TypeError
    ):

        return None


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        user = get_current_user()

        if user is None:

            session.clear()

            if request.path.startswith(
                "/generate"
            ):

                return jsonify({

                    "success": False,

                    "error":
                        "Your session has expired. "
                        "Please log in again."

                }), 401

            flash(
                "Please log in to continue.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# =========================================================
# SEND PASSWORD RESET EMAIL
# =========================================================

def send_reset_email(
    email,
    code
):

    sender = os.getenv(
        "MAIL_USERNAME"
    )

    password = os.getenv(
        "MAIL_PASSWORD"
    )

    if not sender or not password:

        raise ValueError(
            "MAIL_USERNAME or MAIL_PASSWORD is missing."
        )


    message = EmailMessage()

    message["Subject"] = (
        "ContentAI Password Reset Code"
    )

    message["From"] = sender

    message["To"] = email


    message.set_content(
        f"""
ContentAI Password Reset

We received a request to reset your ContentAI password.

Your verification code is:

{code}

This code expires in 10 minutes.

If you did not request this password reset,
you can safely ignore this email.

ContentAI
"""
    )


    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as server:

        server.starttls()

        server.login(
            sender,
            password
        )

        server.send_message(
            message
        )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    user = get_current_user()

    if user:

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "index.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if get_current_user():

        return redirect(
            url_for("dashboard")
        )


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        niche = request.form.get(
            "niche",
            ""
        ).strip()

        audience = request.form.get(
            "audience",
            ""
        ).strip()

        platform = request.form.get(
            "platform",
            ""
        ).strip()

        goal = request.form.get(
            "goal",
            ""
        ).strip()


        if not username or not email or not password:

            flash(
                "Please fill in all required fields.",
                "error"
            )

            return render_template(
                "register.html"
            )


        if not valid_email(email):

            flash(
                "Please enter a valid email address.",
                "error"
            )

            return render_template(
                "register.html"
            )


        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )


        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "register.html"
            )


        if User.query.filter_by(
            username=username
        ).first():

            flash(
                "Username already exists.",
                "error"
            )

            return render_template(
                "register.html"
            )


        if User.query.filter_by(
            email=email
        ).first():

            flash(
                "Email already exists.",
                "error"
            )

            return render_template(
                "register.html"
            )


        try:

            user = User(

                username=username,

                email=email,

                password=generate_password_hash(
                    password
                ),

                niche=niche,

                audience=audience,

                platform=platform,

                goal=goal

            )


            db.session.add(
                user
            )

            db.session.commit()


            session.clear()

            session["user_id"] = user.id


            flash(
                "Account created successfully.",
                "success"
            )


            return redirect(
                url_for("dashboard")
            )


        except Exception as e:

            db.session.rollback()

            print(
                "REGISTER ERROR:",
                e
            )

            flash(
                "Could not create your account.",
                "error"
            )


    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if get_current_user():

        return redirect(
            url_for("dashboard")
        )


    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        user = User.query.filter_by(
            email=email
        ).first()


        if not user:

            flash(
                "Invalid email or password.",
                "error"
            )

            return render_template(
                "login.html"
            )


        if not check_password_hash(
            user.password,
            password
        ):

            flash(
                "Invalid email or password.",
                "error"
            )

            return render_template(
                "login.html"
            )


        session.clear()

        session["user_id"] = user.id


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        if not valid_email(email):

            flash(
                "Please enter a valid email.",
                "error"
            )

            return render_template(
                "forgot_password.html"
            )


        user = User.query.filter_by(
            email=email
        ).first()


        if not user:

            flash(
                "No account was found with that email.",
                "error"
            )

            return render_template(
                "forgot_password.html"
            )


        code = str(
            secrets.randbelow(
                900000
            ) + 100000
        )


        user.reset_code = code

        user.reset_code_expires = (
            datetime.utcnow()
            + timedelta(minutes=10)
        )


        db.session.commit()


        try:

            send_reset_email(
                email,
                code
            )


        except Exception as e:

            print(
                "EMAIL ERROR:",
                e
            )


            user.reset_code = None

            user.reset_code_expires = None

            db.session.commit()


            flash(
                "Could not send the reset email.",
                "error"
            )

            return render_template(
                "forgot_password.html"
            )


        session["reset_email"] = email

        session.pop(
            "reset_verified",
            None
        )


        flash(
            "Reset code sent to your email.",
            "success"
        )


        return redirect(
            url_for(
                "verify_reset_code"
            )
        )


    return render_template(
        "forgot_password.html"
    )


# =========================================================
# VERIFY RESET CODE
# =========================================================

@app.route(
    "/verify-reset-code",
    methods=["GET", "POST"]
)
def verify_reset_code():

    email = session.get(
        "reset_email"
    )


    if not email:

        return redirect(
            url_for(
                "forgot_password"
            )
        )


    user = User.query.filter_by(
        email=email
    ).first()


    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        code = request.form.get(
            "code",
            ""
        ).strip()


        if not user.reset_code:

            flash(
                "No reset code exists.",
                "error"
            )

            return render_template(
                "verify_reset_code.html"
            )


        if not user.reset_code_expires:

            flash(
                "Reset code has expired.",
                "error"
            )

            return redirect(
                url_for(
                    "forgot_password"
                )
            )


        if datetime.utcnow() > user.reset_code_expires:

            user.reset_code = None

            user.reset_code_expires = None

            db.session.commit()


            flash(
                "Reset code has expired.",
                "error"
            )

            return redirect(
                url_for(
                    "forgot_password"
                )
            )


        if code != user.reset_code:

            flash(
                "Invalid reset code.",
                "error"
            )

            return render_template(
                "verify_reset_code.html"
            )


        session["reset_verified"] = True


        return redirect(
            url_for(
                "reset_password"
            )
        )


    return render_template(
        "verify_reset_code.html"
    )


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route(
    "/reset-password",
    methods=["GET", "POST"]
)
def reset_password():

    email = session.get(
        "reset_email"
    )

    verified = session.get(
        "reset_verified"
    )


    if not email or not verified:

        return redirect(
            url_for(
                "forgot_password"
            )
        )


    user = User.query.filter_by(
        email=email
    ).first()


    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return render_template(
                "reset_password.html"
            )


        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "reset_password.html"
            )


        user.password = generate_password_hash(
            password
        )

        user.reset_code = None

        user.reset_code_expires = None


        db.session.commit()


        session.clear()


        flash(
            "Password reset successfully.",
            "success"
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "reset_password.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = get_current_user()


    scripts_count = Content.query.filter_by(
        user_id=user.id
    ).count()


    ideas_count = ContentIdea.query.filter_by(
        user_id=user.id
    ).count()


    recent_scripts = Content.query.filter_by(
        user_id=user.id
    ).order_by(
        Content.created_at.desc()
    ).limit(5).all()


    return render_template(
        "dashboard.html",
        user=user,
        scripts_count=scripts_count,
        ideas_count=ideas_count,
        recent_scripts=recent_scripts
    )


# =========================================================
# SETTINGS
# =========================================================

@app.route(
    "/settings",
    methods=["GET", "POST"]
)
@login_required
def settings():

    user = get_current_user()


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        niche = request.form.get(
            "niche",
            ""
        ).strip()

        audience = request.form.get(
            "audience",
            ""
        ).strip()

        platform = request.form.get(
            "platform",
            ""
        ).strip()

        goal = request.form.get(
            "goal",
            ""
        ).strip()


        if not username:

            flash(
                "Username cannot be empty.",
                "error"
            )

            return redirect(
                url_for("settings")
            )


        existing = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()


        if existing:

            flash(
                "That username is already taken.",
                "error"
            )

            return redirect(
                url_for("settings")
            )


        user.username = username

        user.niche = niche

        user.audience = audience

        user.platform = platform

        user.goal = goal


        db.session.commit()


        flash(
            "Profile updated successfully.",
            "success"
        )


        return redirect(
            url_for("settings")
        )


    return render_template(
        "settings.html",
        user=user
    )


# =========================================================
# IDEAS
# =========================================================

@app.route("/ideas")
@login_required
def ideas():

    user = get_current_user()


    saved_ideas = ContentIdea.query.filter_by(
        user_id=user.id
    ).order_by(
        ContentIdea.created_at.desc()
    ).all()


    return render_template(
        "ideas.html",
        user=user,
        ideas=saved_ideas
    )


# =========================================================
# GENERATE IDEAS
# =========================================================

@app.route(
    "/generate-ideas",
    methods=["POST"]
)
@login_required
def generate_ideas():

    user = get_current_user()


    data = request.get_json(
        silent=True
    ) or {}


    niche = str(
        data.get("niche")
        or user.niche
        or ""
    ).strip()


    audience = str(
        data.get("audience")
        or user.audience
        or ""
    ).strip()


    platform = str(
        data.get("platform")
        or user.platform
        or ""
    ).strip()


    goal = str(
        data.get("goal")
        or user.goal
        or ""
    ).strip()


    if not niche:

        return jsonify({

            "success": False,

            "error":
                "Please set your niche first."

        }), 400


    prompt = f"""
You are an expert social media content strategist.

Generate 10 highly specific content ideas.

Creator niche:
{niche}

Target audience:
{audience}

Platform:
{platform}

Creator goal:
{goal}

Make every idea specific to the niche.

Avoid generic ideas.

Return ONLY valid JSON.

Format:

[
    {{
        "title": "Content idea",
        "description": "Short explanation"
    }}
]

Do not use markdown.
Do not use asterisks.
"""


    try:

        response = client.models.generate_content(

            model=MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                temperature=0.9

            )
        )


        raw = response.text.strip()


        raw = re.sub(
            r"```json",
            "",
            raw,
            flags=re.IGNORECASE
        )

        raw = re.sub(
            r"```",
            "",
            raw
        ).strip()


        ideas_data = json.loads(
            raw
        )


        if not isinstance(
            ideas_data,
            list
        ):

            raise ValueError(
                "Invalid AI response."
            )


        saved = []


        for idea in ideas_data:

            title = str(
                idea.get(
                    "title",
                    "Untitled"
                )
            ).strip()


            description = str(
                idea.get(
                    "description",
                    ""
                )
            ).strip()


            if not title:

                continue


            new_idea = ContentIdea(

                user_id=user.id,

                title=title,

                description=description

            )


            db.session.add(
                new_idea
            )


            saved.append({

                "title": title,

                "description": description

            })


        db.session.commit()


        return jsonify({

            "success": True,

            "ideas": saved

        })


    except Exception as e:

        db.session.rollback()

        print(
            "IDEAS GENERATION ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "error":
                "Could not generate content ideas."

        }), 500


# =========================================================
# SCRIPT PAGE
# =========================================================

@app.route("/script")
@login_required
def script():

    user = get_current_user()


    return render_template(
        "script.html",
        user=user
    )


# =========================================================
# GENERATE SCRIPT
# =========================================================

@app.route(
    "/generate-script",
    methods=["POST"]
)
@login_required
def generate_script():

    user = get_current_user()


    data = request.get_json(
        silent=True
    ) or {}


    topic = str(
        data.get(
            "topic",
            ""
        )
    ).strip()


    if not topic:

        return jsonify({

            "success": False,

            "error":
                "Please enter a topic."

        }), 400


    niche = str(
        data.get("niche")
        or user.niche
        or ""
    ).strip()


    audience = str(
        data.get("audience")
        or user.audience
        or ""
    ).strip()


    platform = str(
        data.get("platform")
        or user.platform
        or ""
    ).strip()


    goal = str(
        data.get("goal")
        or user.goal
        or ""
    ).strip()


    prompt = f"""
You are an elite social media scriptwriter.

Create a detailed short-form content script.

Creator niche:
{niche}

Target audience:
{audience}

Platform:
{platform}

Creator goal:
{goal}

Topic:
{topic}

The script MUST contain exactly:

HOOK
BODY
CTA

HOOK:
Write a powerful attention-grabbing opening.

BODY:
Write a detailed script that sounds natural
when spoken by a real creator.

CTA:
Give one clear call to action.

The body should be the most detailed section.

Do not add extra sections.

Do not use asterisks.

Do not use markdown.

Return ONLY valid JSON:

{{
    "title": "Script title",
    "hook": "Hook",
    "body": "Detailed body",
    "cta": "CTA"
}}
"""


    try:

        response = client.models.generate_content(

            model=MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                temperature=0.8

            )
        )


        raw = response.text.strip()


        raw = re.sub(
            r"```json",
            "",
            raw,
            flags=re.IGNORECASE
        )

        raw = re.sub(
            r"```",
            "",
            raw
        ).strip()


        script_data = json.loads(
            raw
        )


        title = str(
            script_data.get(
                "title",
                topic
            )
        ).strip()


        hook = str(
            script_data.get(
                "hook",
                ""
            )
        ).strip()


        body = str(
            script_data.get(
                "body",
                ""
            )
        ).strip()


        cta = str(
            script_data.get(
                "cta",
                ""
            )
        ).strip()


        if not hook or not body or not cta:

            raise ValueError(
                "Incomplete script returned."
            )


        new_script = Content(

            user_id=user.id,

            title=title,

            hook=hook,

            body=body,

            cta=cta,

            platform=platform

        )


        db.session.add(
            new_script
        )

        db.session.commit()


        return jsonify({

            "success": True,

            "script": {

                "id": new_script.id,

                "title": title,

                "hook": hook,

                "body": body,

                "cta": cta,

                "platform": platform

            }

        })


    except json.JSONDecodeError:

        db.session.rollback()

        print(
            "INVALID SCRIPT JSON:",
            raw
        )


        return jsonify({

            "success": False,

            "error":
                "AI returned an invalid response. "
                "Try again."

        }), 500


    except Exception as e:

        db.session.rollback()

        print(
            "SCRIPT GENERATION ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "error":
                "Could not generate the script."

        }), 500


# =========================================================
# MY SCRIPTS
# =========================================================

@app.route("/scripts")
@login_required
def scripts():

    user = get_current_user()


    contents = Content.query.filter_by(
        user_id=user.id
    ).order_by(
        Content.created_at.desc()
    ).all()


    return render_template(
        "scripts.html",
        user=user,
        contents=contents
    )


# =========================================================
# GET ONE SCRIPT
# =========================================================

@app.route(
    "/content/<int:content_id>"
)
@login_required
def get_content(content_id):

    user = get_current_user()


    content = Content.query.filter_by(

        id=content_id,

        user_id=user.id

    ).first()


    if content is None:

        return jsonify({

            "success": False,

            "error":
                "Script not found."

        }), 404


    return jsonify({

        "success": True,

        "script": {

            "id": content.id,

            "title": content.title,

            "hook": content.hook,

            "body": content.body,

            "cta": content.cta,

            "platform": content.platform,

            "created_at":
                content.created_at.strftime(
                    "%d %b %Y %H:%M"
                )

        }

    })


# =========================================================
# DELETE SCRIPT
# =========================================================

@app.route(
    "/content/<int:content_id>/delete",
    methods=["POST"]
)
@login_required
def delete_content(content_id):

    user = get_current_user()


    content = Content.query.filter_by(

        id=content_id,

        user_id=user.id

    ).first()


    if content is None:

        return jsonify({

            "success": False,

            "error":
                "Script not found."

        }), 404


    try:

        db.session.delete(
            content
        )

        db.session.commit()


        return jsonify({

            "success": True

        })


    except Exception as e:

        db.session.rollback()

        print(
            "DELETE SCRIPT ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "error":
                "Could not delete script."

        }), 500


# =========================================================
# DELETE IDEA
# =========================================================

@app.route(
    "/idea/<int:idea_id>/delete",
    methods=["POST"]
)
@login_required
def delete_idea(idea_id):

    user = get_current_user()


    idea = ContentIdea.query.filter_by(

        id=idea_id,

        user_id=user.id

    ).first()


    if idea is None:

        return jsonify({

            "success": False,

            "error":
                "Idea not found."

        }), 404


    try:

        db.session.delete(
            idea
        )

        db.session.commit()


        return jsonify({

            "success": True

        })


    except Exception as e:

        db.session.rollback()

        print(
            "DELETE IDEA ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "error":
                "Could not delete idea."

        }), 500


# =========================================================
# CALENDAR
# =========================================================

@app.route("/calendar")
@login_required
def calendar():

    user = get_current_user()


    contents = Content.query.filter_by(
        user_id=user.id
    ).order_by(
        Content.created_at.asc()
    ).all()


    return render_template(
        "calendar.html",
        user=user,
        contents=contents
    )


# =========================================================
# ERROR PAGES
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(500)
def internal_error(error):

    db.session.rollback()

    return render_template(
        "500.html"
    ), 500


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )