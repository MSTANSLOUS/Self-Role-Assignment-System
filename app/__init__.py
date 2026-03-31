from flask import Flask
from .routes import routes_pb
from config import Config
from .models import db  # This is good


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        # ⚠️ IMPORTANT: Import models here to ensure they're registered
        from .models import User, Role  # ⚠️ ADD THIS LINE
        db.create_all()  # Now tables will be created

    app.register_blueprint(routes_pb)
    return app