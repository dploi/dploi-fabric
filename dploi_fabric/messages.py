# http://patorjk.com/software/taag/ - font Basic
#
DEPRECATED = """
=================================================================================

 d8888b. d88888b d8888b. d8888b. d88888b  .o88b.  .d8b.  d888888b d88888b d8888b.
 88  `8D 88'     88  `8D 88  `8D 88'     d8P  Y8 d8' `8b `~~88~~' 88'     88  `8D
 88   88 88ooooo 88oodD' 88oobY' 88ooooo 8P      88ooo88    88    88ooooo 88   88
 88   88 88~~~~~ 88~~~   88`8b   88~~~~~ 8b      88~~~88    88    88~~~~~ 88   88
 88  .8D 88.     88      88 `88. 88.     Y8b  d8 88   88    88    88.     88  .8D
 Y8888D' Y88888P 88      88   YD Y88888P  `Y88P' YP   YP    YP    Y88888P Y8888D'

=================================================================================
"""
EXCEPTION = """
============================================================================

d88888b db    db  .o88b. d88888b d8888b. d888888b d888888b  .d88b.  d8b   db
88'     `8b  d8' d8P  Y8 88'     88  `8D `~~88~~'   `88'   .8P  Y8. 888o  88
88ooooo  `8bd8'  8P      88ooooo 88oodD'    88       88    88    88 88V8o 88
88~~~~~  .dPYb.  8b      88~~~~~ 88~~~      88       88    88    88 88 V8o88
88.     .8P  Y8. Y8b  d8 88.     88         88      .88.   `8b  d8' 88  V888
Y88888P YP    YP  `Y88P' Y88888P 88         YP    Y888888P  `Y88P'  VP   V8P

============================================================================
"""
CAUTION = """
===============================================================
 .o88b.  .d8b.  db    db d888888b d888888b  .d88b.  d8b   db db
d8P  Y8 d8' `8b 88    88 `~~88~~'   `88'   .8P  Y8. 888o  88 88
8P      88ooo88 88    88    88       88    88    88 88V8o 88 YP
8b      88~~~88 88    88    88       88    88    88 88 V8o88
Y8b  d8 88   88 88b  d88    88      .88.   `8b  d8' 88  V888 db
 `Y88P' YP   YP ~Y8888P'    YP    Y888888P  `Y88P'  VP   V8P YP
===============================================================
"""





DOMAIN_DICT_DEPRECATION_WARNING = DEPRECATED + """
 - Please use a dict to describe domains in deployments.py , e.g.

    'domains': {
        'main': ['domain.tld'],
        'multisite1': ['domain2.tld'],
    }
=================================================================================
"""

DATABASES_DICT_DEPRECATION_WARNING = DEPRECATED + """
 - Please use a dict to describe databases in deployments.py , e.g.

    'databases': {
        'default': {
            'ENGINE': "django.db.backends.postgresql_psycopg2",
            'NAME': "username-dev",
            'USER': "username-dev",
        }
    }
=================================================================================
"""