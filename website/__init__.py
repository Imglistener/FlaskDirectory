from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app() -> Flask:
    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = 'DirectoryApp'

    from .views import views
    from .auth import auth

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # AbsenceNotice was added, so it's imported here alongside the rest of
    # the models to make sure db.create_all() below picks up its table too.
    from .models import User, Room, Students, AbsenceNotice
    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'  # type: ignore
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    return app

def create_database(app):
    db_path = path.join(path.dirname(path.abspath(__file__)), DB_NAME)
    if not path.exists(db_path):
        with app.app_context():
            db.create_all()
        print('create_database')
