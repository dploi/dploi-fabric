import os
import posixpath

import StringIO
from fabric.operations import run, local
from fabric.api import task, env, get
from fabric.contrib.files import exists
from fabric.state import _AttributeDict


from dploi_fabric.toolbox.datastructures import EnvConfigParser
from dploi_fabric.messages import DOMAIN_DICT_DEPRECATION_WARNING

STATIC_COLLECTED = "../static/"
DATA_DIRECTORY = "../upload/"

class Configuration(object):
    """
    This class is the only correct source of information for this project.
    To reduce the amount of times config.ini is downloaded, it should always
    be used from utils.config, which is an instance of Configuration
    """
    #: Default values for the configuration
    defaults = {
        'django': {
            'base': '.',
            'append_settings': False,
            'cmd': 'bin/django',
            'args': [],
        },
        'checkout': {
            'tool': 'buildout',
        },
        'celery': {
            'enabled': False,
            'concurrency': 1,
            'maxtasksperchild': 500,
            'loglevel': 'WARNING',
            'celerycam': False,
        },
        'static': {

        },
        'redis': {
            'enabled': False,
            'appendonly': 'no',
        },
        'processes': {

        }
    }
    def load_sites(self, config_file_content=None, env_dict=None):
        """
        Called from self.sites and returns a dictionary with the different sites
        and their individual settings.
        """
        if not config_file_content:
            config_file = os.path.join(env.path, "config.ini")
            if exists(config_file):
                output = StringIO.StringIO()
                get(u"%s" % config_file, output)
                output.seek(0)
            else:
                raise Exception("Missing config.ini, tried path %s" % config_file)
        else:
            output = StringIO.StringIO(config_file_content)

        if not env_dict:
            env_dict = env

        config = EnvConfigParser()
        config.readfp(output)
        self._sites = {}
        for site in config.section_namespaces("django") or ["main"]:
            attr_dict = self.defaults.copy()
            for key, value in attr_dict.items():
                attr_dict[key] = _AttributeDict(value.copy())
            for section in config.sections():
                section = section.split(":")[0]
                if self.defaults.get(section) is None:
                    print "Caution: Section %s is not supported, skipped" % section
                    continue
                for option, default_value in config.items(section, env=site):
                    setting = self.defaults.get(section).get(option)
                    if type(setting) == bool:
                        value = config.getboolean(section, option, env=site)
                    elif type(setting) == int:
                        value = config.getint(section, option, env=site)
                    elif type(setting) == float:
                        value = config.getfloat(section, option, env=site)
                    else:
                        variables = {
                            'static_collected': STATIC_COLLECTED,
                            'data_directory': DATA_DIRECTORY,
                        }
                        value = config.get(section, option, env=site) % variables
                    attr_dict[section][option] = value
            self.sites[site] = _AttributeDict(attr_dict)
            attr_dict.update(self.deployment(site, env_dict))
            if attr_dict.get("checkout").get("tool") == "buildout":
                # e.g. bin/django -> /home/username/app/bin/django
                attr_dict["django"]["cmd"] = posixpath.join(
                    attr_dict.get("deployment").get("path"),
                    attr_dict.get("django").get("cmd")
                )
            else:
                # e.g. manage.py -> /home/username/app/bin/python /home/username/app/manage.py
                new_django_cmd = [
                    posixpath.join(
                        attr_dict.get("deployment").get("path"),
                        "bin/python",
                    ),
                    posixpath.join(
                        attr_dict.get("deployment").get("path"),
                        attr_dict.get("django").get("base"),
                        attr_dict.get("django").get("cmd")
                    )
                ]
                attr_dict["django"]["cmd"] = " ".join(new_django_cmd)
                if attr_dict["django"]["append_settings"]:
                    attr_dict["django"]["args"].append(" --settings=%s" % ('_gen.settings', ))

            attr_dict.update({'processes': self.processes(site, env_dict)})
            self._sites[site] = _AttributeDict(attr_dict)
        return self._sites

    @property
    def sites(self):
        if getattr(self, "_sites", False) == False:
            self.load_sites()
        return self._sites

    def processes(self, site, env_dict):
        """
        Returns a dictionary of dictionaries each having the following keys:

        * command
            command to be run by supervisor
        * port
            port number,
        * socket
            path to unix socket
        * type
            gunicorn/memcached/celeryd
        """
        process_dict = {}
        site_dict = self.sites[site]
        django_args = " ".join(site_dict.get("django").get("args", []))
        gunicorn_socket = posixpath.normpath(posixpath.join(env_dict.get("path"), "..", "tmp", "%s_%s_gunicorn.sock" % (env_dict.get("user"), site))) # Asserts pony project layout

        process_dict["%s_%s_gunicorn" % (env_dict.get("user"), site)] = {
                    'command': "%s run_gunicorn %s -w 2 -b unix:%s" % (site_dict.django['cmd'], django_args, gunicorn_socket),
                    'port': None,
                    'socket': gunicorn_socket,
                    'type': 'gunicorn'
                }

        memcached_socket = posixpath.normpath(posixpath.join(env_dict.get("path"), "..", "tmp", "%s_%s_memcached.sock" % (env_dict.get("user"), site))) # Asserts pony project layout

        process_dict["%s_%s_memcached" % (env_dict.get("user"), site)] = {
                    'command': "memcached -s %s" % memcached_socket,
                    'port': None,
                    'socket': memcached_socket,
                    'type': 'memcached'
                }
        if site_dict.get("celery").get("enabled"):
            process_dict["%s_%s_celeryd" % (env_dict.get("user"), site)] = {
                    'command': "%s celeryd %s -E -B -c %s --maxtasksperchild %s --loglevel=%s" % (
                        site_dict.django['cmd'],
                        django_args,
                        site_dict.get("celery").get("concurrency"),
                        site_dict.get("celery").get("maxtasksperchild"),
                        site_dict.get("celery").get("loglevel"),
                    ),
                    'port': None,
                    'socket': None,
                    'type': 'celeryd'
                }
            if site_dict.get("celery").get("celerycam"):
                process_dict["%s_%s_celerycam" % (env_dict.get("user"), site)] = {
                    'command': "%s celerycam %s --loglevel=%s" % (
                        site_dict.django['cmd'],
                        django_args,
                        site_dict.get("celery").get("loglevel"),
                    ),
                    'port': None,
                    'socket': None,
                    'type': 'celerycam'
                }
        if site_dict.get("redis").get("enabled"):
            process_name = "%s_%s_redis" % (env_dict.get("user"), site)
            redis_socket = posixpath.normpath(posixpath.join(env_dict.get("path"), "..", "tmp", process_name + ".sock" )) # Asserts pony project layout
            process_dict[process_name] = {
                'command': "/usr/bin/redis-server %s" % posixpath.normpath(posixpath.join(env_dict.get('path'), '..', 'config', process_name + '.conf')),
                'port': None,
                'socket': redis_socket,
                'type': 'redis'
            }
        if site_dict.get('processes'):
            processes = site_dict.get('processes')
            for process, command in processes.iteritems():
                process_name = "%s_%s_process_%s" % (env_dict.get("user"), site, process)
                process_dict[process_name] = {
                    'command': posixpath.join(env_dict.get("path"), command),
                    'port': None,
                    'socket': None,
                    'type': 'supervisor'
                }

        return process_dict

    def deployment(self, site, env_dict):
        """
        Here we add the information from deployments.py and merge it into our site dictionaries.
        Can also be used to output warnings to the user, if he is using an old deployments.py
        format.
        """
        deployment_dict = {
            # Old settings
            'servername': env_dict.get("host_string"),
            'path': env_dict.get("path"),
            'backup_dir': env_dict.get("backup_dir"),
            'repo': env_dict.get("repo"),
            'branch': env_dict.get("branch"),
            'user': env_dict.get("user"),
            'buildout_cfg': env_dict.get("buildout_cfg"),
            'generated_settings_path': posixpath.join(env_dict.get("path"), "_gen/settings.py"),

            # New settings
            'domains_redirect': env_dict.get('domains_redirect'),
            'url_redirect': env_dict.get('url_redirect'),

            'basic_auth': env_dict.get('basic_auth', False),
            'basic_auth_path': os.path.join(env_dict.get("path"), env_dict.get('basic_auth_path', None) or ""),

            'ssl': env.get('ssl', False),
            'ssl_cert_path': os.path.join(env_dict.get("path"), env_dict.get('ssl_cert_path', None) or ""),
            'ssl_key_path': os.path.join(env_dict.get("path"), env_dict.get('ssl_key_path', None) or ""),

            'home': '/home/%s' %  env_dict.get("user"),
        }

        if not env_dict.get("databases"):
            deployment_dict["databases"] = {
                'default': {
                    'ENGINE': env_dict.get("db_engine", "django.db.backends.postgresql_psycopg2"),
                    'NAME': env_dict.get("db_name"),
                    'USER': env_dict.get("db_username"),
                    'PASSWORD': env_dict.get("db_password"),
                    'HOST': env_dict.get("db_host", "localhost"),
                }
            }

        if type(env_dict.get("domains")) == list:
            domains = {
                "main": env_dict.get("domains"),
            }
            print(DOMAIN_DICT_DEPRECATION_WARNING)
        elif type(env_dict.get("domains")) == dict:
            domains = env_dict.get("domains")
        elif env_dict.get("domains") == None:
            domains = {
                "main": [],
            }
            print("Warning: No domains supplied in settings, ignoring.")
        else:
            raise Exception("Invalid domain format")
        deployment_dict.update({'domains': domains})

        ###############
        # Celery dict #
        ###############

        celery_dict = self.sites[site].get("celery")

        celery_dict["concurrency"] = env_dict.get("celery", {}).get("concurrency", celery_dict.get("concurrency"))
        celery_dict["maxtasksperchild"] = env_dict.get("celery", {}).get("maxtasksperchild", celery_dict.get("maxtasksperchild"))


        return {'deployment': deployment_dict, 'celery': celery_dict}

    def django_manage(self, command, site="main"):
        """
        Wrapper around the commands to inject the correct pythonpath.

        Example: django_manage("migrate"), could result in

        export PYTONPATH=/home/app-dev/app/; /home/app-dev/app/bin/python /home/app-dev/app/manage.py migrate
        """
        site_dict = config.sites[site]
        cmd = site_dict.get("django").get("cmd")
        django_args = " ".join(site_dict.get("django").get("args", []))
        run('export PYTHONPATH=%s; %s %s %s' % (site_dict.get("deployment").get("path"), cmd, command, django_args))

