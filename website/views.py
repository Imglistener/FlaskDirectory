from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime

from . import db
from .models import User, UserRole, Students, Gender, StudentStatus, Room, AbsenceNotice
from .permissions import roles_required

views = Blueprint('views', __name__)


def _parse_optional_date(field_name, form):
    """Parse an optional YYYY-MM-DD form field. Returns (date_or_None, error_message)."""
    raw = form.get(field_name)
    if not raw:
        return None, None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date(), None
    except ValueError:
        return None, f'Please provide a valid {field_name.replace("_", " ")}.'


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
    absences = AbsenceNotice.query.order_by(AbsenceNotice.date.desc()).all()
    # Accounts eligible to be linked to a student record: STUDENT-role
    # accounts that don't already have a student profile attached.
    unlinked_users = [
        u for u in users if u.account_type == UserRole.STUDENT and u.student_profile is None
    ]
    return render_template(
        "dashboard_admin.html",
        user=current_user,
        students=students,
        users=users,
        rooms=rooms,
        absences=absences,
        unlinked_users=unlinked_users,
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

    check_in_date, err = _parse_optional_date('check_in_date', request.form)
    if err:
        flash(err, category='error')
        return redirect(url_for('views.dashboard_admin'))

    check_out_date, err = _parse_optional_date('check_out_date', request.form)
    if err:
        flash(err, category='error')
        return redirect(url_for('views.dashboard_admin'))

    # Optionally link this new record to an existing STUDENT-role account
    # that isn't linked to a student profile yet.
    linked_user_id = None
    raw_user_id = request.form.get('user_id')
    if raw_user_id:
        linked_user = User.query.get(int(raw_user_id))
        if not linked_user:
            flash('Selected account could not be found.', category='error')
            return redirect(url_for('views.dashboard_admin'))
        if linked_user.student_profile is not None:
            flash(f'{linked_user.first_name} is already linked to a student record.', category='error')
            return redirect(url_for('views.dashboard_admin'))
        linked_user_id = linked_user.id

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
        address=request.form.get('address'),
        nationality=request.form.get('nationality'),
        home_town=request.form.get('home_town'),
        emergency_contact=request.form.get('emergency_contact'),
        emergency_phone=request.form.get('emergency_phone'),
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        user_id=linked_user_id,
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
    student.nationality = request.form.get('nationality', student.nationality)
    student.home_town = request.form.get('home_town', student.home_town)
    student.emergency_contact = request.form.get('emergency_contact', student.emergency_contact)
    student.emergency_phone = request.form.get('emergency_phone', student.emergency_phone)

    check_in_date, err = _parse_optional_date('check_in_date', request.form)
    if err:
        flash(err, category='error')
        return redirect(url_for('views.dashboard_admin'))
    if 'check_in_date' in request.form:
        student.check_in_date = check_in_date

    check_out_date, err = _parse_optional_date('check_out_date', request.form)
    if err:
        flash(err, category='error')
        return redirect(url_for('views.dashboard_admin'))
    if 'check_out_date' in request.form:
        student.check_out_date = check_out_date

    status_value = request.form.get('status')
    if status_value:
        student.status = StudentStatus(status_value)

    # Re-link (or unlink) the account tied to this student record.
    raw_user_id = request.form.get('user_id', '')
    current_user_id = str(student.user_id) if student.user_id else ''
    if raw_user_id != current_user_id:
        if raw_user_id:
            linked_user = User.query.get(int(raw_user_id))
            if not linked_user:
                flash('Selected account could not be found.', category='error')
                return redirect(url_for('views.dashboard_admin'))
            if linked_user.student_profile is not None and linked_user.student_profile.id != student.id:
                flash(f'{linked_user.first_name} is already linked to another student record.', category='error')
                return redirect(url_for('views.dashboard_admin'))
            student.user_id = linked_user.id
        else:
            student.user_id = None

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
# Absence notices (Supervisor only — dismiss). Submission lives under
# the Student section below; both Supervisor and Overseer can view them.
# ---------------------------------------------------------------------

@views.route('/dashboard/admin/absences/<int:notice_id>/delete', methods=['POST'])
@login_required
@roles_required(UserRole.ADMIN)
def delete_absence_notice(notice_id):
    notice = AbsenceNotice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash('Absence notice removed.', category='success')
    return redirect(url_for('views.dashboard_admin'))


# ---------------------------------------------------------------------
# Overseer (Moderator) — read-only access to all student data.
# ---------------------------------------------------------------------

@views.route('/dashboard/moderator')
@login_required
@roles_required(UserRole.MODERATOR)
def dashboard_moderator():
    students = Students.query.order_by(Students.name).all()
    absences = AbsenceNotice.query.order_by(AbsenceNotice.date.desc()).all()
    return render_template("dashboard_moderator.html", user=current_user, students=students, absences=absences)


# ---------------------------------------------------------------------
# Normal user — can only see and edit their own linked student record,
# and can submit absence notices tied to that record.
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

    absences = AbsenceNotice.query.filter_by(student_id=profile.id).order_by(AbsenceNotice.date.desc()).all() if profile else []
    return render_template("dashboard_student.html", user=current_user, profile=profile, absences=absences)


@views.route('/dashboard/student/absences/add', methods=['POST'])
@login_required
@roles_required(UserRole.STUDENT)
def add_absence_notice():
    profile = Students.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('No student profile is linked to your account yet. Contact an administrator.', category='error')
        return redirect(url_for('views.dashboard_student'))

    try:
        absence_date = datetime.strptime(request.form.get('date', ''), '%Y-%m-%d').date()
    except ValueError:
        flash('Please provide a valid date for the absence.', category='error')
        return redirect(url_for('views.dashboard_student'))

    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for the absence.', category='error')
        return redirect(url_for('views.dashboard_student'))

    db.session.add(AbsenceNotice(student_id=profile.id, date=absence_date, reason=reason))
    db.session.commit()
    flash('Absence notice submitted.', category='success')
    return redirect(url_for('views.dashboard_student'))
