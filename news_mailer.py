#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import feedparser, smtplib, ssl, logging, os, sys, time, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

GMAIL_USER         = os.environ.get("GMAIL_USER", "JenniferChu0411@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL    = os.environ.get("RECIPIENT_EMAIL", "jennifer.chu@testritegroup.com")
SENDER_NAME        = "每日商業新聞摘要"

TRADE_FEEDS = [
    {"name": "WTO News",                  "url": "https://www.wto.org/library/rss/latest_news_e.xml",                                                                                       "lang": "EN", "category": "國際貿易政策"},
    {"name": "The Guardian - Trade",      "url": "https://www.theguardian.com/business/internationaltrade/rss",                                                                             "lang": "EN", "category": "國際貿易政策"},
    {"name": "Supply Chain Dive",         "url": "https://www.supplychaindive.com/feeds/news/",                                                                                             "lang": "EN", "category": "供應鏈與物流"},
    {"name": "Global Trade Magazine",     "url": "https://www.globaltrademag.com/archives/feed/",                                                                                           "lang": "EN", "category": "全球貿易動態"},
    {"name": "Google News - Trade",       "url": "https://news.google.com/rss/search?q=international+trade+tariff+export+import&hl=en&gl=US&ceid=US:en",                                   "lang": "EN", "category": "國際貿易政策"},
    {"name": "Google News - Supply Chain","url": "https://news.google.com/rss/search?q=supply+chain+logistics+shipping&hl=en&gl=US&ceid=US:en",                                            "lang": "EN", "category": "供應鏈與物流"},
    {"name": "Google News - Market",      "url": "https://news.google.com/rss/search?q=global+trade+market+consumer+trend&hl=en&gl=US&ceid=US:en",                                        "lang": "EN", "category": "消費趨勢與市場分析"},
    {"name": "Google News - 全球貿易",    "url": "https://news.google.com/rss/search?q=%E5%85%A8%E7%90%83%E8%B2%BF%E6%98%93+%E9%97%9C%E7%A8%85&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",         "lang": "ZH", "category": "國際貿易政策"},
]

RETAIL_FEEDS = [
    {"name": "自由時報財經",              "url": "https://news.ltn.com.tw/rss/business.xml",                                                                                                "lang": "ZH", "category": "台灣零售動態"},
    {"name": "Google News - 台灣零售",    "url": "https://news.google.com/rss/search?q=%E5%8F%B0%E7%81%A3+%E9%9B%B6%E5%94%AE+%E9%9B%BB%E5%95%86&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",       "lang": "ZH", "category": "電商與實體零售"},
    {"name": "Google News - 台灣百貨",    "url": "https://news.google.com/rss/search?q=%E5%8F%B0%E7%81%A3+%E7%99%BE%E8%B2%A8+%E8%B3%BC%E7%89%A9+%E6%B6%88%E8%B2%BB&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","lang": "ZH", "category": "消費趨勢"},
    {"name": "Google News - 台灣供應鏈",  "url": "https://news.google.com/rss/search?q=%E5%8F%B0%E7%81%A3+%E4%BE%9B%E6%87%89%E9%8F%88+%E7%89%A9%E6%B5%81&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","lang": "ZH", "category": "供應鏈與物流"},
]

TRADE_KEYWORDS  = ["trade","tariff","export","import","WTO","supply chain","logistics","shipping","customs","market","economic","manufacturing","貿易","關稅","出口","進口","供應鏈","物流","市場","消費","製造"]
RETAIL_KEYWORDS = ["retail","e-commerce","shopping","consumer","store","mall","brand","零售","電商","購物","消費","百貨","門市","品牌","超市","便利商店","網購","實體店","momo","pchome","蝦皮","7-11","全家","統一","SOGO","遠百","新光","家樂福","好市多","costco"]

logging.basicConfig(level=logging.INFO, format='%(asctime )s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

def is_recent(entry, hours=24):
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6]) > datetime.utcnow() - timedelta(hours=hours)
    return True

def contains_keywords(text, keywords):
    t = text.lower()
    return any(k.lower() in t for k in keywords)

def clean_html(raw):
    return re.sub(re.compile('<.*?>'), '', raw or '').strip()

def truncate(text, n=200):
    text = ' '.join(text.split()) if text else ''
    return text[:n] + '...' if len(text) > n else text

def fetch(feed_info, keywords=None, max_items=8, hours=24):
    articles = []
    try:
        feed = feedparser.parse(feed_info['url'])
        if feed.bozo and not feed.entries:
            return articles
        for entry in feed.entries[:max_items*3]:
            if len(articles) >= max_items:
                break
            title   = getattr(entry, 'title', '').strip()
            link    = getattr(entry, 'link',  '').strip()
            if not title or not link:
                continue
            summary = clean_html(getattr(entry, 'summary', '') or getattr(entry, 'description', ''))
            if keywords and not contains_keywords(title + ' ' + summary, keywords):
                continue
            if not is_recent(entry, hours):
                continue
            articles.append({'title': title, 'link': link, 'summary': truncate(summary),
                'date': getattr(entry, 'published', '') or getattr(entry, 'updated', ''),
                'source': feed_info['name'], 'category': feed_info['category'], 'lang': feed_info['lang']})
    except Exception as e:
        logger.error(f"Fetch error {feed_info['name']}: {e}")
    return articles

