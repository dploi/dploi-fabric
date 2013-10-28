.. _public/newrelic:

##################
NewRelic utilities
##################

Settings
========

Can be set in config.ini in the ``[newrelic]`` section or in ``deployment.py`` in
this site ``newrelic`` section:

* ``enabled`` (default: ``False``)
* ``config_file`` (default: 'newrelic.ini'): path to ``newrelic.ini`` (relative to project root)
* ``environment_name`` (default: ``''``): new relic environment name (for deployment specific settings in newrelic.ini)
* ``license_key`` (default: ``''``): license key to override the one in ``newrelic.ini``.
