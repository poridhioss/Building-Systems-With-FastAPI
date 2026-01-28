from flask import Flask
from celery_utils import make_celery
from config import Config

def create_app(config_class=Config):
    """
    Application factory that creates and configures the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app

app = create_app()
celery = make_celery(app)

# IMPORTANT: Import tasks module so Celery worker registers the tasks
from app import tasks