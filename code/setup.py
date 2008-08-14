
# Here is a setup file

from setuptools import setup, find_packages

setup(
    name="cheshire3",
    version="1.0b1",
    packages = find_packages(),
    install_requires = ['lxml>=2.1'],

    author="Rob Sanderson, et al.",
    author_email="azaroth@liverpool.ac.uk",
    description="XML Search Engine and Information Analysis Engine",
    license="BSD",
    keywords="xml search information retrieval data mining",
    url="http://www.cheshire3.org/"
    )
