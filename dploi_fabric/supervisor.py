import StringIO
from fabric.decorators import task
from fabric.api import run, put

from dploi_fabric.toolbox.template import render_template
from dploi_fabric.utils import config

@task
def update_config_file():
    template = 'templates/supervisor/supervisor.conf'
    output = ''
    for site, site_config in config.sites.items():
        for process_name, process_dict in site_config.processes.items():
            context_dict = site_config
            context_dict.update({'process_name': process_name, 'process_cmd': process_dict["command"], 'socket': process_dict["socket"]})
            output += render_template(template, context_dict)
    put(StringIO.StringIO(output), '%(path)s/../config/supervisor.conf' % config.sites["main"].deployment)
    update()

@task
def stop():
    for site, site_config in config.sites.items():
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl stop %s' % process_name)


@task
def start():
    for site, site_config in config.sites.items():
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl start %s' % process_name)

@task
def restart():
    for site, site_config in config.sites.items():
        for process_name, process_cmd in site_config.processes.items():
            run('sudo supervisorctl restart %s' % process_name)

@task
def status():
    """
    print status of the supervisor process
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