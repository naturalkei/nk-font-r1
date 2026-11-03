"""Static site pages: every page's scripts/styles exist and the nav links the sub pages."""

import re

from nkfont import config

SITE = config.ROOT / "site"


def test_pages_reference_existing_assets():
    for page in ("index.html", "compare.html", "tester.html", "design.html"):
        html = (SITE / page).read_text()
        for ref in re.findall(r'(?:src|href)="([\w.-]+\.(?:js|css|html))"', html):
            assert (SITE / ref).exists(), f"{page} -> {ref}"
        for mod in re.findall(r'from "\./([\w.-]+\.js)"', html):
            assert (SITE / mod).exists()


def test_modules_import_existing_files_and_nav_links_sub_pages():
    for js in SITE.glob("*.js"):
        for mod in re.findall(r'from "\./([\w.-]+\.js)"', js.read_text()):
            assert (SITE / mod).exists(), f"{js.name} imports missing {mod}"
    nav = (SITE / "index.html").read_text()
    assert all(f'href="{p}"' in nav for p in ("compare.html", "tester.html", "design.html"))
