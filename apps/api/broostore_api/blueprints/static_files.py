"""Arquivos estáticos (as páginas HTML/JS/CSS da loja antiga) servidos pelo Flask."""
from flask import Blueprint, send_from_directory

from ..config import STATIC_DIR

bp = Blueprint("static_files", __name__)


@bp.route("/")
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@bp.route("/<path:path>")
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)
