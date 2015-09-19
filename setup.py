try:
    from setuptools import setup, find_packages
except ImportError:
    print 'Please download and install setuptools (http://pypi.python.org/pypi/setuptools)'
    exit(1)

setup(
    name = "Brive",
    version = "0.4.0",
    packages = find_packages(),

    author = "Jean Rouge",
    author_email = "jer329@cornell.edu",
    description = "Brive, the Google Apps Domains' Drive Backup application",
    license = "UNLICENSED (cf http://unlicense.org/)",
    keywords = "google drive backup domain",
    url = "https://github.com/x8wk/Brive",

    install_requires = [
        'Brive==0.3.11',
        'cffi==1.2.1',
        'cryptography==1.0.1',
        'enum34==1.0.4',
        'feedparser==5.2.1',
        'google-api-python-client==1.4.2',
        'httplib2==0.9.1',
        'idna==2.0',
        'ipaddress==1.0.14',
        'oauth2client==1.5.1',
        'pyasn1==0.1.8',
        'pyasn1-modules==0.0.7',
        'pycparser==2.14',
        'pyOpenSSL==0.15.1',
        'python-dateutil==2.4.2',
        'PyYAML==3.11',
        'rsa==3.2',
        'simplejson==3.8.0',
        'six==1.9.0',
        'streaming-httplib2==0.7.6',
        'uritemplate==0.6',
        'wheel==0.26.0'
    ],

    dependency_links = [
        "http://pyyaml.org/download/pyyaml/PyYAML-3.11.tar.gz"
    ]
)

# for some reason, the developer of streaming_httplib2 didn't include the certificates
# of signing authorities for SSL, so here we copy the certs from httplib2
# ugly, but eh...
import os, sys, httplib2, streaming_httplib2, shutil
httplib2_root = os.path.dirname(httplib2.__file__)
streaming_httplib2_root = os.path.dirname(streaming_httplib2.__file__)
cacerts_file_path = os.path.join(httplib2_root, 'cacerts.txt')
shutil.copy(cacerts_file_path, streaming_httplib2_root)
