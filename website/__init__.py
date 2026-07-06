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

    from .models import User, Room, Students  # Students was missing, so db.create_all() never made that table
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
    # BUG FIX: 'website/' + DB_NAME only worked if the process happened to be
    # launched from the exact parent directory of this package. Resolving
    # the path relative to this file makes it work regardless of cwd.
    db_path = path.join(path.dirname(path.abspath(__file__)), DB_NAME)
    if not path.exists(db_path):
        with app.app_context():
            db.create_all()
        print('create_database')
