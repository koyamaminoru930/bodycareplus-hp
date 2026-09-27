#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新しいブログ記事を1件、bodycareplus-hp/blog/ に追加するヘルパースクリプト。

日次の自動移植タスクから、記事1件ごとに以下の流れで呼び出す想定:

    python3 add_article.py --json article.json

article.json の形式:
{
  "slug": "example-slug",
  "title": "記事タイトル",
  "description": "一覧・OGP用の説明文",
  "iso_date": "2026-10-01",
  "date_disp": "2026年10月1日",
  "author": "小山稔",
  "kicker": "肩こり・五十肩シリーズ",
  "tags": ["タグ1", "タグ2"],
  "body": ["段落1", "段落2", "..."],
  "related": [["keitsuisho.html", "頸椎症でお悩みの方へ"]]
}

このスクリプトが行うこと:
1. blog/<slug>.html を新規生成する(prev_href/prev_labelは現在の最新記事、next_hrefは仮でindex.html)
2. これまでの最新記事(index.htmlのpost-grid先頭)のHTMLファイルを見つけて、その「次の記事へ」リンクを今回追加した記事に書き換える
3. blog/index.html の post-grid ブロックの先頭に、新しい記事カードを追加する
4. サイトルートの index.html(ホームページ)の「スタッフブログ」新着カード欄を、
   blog/index.html の最新4記事に合わせて自動更新する(手動更新忘れを防ぐため)

