#!/usr/bin/env python3

import argparse
import binascii
import contextlib
import fcntl
import gzip
import hashlib
import msgpack
import operator
import os
import os.path
import pyinotify
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import yaml


# =============================================================================
# ================= HELPER LIBS ===============================================
# =============================================================================
def get_equivalent(container, item, default=None):
    for element in container:
        if element == item:
            return element
    return default


# =============================================================================
# ================= CLASSES ===================================================
# =============================================================================
class Action(object):
    def __init__(self, dirty=True):
        self.deps = set()
        self.influences = set()
        self.dirty = dirty

    def __str__(self):
        return 'unknown action'

    def to_json(self):
        attributes = (
            (a, getattr(self, a))
            for a in dir(self)
            if not a.startswith('__')
        )
        state = dict(
            (k, v)
            for k, v in attributes
            if type(v) in [
                bool,
                bytearray,
                bytes,
                complex,
                dict,
                float,
                frozenset,
                int,
                list,
                set,
                str,
                tuple
            ]
        )
        del state['deps']
        del state['influences']
        del state['dirty']

        return {
            'id': id(self),
            'type': type(self).__name__,
            'deps': [id(x) for x in self.deps],
            'influences': [id(x) for x in self.influences],
            'dirty': self.dirty,
            'state': state
        }

    def from_json(self, j):
        for name, value in j['state'].items():
            setattr(self, name, value)
        self.deps = set()
        self.influences = set()
        self.dirty = j['dirty']

    def add_dependency(self, other):
        self.deps.add(other)
        other.influences.add(self)

    def merge(self, other):
        self.deps.update(other.deps)
        for dep in other.deps:
            dep.influences.remove(other)
            dep.influences.add(self)

        self.influences.update(other.influences)
        for infl in other.influences:
            infl.deps.remove(other)
            infl.deps.add(self)

    def priority(self):
        return 0

    def needs_update(self):
        return self.dirty

    def check_status(self):
        return 0

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
        return not self == other

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return 'watch "{}"'.format(self.path)

    def priority(self):
        return -100

    def needs_update(self):
        return super().needs_update() \
            or (self.path not in INOTIFY_FILTER
                and self.checksum != self.calc_file_checksum())

    def update(self):
        if self.path not in INOTIFY_FILTER:
            INOTIFY_FILTER.add(self.path)

        self.checksum = self.calc_file_checksum()
        checksum_string = str(binascii.hexlify(self.checksum), 'utf8')
        if len(checksum_string) > 9:
            checksum_string = '{}.{}'.format(
                checksum_string[:4],
                checksum_string[-4:]
            )
        print_changed('Changed ({}): {}'.format(
            checksum_string,
            self.path
        ))

        super().update()
        return []

    def calc_file_checksum(self):
        try:
            with open(self.path, 'rb') as binfile:
                return hashlib.sha256(binfile.read()).digest()
        except IOError:
            return b''


