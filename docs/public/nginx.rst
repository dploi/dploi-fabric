.. _public/nginx:

###############
Nginx utilities
###############

The following functions are available through the CLI, e.g. fab <dev/stage/live/...> <command>

Configuration files
===================
.. autofunction:: dploi_fabric.nginx.update_config_file

Process management
==================
.. autofunction:: dploi_fabric.nginx.reload_nginx

Settings
========

Can be set in config.ini in the ``[nginx]`` section or in ``deployment.py`` in
this site ``nginx`` section:

* ``client_max_body_size`` (default: ``10m``)
* ``template`` (default: bundled template): path to template for nginx.conf template (relative to project root)

