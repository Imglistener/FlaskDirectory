from flask import Flask, render_template, session, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "database.db"

# Supported UI languages. Add new entries here (code -> display name) and
# drop a matching translations/<code>/LC_MESSAGES/messages.po file to add
# another language later.
LANGUAGES = {
    'en': 'English',
    'fr': 'Français',
}


def get_locale():
    # 1) explicit choice stored in the session (set via /language/<code>)
    lang = session.get('lang')
    if lang in LANGUAGES:
        return lang
    # 2) fall back to the browser's preferred language
    return request.accept_languages.best_match(LANGUAGES.keys()) or 'en'


def create_app() -> Flask:
    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = 'DirectoryApp'

    # --- Internationalization -------------------------------------------------
    app.config['LANGUAGES'] = LANGUAGES
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = path.join(
        path.dirname(path.abspath(__file__)), 'translations'
    )
    Babel(app, locale_selector=get_locale)

    # Make the current language + language list available to every template
    # without having to pass them into each render_template() call.
    @app.context_processor
    def inject_locale():
        return dict(current_lang=get_locale(), available_languages=LANGUAGES)

    @app.route('/language/<lang_code>')
    def set_language(lang_code):
        if lang_code in LANGUAGES:
            session['lang'] = lang_code
        # Send the user back to whatever page they were on.
        return redirect(request.referrer or url_for('views.home'))
    # ---------------------------------------------------------------------

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
