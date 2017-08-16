from functools import wraps

from flask import abort
from flask_login import current_user


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    from .models import Permission
    return permission_required(Permission.ADMINISTER)(f)


def require_instance(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        if not self._get_pk_value():
            raise TypeError(
                "Can't call %s with a non-instance %s" % (
                    func.__name__, self.__class__.__name__))
        return func(self, *args, **kwargs)
    return inner
