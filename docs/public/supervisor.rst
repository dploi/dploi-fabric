.. _public/supervisor:

####################
Supervisor utilities
####################

The following functions are available through the CLI, e.g. fab <dev/stage/live/...> <command>

Configuration files
===================
.. autofunction:: dploi_fabric.supervisor.add
.. autofunction:: dploi_fabric.supervisor.update
.. autofunction:: dploi_fabric.supervisor.update_config_file

Process management
==================
.. autofunction:: dploi_fabric.supervisor.start
.. autofunction:: dploi_fabric.supervisor.stop
.. autofunction:: dploi_fabric.supervisor.restart
.. autofunction:: dploi_fabric.supervisor.status


Settings
========

Can be set in config.ini in the ``[supervisor]`` section or in ``deployment.py`` in
this site ``supervisor`` section:

* ``template`` (default: bundled ``dploi_fabric/templates/supervisor/supervisor.conf``)
* ``group_template`` (default: bundled ``dploi_fabric/templates/supervisor/supervisor-group.conf``)
* ``gunicorn_command_template`` (default: bundled ``dploi_fabric/templates/supervisor/gunicorn_command``)
* ``celeryd_command_template`` (default: bundled ``dploi_fabric/templates/supervisor/celeryd_command``)
* ``celerycam_command_template`` (default: bundled ``dploi_fabric/templates/supervisor/celerycam_command``)