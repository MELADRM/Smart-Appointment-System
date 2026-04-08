"""URL handlers split by role."""

from . import public as _public
from . import auth as _auth
from . import user as _user
from . import business as _business
from . import admin as _admin

def register_all(app):
    # Attach every route module to the given Flask app.
    _public.register(app)
    _auth.register(app)
    _user.register(app)
    _business.register(app)
    _admin.register(app)

__all__ = ['register_all']
