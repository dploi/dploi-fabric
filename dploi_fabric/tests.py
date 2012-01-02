import ConfigParser
import StringIO
import unittest
from dploi_fabric.utils import EnvConfigParser, Configuration, _AttributeDict, STATIC_COLLECTED

class TestConfigurationTestCase(unittest.TestCase):
    test_config = """
[django]
base = code_checkout/
append_settings = true
cmd = bin/whatever

[django:multisite1]
base = .
append_settings = false
cmd = bin/django

[static]
/static/ = %(static_collected)s

"""
    def setUp(self):
        self.env_dict = {
            'host_string': 'some.server.tld',
            'hosts': ['some.server.tld'],
            'path': '/home/username/app/',
            'user': 'username',
            'buildout_cfg': 'buildout.cfg',
            'repo': 'git@github.com:user/repo.git',
            'branch': 'master',
            'backup_dir': '/home/username/tmp/',
            'db_name': 'db-name',
            'db_username': 'db-name',
            'identifier': 'dev',
            'domains': {
                'main': ['main.domain.tld'],
                'multisite1': ['multisite1.domain.tld'],
            },
            'celery': {
                'concurrency': 32,
            }
        }
        self.sites = Configuration().load_sites(self.test_config, self.env_dict)

    def test_value_types(self):
        config = self.sites["main"]
        self.assertFalse(config.get("celery").get("enabled"))
        self.assertEqual(config.django.base, "code_checkout/")

        config = self.sites["multisite1"]
        self.assertEqual(config.django.base, ".")

    def test_celery(self):
        self.sites = Configuration().load_sites(self.test_config + """
[celery]
enabled=true""", self.env_dict)
        config = self.sites["main"]
        self.assertTrue(config.get("celery").get("enabled"))
        self.assertEqual(config.get("celery").get("concurrency"), 32)
        self.assertEqual(config.get("celery").get("maxtasksperchild"), 500)
        self.assertTrue("%s_%s_celeryd" % (config.deployment.get("user"), "main") in config.get("processes"))
        self.assertTrue("celeryd -E -B -c 32 --maxtasksperchild 500" in config.get("processes").get("%s_%s_celeryd" % (config.deployment.get("user"), "main")).get("command"))

    def test_static(self):
        self.assertEqual(self.sites["main"].get("static").get("/static/"), STATIC_COLLECTED)



class TestInheritConfigParserRead(unittest.TestCase):
    test_config = """
[base]
name = test
type = nginx
count = 5
enable = false
threshold = 1.0

[base:dev]
host = dev.example.com
type = apache
count = 1
enable = True
threshold = 0.9

[other:dev]
foo = bar
"""
    def setUp(self):
        f = StringIO.StringIO(self.test_config)
        self.config = EnvConfigParser()
        self.config.readfp(f)

    def test_items(self):
        items = dict(self.config.items('base', env='dev'))
        self.assertIn('host', items)
        self.assertIn('name', items)

    def test_items_only_env(self):
        self.assertEqual(self.config.items('other', env='dev'), (('foo', 'bar'),))
        self.assertRaises(ConfigParser.NoSectionError, lambda: self.config.items('other'))

    def test_inherited_value(self):
        self.assertEquals(self.config.get('base', 'host', env='dev'), 'dev.example.com')

    def test_value_from_base(self):
        self.assertEquals(self.config.get('base', 'name', env='dev'), 'test')

    def test_overriden_value(self):
        self.assertEquals(self.config.get('base', 'type',), 'nginx')
        self.assertEquals(self.config.get('base', 'type', env='dev'), 'apache')

    def test_correct_exception_on_no_base(self):
        self.assertRaises(ConfigParser.NoOptionError, lambda: self.config.get('other', 'baz', env='dev'))

    def test_int(self):
        self.assertEquals(self.config.getint('base', 'count',), 5)
        self.assertEquals(self.config.getint('base', 'count', env='dev'), 1)

    def test_float(self):
        self.assertEquals(self.config.getfloat('base', 'threshold',), 1.0)
        self.assertEquals(self.config.getfloat('base', 'threshold', env='dev'), 0.9)

    def test_bool(self):
        self.assertFalse(self.config.getboolean('base', 'enable',))
        self.assertEqual(type(self.config.getboolean('base', 'enable',)), bool)
        self.assertTrue(self.config.getboolean('base', 'enable', env='dev'))

    def test_has_section(self):
        self.assertTrue(self.config.has_section('base'))
        self.assertTrue(self.config.has_section('base', env='dev'))
        self.assertTrue(self.config.has_section('base', env='stage'))
        self.assertFalse(self.config.has_section('base', env='stage', strict=True))
        self.assertTrue(self.config.has_section('other', env='dev'))
        self.assertFalse(self.config.has_section('other'))

    def test_section_namespaces(self):
        self.assertEqual(self.config.section_namespaces("base"), ["main", "dev"])


if __name__ == '__main__':
    unittest.main()