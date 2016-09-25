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
    args = ['c++filt', '-n']
    args.extend(names)
    pipe = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, _ = pipe.communicate()
    demangled = stdout.decode('utf-8').split("\n")

    # Each line ends with a newline, so the final entry of the split output
    # will always be ''.
    assert len(demangled) == len(names)+1
    return demangled[:-1]


def sizeof_fmt(num, suffix='B'):
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

    # Symbols with their sizes
    symbols = []

    def __init__(self, filename):
        click.echo(click.style("Processing ", fg='green') + click.style(filename, fg='yellow'))
        self.parse_file(filename)

    def machine_description(self, elf_file):
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

    def process_symbol(self, symbol):
        self.total_size += symbol.entry.st_size
        if symbol.entry.st_size > 0:
            self.symbols.append((symbol.name, symbol.entry.st_size))

    def print_symbol_sizes(self):
        self.symbols.sort(key=lambda value: value[1], reverse=True)
        demangled_symbols = zip(demangle([symbol for symbol, _ in self.symbols[:100]]), [size for _, size in self.symbols[:200]])
        max_digits = len(str(self.symbols[0][1]))
        fmt_string = click.style("** ", fg="green") + click.style("{: <" + str(max_digits) + "}", fg="yellow") + \
                     click.style(" : ", fg="green") + "{}"


        lexer = CppLexer()
        formatter = Terminal256Formatter()
        for symbol, size in demangled_symbols:
            print(fmt_string.format(size, highlight(symbol, lexer, formatter).rstrip()))

    def parse_file(self, filename):
        with open(filename, 'rb') as file:
            elf_file = ELFFile(file)
            # Identify architecture and bitness
            self.architecture = self.machine_description(elf_file)
            click.echo(click.style("Architecture: ", fg='green') + click.style(str(self.architecture), fg='yellow') + "\n")

            for sect in elf_file.iter_sections():
                if isinstance(sect, SymbolTableSection):
                    with click.progressbar(sect.iter_symbols(), length=sect.num_symbols(), label="Processing {}".format(sect.name)) as symbols:
                        for symbol in symbols:
                            self.process_symbol(symbol)
                elif isinstance(sect, StringTableSection):
                    # Ignore debug string sections
                    if sect.name == ".strtab":
                        continue
                    self.total_strings += sect.header.sh_size
                elif sect.name == ".rodata":
                    self.total_constants += sect.header.sh_size

            click.secho("Done!\n", fg="green")
            click.secho("Symbol sizes:", fg="green")
            click.secho("=============", fg="green")
            self.print_symbol_sizes()
            click.echo("\n")
            click.secho("=============", fg="green")
            click.echo(click.style("Total size of symbols: ", fg="green") + click.style(sizeof_fmt(self.total_size), fg="yellow"))
            click.echo(click.style("Total size of strings: ", fg="green") + click.style(sizeof_fmt(self.total_strings), fg="yellow"))
            click.echo(click.style("Total size of constants: ", fg="green") + click.style(sizeof_fmt(self.total_constants), fg="yellow"))
            click.secho("=============", fg="green")
            click.echo(click.style("Filesize: ", fg="green") + click.style(sizeof_fmt(self.total_size + self.total_strings + self.total_constants), fg="yellow"))
            click.secho("=============", fg="green")

if __name__ == "__main__":
    click.secho("\nNDK library size analyzer, v1.0", fg="green")
    filename = sys.argv[1]

    try:
        AndroidLibrary(filename)
    except KeyboardInterrupt as e:
        click.secho("Cancelled!", fg="red")
        sys.exit(-1)
