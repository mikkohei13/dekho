from pathlib import Path

from flask import Flask, render_template

from .db import init_db
from .scan import run_scan


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/scan")
    def scan() -> str:
        scan_result = run_scan(Path("./music"))
        return render_template("scan_result.html", **scan_result)

    return app
