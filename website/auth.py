from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_babel import gettext as _
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, UserRole
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if password:
                if check_password_hash(user.password, password):
                    flash(_('Logged in succesfully!'), category="success")
                    login_user(user, remember=True)
                    return redirect(url_for('views.dashboard'))
                else:
                    flash(_('Incorrect password, try again.'), category='error')
            else:
                # BUG FIX: previously a blank password silently fell through
                # with no flash message and just re-rendered the page.
                flash(_('Please enter your password.'), category='error')
        else:
            flash(_('There is no account by that Email.'), category='error')

    return render_template("login.html")

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        # Validation
        if not email or not first_name or not last_name or not password1 or not password2:
            flash(_('All fields are required.'), category='error')
        elif len(email) < 4:
            flash(_('Email must be at least 4 characters long.'), category='error')
        elif len(first_name) < 2:
            flash(_('First name must be at least 2 characters long.'), category='error')
        elif len(last_name) < 2:
            flash(_('Last name must be at least 2 characters long.'), category='error')
        elif len(password1) < 7:
            flash(_('Password must be at least 7 characters long.'), category='error')
        elif password1 != password2:
            flash(_('Passwords do not match.'), category='error')
        else:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash(_('Email already exists. Please log in or use a different email.'), category='error')
            else:
                # BUG FIX: account_type is a required (non-nullable) column
                # on User, but it was never being set here, so every signup
                # attempt raised an IntegrityError before this fix.
                #
                # Public signup always creates a normal "User" account.
                # The very first account in the whole app is bootstrapped
                # as the Supervisor (admin) so there's always a way in.
                is_first_user = User.query.count() == 0
                new_user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=generate_password_hash(password1),
                    account_type=UserRole.ADMIN if is_first_user else UserRole.STUDENT
                )
                db.session.add(new_user)
                db.session.commit()
                if is_first_user:
                    flash(_('Account created as the Supervisor (admin) account! You can now log in.'), category='success')
                else:
                    flash(_('Account created successfully! You can now log in.'), category='success')
                return redirect(url_for('auth.login'))

    return render_template("signup.html")
