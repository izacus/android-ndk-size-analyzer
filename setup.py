from distutils.core import setup

setup(
    name='android-ndk-size-analyzer',
    version='1.0',
    packages=[''],
    url='',
    license='',
    author='Jernej Virag',
    author_email='jernej@virag.si',
    description='Simple size analyzer for Android NDK library files',
    requires=['click', 'pyelftools', 'pygments']
)