class CommandAction(Action):
    def __init__(self, command, ignores=None):
        super().__init__()
        self.command = command
        self.ignores = ignores or []
        self.status = None

    def __eq__(self, other):
        if isinstance(other, CommandAction):
            return (self.command == other.command) \
                and (self.ignores == other.ignores)
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.command)

    def __str__(self):
        return self.command

    def priority(self):
        return 100

    def check_status(self):
        return self.status

    def update(self):
        # run child process and redirect output
        print_execute(self.command + ': -', False)
        tfname = CONFIG['tmpdir'] + '/trace.log'
        self.status = None
        with open(CONFIG['log'], 'a') as flog, \
                contextlib.ExitStack() as stack:
            child = subprocess.Popen(
                TRACE_CMD + ' ' + tfname + ' ' + self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stack.callback(child.terminate)
            fcntl.fcntl(child.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
            fcntl.fcntl(child.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
            self.print_log_header(flog)
            counter = 0
            while self.status is None:
                status_new = child.poll()
                out = child.stdout.read(1)
                err = child.stderr.read(1)
                if (status_new is not None) and (out == '') and (err == ''):
                    self.status = status_new

                changed = False
                if out != '':
                    flog.write(out)
                    flog.flush()
                    if CONFIG['print_stdout']:
                        self.print_char(out, counter)
                    changed = True
                if err != '':
                    flog.write(err)
                    flog.flush()
                    if CONFIG['print_stderr']:
                        self.print_char(err, counter)
                    changed = True

                if changed:
                    counter = (counter + 1) % 4
                    print_execute(
                        '\b' + self.get_process_char(counter),
                        False,
                        True
                    )
                else:
                    time.sleep(0.05)
            stack.pop_all()

        # get and analyze trace log
        with open(tfname) as tracefile:
            targets = analyze_trace(tracefile)

        # generate new actions and deps
        fas = set(
            FileAction(path)
            for path in targets
            if not self.file_ignored(path)
        ).difference(self.deps)
        for faction in fas:
            self.add_dependency(faction)
        result = [a for fa in fas for a in detect_actions(fa.path)] + list(fas)

        if self.status == 0:
            print_execute('\bOK', True, True)
        else:
            print_error('\bFAILED({})'.format(self.status), True, True)
        super().update()
        return result

    def file_ignored(self, path):
        return any(
            re.search(ext, path)
            for ext in self.ignores
        )

    def get_process_char(self, counter):
        return '-/|\\'[counter]

    def print_char(self, char, counter):
        string = '\b'
        if char == '\n':
            string += ' '
        print_execute(string, False, True)

        print_error(char, False, True)

        print_execute(self.get_process_char(counter), False, True)

    def print_log_header(self, flog):
        flog.write('\n')
        flog.write(2 * ((80 * '+') + '\n'))
        flog.write(('+' * 10) + str(self) + '\n')
        flog.write(2 * ((80 * '+') + '\n'))


class TexBibAction(CommandAction):
    def __init__(self, path):
        self.path = path
        super().__init__(
            command='biber ' + self.path,
            ignores=[r"\.blg$", r"\.utf8$"]
        )


class TexCompileAction(CommandAction):
    def __init__(
            self,
            path,
            engine='luajittex',
            latex=True,
            output_format='pdf'):
        self.path = path
        self.engine = engine.lower()
        self.latex = latex
        self.output_format = output_format.lower()

        cmd = ''
        if self.engine == 'luajittex':
            cmd = 'luajittex --fmt='

            if self.latex:
                cmd = cmd + 'lualatex'
            else:
                cmd = cmd + 'luatex'

            cmd = cmd + ' --jiton --file-line-error --interaction=nonstopmode'

            if self.output_format in ['dvi', 'pdf']:
                cmd = cmd + ' --output-format=' + self.output_format
            else:
                raise Exception('Format(' + self.output_format
                                + ') is not supported by LuaTeX!')
        elif self.engine == 'luatex':
            if self.latex:
                cmd = 'lualatex'
            else:
                cmd = 'luatex'

            cmd = cmd + ' --file-line-error --interaction=nonstopmode'

            if self.output_format in ['dvi', 'pdf']:
                cmd = cmd + ' --output-format=' + self.output_format
            else:
                raise Exception('Format(' + self.output_format
                                + ') is not supported by LuaTeX!')
        elif self.engine == 'xetex':
            if self.latex:
                cmd = 'xelatex'
            else:
                cmd = 'xetex'

            cmd = cmd + ' -file-line-error -interaction=batchmode'

            if self.output_format == 'pdf':
                pass
            elif self.output_format == 'xdv':
                cmd = cmd + ' -no-pdf'
            else:
                raise Exception('Format(' + self.output_format
                                + ') is not supported by XeTeX!')
        elif self.engine == 'pdftex':
            if self.output_format == 'pdf':
                cmd = 'pdf'
            elif self.output_format == 'dvi':
                cmd = ''
            else:
                raise Exception('Format(' + self.output_format
                                + ') is not supported by pdfTeX!')

            if self.latex:
                cmd = cmd + 'latex'
            else:
                cmd = cmd + 'tex'

            cmd = cmd + ' -file-line-error -interaction=batchmode'
        else:
            raise Exception('Unsupported engine(' + self.engine + ')!')

        cmd = cmd + ' ' + self.path

        super().__init__(
            command=cmd,
            ignores=[r"\.log$", r"\.pdf$"]
        )


class TexIndexAction(CommandAction):
    def __init__(self, path, out, style):
        self.path = path
        self.out = out
        self.style = style
        super().__init__('makeindex -q -s ' + self.style
                         + ' -o ' + self.out
                         + ' ' + self.path)


class INotifyHandler(pyinotify.ProcessEvent):
    def process_default(self, event):
        with INOTIFY_CONDITION:
            path = os.path.relpath(event.pathname)
            if CONFIG['verbose']:
                print_debug(path + ': ' + event.maskname)
            if path in INOTIFY_FILTER:
                INOTIFY_FILTER.remove(path)
            INOTIFY_CONDITION.notify_all()


# =============================================================================
# ================= CONSTANTS =================================================
# =============================================================================
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

STATE_VERSION = 2

TARGET_MAP = {
    'access':    0,
    'execve':    0,
    'getcwd':    0,
    'lstat':     0,
    'mkdir':     0,
    'open':      0,
    'openat':    1,
    'readlink':  0,
    'stat':      0,
    'unlink':    0
}

TRACE_CMD = 'strace -e trace=file -f -qq -y -o'

YAML_PATCH = '?+'
YAML_REMOVE = '?-'


# =============================================================================
# ================= GLOBALS ===================================================
# =============================================================================
TMPDIR = tempfile.TemporaryDirectory()

INOTIFY_CONDITION = threading.Condition()

INOTIFY_FILTER = set()

CONFIG = {
    'append_log': False,
    'basedir': os.path.abspath(os.getcwd()),
    'command_map': {
        r"\.bcf": {
            'type': 'TexBibAction',
            'args': {
                'path': '?p'
            },
            'auto': True
        },
        r"\.(ins)|(dtx)|(tex)$": {
            'type': 'TexCompileAction',
            'args': {
                'path': '?p'
            },
            'auto': False
        },
        r"\.idx$": {
            'type': 'TexIndexAction',
            'args': {
                'path': '?p',
                'style': 'gind.ist',
                'out': '?w.ind'
            },
            'auto': True
        }
    },
    'continuously': False,
    'continuously_wait': 0.25,
    'log': 'autotex.log',
    'max_rounds': 10,
    'print_stdout': False,
    'print_stderr': True,
    'state': '.autotex.state',
    'tmpdir': TMPDIR.name,
    'verbose': False
}


# =============================================================================
# ================= ORPHAN METHODS ============================================
# =============================================================================
def detect_actions(path, auto_only=True):
    # find commands
    commands = CONFIG['command_map'].items()
    ok_auto = (
        not auto_only or (('auto' in cmd) and (cmd['auto'] is True))
        for ext, cmd in commands
    )
    ok_path = (
        bool(re.search(ext, path))
        for ext, cmd in commands
    )
    ok_all = (
        all(t)
        for t in zip(ok_auto, ok_path)
    )
    commands_filtered = (
        cmd
        for (ext, cmd), o in zip(commands, ok_all)
        if o
    )

    # prepare argument substitution
    s_path = path
    s_woext, s_ext = os.path.splitext(path)
    s_dir, s_basename = os.path.split(path)
    replace_dict = {
        '??': '?',
        '?b': s_basename,
        '?d': s_dir,
        '?e': s_ext,
        '?p': s_path,
        '?w': s_woext
    }
    pattern = re.compile('|'.join(
        re.escape(k)
        for k in replace_dict.keys()
    ))

    # find all matching commands
    actions = []
    for cmd in commands_filtered:
        # get action and args
        actiontype = globals()[cmd['type']]
        args = cmd['args'].copy() if 'args' in cmd else {}

        # substitute string arguments
        for key, value in args.items():
            if type(value) == str:
                args[key] = pattern.sub(
                    lambda x: replace_dict[x.group()],
                    value
                )

        # construct Action object
        actions.append(actiontype(**args))

    return actions


def analyze_trace(tracefile):
    matches = (
        RE_TRACELINE.search(l)
        for l in tracefile
    )
    parsed = (
        (m.group('func'), m.group('args').split(', '))
        for m in matches
        if m
    )
    targets = (
        os.path.abspath(args[TARGET_MAP[func]].replace('"', ''))
        for func, args in parsed
        if func in TARGET_MAP
    )
    return set(
        os.path.relpath(t)
        for t in targets
        if os.path.commonprefix([CONFIG['basedir'], t]) == CONFIG['basedir']
    )


def patch_list(orig, patch):
    # parse patch
    blacklist = set()
    extension = []
    for entry in patch:
        if entry is not None:
            if (type(entry) == str) and entry.startswith(YAML_REMOVE):
                blacklist.add(entry[len(YAML_REMOVE):])
            elif (type(entry) == str) and entry.startswith(YAML_PATCH):
                # ignore
                pass
            else:
                extension.append(entry)

    # apply patch
    base = [x for x in orig if x not in blacklist] if orig else []
    return base + extension


def patch_dict(orig, patch):
    base = orig or {}

    # parse patch
    blacklist = set()
    replace = {}
    overwrite = {}
    for key, value in patch.items():
        if value is not None:
            if key.startswith(YAML_REMOVE):
                blacklist.add(key[len(YAML_REMOVE):])
            elif value == YAML_REMOVE:
                blacklist.add(key)
            elif key == YAML_PATCH:
                # ignore, important to avoid empty keys
                pass
            elif key.startswith(YAML_PATCH) and (type(value) == dict):
                tmp_key = key[len(YAML_PATCH):]
                if type(value) == dict:
                    suborig = base[tmp_key] \
                        if tmp_key in base and type(base[tmp_key]) == dict \
                        else None
                    replace[tmp_key] = patch_dict(suborig, value)
                elif type(value) == list:
                    suborig = base[tmp_key] \
                        if tmp_key in base and type(base[tmp_key]) == list \
                        else None
                    replace[tmp_key] = patch_list(suborig, value)
            else:
                overwrite[key] = value

    # apply patch
    result = dict(
        (k, v)
        for k, v in base.items()
        if k not in blacklist
    )
    result.update(replace)
    result.update(overwrite)
    return result


def print_master(msg, marker, newline, append):
    if not append:
        sys.stdout.write('[{}] '.format(marker))
    sys.stdout.write(msg)
    if newline:
        print()
    sys.stdout.flush()


def print_info(msg, newline=True, append=False):
    print_master(msg, 'i', newline, append)


def print_changed(msg, newline=True, append=False):
    print_master(msg, '~', newline, append)


def print_execute(msg, newline=True, append=False):
    print_master(msg, '+', newline, append)


def print_error(msg, newline=True, append=False):
    print_master(msg, 'X', newline, append)


def print_debug(msg, newline=True, append=False):
    print_master(msg, '.', newline, append)


def restore_state():
    # load data from file
    with gzip.open(CONFIG['state'], 'rb') as statefile:
        state = msgpack.unpackb(statefile.read(), encoding='utf-8')

    # version check
    if 'state_version' not in state \
            or state['state_version'] != STATE_VERSION:
        raise Exception('Incompatible state version!')

    # create objects
    actions = state['actions']
    table = {}
    for j in actions:
        actiontype = globals()[j['type']]
        obj = actiontype.__new__(actiontype)
        obj.from_json(j)
        table[j['id']] = obj

    # restore dependency graph
    for j in actions:
        action = table[j['id']]
        action.deps.update(table[y] for y in j['deps'])
        action.influences.update(table[y] for y in j['influences'])

    print_info('State restored')
    return set(table.values())


def initialize_state(files):
    complete = (a for f in files for a in detect_actions(f, False))
    actions = set()

    for action in complete:
        if action in actions:
            get_equivalent(actions, action).merge(action)
        else:
            actions.add(action)

    return actions


def save_state(actions):
    # build state
    state = {
        'state_version': STATE_VERSION,
        'actions': [a.to_json() for a in actions]
    }

    # write to temporary file
    state_tmp = CONFIG['state'] + '.new'
    with gzip.GzipFile(
        filename=CONFIG['state'],
        fileobj=open(state_tmp, 'wb')
    ) as statefile:
        statefile.write(msgpack.packb(state, use_bin_type=True))
        statefile.flush()
        os.fsync(statefile)

    # finally overwrite old file
    shutil.move(state_tmp, CONFIG['state'])


def main():
    global CONFIG

    # parse command line arguments
    parser = argparse.ArgumentParser(
        description='Compiles .tex files to PDFs using LuaLaTeX'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='initial processed filed'
    )
    parser.add_argument(
        '--log', '-l',
        type=str,
        help='Log file'
    )
    parser.add_argument(
        '--append_log',
        action='store_true',
        help='Append new entries to log file'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='.autotexrc',
        help='Config file (YAML)'
    )
    parser.add_argument(
        '--continuously', '-e',
        action='store_true',
        default=None,
        help='Update build continuously'
    )
    parser.add_argument(
        '--state', '-s',
        type=str,
        help='File that stores the serialized state of autotex'
    )
    parser.add_argument(
        '-verbose', '-v',
        action='store_true',
        default=None,
        help='verbose output'
    )
    args = parser.parse_args()
    if not args.files:
        args.files = None

    # generate config
    try:
        with open(args.CONFIG) as configfile:
            CONFIG = patch_dict(CONFIG, yaml.load(configfile.read()))
    except Exception:
        pass
    CONFIG = patch_dict(CONFIG, vars(args))

    # clear log?
    if not CONFIG['append_log']:
        open(CONFIG['log'], 'w').close()

    # try to restore or initialize state
    try:
        actions = restore_state()
    except Exception:
        if 'files' in CONFIG:
            actions = initialize_state(CONFIG['files'])
        else:
            parser.print_usage()
            exit(1)

    if not actions:
        print_error('No matching action for this file!')
        exit(1)

    # setup inotify
    mask = pyinotify.EventsCodes.ALL_FLAGS['IN_ATTRIB'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_CREATE'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_DELETE'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_DELETE_SELF'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_MODIFY'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_MOVE_SELF'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_MOVED_FROM'] \
        | pyinotify.EventsCodes.ALL_FLAGS['IN_MOVED_TO']
    watch_manager = pyinotify.WatchManager()
    notifier = pyinotify.ThreadedNotifier(watch_manager, INotifyHandler())
    # double with to avoid crashing pylint
    with contextlib.ExitStack() as stack:
        with INOTIFY_CONDITION:
            stack.callback(notifier.stop)
            notifier.start()
            watch_manager.add_watch(
                CONFIG['basedir'],
                mask,
                rec=True
            )

            # main loop (fixpoint iteration)
            changed = True
            rounds = 0
            terminate = False
            while changed and not terminate:
                changed = False
                schedule = sorted((a for a in actions if a.needs_update()),
                                  key=operator.methodcaller('priority'))

                try:
                    # update actions
                    for action in schedule:
                        novel = action.update()

                        # merge new actions to existing ones
                        for new in novel:
                            if new in actions:
                                get_equivalent(actions, new).merge(new)
                            else:
                                actions.add(new)

                        changed = True
                except KeyboardInterrupt:
                    signal.signal(signal.SIGINT, signal.SIG_IGN)
                    print()
                    print_info('Interrupted')
                    terminate = True

                # debug prints
                if CONFIG['verbose']:
                    print_debug('')
                    print_debug('Tracked commands:')
                    for action in actions:
                        print_debug(str(action))
                    print_debug('')

                # safe state
                if changed:
                    save_state(actions)
                elif CONFIG['continuously'] and not terminate:
                    print_info('Sleep', False)
                    try:
                        while not any(a.needs_update() for a in actions):
                            print_info('.', False, True)
                            INOTIFY_CONDITION.wait()
                            time.sleep(CONFIG['continuously_wait'])
                        print_info('wake up!', True, True)
                        changed = True
                        rounds = 0
                    except KeyboardInterrupt:
                        signal.signal(signal.SIGINT, signal.SIG_IGN)
                        print()
                        print_info('Interrupted')
                        terminate = True
                    continue

                rounds = rounds + 1
                if (CONFIG['max_rounds'] != 0) \
                        and (rounds > CONFIG['max_rounds']) \
                        and not terminate:
                    print_error('Reached maximum number of rounds!')
                    exit(1)

    # check status of all actions
    if any(a.check_status() for a in actions):
        print_error('There are some errors!')
        exit(1)

    print_info('Done')

if __name__ == '__main__':
    main()
