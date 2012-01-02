from fabric.operations import run as do_run
from fabric.api import task, env

@task
def run():
    """
    runs buildout
    """
    do_run('cd %(path)s;./bin/buildout -c %(buildout_cfg)s' % env)

