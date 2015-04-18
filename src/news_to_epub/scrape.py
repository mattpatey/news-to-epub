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
from json import loads
import logging
import os
import sys

from ebooklib import epub
import requests


logger = logging.getLogger()


def safe_filename(name):
    safe_name = u''.join([c for c in name if c.isalpha() or c.isspace() or c.isdigit()])
    safe_name = safe_name.replace(u' ', u'-')

    return safe_name.lower()
    
def render_chapter(title, contents, publication_date):
    safe_title = safe_filename(title)
    file_name = u'chapter-{}.xhtml'.format(safe_title)
    chapter = epub.EpubHtml(title=title, file_name=file_name, lang='en')
    chapter.content = u'<h1>{}</h1><h6>{}</h6>{}'.format(title, publication_date, contents())

    return chapter

def render_section(name, articles):
    sorted_articles = sorted(articles, key=lambda a: a['date'])
    chapters = [render_chapter(a['title'], a['content'], a['date']) for a in sorted_articles]

    return name, chapters

def make_ebook(title, sections):
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')
    all_sections = [render_section(k, v) for k, v in sections.items()]
    book.toc = ([(epub.Section(s), c) for s, c in all_sections])
    all_chapters = []
    for s in all_sections:
        for c in s[1]:
            all_chapters.append(c)
            book.add_item(c)
    book.spine = ['nav'] + all_chapters
    book.add_item(epub.EpubNcx())

    return book

def main():
    parser = argparse.ArgumentParser("Transform news from The Guardian's website into an epub file.")
    parser.add_argument('--from', dest='from_date', type=str, help='Fetch news since a specified date (YYYY-MM-DD)')
    parser.add_argument('--loglevel', type=str, default='warn', help='Log level. Valid values include: debug, error, warn, info. Default: warn.')
    parser.add_argument('--output-path', type=str, default='~', help='Path to where the .epub file will be written, e. g. ~/Desktop')
    args = parser.parse_args()

    if args.from_date:
        from_date = datetime.strptime(args.from_date, '%Y-%m-%d')
    else:
        from_date = datetime.now()

    if args.loglevel == 'debug':
        level = logging.DEBUG    
    elif args.loglevel == 'error':
        level = logging.ERROR
    elif args.loglevel == 'warn':
        level = logging.WARN
    elif args.loglevel == 'info':
        level = logging.INFO
    else:
        print(u"Invalid log level '{}'. Using default value.".format(args.loglevel))
        level = logging.WARN

    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    config_filepath = os.path.expanduser('~/news_to_epub.cfg')
    try:
        config = SafeConfigParser()
        with open(config_filepath, 'r') as c:
            config.readfp(c)
    except IOError:
        msg = "Couldn't find configuration file {}".format(config_filepath)
        logger.error(msg)
        sys.exit(1)

    # Fetch articles from news source(s)
    # 
    articles = defaultdict(list)
    pickle_file = os.path.expanduser('~/news_to_epub.pkl')

    try:
        published_articles = get_published_articles(pickle_file)
    except IOError:
        published_articles = []

    from www_guardian_com import get_content
    for article in get_content(from_date, config.items('www_guardian_com')):
        if get_article_hash('www_guardian_com', article) not in published_articles:
            articles['www_guardian_com'].append(article)
        else:
            msg = u'Skipping already published article "{}".'.format(article['title'])
            logger.warn(msg)

    if sum(map(len, articles.values())) == 0:
        logger.warn(u'No articles to publish. Exiting.')
        sys.exit(0)

    # Generate the .epub file for reader devices
    # 
    date = datetime.now().strftime(u'%A %d %B %Y')
    title = u'Reading for {}'.format(date)
    book = make_ebook(title, articles)
    filename = '{}.epub'.format(safe_filename(title))
    path = os.path.expanduser(args.output_path)
    filepath = os.path.join(path, filename)
    epub.write_epub(filepath, book, {})

    # Update pickle with hashes of articles we just published.
    #
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

if __name__ == '__main__':
    main()
