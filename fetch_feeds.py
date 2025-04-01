import feedparser
import re
import json
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
import yaml

def get_feed_category(feed_url, feed_list_content):
    lines = feed_list_content.split('\n')
    current_category = None
    for line in lines:
        line = line.strip()
        if line.endswith(':'):
            current_category = line[:-1]
        elif line == feed_url:
            return current_category
    return 'Blog'

def fetch_feeds():
    # 新增控制变量（True启用24小时过滤）
    ENABLE_24H_FILTER = True  # 可在此控制全局开关
    
    with open('config/labels.yml', 'r', encoding='utf-8') as f:
        label_config = yaml.safe_load(f)
    
    category_configs = {label['feed_category']: label for label in label_config['labels']}
    default_limit = label_config['default_limit']

    with open('feed.list', 'r') as f:
        feed_list_content = f.read()
        feeds = [line.strip() for line in feed_list_content.splitlines() if line.strip() and not line.endswith(':')]
    
    articles_by_category = defaultdict(list)
    beijing_tz = pytz.timezone('Asia/Shanghai')

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            category = get_feed_category(feed_url, feed_list_content)
            category_config = category_configs.get(category, {})
            article_limit = category_config.get('article_limit', default_limit)

            # 时间过滤逻辑
            now = datetime.now(beijing_tz)
            time_threshold = now - timedelta(hours=24)
            
            valid_entries = []
            for entry in feed.entries:
                published = entry.get('published_parsed', entry.get('updated_parsed'))
                if not published:
                    continue
                
                dt = datetime(*published[:6])
                dt = pytz.UTC.localize(dt).astimezone(beijing_tz)
                
                if ENABLE_24H_FILTER and dt < time_threshold:
                    continue
                
                valid_entries.append(entry)

            if article_limit > 0:
                valid_entries = valid_entries[:article_limit]

            for entry in valid_entries:
                published = entry.get('published_parsed', entry.get('updated_parsed'))
                dt = datetime(*published[:6])
                dt = pytz.UTC.localize(dt).astimezone(beijing_tz)
                published_str = dt.strftime('%Y-%m-%d %H:%M')

                summary = ''
                if 'summary' in entry:
                    summary = re.sub(r'<[^>]+>', '', entry.summary)[:150]
                elif 'description' in entry:
                    summary = re.sub(r'<[^>]+>', '', entry.description)[:150]
                
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'date': published_str,
                    'author': feed.feed.title,
                    'timestamp': dt.timestamp(),
                    'summary': summary.strip() + '...' if len(summary) > 150 else summary.strip(),
                    'source_url': feed.feed.link or feed_url,
                    'category': category
                }
                articles_by_category[category].append(article)
                
        except Exception as e:
            print(f"Error fetching {feed_url}: {str(e)}")
            continue

    # 排序逻辑保持不变
    all_articles = []
    for category, articles in articles_by_category.items():
        articles.sort(key=lambda x: x['timestamp'], reverse=True)
        all_articles.extend(articles)
    
    all_articles.sort(key=lambda x: x['timestamp'], reverse=True)
    
    data = {
        'update_time': datetime.now(beijing_tz).strftime('%Y-%m-%d'),
        'articles': all_articles
    }
    
    with open('feed.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    fetch_feeds()
