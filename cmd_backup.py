#!/usr/bin/python
"""
Backup the current system

Arguments:
    <override> := -?( /path/to/add/or/remove | mysql:database[/table] )

    Default overrides read from $CONF_OVERRIDES

Options:
    --address=TARGET_URL    manual backup target URL
                            default: automatically configured via Hub

    -v --verbose            Turn on verbosity
    -s --simulate           Simulate operation. Don't actually backup.

"""

from os.path import *

import sys
import getopt

from string import Template

import backup
from registry import registry

def fatal(e):
    print >> sys.stderr, "error: " + str(e)
    sys.exit(1)

def usage(e=None):
    if e:
        print >> sys.stderr, "error: " + str(e)

    print >> sys.stderr, "Syntax: %s [ -options ] [ override ... ]" % sys.argv[0]
    tpl = Template(__doc__.strip())
    Conf = backup.BackupConf
    print >> sys.stderr, tpl.substitute(CONF=Conf.paths.path,
                                        CONF_OVERRIDES=Conf.paths.overrides)
    sys.exit(1)

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'svh', 
                                       ['simulate', 'verbose', 
                                        'profile=', 'secretfile=', 'address='])
    except getopt.GetoptError, e:
        usage(e)

    conf = backup.BackupConf()
    conf.secretfile = registry.path.secret

    opt_simulate = False
    opt_verbose = False

    opt_profile = None
    for opt, val in opts:
        if opt in ('-v', '--verbose'):
            opt_verbose = True
        elif opt in ('-s', '--simulate'):
            opt_simulate = True

        elif opt == '--profile':
            opt_profile = val

        elif opt == '--secretfile':
            if not exists(val):
                usage("secretfile %s does not exist" % `val`)
            conf.secretfile = val
        elif opt == '--address':
            conf.address = val
        elif opt == '-h':
            usage()

    conf.overrides += args

    if not conf.address:
        # TODO: auto-configure via Hub
        fatal("not implemented yet")
        conf.address = registry.hbr.address

    if opt_simulate:
        opt_verbose = True

    print "backup.Backup(%s)" % (`conf`)

    #b = backup.Backup(conf)
    #if opt_verbose:
    #    print "PASSPHRASE=$(cat %s) %s" % (conf.secretfile, b.command)

    #if not opt_simulate:
    #    try:
    #        b.run()
    #    finally:
    #        b.cleanup()

if __name__=="__main__":
    main()
