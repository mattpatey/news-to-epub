#!/usr/bin/env python


from __future__ import print_function

import argparse
from collections import defaultdict
from ConfigParser import SafeConfigParser
from cPickle import (
    dump as pdump,
    loads as ploads,
    Pickler,
    Unpickler,
)
from datetime import datetime
import hashlib
from itertools import chain
from json import loads
import logging
import os
import sys

from ebooklib import epub
import requests

from www_guardian_com import SourceWwwGuardianCom


logger = logging.getLogger()


def safe_filename(name):
    safe_name = u''.join([c for c in name if c.isalpha() or c.isspace() or c.isdigit()])
    safe_name = safe_name.replace(u' ', u'-')

    return safe_name.lower()

def make_ebook(title, contents):
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')

    sections = []
    chapters = []
    for name, articles in contents.items():
        section_chapters = []
        for a in sorted(articles, key=lambda a: a['date']):
            safe_title = safe_filename(a['title'])
            file_name = u'chapter-{}.xhtml'.format(safe_title)
            chapter = epub.EpubHtml(title=a['title'], file_name=file_name, lang='en')
            chapter.content = u'<h1>{}</h1><h6>{}</h6>{}<span epub:type="pagebreak"></span>'.format(a['title'], a['date'], a['content'])
            section_chapters.append(chapter)
            book.add_item(chapter)
        sections.append((name, section_chapters))
        chapters.append(section_chapters)

    book.toc = ([(epub.Section(n), c) for n, c in sections])
    book.spine = ['nav'] + [c for c in chain(*chapters)]
    book.add_item(epub.EpubNcx())

    return book

def configure_logging(level=logging.WARN):
    if level == 'debug':
        level = logging.DEBUG
    elif level == 'error':
        level = logging.ERROR
    elif level == 'warn':
        level = logging.WARN
    elif level == 'info':
        level = logging.INFO

    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def configure_news2epub():
    config_filepath = os.path.expanduser('~/news_to_epub.cfg')
    config = SafeConfigParser()
    try:
        with open(config_filepath, 'r') as c:
            config.readfp(c)
    except IOError:
        msg = "Couldn't find configuration file {}".format(config_filepath)
        raise

    return config

def fetch_content(sources, pickle_file):
    # Fetch articles from news source(s)
    #
    articles = defaultdict(list)

    try:
        published_articles = get_published_articles(pickle_file)
    except IOError:
        published_articles = []

    for source in sources:
        # get_content should return a dict with the keys `title`,
        # `date`, and `content`
        for article in source.get_content():
            if get_article_hash(source.name, article) not in published_articles:
                articles[source.name].append(article)
            else:
                msg = u'Skipping already published article "{}".'.format(article['title'])
                logger.warn(msg)

    return articles

def create_epub_file(articles, output_path):
    date = datetime.now().strftime(u'%A %d %B %Y')
    title = u'Reading for {}'.format(date)
    book = make_ebook(title, articles)
    filename = '{}.epub'.format(safe_filename(title))
    path = os.path.expanduser(output_path)
    filepath = os.path.join(path, filename)
    epub.write_epub(filepath, book, {})

    return filepath

def update_article_archive(articles, pickle_file):
    new_hashes = []
    for source, source_articles in articles.items():
        for article in source_articles:
            article_hash = get_article_hash(source, article)
            new_hashes.append(article_hash)

    try:
        published_articles = set(get_published_articles(pickle_file))
    except IOError:
        published_articles = set([])

    published_articles.update(new_hashes)

    with open(pickle_file, 'wb') as pf:
        pickler = Pickler(pf)
        pickler.dump(published_articles)

def get_article_hash(source, article):
    article_key = u'{}_{}_{}'.format(source, unicode(article['date'].isoformat()), article['title'])
    article_hash = hashlib.md5(article_key.encode('utf-8'))
    return article_hash.hexdigest()

def get_published_articles(pickle_file):
    with open(pickle_file, 'rb') as pf:
        upickler = Unpickler(pf)
        published_hashes = upickler.load()

    return published_hashes


def main():
    parser = argparse.ArgumentParser("Transform news from the web into an epub file.")
    parser.add_argument('--loglevel', type=str, default='warn', help='Log level. Valid values include: debug, error, warn, info. Default: warn.')
    parser.add_argument('--output-path', type=str, default='~', help='Path to where the .epub file will be written, e. g. ~/Desktop')
    args = parser.parse_args()

    configure_logging(args.loglevel)
    config = configure_news2epub()

    archive = os.path.expanduser('~/news_to_epub.pkl')
    content = fetch_content([
        SourceWwwGuardianCom(config.get('www_guardian_com', 'api_key')),
    ], archive)
    create_epub_file(content, args.output_path)
    update_article_archive(content, archive)

if __name__ == '__main__':
    main()
