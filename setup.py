import metadata as m

from setuptools import setup, find_packages

install_requires = [
    "fabric >= 1.2",
    "requests",
    "Django",
]

setup(
    name = m.name,
    version = m.version,
    url = m.project_url,
    license = m.license,
    platforms=['OS Independent'],
    description = m.description,
    author = m.author,
    author_email = m.author_email,
    packages=find_packages(),
    install_requires = install_requires,
    include_package_data = True, #Accept all data files and directories matched by MANIFEST.in or found in source control.
    package_dir = {
        m.package_name:m.package_name,
    },
    zip_safe=False,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
