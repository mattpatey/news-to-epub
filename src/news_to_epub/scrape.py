#!/usr/bin/env python


from __future__ import print_function

import argparse
from ConfigParser import SafeConfigParser
from datetime import datetime
from json import loads
import os
import sys

from ebooklib import epub
import requests


def render_chapter(title, contents, publication_date):
    safe_title = u''.join([c for c in title if c.isalpha() or c.isspace()]).replace(u' ', u'-')
    file_name = u'chapter-{}.xhtml'.format(safe_title)
    chapter = epub.EpubHtml(title=title, file_name=file_name, lang='en')
    chapter.content = u'<h1>{}</h1><h6>{}</h6>{}'.format(title, publication_date, contents)
    return chapter

def make_ebook(title, articles):
    chapters = [render_chapter(c['title'], c['content'], c['date']) for c in articles]

    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')

    date = datetime.now().strftime(u'%A %d %B %Y')
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
    parser.add_argument('--output-path', type=str, default='~', help='Path to where the .epub file will be written, e. g. ~/Desktop')
    args = parser.parse_args()

    config_filepath = os.path.expanduser('~/news_to_epub.cfg')
    try:
        config = read_config(config_filepath)
    except IOError:
        msg = "Couldn't find configuration file {}".format(config_filepath)
        print(msg)
        sys.exit(1)

    if args.from_date:
        from_date = datetime.strptime(args.from_date, '%Y-%m-%d')
    else:
        from_date = datetime.now()

    from www_guardian_com import get_content

    try:
        articles = get_content(from_date, config.items('www_guardian_com'))
    except Exception, e:
        print(e)
        sys.exit(1)

    date = datetime.now().strftime(u'%A %d %B %Y')
    title = u'News for {}'.format(date)
    book = make_ebook(title, articles)
    safe_filename = u''.join([x for x in title if x.isalpha() or x.isspace() or x.isdigit()]).replace(u' ', u'-')
    filename = u'{}.epub'.format(safe_filename.lower())
    path = os.path.expanduser(args.output_path)
    filepath = os.path.join(path, filename)
    epub.write_epub(filepath, book, {})

def read_config(filepath):
    config = SafeConfigParser()
    with open(filepath, 'r') as c:
        config.readfp(c)
    return config

if __name__ == '__main__':
    main()
