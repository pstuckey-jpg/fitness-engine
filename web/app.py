"""Mobile-friendly web foundation for the fitness insight engine."""

from __future__ import annotations

import os
from functools import wraps
from typing import Callable

from flask import Flask, redirect, render_template, request, session, url_for

from core import add_entry, compute_trends, generate_brief, generate_weekly_summary
from core.auth import authenticate_user, signup_user
from core.profile import load_profile, save_profile
from core.storage import DEFAULT_USER_ID, get_user, load_entries


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-fitness-insight-session-key")
    demo_auto_login = os.environ.get("DEMO_AUTO_LOGIN", "true").lower() in {"1", "true", "yes"}

    def current_user_id() -> str:
        if demo_auto_login:
            session.setdefault("user_id", DEFAULT_USER_ID)
        return session["user_id"]

    def login_required(view: Callable):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                if demo_auto_login:
                    session["user_id"] = DEFAULT_USER_ID
                    return view(*args, **kwargs)
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped_view

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        error = None
        if request.method == "POST":
            user, error = signup_user(request.form.get("email", ""), request.form.get("password", ""))
            if user:
                session.clear()
                session["user_id"] = user["user_id"]
                return redirect(url_for("profile"))
        return render_template("auth.html", mode="signup", error=error)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            user, error = authenticate_user(request.form.get("email", ""), request.form.get("password", ""))
            if user:
                session.clear()
                session["user_id"] = user["user_id"]
                return redirect(url_for("daily_entry"))
        return render_template("auth.html", mode="login", error=error)

    @app.get("/logout")
    def logout():
        session.clear()
        if demo_auto_login:
            return redirect(url_for("daily_entry"))
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def daily_entry() -> str:
        return render_template("daily.html", user_id=current_user_id())

    @app.post("/entries")
    @app.post("/add_entry")
    @login_required
    def create_entry():
        raw_text = request.form.get("raw_text", "").strip()
        if raw_text:
            add_entry(raw_text, user_id=current_user_id())
        return redirect(url_for("brief"))

    @app.get("/brief")
    @login_required
    def brief() -> str:
        user_id = current_user_id()
        return render_template("brief.html", brief=generate_brief(user_id=user_id), user_id=user_id)

    @app.get("/history")
    @login_required
    def history() -> str:
        user_id = current_user_id()
        entries = reversed(load_entries(user_id=user_id))
        return render_template("history.html", entries=entries, user_id=user_id)

    @app.get("/weekly")
    @login_required
    def weekly() -> str:
        user_id = current_user_id()
        return render_template("weekly.html", summary=generate_weekly_summary(user_id=user_id), trends=compute_trends(user_id=user_id), user_id=user_id)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile() -> str:
        user_id = current_user_id()
        if request.method == "POST":
            profile_data = {
                "calorie_target": request.form.get("calorie_target", ""),
                "protein_target": request.form.get("protein_target", ""),
                "goal_direction": request.form.get("goal_direction", ""),
                "diet_preferences": request.form.get("diet_preferences", ""),
                "equipment": request.form.get("equipment", ""),
                "injuries": request.form.get("injuries", ""),
            }
            save_profile(profile_data, user_id=user_id)
            return redirect(url_for("profile"))
        return render_template("profile.html", profile=load_profile(user_id=user_id), user_id=user_id)

    @app.get("/settings")
    @login_required
    def settings() -> str:
        return render_template("settings.html", user_id=current_user_id())

    @app.get("/account")
    @login_required
    def account() -> str:
        user_id = current_user_id()
        user = get_user(user_id) or {"user_id": user_id, "email": "demo@local", "created_at": "Demo account"}
        return render_template("account.html", user=user)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
