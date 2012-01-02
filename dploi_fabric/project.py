import os

from fabric.api import env, task, prompt, run
from fabric.contrib import files
from .django_utils import django_exec
from github import upload_ssh_deploy_key
from supervisor import update_config_file as supervisor_update_config_file
from nginx import update_config_file as nginx_update_config_file
import django_utils
@task
def init():
    if files.exists(os.path.join(env.path, 'bin')):
        print "buildout environment exists already"
        return
    upload_ssh_deploy_key()
    run('mkdir -p %(path)s' % env)
    if env.repo.startswith('git'):
        run('cd %(path)s; git clone -b %(branch)s %(repo)s .' % env)
    elif env.repo.startswith('ssh+svn'):
        run('cd %(path)s; svn co %(repo)s' % env)
    tool = django_exec().get("checkout_tool")
    if tool == "buildout":
        run('cd %(path)s; sh init.sh -c %(buildout_cfg)s' % env)
        django_utils.append_settings()
    elif tool == "virtualenv":
        import virtualenv
        virtualenv.create()
        django_utils.append_settings()
        django_utils.manage("syncdb --all --noinput")
        django_utils.manage("migrate --fake")
    else:
        print "WARNING: Couldnt find [checkout] tool - please set it to either virtualenv or buildout in your config.ini"
        print "Got tool: %s" % tool
        django_utils.append_settings()
    supervisor_update_config_file()
    nginx_update_config_file()
