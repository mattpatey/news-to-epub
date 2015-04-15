

from datetime import datetime
from itertools import chain
from json import loads
import logging
import os 

from bs4 import BeautifulSoup
import requests


logger = logging.getLogger(__file__)


def is_live_article(article):
    id = article['id'].split('/')
    if id[1] == 'live':
        return True

def scrape(uri):
    response = requests.get(uri)
    soup = BeautifulSoup(response.text)
    content = soup.find('div', class_='content__article-body')
    filtered_content = content.find_all('p')
    processed_content = u''.join([unicode(x) for x in filtered_content])
    return processed_content

def articles_from_response(res):
    collated_articles = []
    num_results = len(res['results'])
    for n, article in enumerate(res['results'], start=1):
        if is_live_article(article):
            continue
        article = dict(title=article['webTitle'],
                       publication_date=article['webPublicationDate'],
                       url=article['webUrl'],)
        collated_articles.append(article)
    return collated_articles

def call_api(api_args):
    res = requests.get('http://content.guardianapis.com/search', params=api_args)
    res.raise_for_status()
    return loads(res.text)['response']

def get_content(from_date, config):
    try:
        api_args = dict(config)
        api_args.update({'from-date': from_date.isoformat()})
        response = call_api(api_args)
    except requests.exceptions.HTTPError, e:
        error_msg = loads(e.response.text)['response']['message']
        msg = '{}: {}'.format(error_msg, e.request.url)
        logger.error(msg)
        raise

    all_articles = []
    for page in xrange(1, response['pages'] + 1):
        response = call_api(dict(api_args, page=page))
        articles = articles_from_response(response)
        all_articles.append(articles)
        
    all_articles = [i for i in chain(*all_articles)]

    chapters = []
    for article in sorted(all_articles, key=lambda k: k['publication_date']):
        date = datetime.strptime(article['publication_date'], "%Y-%m-%dT%H:%M:%SZ")
        content = scrape(article['url'])
        article = dict(title=article['title'], date=date, content=content)
        chapters.append(article)

    return chapters
