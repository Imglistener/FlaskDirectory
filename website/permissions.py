from functools import wraps
from flask import abort
from flask_login import current_user


def roles_required(*roles):
    """Restrict a view to users whose account_type is one of `roles`."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.account_type not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
