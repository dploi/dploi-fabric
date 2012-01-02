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