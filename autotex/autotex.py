#!/usr/bin/env python3

import argparse
import binascii
import fcntl
import hashlib
import json
import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile
import time

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

        state = self.__dict__.copy()
        del state['_id']
        del state['deps']
        del state['influences']

        return {
            'id': self._id,
            'type': type(self).__name__,
            'deps': deps,
            'influences': influences,
            'state': state
        }


    def from_json(self, j):
        self.__dict__ = j['state']
        self.deps = set()
        self.influences = set()

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
            return str(binascii.hexlify(checksum), 'utf8')
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

    def update(self):
        super().update()
        tfname = config['tmpdir'].name + '/trace.log'
        cmd = TRACE_CMD + ' ' + tfname + ' ' + self.command

        # run child process and redirect output
        print(self.command + ': -', end='')
        sys.stdout.flush()
        child = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        fcntl.fcntl(child.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(child.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
        status = None
        counter = 0
        while status == None:
            s = child.poll()
            out = child.stdout.read(1)
            err = child.stderr.read(1)
            if (s != None) and (out == '') and (err == ''):
                status = s

            changed = False
            if out != '':
                config['log'].write(out)
                config['log'].flush()
                changed = True
            if err != '':
                config['log'].write(err)
                config['log'].flush()
                changed = True

            if changed:
                counter = (counter + 1) % 4
                if counter == 0:
                    print('\b-', end='')
                elif counter == 1:
                    print('\b/', end='')
                elif counter == 2:
                    print('\b|', end='')
                elif counter == 3:
                    print('\b\\', end='')
                sys.stdout.flush()
            else:
                time.sleep(0.05)

        # get and analyze trace log
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

        print('\bOK(' + str(status) + ')')
        return result

class IndexAction(CommandAction):
    def __init__(self, path, out, style):
        self.path = path
        self.out = out
        self.style = style
        super().__init__('makeindex -s ' + self.style + ' -o ' + self.out + ' ' + self.path)

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
config = {
    'basedir': os.path.abspath(os.getcwd()),
    'command_map': {
        '.idx': {
            'type': 'IndexAction',
            'args': {
                'path': '%p',
                'style': 'gind.ist',
                'out': '%w.ind'
            }
        }
    },
    'file_blacklist': [
        '.log',
        '.pdf'
    ],
    'tmpdir': tempfile.TemporaryDirectory()
}

################################################################################
################### ORPHAN METHODS #############################################
################################################################################
def file_blacklisted(path):
    for ext in config['file_blacklist']:
        if path.endswith(ext):
            return True

    return False

def detect_command(path):
    for ext, cmd in config['command_map'].items():
        if path.endswith(ext):
            # get action and args
            t = globals()[cmd['type']]
            args = {}
            if 'args' in cmd:
                args = cmd['args']

            # substitute string arguments
            s_path = path
            s_woext, s_ext = os.path.splitext(path)
            s_dir, s_basename = os.path.split(path)
            for key, value in args.items():
                if type(value) == str:
                    value = value.replace('%p', s_path)
                    value = value.replace('%w', s_woext)
                    value = value.replace('%e', s_ext)
                    value = value.replace('%d', s_dir)
                    value = value.replace('%b', s_basename)
                    args[key] = value

            # construct Action object
            return t(**args)
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
                if os.path.commonprefix([config['basedir'], target]) == config['basedir']:
                    targets.add(os.path.relpath(target))

    return targets

def decode_json(f):
    a = json.load(f)
    table = {}
    for j in a:
        t = globals()[j['type']]
        obj = t.__new__(t)
        obj.from_json(j)
        table[j['id']] = obj

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
        '--log', '-l',
        type=argparse.FileType('w'),
        default='autotex.log',
        help='Log file'
    )
    parser.add_argument(
        '--state', '-s',
        type=str,
        default='.autotex.state',
        help='File that stores the serialized state of autotex'
    )
    parser.add_argument(
        '-verbose', '-v',
        action='store_true',
        default=False,
        help='verbose output'
    )
    args = parser.parse_args()
    config.update(vars(args))

    actions = set()

    # try to restore state
    sf = None
    try:
        sf = open(config['state'], 'r')
        actions = decode_json(sf)
        print('State restored from file')
    except Exception:
        if config['file']:
            a1 = FileAction(config['file'])
            a2 = CommandAction('lualatex -pdf ' + config['file'])
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

        # safe state
        if changed:
            state_tmp = config['state'] + '.new'
            sf = open(state_tmp, 'w')
            json.dump(actions, sf, cls=MyEncoder, indent=4)
            sf.close()
            shutil.move(state_tmp, config['state'])

        if config['verbose']:
            print()
            print("Tracked commands:")
            for a in actions:
                print(str(a))
            print()

if __name__ == '__main__':
    main()

