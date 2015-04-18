

from datetime import datetime
from functools import partial
from json import loads
import logging

from bs4 import BeautifulSoup
import requests


logger = logging.getLogger()


def scrape(uri):
    response = requests.get(uri)
    soup = BeautifulSoup(response.text)
    content = soup.find('div', class_='content__article-body')
    filtered_content = content.find_all('p')
    processed_content = u''.join([unicode(i) for i in filtered_content])
    return processed_content

def collate_paginated_results(search_func, total_pages):
    articles = []

    for page in xrange(1, total_pages + 1):
        try: 
            response = search_func(page=page)
        except requests.exceptions.HTTPError, e:
            error_msg = loads(e.response.text)['response']['message']
            msg = '{}: {}'.format(error_msg, e.request.url)
            logger.error(msg)
            raise

        for article in response['results']:
            if '/live/' in article['id']:
                logger.warn('Skipping live updating article "{}".'.format(article['webUrl']))
                continue
            title = article['webTitle']
            date = datetime.strptime(article['webPublicationDate'], "%Y-%m-%dT%H:%M:%SZ")
            content = partial(scrape, article['webUrl'])
            articles.append(dict(title=title, date=date, content=content))

    return articles

def search(api_args, **kwargs):
    merged_args = dict(api_args, **kwargs)
    res = requests.get('http://content.guardianapis.com/search', params=merged_args)
    res.raise_for_status()
    return loads(res.text)['response']

def get_content(from_date, config):
    search_args = dict(config)
    search_args.update({'from-date': from_date.isoformat()})
    a_search = partial(search, search_args)

    try:
        response = a_search()
    except requests.exceptions.HTTPError, e:
        error_msg = loads(e.response.text)['response']['message']
        msg = '{}: {}'.format(error_msg, e.request.url)
        logger.error(msg)
        raise

    articles = collate_paginated_results(a_search, response['pages'])

    return articles
