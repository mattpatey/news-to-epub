#!/usr/bin/env python


import argparse
from datetime import datetime
from itertools import chain
from json import loads

from bs4 import BeautifulSoup
from ebooklib import epub
import requests


def make_request(api_key, args=None):
    payload = { 'api-key': api_key }
    if args:
        payload.update(args)
    res = requests.get('http://content.guardianapis.com/search', params=payload)

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

def get_news(section, api_key, date=None):
    if date:
        d = datetime.strptime(date, '%Y-%m-%d')
    else:
        d = datetime.now()

    args = {'section': section,
            'from-date': d.strftime('%Y-%m-%d')}
    response = make_request(api_key, args)

    all_articles = []
    for page in xrange(1, response['pages']):
        args.update(page=page)
        response = make_request(api_key, args)
        articles = articles_from_response(response)
        all_articles.append(articles)

    all_articles = [i for i in chain(*all_articles)]

    return sorted(all_articles, key=lambda k: k['publication_date'])

def scrape(uri):
    response = requests.get(uri)
    soup = BeautifulSoup(response.text)
    content = soup.find('div', class_='content__article-body')
    filtered_content = content.find_all('p')
    processed_content = u''.join([unicode(x) for x in filtered_content])
    return processed_content

def make_article(title, date, content):
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

    safe_filename = u''.join([x for x in title if x.isalpha() or x.isspace() or x.isdigit()]).replace(u' ', u'-')
    filename = u'{}.epub'.format(safe_filename.lower())
    epub.write_epub(filename, book, {})

def main():
    parser = argparse.ArgumentParser("Transform news from The Guardian's website into an epub file.")
    parser.add_argument('api_key', type=str)
    parser.add_argument('--news-since', type=str, help='Fetch news since a specified date (YYYY-MM-DD)')
    args = parser.parse_args()
    articles = get_news('world', args.api_key, date=args.news_since)
    chapters = []
    for article in articles:
        date = datetime.strptime(article['publication_date'], "%Y-%m-%dT%H:%M:%SZ")
        content = scrape(article['url'])
        a = make_article(article['title'], date, content)
        chapters.append(a)
    date = datetime.now().strftime(u'%A %d %B %Y')
    book_title = u'News for {}'.format(date)
    make_ebook(book_title, chapters)

if __name__ == '__main__':
    main()
