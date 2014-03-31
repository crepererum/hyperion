#!/usr/bin/env python3

import argparse
from datetime import date
import os
import re

"""Helper map for roman number convertion"""
NUMERAL_MAP = (
    (10000000, 'S'),
    (9000000, 'FS'),
    (5000000, 'T'),
    (4000000, 'FT'),
    (1000000, 'F'),
    (900000, 'AF'),
    (500000, 'G'),
    (400000, 'AG'),
    (100000, 'A'),
    (90000, 'ZA'),
    (50000, 'B'),
    (40000, 'ZB'),
    (10000, 'Z'),
    (9000, 'MZ'),
    (5000, 'Y'),
    (4000, 'MY'),
    (1000, 'M'),
    (900, 'CM'),
    (500, 'D'),
    (400, 'CD'),
    (100, 'C'),
    (90, 'XC'),
    (50, 'L'),
    (40, 'XL'),
    (10, 'X'),
    (9, 'IX'),
    (5, 'V'),
    (4, 'IV'),
    (1, 'I')
)


def int_to_roman(i):
    """Converts integer to roman number string

    Args:
        i: positive integer

    Returns:
        Roman string representation

    """
    result = []

    for integer, numeral in NUMERAL_MAP:
        count = i // integer
        result.append(numeral * count)
        i -= integer * count

    return ''.join(result)


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
    a = map(lambda x: x[0].upper() + x[1:].lower(), a)
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


def create_new_package(
        pname,
        dout,
        version,
        date,
        description,
        fdocall=None,
        fall=None
        ):
    """Creates a new LaTeX package

    Args:
        pname: escaped package name
        dout: output directory
        version: package version string
        date: package date (YYYY/MM/DD)
        description: package description
        fdocall: main documentation .tex file
        fall: LaTeX package that collects all packages (metapackage)

    Returns:
        File handler of the new LaTeX package file

    """
    f = open(dout + '/' + pname + '.sty', 'w')
    fdoc = open(dout + '/' + pname + '.tex', 'w')

    f.write(
        '\\NeedsTeXFormat{{LaTeX2e}}\n'
        '\\ProvidesPackage{{{0}}}[{1} v{2} {3}]\n'
        .format(pname, date, version, description)
    )

    print_header('requirements', f)
    f.write(
        '\\RequirePackage{{ifluatex}}\n'
        '\\RequirePackage{{ifxetex}}\n'
        '\\ifluatex\n'
        '\\else\n'
        '\\ifxetex\n'
        '\\else\n'
        '\\ClassError{{{0}}}{{LuaLaTeX or XeLaTeX required!}}%\n'
        '{{Please use LuaLaTeX or XeLaTeX. (no pdfTeX support, sorry)'
        'See http://www.luatex.org/ and http://xetex.sourceforge.net/}}\n'
        '\\fi\n'
        '\\fi\n'
        .format(pname)
    )

    if fall:
        fall.write(
            '\\RequirePackage{{{0}}}\n'
            .format(pname)
        )

        print_header('style', f)
        pall = package_name('all')
        f.write(
            '\\newcommand{{\\{0}@style}}[1]{{#1}}\n'
            '\\newcommand{{\\{0}Style}}[1]'
            '{{\\renewcommand{{\\{0}@style}}[1]{{{{#1##1}}}}}}\n'
            '\\@ifundefined{{{1}Style}}%\n'
            '{{%\n'
            '\\newcommand{{\\{1}Style}}[1]{{\\{0}Style{{#1}}}}%\n'
            '}}{{%\n'
            '\\let\\{0}@list\\{1}Style%\n'
            '\\renewcommand{{\\{1}Style}}[1]'
            '{{\\{0}Style{{#1}}\\{0}@list{{#1}}}}%\n'
            '}}\n'
            .format(pname, pall)
        )

        fdoc.write('\\section{' + pname + '}\n')
        fdocall.write('\\include{' + pname + '}\n')
    else:
        doc_begin(fdoc)

    print_header('symbols', f)

    return f, fdoc


