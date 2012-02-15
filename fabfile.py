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
    local('PYTHONPATH=. ./virtualenv/bin/python spacecraft/client.py')


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
    system_deps = ['pygame']
    missing_deps = []
    for dep in system_deps:
        result = local('''%s -c "try:
    import %s
except ImportError:
    print ':('
"''' % (sys.executable, dep), capture=True)
        if result:
            missing_deps.append(dep)
    if missing_deps:
        print "Please install the following deps on your system:"
        print '\n'.join(' * %s' % x for x in missing_deps)


def install_requirements():
    local("virtualenv/bin/pip install -U -r requirements.txt", capture=False)


def check_bootstrap():
    if not os.path.isdir('virtualenv'):
        bootstrap()
