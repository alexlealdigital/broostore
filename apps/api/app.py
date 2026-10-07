from broostore_api import create_app

app = create_app()

if __name__ == "__main__":  # execução local: python app.py (o Render usa: gunicorn app:app)
    from broostore_api.config import get_settings
    app.run(host="0.0.0.0", port=get_settings().port, debug=False)
