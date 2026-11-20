# -*- coding: utf-8 -*-
"""sitemap.xml をサイト内のページから作り直す。

トップ・お悩みページ・ブログ一覧・ブログ全記事を載せる。
ブログ記事の lastmod は記事内の datePublished を使う。
add_article.py から記事追加のたびに呼ばれる。単体でも実行できる:
    python3 blog/_tools/build_sitemap.py
"""
import datetime
import glob
import os
import re

SITE = "https://bodycareplus.jp/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# 公開途中のページなど、検索に出したくないものはここに入れる
EXCLUDE = {"symptoms/bodychart_prototype.html"}
DATE_RE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')


def _entry(path, lastmod, freq, prio):
    return (
        "  <url>\n"
        "    <loc>{0}{1}</loc>\n"
        "    <lastmod>{2}</lastmod>\n"
        "    <changefreq>{3}</changefreq>\n"
        "    <priority>{4}</priority>\n"
        "  </url>\n"
    ).format(SITE, path, lastmod, freq, prio)


def build(today=None):
    today = today or datetime.date.today().isoformat()
    items = [("", today, "weekly", "1.0")]
    items.append(("symptoms/index.html", today, "monthly", "0.8"))
    for p in sorted(glob.glob(os.path.join(ROOT, "symptoms", "*.html"))):
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        if rel in EXCLUDE or rel == "symptoms/index.html":
            continue
        items.append((rel, today, "monthly", "0.8"))
    items.append(("blog/index.html", today, "weekly", "0.7"))
    posts = []
    for p in glob.glob(os.path.join(ROOT, "blog", "*.html")):
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        if rel == "blog/index.html" or rel in EXCLUDE:
            continue
        with open(p, encoding="utf-8") as f:
            m = DATE_RE.search(f.read())
        posts.append((m.group(1) if m else today, rel))
    for date, rel in sorted(posts, reverse=True):
        items.append((rel, date, "yearly", "0.5"))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "".join(_entry(*i) for i in items) + "</urlset>\n")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    return len(items)


if __name__ == "__main__":
    print("sitemap urls:", build())
