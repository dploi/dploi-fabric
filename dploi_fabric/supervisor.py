import StringIO
from copy import copy
from fabric.decorators import task
from fabric.api import run, put, env
from dploi_fabric.toolbox.template import render_template
from dploi_fabric.utils import config
import posixpath

@task
def update_config_file(dryrun=False):
    output = ''
    groups = {}
    for site, site_config in config.sites.items():
        template_path = site_config['supervisor']['template']
        group_template_path = site_config['supervisor']['group_template']
        group_name = get_group_name(site, site_config)
        groups[group_name] = []
        for process_name, process_dict in site_config.processes.items():
            context_dict = copy(site_config)
            env_dict = {
                'HOME': site_config.deployment['home'],
                'USER': site_config.deployment['user'],
                'PYTHONPATH': ":".join([
                    site_config.deployment['path'],
                    posixpath.join(site_config.deployment['path'], site_config.get("django").get("base")+'/'),
                ]),
            }
            env_dict.update(site_config.environment)
            context_dict.update({
                'process_name': process_name,
                'process_cmd': process_dict["command"],
                'socket': process_dict["socket"],
                'env': env_dict,
                'priority': process_dict.get('priority', 200),
                'autostart': 'True' if getattr(env, 'autostart', True) else 'False',
            })
            output += render_template(template_path, context_dict)
            groups[group_name].append(process_name)
    output += render_template(group_template_path, {'groups': groups})
    path = posixpath.abspath(posixpath.join(config.sites["main"].deployment['path'], '..', 'config', 'supervisor.conf'))
    if dryrun:
        print path + ':'
        print output
    else:
        put(StringIO.StringIO(output), path)
        update()

@task
def stop():
    for site, site_config in config.sites.items():
        run('sudo supervisorctl stop %s:*' %  get_group_name(site, site_config))


@task
def start():
    for site, site_config in config.sites.items():
        run('sudo supervisorctl start %s:*' % get_group_name(site, site_config))

@task
def restart():
    for site, site_config in config.sites.items():
        run('sudo supervisorctl restart %s:*' % get_group_name(site, site_config))

@task
def status():
    """
    print status of the supervisor process

    Note: "status" does not yet support the group syntax
    """
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl status %s:%s' % (group_name, process_name))

@task
def add():
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl add %s:%s' % (group_name, process_name))

@task
def update():
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl update %s:%s' % (group_name, process_name))

def get_group_name(site, site_config):
    return '%s-%s' % (site_config['deployment']['user'], site)