import StringIO
from copy import copy
from fabric.decorators import task
from fabric.api import run, put
from dploi_fabric.toolbox.template import render_template
from dploi_fabric.utils import config

@task
def update_config_file():
    template = 'templates/supervisor/supervisor.conf'
    group_template = 'templates/supervisor/supervisor-group.conf'
    output = ''
    groups = {}
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        groups[group_name] = []
        for process_name, process_dict in site_config.processes.items():
            context_dict = copy(site_config)
            env_dict = {
                'HOME': site_config.deployment['home'],
                'PYTHONPATH': site_config.deployment['path'],
            }
            env_dict.update(site_config.environment)
            context_dict.update({
                'process_name': process_name,
                'process_cmd': process_dict["command"],
                'socket': process_dict["socket"],
                'env': env_dict,
                'priority': process_dict.get('priority', 200),
            })
            output += render_template(template, context_dict)
            groups[group_name].append(process_name)
    output += render_template(group_template, {'groups': groups})
    put(StringIO.StringIO(output), '%(path)s/../config/supervisor.conf' % config.sites["main"].deployment)
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
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl status %s' % process_name)

@task
def add():
    for site, site_config in config.sites.items():
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl add %s' % process_name)

@task
def update():
    for site, site_config in config.sites.items():
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl update %s' % process_name)

def get_group_name(site, site_config):
    return '%s-%s' % (site_config['deployment']['user'], site)