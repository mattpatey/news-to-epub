from setuptools import setup, find_packages

setup(
    name = 'News2Epub',
    version = '1.0a',
    install_requires = [
        'EbookLib==0.15',
        'beautifulsoup4==4.3.2',
        'requests==2.6.0',
    ],

    author = 'Matt Patey',
    description = 'Convert news from The Guardian website into Epub format for reading on a BQ Cervantes2',
    license = 'MIT',
    url = 'https://github.com/mattpatey/news-to-epub',
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    entry_points = {
        'console_scripts': {
            'news2epub = news_to_epub.scrape:main',
        },
    },
)
