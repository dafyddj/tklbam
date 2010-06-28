#!/usr/bin/python
"""
Restore a backup

Arguments:

    <hub-backup> := backup-id || unique label pattern

Options:
    --limits="<limit1> .. <limitN>"   Restore filesystem or database limitations

      <limit> := -?( /path/to/add/or/remove | mysql:database[/table] )

    --keyfile=KEYFILE                 Path to escrow keyfile.
                                      default: Hub provides this automatically.

    --address=TARGET_URL              manual backup target URL (needs --keyfile)
                                      default: Hub provides this automatically.

    --skip-files                      Don't restore filesystem
    --skip-database                   Don't restore databases
    --skip-packages                   Don't restore new packages

    --no-rollback                     Disable rollback
    --silent                          Disable feedback

"""

import sys
import getopt

import re

from os.path import *
from restore import Restore
from redirect import RedirectOutput
from temp import TempFile

import hub
from registry import registry
import keypacket

import passphrase

class Error(Exception):
    pass

def get_backup_record(arg):
    hb = hub.Backups(registry.sub_apikey)
    if re.match(r'^\d+$', arg):
        backup_id = arg

        try:
            return hb.get_backup_record(backup_id)
        except hub.InvalidBackupError, e:
            raise Error('invalid backup id (%s)' % backup_id)

    # treat our argument as a pattern
    matches = [ hbr for hbr in hb.list_backups() 
                if re.search(arg, hbr.label, re.IGNORECASE) ]

    if not matches:
        raise Error("'%s' doesn't match any backup labels" % arg)

    if len(matches) > 1:
        raise Error("'%s' matches more than one backup label" % arg)

    return matches[0]

def decrypt_key(key):
    try:
        return keypacket.parse(key, "")
    except keypacket.Error:
        pass

    while True:
        try:
            return keypacket.parse(key, passphrase.get_passphrase(confirm=False))
        except keypacket.Error:
            print >> sys.stderr, "Incorrect passphrase, try again"

def fatal(e):
    print >> sys.stderr, "error: " + str(e)
    sys.exit(1)

def usage(e=None):
    if e:
        print >> sys.stderr, "error: " + str(e)

    print >> sys.stderr, "Syntax: %s [ -options ] [ <hub-backup> ]" % sys.argv[0]
    print >> sys.stderr, __doc__.strip()
    sys.exit(1)

def main():
    opt_limits = []
    opt_key = None
    opt_address = None

    skip_files = False
    skip_database = False
    skip_packages = False
    no_rollback = False
    silent = False

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'h', 
                                       ['limits=', 'address=', 'keyfile=', 
                                        'silent',
                                        'skip-files', 'skip-database', 'skip-packages',
                                        'no-rollback'])
                                        
    except getopt.GetoptError, e:
        usage(e)

    for opt, val in opts:
        if opt == '--limits':
            opt_limits += re.split(r'\s+', val)
        elif opt == '--keyfile':
            if not isfile(val):
                fatal("keyfile %s does not exist or is not a file" % `val`)

            opt_key = file(val).read()
        elif opt == '--address':
            opt_address = val
        elif opt == '--skip-files':
            skip_files = True
        elif opt == '--skip-database':
            skip_database = True
        elif opt == '--skip-packages':
            skip_packages = True
        elif opt == '--no-rollback':
            no_rollback = True
        elif opt == '--silent':
            silent = True
        elif opt == '-h':
            usage()

    hbr = None
    credentials = None

    if args:
        if len(args) != 1:
            usage("incorrect number of arguments")

        try:
            hbr = get_backup_record(args[0])
            credentials = hub.Backups(registry.sub_apikey).get_credentials()
        except Error, e:
            fatal(e)

    else:
        if not opt_address:
            usage()

    if opt_address:
        if hbr:
            fatal("a manual --address is incompatible with a <backup-id>")

        if not opt_key:
            fatal("a manual --address needs a --keyfile")

    address = hbr.address if hbr else opt_address

    if hbr and opt_key and \
       keypacket.fingerprint(hbr.key) != keypacket.fingerprint(opt_key):
        fatal("invalid escrow key for the selected backup")

    key = opt_key if opt_key else hbr.key
    secret = decrypt_key(key)

    print "address: " + `address`
    print "secret: " + `secret`
    print "opt_limits: " + `opt_limits`
    print "credentials: " + `credentials`

    if silent:
        log = TempFile()
    else:
        log = sys.stdout

    redir = RedirectOutput(log)
    try:
        restore = Restore(address, secret, opt_limits, 
                          credentials=credentials,
                          rollback=not no_rollback)

        if not skip_packages:
            restore.packages()

        if not skip_files:
            restore.files()

        if not skip_database:
            restore.database()
    finally:
        redir.close()

if __name__=="__main__":
    main()