def finalize_package(f, fdoc, all=False):
    """Write final LaTeX package data and close stream

    Args:
        f: LaTeX file
        fdoc: documentation .tex file
        all: True if f is the metapackage (all)

    """
    if f:
        print_header('end', f)
        f.write('\\endinput\n')
        f.close()
        print('done')

        if all:
            doc_end(fdoc)
        else:
            fdoc.write(
                '\\endinput\n'
                '\n'
            )
            fdoc.close()


def doc_begin(fdoc):
    """Creates new main documentation file

    Args:
        fdoc: documentation TeX file

    """
    fdoc.write(
        '\\documentclass{{hyperiondoc}}\n'
        '\n'
        '\\usepackage{{adjustbox}}\n'
        '\\usepackage{{{0}}}\n'
        '\\newfontfamily{{\\symbola}}{{Symbola}}\n'
        '\\USymbolAllStyle{{\\symbola}}\n'
        '\n'
        '\\newcommand{{\\symboldemo}}[3]{{%\n'
        '    \\noindent\\begin{{minipage}}[c]{{.1\\textwidth}}\n'
        '        \\centering\\textlarger[2]{{#3}}\n'
        '    \\end{{minipage}}%\n'
        '    \\begin{{minipage}}{{.8\\textwidth}}\n'
        '        $\\mathtt{{0x#1}}$\\\\[-0.4em]\n'
        '        \\adjustbox{{max width=.9\\textwidth}}{{\\code{{\\bs #2}}}}\n'
        '    \\end{{minipage}}\\\\[0.6em]\n'
        '}}\n'
        '\n'
        '\\begin{{document}}\n'
        .format(package_name('all'))
    )


def doc_end(fdoc):
    """Finalize and close documentation file

    Args:
        fdoc: documentation .tex file

    """
    fdoc.write('\\end{document}\n')
    fdoc.close()


def print_symbol(f, name, hnumber, pname, fdoc):
    """Prints a symbol definition to a LaTeX file

    Args:
        f: LaTeX file
        name: escpaed symbol name
        hnumber: hexnumber string
        pname: escaped package name
        fdoc: documentation .tex file

    """
    f.write(
        '\\newcommand{{\\{0}}}{{\\{1}@style{{\\symbol{{"{2}}}}}}}\n'
        .format(name, pname, hnumber)
    )
    fdoc.write(
        '\\symboldemo{{{0}}}{{{1}}}{{\\{1}}}\n'
        .format(hnumber, name)
    )


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
    fall, fdocall = create_new_package(
        pname=package_name('all'),
        dout=dout,
        version=version,
        date=date,
        description='Provides macros for all Unicode symbols',
    )
    f = None
    fdoc = None
    it = iter(blocks)
    end = None
    pname = None
    index = set()

    for l in fdata:
        # parse line
        a = l.split(';')
        hnumber = a[0]
        name1 = a[1]
        name2 = a[10]
        name_base = symbol_name(name1 + ' ' + name2)
        name = name_base

        # prevent duplicate names
        n = 1
        while name in index:
            n += 1
            name = name_base + convert_name(str(n))
        index.add(name)

        # next block?
        if (not f) or (int(hnumber, 16) > end):
            finalize_package(f, fdoc)

            block = next(it)
            print(block['name'] + ': ', end='')
            end = block['end']
            pname = package_name(block['name'])
            f, fdoc = create_new_package(
                pname=pname,
                dout=dout,
                version=version,
                date=date,
                description='Provides macros for Unicode symbols of block {0}'
                .format(block['name']),
                fall=fall,
                fdocall=fdocall
            )

        print_symbol(f, name, hnumber, pname, fdoc)

    finalize_package(f, fdoc)
    finalize_package(fall, fdocall, True)


def main():
    parser = argparse.ArgumentParser(
        description='Creates Unicode symbol macros for LuaLaTeX and XeLaTeX',
        epilog='To get the required files, go to'
        'http://www.unicode.org/Public/UCD/latest/ucd/',
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
        default=date.today().strftime('%Y/%m/%d'),
        help='Date of the generated packages (YYYY/MM/DDD)'
    )
    parser.add_argument(
        '--version',
        type=str,
        default="1.0",
        help='Version of the generated packages'
    )

    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

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
