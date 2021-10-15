import logging
import sys
import os
import urllib
import requests
import feedparser
from readability import Document
import jinja2
from datetime import datetime
from lxml.html import fromstring, tostring
from lxml.html import builder as E
import pytz

from config import YamlReader

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.INFO,
                    stream=sys.stdout)


templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)

def process(rss):
    logging.info("start processing {} by url: {}".format(rss["name"], rss["url"]))
    limit = YamlReader('general.limit')
    article_list = get_article_list_by_rss(rss["url"])[:limit]
    latest=datetime.strptime('1970-01-01', '%Y-%m-%d')
    for article in article_list:
        # get the latest article
        if article["published_parsed"] > latest:
            latest = article["published_parsed"]
        clean_page = ""
        if rss["full_content"]:
            clean_page = inject_style(article["content"], article["title"])
        else:
            try:
                page = get_page_by_url(article['link'])
                clean_page = extract_body_from_page(page, article)
            except:
                logging.warning("error get page {}".format(article['link']))
                clean_page = '<html><body><p><a href="{link}">{link}</a></p></body></html>'.format(link=article['link']).encode('utf-8')
        file_name = '{base_dir}/{rss_name}/{article_title}.html'.format(
            base_dir = YamlReader('general.target_dir'),
            rss_name = rss["name"],
            article_title = article['filename']
        )
        # get the size of page
        article["size"] = "{:.2f}k".format(len(clean_page) / 1024)
        write_body_to_file(clean_page, file_name, 'wb')
    #put the age of latest article in dict for index rendering
    age = (datetime.now() - latest).days
    rss["age"] = 0 if age < 0 else age
    render_rss(rss, article_list)
    logging.info("{} done".format(rss["name"]))
    return

def render_index(rss_list):
    template = templateEnv.get_template("index.tplt")
    body = template.render(rss_list = rss_list, updated=datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S'))
    write_body_to_file(body,
                       '{base_dir}/index.html'.format(base_dir=YamlReader('general.target_dir')),
                       'w')
    return

def render_rss(rss, article_list):
    template = templateEnv.get_template("rss.tplt")
    body = template.render(rss_name = rss["name"], article_list = article_list)
    write_body_to_file(body,
                       '{base_dir}/{rss_name}/index.html'.format(
                           base_dir=YamlReader('general.target_dir'),
                           rss_name = rss["name"]),
                       'w')
    return

def get_article_list_by_rss(url):
    feed = feedparser.parse(url)
    article_list = []
    for i in feed['entries']:
        published_parsed = i['published_parsed'] if 'published_parsed' in i else i['updated_parsed']
        published_parsed = datetime(*published_parsed[:6])
        article = {'title': i['title'],
                   'filename': i['title'][:64],
                   'filename_escaped': urllib.parse.quote(i['title'][:64]),
                   'content': i['content'][0]['value'] if 'content' in i else i['description'],
                   'published': published_parsed.strftime('%Y-%m-%d %H:%M:%S'),
                   'published_parsed': published_parsed,
                   'link': i['link']}
        article_list.append(article)
    return article_list

def get_page_by_url(url):
    logging.info("retrieve content from {}".format(url))
    r = requests.get(url)
    if r.status_code == 200:
        return r.content

def extract_body_from_page(page, article):
    doc = Document(page)
    doc_summary = ''
    doc_summary = doc.summary()
    return inject_style(doc_summary, article["title"])

def inject_style(doc, title):
    page = fromstring(doc)
    page.insert(0, E.HEAD(
        E.META(charset="UTF-8", name="viewport", content="width=device-width, initial-scale=1"),
        E.LINK(rel="stylesheet", href="/ok.min.css", type="text/css"),
        E.TITLE(title)
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
    rss_list = YamlReader('rss')
    for rss in rss_list:
        rss["name_escaped"] = urllib.parse.quote(rss["name"])
        process(rss)
    render_index(rss_list)
