import sys
from setuptools import setup
from ndk_size_analyzer.version import VERSION

requirements = ['click==4.1', 'pyelftools==0.24', 'Pygments==2.1.3']

if sys.version_info < (3, 4):
    # We need to barkport enums for Python < 3.4
    requirements.append('enum34')

setup(
    name='android-ndk_size_analyzer',
    version=VERSION,
    packages=['ndk_size_analyzer'],
    url='',
    license='',
    author='Jernej Virag',
    author_email='jernej@virag.si',
    description='Simple size ndk_size_analyzer for Android NDK library files',
    install_requires=requirements,
    entry_points='''
        [console_scripts]
        ndk-size-analyzer=ndk_size_analyzer.analyzer:process
    '''
)
