#!/usr/bin/env python


from datetime import datetime
from json import loads

from bs4 import BeautifulSoup
from ebooklib import epub
import requests


def get_todays_news():
    api_key = ''
    payload = {'api-key': api_key,
               'section': 'world',
               'from-date': '2015-03-22'}
    r = requests.get('http://content.guardianapis.com/search', params=payload)
    json = loads(r.text)
    articles = [(x['webTitle'], x['webUrl']) for x in json['response']['results']]
    return articles

def scrape(uri):
    response = requests.get(uri)
    soup = BeautifulSoup(response.text)
    content = soup.find('div', class_='content__article-body')
    filtered_content = content.find_all('p')
    processed_content = u''.join([unicode(x) for x in filtered_content])
    return processed_content

def make_chapter(title, content):
    safe_title = u''.join([x for x in title if x.isalpha() or x.isspace()]).replace(u' ', u'-')
    file_name = u'chapter-{}.xhtml'.format(safe_title)
    chapter = epub.EpubHtml(title=title, file_name=file_name, lang='en')
    chapter.content = u'<h1>{}</h1>{}'.format(title, content)
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
    uris = get_todays_news()
    chapters = []
    for title, raw_content in uris:
        processed_content = scrape(raw_content)
        chapter = make_chapter(title, processed_content)
        chapters.append(chapter)
    date = datetime.now().strftime(u'%A %d %B %Y')
    book_title = u'News for {}'.format(date)
    make_ebook(book_title, chapters)

if __name__ == '__main__':
    main()
