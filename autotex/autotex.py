#!/usr/bin/env python3

import argparse
import binascii
import hashlib
import json
import os
import os.path
import re
import subprocess
import tempfile

################################################################################
################### HELPER LIBS ################################################
################################################################################
def get_equivalent(container, item, default=None):
    for x in container:
        if x == item:
            return x
    return default

################################################################################
################### CLASSES ####################################################
################################################################################
class Action:
    def __init__(self):
        self.deps = set()
        self.influences = set()
        self.dirty = False

    def __str__(self):
        return 'unknown action'

    def to_json(self):
        deps = []
        for x in self.deps:
            deps.append(x._id)

        influences = []
        for x in self.influences:
            influences.append(x._id)

        return {
            'id': self._id,
            'type': 'Action',
            'deps': deps,
            'influences': influences,
            'dirty': self.dirty
        }

    def from_json(j):
        return Action()

    def add_dependency(self, other):
        self.deps.add(other)
        other.influences.add(self)

    def merge(self, other):
        self.deps.update(other.deps)
        for d in other.deps:
            d.influences.remove(other)
            d.influences.add(self)

        self.influences.update(other.influences)
        for i in other.influences:
            i.deps.remove(other)
            i.deps.add(self)

    def needs_update(self):
        return self.dirty

    def update(self):
        self.dirty = False
        for action in self.influences:
            action.dirty = True

        return []

class FileAction(Action):
    def __init__(self, path, checksum=None):
        super().__init__()
        self.path = path
        self.checksum = checksum

    def __eq__(self, other):
        if isinstance(other, FileAction):
            return self.path == other.path
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return 'watch "' + self.path + '"'

    def to_json(self):
        j = super().to_json()
        j['type'] = 'FileAction'
        j['path'] = self.path
        j['checksum'] = self.checksum
        return j

    def from_json(j):
        return FileAction(
            path=j['path'],
            checksum=j['checksum'])

    def needs_update(self):
        return super().needs_update() or (self.checksum != self.calc_file_checksum())

    def update(self):
        super().update()
        self.checksum = self.calc_file_checksum()
        print('File changed: "' + self.path + '" (Checksum=' + self.checksum + ')')
        return []

    def calc_file_checksum(self):
        try:
            f = open(self.path, 'rb')
            checksum = hashlib.sha256(f.read()).digest()
            f.close()
            return str(binascii.hexlify(checksum))
        except IOError:
            return None

class CommandAction(Action):
    def __init__(self, command):
        super().__init__()
        self.command = command

    def __eq__(self, other):
        if isinstance(other, CommandAction):
            return self.command == other.command
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.command)

    def __str__(self):
        return self.command

    def to_json(self):
        j = super().to_json()
        j['type'] = 'CommandAction'
        j['command'] = self.command
        return j

    def from_json(j):
        return CommandAction(command=j['command'])

    def update(self):
        super().update()

        tfname = tmpdir.name + '/trace.log'
        status = subprocess.call(TRACE_CMD + ' ' + tfname + ' ' + self.command, shell=True)

        f = open(tfname)
        targets = analyze_trace(f)
        f.close()

        # generate new actions and deps
        result = []
        for path in targets:
            if not file_blacklisted(path):
                a = FileAction(path)

                if not a in self.deps:
                    self.add_dependency(a)
                    result.append(a)

                    # some files results in new commands
                    cmd = detect_command(path)
                    if cmd:
                        cmd.add_dependency(a)
                        result.append(cmd)

        return result

class IndexAction(CommandAction):
    def __init__(self, path):
        self.path = path
        out = self.path.replace('.idx', '.ind')
        super().__init__('makeindex -s gind.ist -o ' + out + ' ' + self.path)

    def to_json(self):
        j = super().to_json()
        j['type'] = 'IndexAction'
        j['path'] = self.path
        return j

    def from_json(j):
        return IndexAction(path=j['path'])

