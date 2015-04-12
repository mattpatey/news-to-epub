#!/usr/bin/env python


from __future__ import print_function

import argparse
from datetime import datetime
from itertools import chain
from json import loads
import os
import sys

from bs4 import BeautifulSoup
from ebooklib import epub
import requests


def call_api(api_args):
    res = requests.get('http://content.guardianapis.com/search', params=api_args)
    res.raise_for_status()
    return loads(res.text)['response']

def is_live_article(article):
    id = article['id'].split('/')
    if id[1] == 'live':
        return True

def articles_from_response(res):
    collated_articles = []
    for article in res['results']:
        if is_live_article(article):
            continue

        article = dict(title=article['webTitle'],
                       publication_date=article['webPublicationDate'],
                       url=article['webUrl'],)
        collated_articles.append(article)

    return collated_articles

def get_content(api_args):
    response = call_api(dict(api_args))
    all_articles = []
    for page in xrange(1, response['pages'] + 1):
        response = call_api(dict(api_args, page=page))
        articles = articles_from_response(response)
        all_articles.append(articles)

    all_articles = [i for i in chain(*all_articles)]

    return all_articles

def scrape(uri):
    response = requests.get(uri)
    soup = BeautifulSoup(response.text)
    content = soup.find('div', class_='content__article-body')
    filtered_content = content.find_all('p')
    processed_content = u''.join([unicode(x) for x in filtered_content])
    return processed_content

def scrape_articles(articles):
    chapters = []
    for article in sorted(articles, key=lambda k: k['publication_date']):
        date = datetime.strptime(article['publication_date'], "%Y-%m-%dT%H:%M:%SZ")
        content = scrape(article['url'])
        article_html = render_article(article['title'], date, content)
        chapters.append(article_html)
    return chapters

def render_article(title, date, content):
    safe_title = u''.join([x for x in title if x.isalpha() or x.isspace()]).replace(u' ', u'-')
    file_name = u'chapter-{}.xhtml'.format(safe_title)
    chapter = epub.EpubHtml(title=title, file_name=file_name, lang='en')
    chapter.content = u'<h1>{}</h1><h6>{}</h6>{}'.format(title, date, content)
    return chapter

def make_ebook(title, chapters):
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
    parser.add_argument('api_key', type=str)
    parser.add_argument('--from', dest='from_date', type=str, help='Fetch news since a specified date (YYYY-MM-DD)')
    parser.add_argument('--output-path', type=str, default='~', help='Path to where the .epub file will be written, e. g. ~/Desktop')
    args = parser.parse_args()

    if args.from_date:
        from_date = datetime.strptime(args.from_date, '%Y-%m-%d')
    else:
        from_date = datetime.now()
    api_args = (
        ('api-key', args.api_key),
        ('section', 'world'),
        ('from-date', from_date.isoformat()),
    )

    try:
        content = get_content(api_args)
    except requests.exceptions.HTTPError, e:
        error_msg = loads(e.response.text)['response']['message']
        msg = '{}: {}'.format(error_msg, e.request.url)
        print(msg)
        sys.exit(1)

    articles = scrape_articles(content)
    date = datetime.now().strftime(u'%A %d %B %Y')
    title = u'News for {}'.format(date)
    book = make_ebook(title, articles)

    safe_filename = u''.join([x for x in title if x.isalpha() or x.isspace() or x.isdigit()]).replace(u' ', u'-')
    filename = u'{}.epub'.format(safe_filename.lower())
    path = os.path.expanduser(args.output_path)
    filepath = os.path.join(path, filename)
    epub.write_epub(filepath, book, {})

if __name__ == '__main__':
    main()
