from flask import Blueprint

members = Blueprint('members', __name__)

from . import views
