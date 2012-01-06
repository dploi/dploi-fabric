import os

from fabric.api import env, task, prompt, run, put
from fabric.contrib import files
from .django_utils import django_exec
from github import upload_ssh_deploy_key
from supervisor import update_config_file as supervisor_update_config_file
from nginx import update_config_file as nginx_update_config_file
import django_utils
from .utils import config
@task
def init():
    # TODO: Use utils.config (after checkout)
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

@task
def upload_ssl():
    """
    Upload the SSL key and certificate to the directories and with the filenames
    specified in your settings.
    """
    for site, site_dict in config.sites.items():
        ssl_key_path = prompt("SSL Key path (%s):" % site)
        ssl_cert_path = prompt("SSL Certificate path (%s):" % site)
        put(ssl_key_path, site_dict.get("deployment").get("ssl_key_path"))
        put(ssl_cert_path, site_dict.get("deployment").get("ssl_cert_path"))