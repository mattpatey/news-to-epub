

from datetime import datetime
from functools import partial
from json import loads
import logging

import requests


logger = logging.getLogger()

def search(api_args, **kwargs):
    merged_args = dict(api_args, **kwargs)
    logger.debug('Performing Guardian API search')
    res = requests.get('http://content.guardianapis.com/search', params=merged_args)
    res.raise_for_status()
    logger.debug('Converting JSON')
    return loads(res.text)['response']

def all_pages(search_func, articles_per_page=10, max_pages=100):
    res = search_func(page=1, pageSize=1)
    for i in xrange(1, min(res['pages'] + 1, max_pages)):
        logger.debug('Yielding page {}'.format(i))
        try:
            yield search_func(page=i, pageSize=articles_per_page)
        except requests.exceptions.HTTPError, e:
            error_msg = loads(e.res.text)['response']['message']
            msg = '{}: {}'.format(error_msg, e.request.url)
            logger.error(msg)
            raise

def excluded_article(article):
    # Skip some content based on certain URL patterns
    return any(s in article['id'] for s in ['observer-sudoku', '/crosswords/', '/live/'])

def collate(search_func):
    articles = []

    for page in all_pages(search_func, max_pages=2):
        for article in page['results']:
            if excluded_article(article):
                logger.warn('Skipping article "{}".'.format(article['webUrl']))
                continue
            else:
                title = article['webTitle']
                date = datetime.strptime(article['webPublicationDate'], "%Y-%m-%dT%H:%M:%SZ")
                sectionId = article['sectionId']
                try:
                    content = article['blocks']['body'][0]['bodyHtml']
                except IndexError:
                    logger.error('Failed to extract text from article {}'.format(article['webTitle']))
                    continue
                articles.append(dict(title=title, date=date, content=content, section=sectionId))

    return articles

def get_content(config):
    # TODO: Document valid structure and content for `config`
    search_args = dict(config)

    search_func = partial(search, search_args)
    articles = collate(search_func)

    return articles
