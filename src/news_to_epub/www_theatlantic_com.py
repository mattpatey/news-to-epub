

from datetime import datetime
from functools import partial
from json import loads

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import requests


def scrape(uri):
    response = requests.get(uri)
    soup = BeautifulSoup(response.text)
    md_json = soup.find('meta', {'name': 'parsely-page'})['content']
    meta_data = loads(md_json)
    content = soup.find('div', class_='article-content', itemprop='articleBody')
    filtered_content = content.find_all('p')
    processed_content = u''.join([unicode(i) for i in filtered_content])

    return meta_data, processed_content

def top_stories(section_name):
    """Search for top content by section."""
    response = requests.get('http://www.theatlantic.com/')
    soup = BeautifulSoup(response.text)
    section_parent = soup.find('ul', id='nav-channels')
    section = section_parent.find('li', class_='nav-channel {}'.format(section_name))
    section_stories = section.find_all('li', class_='dropdown-item')
    story_links = []
    for i in section_stories:
        story_links.append(i.find('a')['href'])

    return story_links

def get_content(from_date, config):
    search_args = dict(config)
    section = search_args['section']
    content_links = top_stories(section)
    articles = []
    for uri in content_links:
        # Unfortunately the publication date is in the document
        # itself, so we have to scrape the document now, instead of
        # after checking if we actually want to publish the document
        meta_data, scraped_content = scrape(uri)
        date = date_parser.parse(meta_data['pub_date'])
        title = meta_data['title']
        content = partial(unicode, scraped_content)
        article = dict(content=content, date=date, title=title)
        articles.append(article)

    return articles