def collect():
    logger.info("開始收集新聞...")
    trade, retail = [], []
    for f in TRADE_FEEDS:
        trade.extend(fetch(f, TRADE_KEYWORDS)); time.sleep(0.5)
    for f in RETAIL_FEEDS:
        retail.extend(fetch(f, RETAIL_KEYWORDS)); time.sleep(0.5)
    def dedup(lst):
        seen, out = set(), []
        for a in lst:
            k = a['title'][:50].lower()
            if k not in seen:
                seen.add(k); out.append(a)
        return out
    t, r = dedup(trade), dedup(retail)
    if not t and not r:
        for f in TRADE_FEEDS:  t.extend(fetch(f, None, 5, 48))
        for f in RETAIL_FEEDS: r.extend(fetch(f, None, 5, 48))
    logger.info(f"收集完成：貿易 {len(t)} 則，零售 {len(r)} 則")
    return t, r

def group(articles):
    g = {}
    for a in articles:
        g.setdefault(a['category'], []).append(a)
    return g

def render_section(grouped, empty_msg):
    if not grouped:
        return f'  <div class="no-news">{empty_msg}</div>\n'
    html = ''
    for cat, items in grouped.items():
        html += f'  <div class="section-subtitle">▸ {cat}</div>\n'
        for item in items:
            badge = '<span class="badge badge-en">EN</span>' if item['lang'] == 'EN' else '<span class="badge badge-zh">中文</span>'
            d = item['date'][:25] if item['date'] else 'N/A'
            html += f"""  <div class="news-item">
    <div class="news-title"><a href="{item['link']}" target="_blank">{item['title']}</a>{badge}</div>
    <div class="news-meta">📰 {item['source']}　⏱ {d}</div>
    <div class="news-summary">{item['summary']}</div>
    <div><a href="{item['link']}" target="_blank" class="news-link">🔗 閱讀原文</a></div>
  </div>\n"""
    return html

def build_html(trade, retail):
    date_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{{font-family:'Helvetica Neue',Arial,'PingFang TC','Microsoft JhengHei',sans-serif;background:#f4f6f9;margin:0;padding:20px;color:#333}}
.container{{max-width:700px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
.header{{background:linear-gradient(135deg,#1a3a5c,#2d6a9f);color:#fff;padding:28px 30px;text-align:center}}
.header h1{{margin:0;font-size:22px;letter-spacing:1px}}
.header p{{margin:6px 0 0;font-size:13px;opacity:.85}}
.section-title{{padding:16px 24px 8px;font-size:18px;font-weight:bold;color:#1a3a5c;border-bottom:3px solid #2d6a9f;background:#f0f5fb}}
.section-subtitle{{padding:10px 24px 4px;font-size:14px;font-weight:bold;color:#2d6a9f;background:#f8fafd;border-left:4px solid #2d6a9f;margin:10px 16px 0}}
.news-item{{padding:12px 24px;border-bottom:1px solid #eef0f3}}
.news-title a{{font-size:15px;font-weight:600;color:#1a3a5c;text-decoration:none;line-height:1.4}}
.news-meta{{font-size:11px;color:#888;margin:3px 0 5px}}
.news-summary{{font-size:13px;color:#555;line-height:1.6}}
.badge{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:bold;margin-left:6px;vertical-align:middle}}
.badge-en{{background:#e8f0fe;color:#1a73e8}}
.badge-zh{{background:#e6f4ea;color:#188038}}
.news-link{{display:inline-block;margin-top:8px;font-size:12px;color:#2d6a9f;text-decoration:none;border:1px solid #c5d8ee;border-radius:4px;padding:3px 12px;background:#f0f5fb}}
.no-news{{padding:16px 24px;color:#999;font-size:13px;font-style:italic}}
.footer{{background:#f0f5fb;padding:16px 24px;text-align:center;font-size:11px;color:#999;border-top:1px solid #e0e5ed}}
.divider{{height:10px;background:#f4f6f9}}
</style></head><body>
<div class="container">
  <div class="header">
    <h1>📊 每日貿易與零售新聞摘要</h1>
    <p>Daily Trade &amp; Retail News Digest &nbsp;|&nbsp; {date_str}</p>
  </div>
  <div class="section-title">🌐 全球貿易新聞 Global Trade News</div>
{render_section(group(trade), "本時段暫無最新全球貿易新聞。")}
  <div class="divider"></div>
  <div class="section-title">🏪 台灣零售新聞 Taiwan Retail News</div>
{render_section(group(retail), "本時段暫無最新台灣零售新聞。")}
  <div class="footer">
    此郵件由 GitHub Actions 自動產生，每日 08:00 及 15:00 發送  

    涵蓋：國際貿易政策 | 零售產業動態 | 供應鏈與物流 | 消費趨勢 | 市場分析
  </div>
</div></body></html>"""

def send_email(html, trade_count, retail_count):
    now = datetime.now()
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"【每日新聞摘要】貿易 & 零售資訊 — {now.strftime('%Y/%m/%d %H:%M')}"
    msg['From']    = f"{SENDER_NAME} <{GMAIL_USER}>"
    msg['To']      = RECIPIENT_EMAIL
    msg.attach(MIMEText(f"每日貿易與零售新聞摘要\n日期：{now.strftime('%Y/%m/%d %H:%M')}\n貿易：{trade_count} 則\n零售：{retail_count} 則", 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        logger.info(f"郵件已發送至 {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"發送失敗: {e}")
        return False

if __name__ == "__main__":
    trade, retail = collect()
    html    = build_html(trade, retail)
    success = send_email(html, len(trade), len(retail))
    sys.exit(0 if success else 1)
