import os

from fabric.api import env, task, prompt, run, put
from fabric.contrib import files
from dploi_fabric import git
from github import upload_ssh_deploy_key
from supervisor import update_config_file as supervisor_update_config_file
from nginx import update_config_file as nginx_update_config_file
from redis import update_config_file as redis_update_config_file
import django_utils
from .utils import config


@task
def init():
    if files.exists(os.path.join(env.path, 'bin')):
        print "buildout environment exists already"
        return
    upload_ssh_deploy_key()
    run('mkdir -p %(path)s' % env)
    run('mkdir -p %(logdir)s' % env)
    run('mkdir -p %(path)s../tmp' % env)
    run('mkdir -p %(path)s../config' % env)
    if env.repo.startswith('git'):
        run('cd %(path)s; git clone -b %(branch)s %(repo)s .' % env)
        git.update()
    elif env.repo.startswith('ssh+svn'):
        run('cd %(path)s; svn co %(repo)s' % env)

    if config.sites['main']['redis']['enabled']:
        redis_update_config_file()

    if config.sites["main"]['supervisor']['use_global_supervisord'] == True:
        supervisor_update_config_file()
    else:
        supervisor_update_config_file(load_config=False)
        run(config.sites["main"]['supervisor']['supervisord_command'])
        supervisor_update_config_file(load_config=True)

    if config.sites["main"]['nginx']['enabled'] == True:
        nginx_update_config_file()

    tool = config.sites['main'].get('checkout', {}).get('tool')
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
