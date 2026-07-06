from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime

from . import db
from .models import User, UserRole, Students, Gender, StudentStatus, Room
from .permissions import roles_required

views = Blueprint('views', __name__)


@views.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))
    return render_template("home.html", user=current_user)


@views.route('/dashboard')
@login_required
def dashboard():
    """Send each user to the dashboard that matches their role."""
    if current_user.account_type == UserRole.ADMIN:
        return redirect(url_for('views.dashboard_admin'))
    elif current_user.account_type == UserRole.MODERATOR:
        return redirect(url_for('views.dashboard_moderator'))
    else:
        return redirect(url_for('views.dashboard_student'))


# ---------------------------------------------------------------------
# Supervisor (Admin) — full read/write access to all student data,
# plus the ability to change what role any account has.
# ---------------------------------------------------------------------

@views.route('/dashboard/admin')
@login_required
@roles_required(UserRole.ADMIN)
def dashboard_admin():
    students = Students.query.order_by(Students.name).all()
    users = User.query.order_by(User.first_name).all()
    rooms = Room.query.order_by(Room.name).all()
    return render_template(
        "dashboard_admin.html",
        user=current_user,
        students=students,
        users=users,
        rooms=rooms,
        Gender=Gender,
        StudentStatus=StudentStatus,
        UserRole=UserRole,
    )


