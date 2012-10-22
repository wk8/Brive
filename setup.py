try:
    from setuptools import setup, find_packages
except ImportError:
    print 'Please download and install setuptools (http://pypi.python.org/pypi/setuptools)'
    exit(1)

setup(
    name = "Brive",
    version = "0.2.0",
    packages = find_packages(),

    author = "Jean Rouge",
    author_email = "jer329@cornell.edu",
    description = "Brive, the Google Apps Domains' Drive Backup application",
    license = "UNLICENSED (cf http://unlicense.org/)",
    keywords = "google drive backup domain",
    url = "https://github.com/x8wk/Brive",

    install_requires = [
        "PyYAML",
        "feedparser",
        "google-api-python-client",
        "pyOpenSSL",
        "python-dateutil",
    ],

    dependency_links = [
        "http://pyyaml.org/download/pyyaml/PyYAML-3.10.tar.gz"
    ]
)
