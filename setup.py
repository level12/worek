import os.path as osp
from setuptools import setup, find_packages

cdir = osp.abspath(osp.dirname(__file__))
README = open(osp.join(cdir, 'readme.rst')).read()
CHANGELOG = open(osp.join(cdir, 'changelog.rst')).read()

version_fpath = osp.join(cdir, 'worek', 'version.py')
version_globals = {}

with open(version_fpath) as fo:
    exec(fo.read(), version_globals)

setup(
    name="worek",
    version=version_globals['VERSION'],
    description=("Database Backup Command Line Utility"),
    long_description='\n\n'.join((README, CHANGELOG)),
    author="Nick Zaccardi",
    author_email="nick.zaccardi@level12.io",
    url='https://github.com/level12/worek',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
    ],
    license='BSD',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'sqlalchemy',
        'click',
        'psycopg2-binary',
    ],
    extras_require={
        'ci': [
            'pytest',
            'pytest-cov',
            'flake8',
            'check-manifest',
            'docutils',
        ]
    },
    entry_points='''
        [console_scripts]
        worek=worek.cli:cli
    '''
)
