# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# This file contains functions used by the hooks to enable PLUMgrid
# in Openstack.

from collections import OrderedDict
from copy import deepcopy
import os
from subprocess import check_call
from charmhelpers.contrib.openstack import templating
from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from charmhelpers.contrib.python.packages import pip_install
from charmhelpers.fetch import (
    apt_cache
)
from charmhelpers.core.hookenv import (
    config,
)
from charmhelpers.contrib.openstack.utils import (
    os_release,
)
from charmhelpers.core.hookenv import (
    relation_set,
)

import neutron_plumgrid_context

TEMPLATES = 'templates/'

PG_PACKAGES = [
    'plumgrid-pythonlib',
    #'neutron-plugin-plumgrid'
]

NEUTRON_CONF_DIR = "/etc/neutron"

SU_FILE = '/etc/sudoers.d/neutron_sudoers'
PLUMGRID_CONF = '%s/plugins/plumgrid/plumgrid.ini' % NEUTRON_CONF_DIR
PGLIB_CONF = '%s/plugins/plumgrid/plumlib.ini' % NEUTRON_CONF_DIR

BASE_RESOURCE_MAP = OrderedDict([
    (SU_FILE, {
        'services': [],
        'contexts': [neutron_plumgrid_context.NeutronPGPluginContext()],
    }),
    (PLUMGRID_CONF, {
        'services': ['neutron-server'],
        'contexts': [neutron_plumgrid_context.NeutronPGPluginContext()],
    }),
    (PGLIB_CONF, {
        'services': ['neutron-server'],
        'contexts': [neutron_plumgrid_context.NeutronPGPluginContext()],
    }),
])

NETWORKING_PLUMGRID_VERSION = OrderedDict([
    ('kilo', '2015.1.1.1'),
    ('liberty', '2015.2.1.1'),
])


def determine_packages():
    '''
    Returns list of packages required to be installed alongside neutron to
    enable PLUMgrid in Openstack.
    '''
    pkgs = []
    tag = config('plumgrid-build')
    for pkg in PG_PACKAGES:
        if tag == 'latest':
            pkgs.append(pkg)
        else:
            if tag in [i.ver_str for i in apt_cache()[pkg].version_list]:
                pkgs.append('%s=%s' % (pkg, tag))
            else:
                error_msg = \
                    "Build version '%s' for package '%s' not available" \
                    % (tag, pkg)
                raise ValueError(error_msg)
    # if subordinate
    #pkgs.append('neutron-plugin-plumgrid')
    cmd = ['mkdir', '-p', '/etc/neutron/plugins/plumgrid']
    check_call(cmd)
    cmd = ['touch', '/etc/neutron/plugins/plumgrid/plumgrid.ini']
    check_call(cmd)
    return pkgs


def resource_map():
    '''
    Dynamically generate a map of resources that will be managed for a single
    hook execution.
    '''
    resource_map = deepcopy(BASE_RESOURCE_MAP)
    return resource_map


def register_configs(release=None):
    '''
    Returns an object of the Openstack Tempating Class which contains the
    the context required for all templates of this charm.
    '''
    release = release or os_release('neutron-common', base='kilo')
    if release < 'kilo':
        raise ValueError('OpenStack %s release not supported' % release)

    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release=release)
    for cfg, rscs in resource_map().iteritems():
        configs.register(cfg, rscs['contexts'])
    return configs


def restart_map():
    '''
    Constructs a restart map based on charm config settings and relation
    state.
    '''
    return OrderedDict([(cfg, v['services'])
                        for cfg, v in resource_map().iteritems()
                        if v['services']])


def ensure_files():
    '''
    Ensures PLUMgrid specific files exist before templates are written.
    '''
    install_networking_plumgrid()
    os.chmod('/etc/sudoers.d/neutron_sudoers', 0o440)


def install_networking_plumgrid():
    '''
    Installs networking-plumgrid package
    '''
    release = os_release('neutron-common', base='kilo')
    if config('networking-plumgrid-version') is None:
        package_version = NETWORKING_PLUMGRID_VERSION[release]
    else:
        package_version = config('networking-plumgrid-version')
    package_name = 'networking-plumgrid==%s' % package_version
    pip_install(package_name, fatal=True)


def set_neutron_relation():
    #release = os_release('neutron-common', base='kilo')
    #plugin = "neutron.plugins.plumgrid.plumgrid_plugin.plumgrid_plugin.NeutronPluginPLUMgridV2" \
    #         if  release == 'kilo'\
    #         else "networking_plumgrid.neutron.plugins.plugin.NeutronPluginPLUMgridV2"
    print "#### core-plugin: %s" % neutron_plugin_attribute('plumgrid','driver','neutron')
    print "#### neutron-plugin-config %s" %  neutron_plugin_attribute('plumgrid','config','neutron')
    settings = { "neutron-plugin": "plumgrid",
                 "core-plugin": neutron_plugin_attribute('plumgrid','driver','neutron'),
                 "neutron-plugin-config": neutron_plugin_attribute('plumgrid','config','neutron'),
                 "service-plugins": " ",
                 "quota-driver": " "}
    relation_set(relation_settings=settings)
