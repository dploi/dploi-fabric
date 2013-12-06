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
* ``deployment_tracking_apikey`` (default: ``''``): new relic deployment tracking API key (this has to be set in ``deployment.py``)


Deployment Tracking
===================

You can track deployments and send them to New Relic's API. There are two parts to it:

* ``@newrelic.register_deployment`` by using this decorator the deployment info will be sent to New Relic's API after the deployment has run through
* ``newrelic.log_output()`` by using this context manager, you can specify which additional logging data should be sent

Example usage
-------------

::

    from dploi_fabric import newrelic

    @task
    @newrelic.register_deployment
    def deploy():
        with newrelic.log_output():
            pg.dump.run()
            git.update()
        virtualenv.update()
        south.migrate.run()
        django_utils.collectstatic()
        django_utils.manage('compress --force')
        run('~/bin/gunicorn restart')

