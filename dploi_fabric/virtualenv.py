from fabric.operations import run as do_run
from fabric.api import task
from .utils import config

@task
def update():
    """
    updates a virtualenv (pip install requirements.txt)
    """
    do_run('cd %(path)s; bin/pip install -r requirements.txt --upgrade' % config.sites["main"].deployment)

@task
def create():
    """
    creates a virtualenv and calls update
    """
    do_run('cd %(path)s; virtualenv . --system-site-packages --setuptools' % config.sites["main"].deployment)
    update()
    # this is ugly. I know. But it seems that on first run, pip does not
    # install the correct version of packages that are pulled directly from
    # git. Only the second time around it uses the correct one.
    update()
