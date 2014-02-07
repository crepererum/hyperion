#!/usr/bin/env python3

import argparse
from datetime import date
import re

def default_version():
    """Creates version string according to the current date

    Returns:
        default version string

    """
    return date.today().strftime('%Y/%m/%d')

def parse_blocks(fblocks):
    """Parses the Blocks.txt file

    Args:
        fblocks: Blocks.txt file handler

    Returns:
        Array of dicts {begin: int, end: int, name:string}

    """
    print('Parse blocks: ', end='')
    result = []

    for l in fblocks:
        s = l.strip()
        if len(s) > 0 and s[0] != '#':
            m = re.match(r"([0-9A-F]+)\.{2}([0-9A-F]+);\s+(.+)", s)
            result.append({
                'begin': int(m.group(1), 16),
                'end': int(m.group(2), 16),
                'name': m.group(3)
            })

    print('done')
    return result

def convert_namepart(s):
    """Converts a part (mostly words) of a name to a LaTeX name part

    Args:
        s: escpaped python string of the part

    Returns:
        LaTeX compatible name part

    """
    s = s.lower()
    return s[0].upper() + s[1:]

def convert_name(s):
    """Converts an entire name by appending its parts

    Args:
        s: unescaped python string containing all parts of the name

    Returns:
        LaTeX compatible name

    """
    s = re.sub(r"[^a-zA-Z0-9\s]", '', s)
    s = s.strip()
    s = re.sub(r"\s+", ' ', s)
    a = s.split(' ')
    a = map(convert_namepart, a)
    return ''.join(a)

def package_name(s):
    """Converts a string to a LaTeX package name

    Args:
        s: unescaped python string

    Returns:
        LaTeX package name

    """
    return 'USymbol' + convert_name(s)

def symbol_name(s):
    """Converts a string to a LaTeX symbol name

    Args:
        s: unescaped python string

    Returns:
        LaTeX symbol name

    """
    return 'USymbol' + convert_name(s)

def print_header(s, f):
    """Prints a LaTeX section header comment to a file

    Args:
        s: name of the section header (one word!)
        f: LaTeX file

    """
    f.write('\n')
    f.write('%--------------------\n')
    f.write('%---' + s.upper() + ('-' * (17 - len(s))) + '\n')
    f.write('%--------------------\n')

def create_new_package(name, dout, version, fall=None):
    """Creates a new LaTeX package

    Args:
        name: unescaped package name
        dout: output directory
        version: package version string
        fall: LaTeX package that collects all packages (metapackage)

    Returns:
        File handler of the new LaTeX package file

    """
    print(name + ': ', end='')
    pname = package_name(name)

    f = open(dout + '/' + pname + '.sty', 'w')

    f.write('\\NeedsTeXFormat{LaTeX2e}\n')
    f.write('\\ProvidesPackage{' + pname + '}[' + version + ']\n')

    print_header('requirements', f)
    f.write('\\RequirePackage{ifluatex}\n')
    f.write('\\RequirePackage{ifxetex}\n')
    f.write('\\ifluatex\n')
    f.write('\\else\n')
    f.write('\\ifxetex\n')
    f.write('\\else\n')
    f.write('\\ClassError{hyperionbook}{LuaLaTeX or XeLaTeX required!}{Please compile with LuaLaTeX or XeLaTeX to when using this class. See http://www.luatex.org/ and http://xetex.sourceforge.net/}\n')
    f.write('\\fi\n')
    f.write('\\fi\n')

    if fall:
        fall.write('\\RequirePackage{' + pname + '}\n')

    print_header('symbols', f)

    return f

def print_symbol(f, name, hnumber):
    """Prints a symbol definition to a LaTeX file

    Args:
        f: LaTeX file
        name: unescpaed symbol name
        hnumber: hexnumber string

    """
    sname = symbol_name(name)
    f.write('\\newcommand{\\' + sname + '}{\\symbol{"' + hnumber + '}}\n')

def process_data(fdata, blocks, dout, version):
    """Processes UnicodeData.txt

    Args:
        fdata: UnicodeData.txt file handler
        blocks: parsed blocks
        dout: output directory
        version: package version string

    """
    print('')
    print('---Process data---')
    fall = create_new_package('all', dout, version)
    f = None
    it = iter(blocks)
    end = None

    for l in fdata:
        a = l.split(';')
        hnumber = a[0]
        name1 = a[1]
        name2 = a[10]
        name = name1 + ' ' + name2

        if (not f) or (int(hnumber, 16) > end):
            if f:
                print('done')
                f.close()

            block = next(it)
            end = block['end']
            f = create_new_package(block['name'], dout, version, fall)

        print_symbol(f, name, hnumber)

    if f:
        print('done')
        f.close()

    fall.close()

def main():
    parser = argparse.ArgumentParser(
        description='Creates Unicode symbol macros for LuaLaTeX and XeLaTeX',
        epilog='To get the required files, go to http://www.unicode.org/Public/UCD/latest/ucd/'
    )
    parser.add_argument(
        '--blocks',
        type=open,
        default='Blocks.txt',
        help="Blocks.txt file"
    )
    parser.add_argument(
        '--data',
        type=open,
        default='UnicodeData.txt',
        help='UnicodeData.txt file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='./out/',
        help='Output folder'
    )
    parser.add_argument(
        '--version',
        type=str,
        default=default_version(),
        help='Version of the generated packages'
    )

    args = parser.parse_args()

    blocks = parse_blocks(args.blocks)
    args.blocks.close()

    process_data(args.data, blocks, args.output, args.version)
    args.data.close()

if __name__ == '__main__':
    main()

