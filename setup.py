try:
    from setuptools import setup, find_packages
except ImportError:
    print 'Please download and install setuptools (http://pypi.python.org/pypi/setuptools)'
    exit(1)

setup(
    name = "Brive",
    version = "0.3.6",
    packages = find_packages(),

    author = "Jean Rouge",
    author_email = "jer329@cornell.edu",
    description = "Brive, the Google Apps Domains' Drive Backup application",
    license = "UNLICENSED (cf http://unlicense.org/)",
    keywords = "google drive backup domain",
    url = "https://github.com/x8wk/Brive",

    install_requires = [
        "PyYAML==3.10",
        "feedparser==5.1.2",
        "google-api-python-client==1.0",
        "pyOpenSSL",
        "python-dateutil==1.5",
        "streaming_httplib2==0.7.6",
        "httplib2==0.7.6",
    ],

    dependency_links = [
        "http://pyyaml.org/download/pyyaml/PyYAML-3.10.tar.gz"
    ]
)
