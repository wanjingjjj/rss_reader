import logging
import sys
import os
import requests
import feedparser
from readability import Document
import jinja2
from datetime import datetime
from lxml.html import fromstring, tostring
from lxml.html import builder as E

from config import YamlReader

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.INFO,
                    stream=sys.stdout)


templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)

def process(rss):
    logging.info("start processing {} by url: {}".format(rss["name"], rss["url"]))
    limit = YamlReader('general.limit')
    article_list = get_article_list_by_rss(rss["url"])
    for article in article_list[:limit]:
        page = get_page_by_url(article['link'])
        clean_page = extract_body_from_page(page)
        file_name = '{base_dir}/{rss_name}/{article_title}.html'.format(
            base_dir = YamlReader('general.target_dir'),
            rss_name = rss["name"],
            article_title = article['title']
        )
        write_body_to_file(clean_page, file_name, 'wb')
    render_rss(rss["name"], article_list)
    logging.info("{} done".format(rss["name"]))
    return

def render_index(rss_list):
    template = templateEnv.get_template("index.tplt")
    body = template.render(rss_list = rss_list, updated=datetime.now().strftime('%Y-%d-%m %H:%M:%S'))
    write_body_to_file(body,
                       '{base_dir}/index.html'.format(base_dir=YamlReader('general.target_dir')),
                       'w')
    return

def render_rss(rss_name, article_list):
    template = templateEnv.get_template("rss.tplt")
    body = template.render(rss_name = rss_name, article_list = article_list)
    write_body_to_file(body,
                       '{base_dir}/{rss_name}/index.html'.format(
                           base_dir=YamlReader('general.target_dir'),
                           rss_name = rss_name),
                       'w')
    return

def get_article_list_by_rss(url):
    feed = feedparser.parse(url)
    article_list = []
    for i in feed['entries']:
        article = {'title': i['title'],
                   'published': i['published'],
                   'link': i['link']}
        article_list.append(article)
    return article_list

def get_page_by_url(url):
    logging.info("retrieve content from {}".format(url))
    r = requests.get(url)
    if r.status_code == 200:
        return r.text

def extract_body_from_page(page):
    doc = Document(page)
    return inject_style(doc.summary())

def inject_style(doc):
    page = fromstring(doc)
    page.insert(0, E.HEAD(
        E.META(name="viewport", content="width=device-width, initial-scale=1"),
        E.LINK(rel="stylesheet", href="pure-min.css", type="text/css")
#        E.TITLE("")
    ))
    return tostring(page)

def write_body_to_file(body, filename, mode):
    dirname = os.path.dirname(filename)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    with open(filename, mode) as f:
        f.write(body)
    logging.info("write content to file:{}".format(filename))
    return

if __name__ == '__main__':
    for rss in YamlReader('rss'):
        process(rss)
    render_index(YamlReader('rss'))
