#!/usr/bin/env python3

import argparse
from datetime import date
import re

"""Helper map for roman number convertion"""
numeral_map = (
    (1000,  'M'),
    ( 900, 'CM'),
    ( 500,  'D'),
    ( 400, 'CD'),
    ( 100,  'C'),
    (  90, 'XC'),
    (  50,  'L'),
    (  40, 'XL'),
    (  10,  'X'),
    (   9, 'IX'),
    (   5,  'V'),
    (   4, 'IV'),
    (   1,  'I')
)

def int_to_roman(i):
    """Converts integer to roman number string

    Args:
        i: positive integer

    Returns:
        Roman string representation

    """
    result = []

    for integer, numeral in numeral_map:
        count = i // integer
        result.append(numeral * count)
        i -= integer * count

    return ''.join(result)

def default_date():
    """Creates date string according to the current date

    Returns:
        default date string

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

def convert_number(s):
    """Converts number to LaTeX name parts

    Args:
        s: positive integer

    Returns:
        String containing LaTeX name parts

    """
    return ' ' + ' '.join(list(int_to_roman(s))) + ' '

def convert_name(s, specials=False):
    """Converts an entire name by appending its parts

    Args:
        s: unescaped python string containing all parts of the name
        specials: if True, special characters get converted to strings

    Returns:
        LaTeX compatible name

    """
    # convert special characters to string representations
    if specials:
        s = s.replace('-', ' Minus ')

    # convert numbers to roman strings
    s = re.sub(r"[0-9]+", lambda x: convert_number(int(x.group(0))), s)

    # strip all illegal characters
    s = re.sub(r"[^a-zA-Z\s]", '', s)

    # remove unnecessary whitespaces
    s = s.strip()
    s = re.sub(r"\s+", ' ', s)

    # build one string of all words
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
    return 'USymbol' + convert_name(s, False)

def symbol_name(s):
    """Converts a string to a LaTeX symbol name

    Args:
        s: unescaped python string

    Returns:
        LaTeX symbol name

    """
    return 'USymbol' + convert_name(s, True)

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

def create_new_package(name, dout, version, date, description, fall=None):
    """Creates a new LaTeX package

    Args:
        name: unescaped package name
        dout: output directory
        version: package version string
        date: package date (YYYY/MM/DD)
        description: package description
        fall: LaTeX package that collects all packages (metapackage)

    Returns:
        File handler of the new LaTeX package file

    """
    print(name + ': ', end='')
    pname = package_name(name)

    f = open(dout + '/' + pname + '.sty', 'w')

    f.write('\\NeedsTeXFormat{LaTeX2e}\n')
    f.write('\\ProvidesPackage{' + pname + '}[' + date + ' v' + version + ' ' + description + ']\n')

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

def finalize_package(f):
    """Write final LaTeX package data and close stream

    Args:
        f: LaTeX file

    """
    if f:
        print_header('end', f)
        f.write('\\endinput\n')
        f.close()
        print('done')

def print_symbol(f, name, hnumber):
    """Prints a symbol definition to a LaTeX file

    Args:
        f: LaTeX file
        name: escpaed symbol name
        hnumber: hexnumber string

    """
    f.write('\\newcommand{\\' + name + '}{\\symbol{"' + hnumber + '}}\n')

def process_data(fdata, blocks, dout, version, date):
    """Processes UnicodeData.txt

    Args:
        fdata: UnicodeData.txt file handler
        blocks: parsed blocks
        dout: output directory
        version: package version string
        date: date string (YYYY/MM/DD)

    """
    print('')
    print('---Process data---')
    fall = create_new_package(
        name='all',
        dout=dout,
        version=version,
        date=date,
        description='Provides macros for all Unicode symbols'
    )
    f = None
    it = iter(blocks)
    end = None
    index = {}

    for l in fdata:
        a = l.split(';')
        hnumber = a[0]
        name1 = a[1]
        name2 = a[10]
        name = symbol_name(name1 + ' ' + name2)

        # prevent duplicate names
        while name in index:
            index[name] += 1
            name += convert_name(str(index[name]))
        index[name] = 1

        if (not f) or (int(hnumber, 16) > end):
            finalize_package(f)

            block = next(it)
            end = block['end']
            f = create_new_package(
                name=block['name'],
                dout=dout,
                version=version,
                date=date,
                description='Provides macros for Unicode symbols of block ' + block['name'],
                fall=fall
            )

        print_symbol(f, name, hnumber)

    finalize_package(f)
    fall.close()

def main():
    parser = argparse.ArgumentParser(
        description='Creates Unicode symbol macros for LuaLaTeX and XeLaTeX',
        epilog='To get the required files, go to http://www.unicode.org/Public/UCD/latest/ucd/',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
        '--date',
        type=str,
        default=default_date(),
        help='Date of the generated packages (YYYY/MM/DDD)'
    )
    parser.add_argument(
        '--version',
        type=str,
        default="1.0",
        help='Version of the generated packages'
    )

    args = parser.parse_args()

    blocks = parse_blocks(args.blocks)
    args.blocks.close()

    process_data(
        fdata=args.data,
        blocks=blocks,
        dout=args.output,
        version=args.version,
        date=args.date
    )
    args.data.close()

if __name__ == '__main__':
    main()

