from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'

    db.init_app(app)

    with app.app_context():
        from .routes import main_routes  # Импорт маршрутов в контексте приложения
        app.register_blueprint(main_routes.main)

        return app