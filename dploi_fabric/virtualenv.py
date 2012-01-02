from fabric.operations import run as do_run
from fabric.api import task
from .utils import config

@task
def update():
    """
    updates a virtualenv (pip install requirements.txt)
    """
    do_run('cd %(path)s; bin/pip install -r requirements.txt' % config.sites["main"].deployment)

@task
def create():
    """
    creates a virtualenv and calls update
    """
    do_run('cd %(path)s; virtualenv . ' % config.sites["main"].deployment)
    update()