class MyEncoder(json.JSONEncoder):
    def default(self, o):
        # assign IDs
        i = 0
        for x in o:
            x._id = i
            i = i + 1

        # dump all objects
        l = []
        for x in o:
            l.append(x.to_json())

        return l

################################################################################
################### CONSTANTS ##################################################
################################################################################
COMMAND_MAP = {
    '.idx': IndexAction
}

FILEACTION_BLACKLIST = [
    '.log',
    '.pdf'
]

RE_TRACELINE = re.compile(r"""
    ^
    \d+                    # PID (dropped)
    \s+
    (?P<func> \w+ )        # function
    \(
    (?P<args> [^)]* )      # arguments
    \) \s* = \s*
    [0-9-]+                # status code (dropped)
                           # additional infos (dropped)
    """, re.VERBOSE)

TARGET_MAP = {
    'access': 0,
    'open': 0,
    'openat': 1,
    'stat': 0
}

TRACE_CMD = 'strace -e trace=file -f -qq -y -o'

################################################################################
################### GLOBALS ####################################################
################################################################################
basedir = os.path.abspath(os.getcwd())
tmpdir = tempfile.TemporaryDirectory()

################################################################################
################### ORPHAN METHODS #############################################
################################################################################
def file_blacklisted(path):
    for ext in FILEACTION_BLACKLIST:
        if path.endswith(ext):
            return True

    return False

def detect_command(path):
    for ext, Cmd in COMMAND_MAP.items():
        if path.endswith(ext):
            return Cmd(path)
    return None

def analyze_trace(f):
    targets = set()

    # analyze all lines
    for l in f:
        m = RE_TRACELINE.search(l)

        # valid line?
        if (m):
            func = m.group('func')
            args_raw = m.group('args')
            args = args_raw.split(', ')

            # can we get the target?
            if func in TARGET_MAP:
                target = os.path.abspath(args[TARGET_MAP[func]].replace('"', ''))

                # is this a local file?
                if os.path.commonprefix([basedir, target]) == basedir:
                    targets.add(os.path.relpath(target))

    return targets

def decode_json(f):
    a = json.load(f)
    table = {}
    for j in a:
        table[j['id']] = globals()[j['type']].from_json(j)

    result = set()
    for j in a:
        o = table[j['id']]

        for y in j['deps']:
            o.deps.add(table[y])

        for y in j['influences']:
            o.influences.add(table[y])

        result.add(o)

    return result

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        description='Compiles .tex files to PDFs using LuaLaTeX',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'file',
        nargs='?',
        help='.tex file'
    )
    parser.add_argument(
        '--state', '-s',
        type=str,
        default='.autotex.state',
        help='File that stores the serialized state of autotex'
    )
    parser.add_argument(
        '-v',
        action='store_true',
        default=False,
        help='verbose output'
    )
    args = parser.parse_args()

    actions = set()

    # try to restore state
    sf = None
    try:
        sf = open(args.state, 'r')
        actions = decode_json(sf)
    except Exception:
        exit(22)
        if args.file:
            a1 = FileAction(args.file)
            a2 = CommandAction('lualatex -pdf ' + args.file)
            a2.add_dependency(a1)
            actions.add(a1)
            actions.add(a2)
        else:
            parser.print_usage()
            exit(1)
    finally:
        if sf:
            sf.close()

    # main loop (fixpoint iteration)
    changed = True
    while changed:
        changed = False
        novel = set()

        for a in actions:
            if a.needs_update():
                novel.update(a.update())
                changed = True

        for n in novel:
            if n in actions:
                get_equivalent(actions, n).merge(n)
            else:
                actions.add(n)

        print()
        print("Tracked commands:")
        for a in actions:
            print(str(a))
        print()

    # safe state
    sf = open(args.state, 'w')
    json.dump(actions, sf, cls=MyEncoder, indent=4)
    sf.close()

if __name__ == '__main__':
    main()