if not __name__ == '__main__':
    #: A shared instance of configuration, always to be used
    config = Configuration()


@task
def check_config():
    for section in config_ini.config_parser.sections():
        print "[%s]" % section
        print config_ini.config_parser.items(section)

@task
def uname():
    print env.host_string
    run('uname -a')

@task
def ls():
    run('cd %(path)s;ls -lAF' % env)

@task
def ps():
    """
    show processes of this user
    """
    run('ps -f -u %(user)s | grep -v "ps -f" | grep -v sshd' % env)

@task
def download_media(to_dir="./tmp/media/", from_dir="../upload/"):
    """
    Downloads media from a remote folder, default ../uploads/ -> ./tmp/media/
    
    * Example: upload_media:from_dir="py_src/project/media/"
    """
    print "Downloading media from", env.host_string
    env.from_dir = from_dir
    local('rsync -avz --no-links --progress --exclude=".svn" -e "ssh" %(user)s@%(host_string)s:"%(path)s/%(from_dir)s"' % env + " " +to_dir)

@task
def upload_media(from_dir="./tmp/media/", to_dir="../upload/"):
    """
    Uploads media from a local folder, default ./tmp/media -> ../uploads/
    
    * Example: upload_media:to_dir="py_src/project/media/"
    """
    print "Uploading media to", env.host_string
    env.to_dir = to_dir
    local('rsync -avz --no-links --progress --exclude=".svn" '+ from_dir +' -e "ssh" %(user)s@%(host_string)s:"%(path)s/%(to_dir)s"' % env)
