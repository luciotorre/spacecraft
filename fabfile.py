import os
import sys

from fabric.api import local


def bootstrap():
    check_system_deps()
    virtualenv_create()
    install_requirements()


def run_server(*args):
    check_bootstrap()
    local('./virtualenv/bin/twistd -n spacecraft %s' % ' '.join(args))


def run_client():
    check_bootstrap()
    local('PYTHONPATH=. ./virtualenv/bin/python spacecraft/manual_client.py')


def run_monitor():
    check_bootstrap()
    local('PYTHONPATH=. ./virtualenv/bin/python spacecraft/monitor.py')


def clean():
    local("rm -rf virtualenv")


def test():
    check_bootstrap()
    local('./virtualenv/bin/trial spacecraft')

# -----------------------------------------------------------------
# Tasks from here down aren't intended to be used directly


def virtualenv_create():
    local("rm -rf virtualenv")
    local("%s /usr/bin/virtualenv virtualenv" % sys.executable, capture=False)


def check_system_deps():
    missing_bindeps = []
    missing_pydeps = []
    bindeps = ['svn', 'gcc', 'g++', 'swig']
    pydeps = ['pygame', 'virtualenv', 'setuptools']
    for dep in bindeps:
        result = local('which %s || true' % dep, capture=True)
        if not result:
            missing_bindeps.append(dep)
    for dep in pydeps:
        result = local('''%s -c "try:
    import %s
except ImportError:
    print ':('
"''' % (sys.executable, dep), capture=True)
        if result:
            missing_pydeps.append(dep)
    if missing_bindeps:
        print "\nPlease install the following binary deps on your system:"
        print '\n'.join(' * %s' % x for x in missing_bindeps)
    if missing_pydeps:
        print "Please install the following Python deps on your system:"
        print '\n'.join(' * %s' % x for x in missing_pydeps)
    if missing_bindeps or missing_pydeps:
        sys.exit(1)


def install_requirements():
    local("virtualenv/bin/pip install -U -r requirements.txt", capture=False)


def check_bootstrap():
    if not os.path.isdir('virtualenv'):
        bootstrap()
