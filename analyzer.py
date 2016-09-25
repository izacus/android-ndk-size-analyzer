#! /usr/bin/env python3

from pygments import highlight
from pygments.lexers.c_cpp import CppLexer
from pygments.formatters.terminal256 import Terminal256Formatter

import click
import subprocess
import sys
from enum import Enum

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection, StringTableSection


class Architecture(Enum):
    ARM_32 = 1
    ARM_64 = 2
    X86 = 3
    X86_64 = 4
    UNKNOWN = 99


def demangle(names):
    """
    Invokes c++filt command-line tool to demangle the C++ symbols into something readable. If not available,
    it'll do nothing and just return the input names.
    """
    try:
        args = ['c++filt', '-n']
        args.extend(names)
        pipe = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, _ = pipe.communicate()
        demangled = stdout.decode('utf-8').split("\n")

        # Each line ends with a newline, so the final entry of the split output
        # will always be ''.
        assert len(demangled) == len(names)+1
        return demangled[:-1]
    except OSError:
        return names


def sizeof_fmt(num, suffix='B'):
    """
    Formats passed integer number into human readable filesize, e.g. 15000000B into 15MiB.
    """
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class AndroidLibrary(object):
    architecture = Architecture.UNKNOWN

    total_size = 0
    total_strings = 0
    total_constants = 0

    # This is list of just top symbols
    top_symbols = []

    def __init__(self, filename, symbol_count):
        click.echo(click.style("Processing ", fg='green') + click.style(filename, fg='yellow'))
        self._parse_file(filename, symbol_count)
        click.secho("Done!\n", fg="green")

    @staticmethod
    def _machine_description(elf_file):
        """
        Determines architecture of the passed-in library file.
        """
        is_64_bit = elf_file.header.e_ident["EI_CLASS"] == "ELFCLASS64"
        arch = Architecture.UNKNOWN

        if is_64_bit:
            if elf_file.header.e_machine == "EM_ARM":
                arch = Architecture.ARM_64
            elif elf_file.header.e_machine == "EM_386":
                arch = Architecture.X86_64
        else:
            if elf_file.header.e_machine == "EM_ARM":
                arch = Architecture.ARM_32
            elif elf_file.header.e_machine == "EM_386":
                arch = Architecture.X86
        return arch

    def _process_symbol(self, symbols, symbol):
        """
        Handles a single symbol
        """
        self.total_size += symbol.entry.st_size
        if symbol.entry.st_size > 0:
            symbols.append((symbol.name, symbol.entry.st_size))

    def print_symbol_sizes(self):
        """
        Prints top list of symbols
        :return:
        """
        if len(self.top_symbols) == 0:
            return

        demangled_symbols = zip(demangle([symbol for symbol, _ in self.top_symbols]), [size for _, size in self.top_symbols])
        max_digits = len(str(self.top_symbols[0][1]))
        fmt_string = click.style("** ", fg="green") + click.style("{: <" + str(max_digits) + "}", fg="yellow") + \
                     click.style(" : ", fg="green") + "{}"

        lexer = CppLexer()
        formatter = Terminal256Formatter()
        for symbol, size in demangled_symbols:
            print(fmt_string.format(size, highlight(symbol, lexer, formatter).rstrip()))

    def print_statistics(self):
        click.secho("Symbol sizes:", fg="green")
        click.secho("=============", fg="green")
        self.print_symbol_sizes()
        click.echo("\n")
        click.secho("=============", fg="green")
        click.echo(
            click.style("Total size of symbols: ", fg="green") + click.style(sizeof_fmt(self.total_size), fg="yellow"))
        click.echo(click.style("Total size of strings: ", fg="green") + click.style(sizeof_fmt(self.total_strings),
                                                                                    fg="yellow"))
        click.echo(click.style("Total size of constants: ", fg="green") + click.style(sizeof_fmt(self.total_constants),
                                                                                      fg="yellow"))
        click.secho("=============", fg="green")
        click.echo(click.style("Filesize: ", fg="green") + click.style(
            sizeof_fmt(self.total_size + self.total_strings + self.total_constants), fg="yellow"))
        click.secho("=============", fg="green")

    def _parse_file(self, filename, symbol_count):
        """
        Parses the .so library file and determines sizes of all the symbols.
        """

        symbols = []
        with open(filename, 'rb') as file:
            elf_file = ELFFile(file)
            # Identify architecture and bitness
            self.architecture = AndroidLibrary._machine_description(elf_file)
            click.echo(click.style("Architecture: ", fg='green') + click.style(str(self.architecture), fg='yellow') + "\n")

            for sect in elf_file.iter_sections():
                if isinstance(sect, SymbolTableSection):
                    with click.progressbar(sect.iter_symbols(), length=sect.num_symbols(), label="Processing {}".format(sect.name)) as section_syms:
                        for symbol in section_syms:
                            self._process_symbol(symbols, symbol)
                elif isinstance(sect, StringTableSection):
                    # Ignore debug string sections, strtab is only present in debug libraries and size of those we're
                    # not interested in.
                    if sect.name == ".strtab":
                        continue
                    self.total_strings += sect.header.sh_size
                elif sect.name == ".rodata":
                    self.total_constants += sect.header.sh_size

        symbols.sort(key=lambda value: value[1], reverse=True)
        self.top_symbols = symbols[:symbol_count]


@click.command()
@click.argument("filename", nargs=1)
@click.option("--symbols", default=200, help="Number of symbols to list.")
def process(filename, symbols):
    click.secho("\nNDK library size analyzer, v1.0", fg="green")
    try:
        library = AndroidLibrary(filename, symbols)
        library.print_statistics()
    except KeyboardInterrupt:
        click.secho("Cancelled!", fg="red")
        sys.exit(-1)


if __name__ == "__main__":
    process()