このスクリプトは1回のコミットで複数回呼び出せる(複数記事を続けて追加する場合)。
"""
import sys, os, re, json, argparse

sys.path.insert(0, os.path.dirname(__file__))
from blog_template import render

BLOG_DIR = os.path.join(os.path.dirname(__file__), "..")
BLOG_DIR = os.path.abspath(BLOG_DIR)
INDEX_PATH = os.path.join(BLOG_DIR, "index.html")
SITE_ROOT = os.path.abspath(os.path.join(BLOG_DIR, ".."))
HOMEPAGE_PATH = os.path.join(SITE_ROOT, "index.html")

CARD_RE = re.compile(
    r'(<div class="post-grid">\n)(.*?)(\n    </div>)', re.DOTALL
)

# 1つの記事カードのHTML片を抜き出す正規表現(実際のindex.htmlの構造に合わせる)
CARD_ITEM_RE = re.compile(
    r'<a class="post-card reveal" href="([^"]+)\.html">', re.DOTALL
)

# blog/index.html の1件分のカード全体(href, タイトル, 投稿日)を取り出す正規表現
FULL_CARD_RE = re.compile(
    r'<a class="post-card reveal" href="([^"]+)\.html">\s*'
    r'<span class="post-kicker">.*?</span>\s*'
    r'<h2>(.*?)</h2>\s*'
    r'<p class="post-desc">.*?</p>\s*'
    r'<span class="post-date">(.*?)</span>\s*'
    r'</a>',
    re.DOTALL,
)

JP_DATE_RE = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日')

HOMEPAGE_GRID_RE = re.compile(
    r'(<ul class="blog-grid reveal-stagger">\n)(.*?)(\n    </ul>)', re.DOTALL
)


def jp_date_to_dotted(date_disp):
    m = JP_DATE_RE.search(date_disp)
    if not m:
        return date_disp
    y, mo, d = m.groups()
    return "{0}.{1:02d}.{2:02d}".format(int(y), int(mo), int(d))


def update_homepage_preview():
    """ホームページ(サイトルートのindex.html)の「スタッフブログ」新着カード4件を、
    blog/index.html の最新4記事に合わせて更新する。"""
    with open(INDEX_PATH, encoding="utf-8") as f:
        blog_index_html = f.read()
    cards = FULL_CARD_RE.findall(blog_index_html)[:4]
    if not cards:
        raise RuntimeError("blog/index.html からカード情報を抽出できませんでした")

    items = []
    for slug, title, date_disp in cards:
        items.append(
            '      <li class="blog-card">\n'
            '        <a href="blog/{slug}.html">\n'
            '          <span class="blog-date">{date}</span>\n'
            '          <p class="blog-title">{title}</p>\n'
            '          <span class="blog-arrow">続きを読む →</span>\n'
            '        </a>\n'
            '      </li>'.format(
                slug=slug, date=jp_date_to_dotted(date_disp), title=title
            )
        )
    new_block = "\n".join(items)

    with open(HOMEPAGE_PATH, encoding="utf-8") as f:
        home_html = f.read()
    m = HOMEPAGE_GRID_RE.search(home_html)
    if not m:
        raise RuntimeError("ホームページのindex.htmlから blog-grid ブロックが見つかりませんでした")
    new_home_html = home_html[: m.start(2)] + new_block + home_html[m.end(2):]
    with open(HOMEPAGE_PATH, "w", encoding="utf-8") as f:
        f.write(new_home_html)


def find_latest_slug():
    """index.html の post-grid 内で最初に出てくる記事カードのスラッグ(=現在の最新記事)を返す。"""
    with open(INDEX_PATH, encoding="utf-8") as f:
        html = f.read()
    m = CARD_ITEM_RE.search(html)
    if not m:
        raise RuntimeError("index.html から既存の記事カードを見つけられませんでした")
    return m.group(1)


def patch_prev_article_next_link(prev_slug, new_slug, new_title):
    path = os.path.join(BLOG_DIR, prev_slug + ".html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    old = '<a href="index.html">ブログ一覧へ →</a>'
    new = '<a href="{0}.html">{1} →</a>'.format(new_slug, new_title)
    if old not in html:
        raise RuntimeError(
            "{0} の次の記事リンクが想定形式(index.htmlへの仮リンク)ではありません。"
            "手動で確認してください。".format(path)
        )
    html = html.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def build_card_html(a):
    return (
        '      <a class="post-card reveal" href="{slug}.html">\n'
        '        <span class="post-kicker">{kicker}</span>\n'
        '        <h2>{title}</h2>\n'
        '        <p class="post-desc">{desc}</p>\n'
        '        <span class="post-date">{date}</span>\n'
        '      </a>'
    ).format(
        slug=a["slug"], kicker=a["kicker"], date=a["date_disp"],
        title=a["title"], desc=a["description"],
    )


def prepend_card_to_index(a):
    with open(INDEX_PATH, encoding="utf-8") as f:
        html = f.read()
    m = CARD_RE.search(html)
    if not m:
        raise RuntimeError("index.html の post-grid ブロックが見つかりませんでした")
    existing_cards = m.group(2)
    new_card = build_card_html(a)
    new_block = new_card + "\n" + existing_cards
    new_html = html[: m.start(2)] + new_block + html[m.end(2):]
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)


def add_article(a):
    prev_slug = find_latest_slug()
    # find prev article's title for the prev-link label
    prev_path = os.path.join(BLOG_DIR, prev_slug + ".html")
    with open(prev_path, encoding="utf-8") as f:
        prev_html = f.read()
    tmatch = re.search(r"<h1[^>]*>(.*?)</h1>", prev_html, re.DOTALL)
    prev_title = tmatch.group(1).strip() if tmatch else prev_slug

    html = render(
        title=a["title"], description=a["description"], slug=a["slug"],
        iso_date=a["iso_date"], date_disp=a["date_disp"], author=a["author"],
        kicker=a["kicker"], body_paragraphs=a["body"], tags=a["tags"],
        prev_href=prev_slug + ".html", prev_label="← " + prev_title,
        next_href="index.html", next_label="ブログ一覧へ →",
        related_links=[tuple(x) for x in a.get("related", [])],
    )
    out_path = os.path.join(BLOG_DIR, a["slug"] + ".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    patch_prev_article_next_link(prev_slug, a["slug"], a["title"])
    prepend_card_to_index(a)
    update_homepage_preview()
    print("added:", a["slug"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--json", required=True, help="記事データのJSONファイルパス")
    args = p.parse_args()
    with open(args.json, encoding="utf-8") as f:
        data = json.load(f)
    add_article(data)
