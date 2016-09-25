#! /usr/bin/env python3
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
        fmt_string = "- {: <" + str(max_digits) + "} : {}"

        for symbol, size in demangled_symbols:
            print(fmt_string.format(size, symbol))

    def parse_file(self, filename):
        with open(filename, 'rb') as file:
            elf_file = ELFFile(file)
            # Identify architecture and bitness
            self.architecture = self.machine_description(elf_file)
            print("Architecture: {}".format(self.architecture))

            for sect in elf_file.iter_sections():
                if isinstance(sect, SymbolTableSection):
                    for symbol in sect.iter_symbols():
                        self.process_symbol(symbol)
                elif isinstance(sect, StringTableSection):
                    # Ignore debug string sections
                    if sect.name == ".strtab":
                        continue
                    self.total_strings += sect.header.sh_size
                elif sect.name == ".rodata":
                    self.total_constants += sect.header.sh_size

            print("=====")
            self.print_symbol_sizes()
            print("=====")
            print("Total size of symbols: {} / [{}]".format(sizeof_fmt(self.total_size), len(self.symbols)))
            print("Total size of strings: {}".format(sizeof_fmt(self.total_strings)))
            print("Total size of constants: {}".format(sizeof_fmt(self.total_constants)))
            print("=====")
            print("Filesize: {}".format(sizeof_fmt(self.total_size + self.total_strings + self.total_constants)))


if __name__ == "__main__":
    filename = sys.argv[1]
    AndroidLibrary(filename)
