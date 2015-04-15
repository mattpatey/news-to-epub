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


def render_chapter(title, contents, publication_date):
    safe_title = u''.join([c for c in title if c.isalpha() or c.isspace()]).replace(u' ', u'-')
    file_name = u'chapter-{}.xhtml'.format(safe_title)
    chapter = epub.EpubHtml(title=title, file_name=file_name, lang='en')
    chapter.content = u'<h1>{}</h1><h6>{}</h6>{}'.format(title, publication_date, contents)
    return chapter

def make_ebook(title, articles):
    assert len(articles) > 0
    chapters = [render_chapter(c['title'], c['content'], c['date']) for c in articles]

    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')

    date = datetime.now().strftime('%A %d %B %Y')
    section_name = u'Headlines for {}'.format(date) 
    book.toc = ((epub.Link(c.file_name, c.title, c.title) for c in chapters),
                (epub.Section(section_name), chapters))

    for c in chapters:
        book.add_item(c)

    book.spine = ['nav'] + chapters
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
    try:
        for article in get_content(from_date, config.items('www_guardian_com')):
            if get_article_hash('www_guardian_com', article) not in published_articles:
                articles['www_guardian_com'].append(article)
            else:
                msg = u'Skipping already published article "{}".'.format(article['title'])
                logger.debug(msg)
    except Exception, e:
        logger.error(e)
        sys.exit(1)

    if len(articles['www_guardian_com']) == 0:
        logger.info(u'No articles to publish. Exiting.')
        sys.exit(0)

    # Generate the .epub file for reader devices
    # 
    date = datetime.now().strftime(u'%A %d %B %Y')
    title = u'News for {}'.format(date)
    book = make_ebook(title, articles['www_guardian_com'])
    safe_filename = u''.join([x for x in title if x.isalpha() or x.isspace() or x.isdigit()]).replace(u' ', u'-')
    filename = u'{}.epub'.format(safe_filename.lower())
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