@views.route('/dashboard/admin/students/add', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def add_student():
    try:
        birth_date = datetime.strptime(request.form.get('birth_date', ''), '%Y-%m-%d').date()
    except ValueError:
        flash('Please provide a valid birth date.', category='error')
        return redirect(url_for('views.dashboard_admin'))

    new_student = Students(
        name=request.form.get('name'),
        student_code=request.form.get('student_code'),
        internal_number=request.form.get('internal_number'),
        level_and_section=request.form.get('level_and_section'),
        national_id=request.form.get('national_id'),
        sex=Gender(request.form.get('sex')),
        birth_date=birth_date,
        email=request.form.get('email') or None,
        phone=request.form.get('phone'),
    )
    db.session.add(new_student)
    db.session.commit()
    flash('Student added successfully.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/students/<int:student_id>/edit', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def edit_student(student_id):
    student = Students.query.get_or_404(student_id)
    student.name = request.form.get('name', student.name)
    student.student_code = request.form.get('student_code', student.student_code)
    student.internal_number = request.form.get('internal_number', student.internal_number)
    student.level_and_section = request.form.get('level_and_section', student.level_and_section)
    student.phone = request.form.get('phone', student.phone)
    student.email = request.form.get('email') or student.email
    student.address = request.form.get('address', student.address)

    status_value = request.form.get('status')
    if status_value:
        student.status = StudentStatus(status_value)

    db.session.commit()
    flash('Student record updated.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/students/<int:student_id>/delete', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def delete_student(student_id):
    student = Students.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash('Student record deleted.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def update_user_role(user_id):
    target_user = User.query.get_or_404(user_id)
    new_role = request.form.get('account_type')

    if target_user.id == current_user.id:
        flash("You can't change your own role.", category='error')
        return redirect(url_for('views.dashboard_admin'))

    try:
        target_user.account_type = UserRole[new_role]
        db.session.commit()
        flash(f'{target_user.first_name} is now a {target_user.account_type.value}.', category='success')
    except KeyError:
        flash('Unknown role.', category='error')

    return redirect(url_for('views.dashboard_admin'))


# ---------------------------------------------------------------------
# Room management (Supervisor only) — create rooms, edit them, assign
# or remove students manually, and auto-sort unassigned students into
# rooms that match their sex and still have free capacity.
# ---------------------------------------------------------------------

@views.route('/dashboard/admin/rooms/add', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def add_room():
    name = request.form.get('name')
    sex = request.form.get('sex')
    max_occupancy = request.form.get('max_occupancy')

    if not name or not sex or not max_occupancy:
        flash('Please fill in all room fields.', category='error')
        return redirect(url_for('views.dashboard_admin'))

    try:
        max_occupancy = int(max_occupancy)
        if max_occupancy < 1:
            raise ValueError
    except ValueError:
        flash('Max occupancy must be a positive whole number.', category='error')
        return redirect(url_for('views.dashboard_admin'))

    db.session.add(Room(name=name, sex=Gender(sex), max_occupancy=max_occupancy))
    db.session.commit()
    flash('Room added successfully.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/rooms/<int:room_id>/edit', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    room.name = request.form.get('name', room.name)

    sex_value = request.form.get('sex')
    if sex_value:
        room.sex = Gender(sex_value)

    max_occupancy = request.form.get('max_occupancy')
    if max_occupancy:
        try:
            max_occupancy = int(max_occupancy)
        except ValueError:
            flash('Max occupancy must be a number.', category='error')
            return redirect(url_for('views.dashboard_admin'))
        if max_occupancy < room.occupant_count:
            flash(
                f'Room has {room.occupant_count} student(s) assigned; '
                f'max occupancy cannot be set lower than that.',
                category='error',
            )
            return redirect(url_for('views.dashboard_admin'))
        room.max_occupancy = max_occupancy

    db.session.commit()
    flash('Room updated.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    for student in room.students:
        student.room_id = None
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted. Any assigned students were unassigned.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/rooms/<int:room_id>/assign', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def assign_student_to_room(room_id):
    room = Room.query.get_or_404(room_id)
    student_id = request.form.get('student_id')

    if not student_id:
        flash('Please select a student to assign.', category='error')
        return redirect(url_for('views.dashboard_admin'))

    student = Students.query.get_or_404(int(student_id))

    if student.sex != room.sex:
        flash(f'{student.name} cannot be assigned to a {room.sex.value} room.', category='error')
        return redirect(url_for('views.dashboard_admin'))

    if room.is_full:
        flash(f'Room "{room.name}" is already at full occupancy.', category='error')
        return redirect(url_for('views.dashboard_admin'))

    student.room_id = room.id
    db.session.commit()
    flash(f'{student.name} assigned to "{room.name}".', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/rooms/<int:room_id>/remove/<int:student_id>', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def remove_student_from_room(room_id, student_id):
    student = Students.query.get_or_404(student_id)
    if student.room_id == room_id:
        student.room_id = None
        db.session.commit()
        flash(f'{student.name} removed from room.', category='success')
    return redirect(url_for('views.dashboard_admin'))


@views.route('/dashboard/admin/rooms/auto-sort', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def auto_sort_students():
    unassigned = Students.query.filter_by(room_id=None).order_by(Students.name).all()
    rooms = Room.query.all()

    assigned_count = 0
    skipped = []

    for student in unassigned:
        target_room = next(
            (r for r in rooms if r.sex == student.sex and r.occupant_count < r.max_occupancy),
            None
        )
        if target_room:
            target_room.students.append(student)  # keeps occupant_count in sync in-memory too
            assigned_count += 1
        else:
            skipped.append(student.name)

    db.session.commit()

    if assigned_count:
        flash(f'Auto-sorted {assigned_count} student(s) into rooms.', category='success')
    if skipped:
        flash(f'No available room for: {", ".join(skipped)}.', category='error')
    if not unassigned:
        flash('No unassigned students to sort.', category='success')

    return redirect(url_for('views.dashboard_admin'))


# ---------------------------------------------------------------------
# Overseer (Moderator) — read-only access to all student data.
# ---------------------------------------------------------------------

@views.route('/dashboard/moderator')
@login_required
@roles_required(UserRole.MODERATOR)
def dashboard_moderator():
    students = Students.query.order_by(Students.name).all()
    return render_template("dashboard_moderator.html", user=current_user, students=students)


# ---------------------------------------------------------------------
# Normal user — can only see and edit their own linked student record.
# ---------------------------------------------------------------------

@views.route('/dashboard/student', methods=['GET', 'POST'])
@login_required
@roles_required(UserRole.STUDENT)
def dashboard_student():
    profile = Students.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        if not profile:
            flash('No student profile is linked to your account yet. Contact an administrator.', category='error')
            return redirect(url_for('views.dashboard_student'))

        # Normal users may only update their own contact-type details,
        # not identity fields like name/student code/national ID.
        profile.phone = request.form.get('phone', profile.phone)
        profile.address = request.form.get('address', profile.address)
        profile.emergency_contact = request.form.get('emergency_contact', profile.emergency_contact)
        profile.emergency_phone = request.form.get('emergency_phone', profile.emergency_phone)
        db.session.commit()
        flash('Your information has been updated.', category='success')
        return redirect(url_for('views.dashboard_student'))

    return render_template("dashboard_student.html", user=current_user, profile=profile)