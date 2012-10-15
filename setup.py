try:
    from setuptools import setup, find_packages
except ImportError:
    print 'Please download and install setuptools (http://pypi.python.org/pypi/setuptools)'
    exit(1)

setup(
    name = "Brive",
    version = "0.1",
    packages = find_packages(),

    author = "Jean Rouge",
    author_email = "jer329@cornell.edu",
    description = "Brive, the Google Apps Domains' Drive Backup application",
    license = "MIT",
    keywords = "google drive backup domain",
    url = "https://github.com/x8wk/Brive",

)
