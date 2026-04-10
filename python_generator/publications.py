import os
import os.path
import re
import subprocess
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright
from datetime import datetime
from urllib.parse import quote
from urllib.parse import quote_plus

import requests
import yaml

from python_generator import constants
from python_generator.utils import get_dir_path, sanitize_title
from python_generator.utils import read_published_google_sheet
import tempfile


def resolve_final_url(url):
    if url.startswith('doi:'):
        doi = url[4:].strip()
        doi_url = f'https://doi.org/{quote(doi)}'
        try:
            response = requests.head(doi_url, allow_redirects=True)
            final_url = response.url
            return final_url
        except requests.exceptions.RequestException as e:
            print(f"Publications: Error resolving DOI URL: {e}")
            return doi_url
    else:
        return url


PUBMED_CLEANUP_SELECTORS = ",".join([
    ".search-links-wrapper",
    ".search-input",
    "#article-page-header",
    ".usa-banner",
    ".actions-buttons",
    ".ncbi-header",
    ".u-lazy-ad-wrapper",
    ".no-script-banner",
    ".ncbi-alerts",
    ".conflict-of-interest",
    "#publication-types",
    ".similar-cited-articles",
    ".similar-articles",
    "#linkout",
    "#ncbi-footer",
    "#disclaimer",
    ".ahead-of-print",
    ".short-article-details",
    "#related-links",
    ".page-sidebar",
    "#vdp",
    ".related-db-links",
    ".overlay"
])


def take_svg_screenshot_of_url(ids, output_dir, width=960, height=1100):
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            java_script_enabled=False,
        )
        page = context.new_page()

        try:
            for pubmed_id in ids:
                output_path = os.path.join(output_dir, f"pubmed_{pubmed_id}.svg")
                if os.path.exists(output_path):
                    continue

                page.goto(
                    f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                page.emulate_media(media="print")
                page.evaluate(
                    """(selectors) => {
                        document.querySelectorAll(selectors).forEach(el => el.remove());
                    }""",
                    PUBMED_CLEANUP_SELECTORS,
                )
                page.evaluate("window.scrollTo(0, 0);")
                page.add_style_tag(
                    content="""
                        .search-form.content-page-layout {
                            padding-top: 1em;
                            padding-right: 0;
                            padding-bottom: 2em;
                            padding-left: 2em;
                        }
                        a.usa-link--external::before,
                        a.usa-link--external::after {
                            content: none !important;
                            display: none !important;
                        }
                        @media print {
                            .article-top-actions-bar,
                            .actions-buttons,
                            .share-permalink,
                            .page-navigator,
                            .adjacent-navigation,
                            .search-form,
                            .similar-articles,
                            .citedby-articles,
                            .publication-types,
                            .mesh-terms,
                            .substances,
                            .supplemental-data,
                            .grants,
                            .references,
                            .conflict-of-interest,
                            .back-to-top,
                            .article-page .article-details > .heading .more-details,
                            footer {
                                display: inherit;
                            }
                        }
                    """
                )

                page.evaluate("""
                () => {
                    const target = 'vulnerability';
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.innerText || '';
                        if (text.toLowerCase().includes(target)) {
                            node.style.display = 'none';
                        }
                    }
                }
                """)

                with tempfile.TemporaryDirectory() as tmp:
                    pdf_path = Path(tmp) / "page.pdf"
                    page.pdf(
                        scale=2,
                        width="1040", height="1040",
                        prefer_css_page_size=True,
                        path=str(pdf_path),
                        display_header_footer=False,
                        print_background=True,
                        page_ranges="1"
                    )
                    # pdf2svg usage: pdf2svg <input.pdf> <output.svg> [page no or "all"]
                    # Convert all pages into SVG files in out_dir.
                    subprocess.run(
                        [r"pdf2svg", str(pdf_path), str(output_path),
                         "all"],
                        check=True,
                    )
        finally:
            context.close()
            browser.close()


def take_screenshot_of_url(ids, output_dir, width=960, height=1100, crop_width=948):
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        page = context.new_page()

        try:
            for pubmed_id in ids:
                output_path = os.path.join(output_dir, f"pubmed_{pubmed_id}.png")
                if os.path.exists(output_path):
                    continue

                page.goto(
                    f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                page.evaluate(
                    """(selectors) => {
                        document.querySelectorAll(selectors).forEach(el => el.remove());
                    }""",
                    PUBMED_CLEANUP_SELECTORS,
                )

                time.sleep(2)
                page.screenshot(path=output_path)

                with Image.open(output_path) as img:
                    if img.width != crop_width:
                        img.crop((0, 0, crop_width, img.height)).save(output_path)

        finally:
            context.close()
            browser.close()


def produce_screenshots(site_dir):
    publications_file = os.path.join(get_dir_path(site_dir, constants.DATA_DIR), constants.FILE_ALL_PUBLICATIONS)

    with open(publications_file, 'r') as file:
        publications = yaml.safe_load(file)

    pubmed_ids = [pub['pubmed_id'] for pub in publications if pub['pubmed_id'] and pub['pubmed_id'] != "null"]
    take_screenshot_of_url(pubmed_ids, get_dir_path(site_dir, "assets", "posts"))


def extract_year(year_string):
    year_string = str(year_string)
    match = re.search(r'\b(19|20)\d{2}\b', year_string)
    if match:
        return match.group(0).strip()
    return None


def fetch_publications_by_term(search_term):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={quote_plus(search_term)}&retmode=json&retmax=10000"
    response = requests.get(search_url)
    if response.status_code == 200:
        data = response.json()
        pubmed_ids = data['esearchresult']['idlist']
        return pubmed_ids
    else:
        print(f"Publications: Error fetching publications. Status code: {response.status_code}")
        return []


def parse_year(year_str):
    year_str = str(year_str)
    try:
        return datetime.strptime(year_str, "%Y %b %d")
    except ValueError:
        try:
            return datetime.strptime(year_str, "%Y %b")
        except ValueError:
            return datetime.strptime(year_str, "%Y")


def get_publication_details(pubmed_id):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    summary_url = f"{base_url}esummary.fcgi?db=pubmed&id={pubmed_id}&retmode=json"

    sleep_time = 5 * 60  # Start with 5 minutes in seconds
    max_sleep_time = 20 * 60  # Maximum sleep time of 20 minutes in seconds

    while True:
        response = requests.get(summary_url)
        if response.status_code == 200:
            data = response.json()
            try:
                title = data['result'][pubmed_id]['title']
                authors = data['result'][pubmed_id]['authors']
                authors = [f["name"] for f in authors]

                year = data['result'][pubmed_id]['pubdate']
                if " " not in year:
                    year = int(year)

                if "Demaria" not in ", ".join(authors):
                    return None
                journal = data['result'][pubmed_id]['source']

                return {
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'journal': journal
                }
            except KeyError:
                print(f"Publications: Error parsing publication details for PubMed ID: {pubmed_id}")
                return None
        elif response.status_code == 429:
            print(f"Too many requests. Sleeping for {sleep_time // 60} minutes...")
            time.sleep(sleep_time)
            sleep_time = min(max_sleep_time, sleep_time * 2)  # Exponentially increase sleep time up to the max limit
        else:
            print(f"Publications: Error fetching publication details. Status code: {response.status_code}")
            return None


def fetch_and_save_publications(data_dir, args):
    selected_pubmed_ids = [f.get("pubmed_id") for f in
                           read_published_google_sheet(args[constants.ARG_SELECTED_PUBLICATIONS_SHEET_ID])["data"] if
                           f.get("pubmed_id")]
    if selected_pubmed_ids:
        selected_pubmed_ids_search_appendix = " ".join(["OR " + item for item in selected_pubmed_ids])
    else:
        selected_pubmed_ids_search_appendix = ""
    output_file = os.path.join(data_dir, constants.FILE_ALL_PUBLICATIONS)

    existing_publications = []
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            existing_publications = yaml.safe_load(f) or []

    new_publications = []
    pubmed_ids = fetch_publications_by_term(
        '(("demaria m"[Author] or "m demaria"[Author] or "Marco Demaria"[Author]) AND (groningen[Affiliation])) OR (demaria[Author] AND (Campisi[Author] OR Poli[Author]))' + selected_pubmed_ids_search_appendix)
    if len(existing_publications) != len(pubmed_ids):
        for pubmed_id in pubmed_ids:
            if any(pub['pubmed_id'] == pubmed_id for pub in existing_publications):
                continue
            publication_details = get_publication_details(pubmed_id)
            if publication_details:
                authors = publication_details['authors']
                authors = ", ".join(authors)
                publication = {
                    'pubmed_id': pubmed_id,
                    'title': publication_details['title'],
                    'authors': authors,
                    'year': publication_details['year'],
                    'journal': publication_details['journal']
                }
                new_publications.append(publication)

        existing_publications.extend(new_publications)
    else:
        print("Publications: No new items to add. Checking selected publications")

    existing_publications = list({
                                     str(d["pubmed_id"]): {**d, 'pubmed_id': str(d["pubmed_id"]),
                                                           'is_selected': str(d["pubmed_id"]) in selected_pubmed_ids}
                                     for d in existing_publications
                                 }.values())

    # Sort by 'year' key
    existing_publications = sorted(
        existing_publications,
        key=lambda d: parse_year(d['year']),
        reverse=True  # Sort from newest to oldest
    )
    with open(output_file, 'w', encoding="utf-8") as f:
        yaml.safe_dump(existing_publications, f, default_flow_style=False)


def delete_paper_files(site_dir):
    posts_path = Path(get_dir_path(site_dir, constants.POSTS_DIR))
    pattern = re.compile(r"\d{4}-\d{2}-\d{2}-paper_\d+\.md$")

    for file_path in posts_path.iterdir():
        if file_path.is_file() and pattern.match(file_path.name):
            file_path.unlink()


def export_news(site_dir):
    publications_file = os.path.join(get_dir_path(site_dir, constants.DATA_DIR), constants.FILE_ALL_PUBLICATIONS)
    delete_paper_files(site_dir)
    if os.path.exists(publications_file):
        with open(publications_file, 'r') as file:
            publications = yaml.safe_load(file)

        date_pattern = re.compile(r'^\d{4} \w{3}( \d{1,2})?$')
        # Filter publications
        filtered_publications = []
        for pub in publications:
            match = date_pattern.match(str(pub['year']))
            if match:
                if len(match.group(0).split()) == 2:
                    pub['year'] += ' 01'
                filtered_publications.append(pub)
        filtered_publications = [
            f for f in filtered_publications
            if f["authors"]
               and f["authors"].split(",")[-1].strip().lower() == "demaria m"
        ]
        for pub in filtered_publications:
            date_str = pub['year']
            date_obj = datetime.strptime(date_str, '%Y %b %d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            sanitized_title = sanitize_title(pub['title'])
            content = f"""---
layout: double
title: \"New publication: {sanitized_title}\"
date: {pub['year']}
thumbnail: "'/assets/posts/pubmed_{pub['pubmed_id']}.png'"
---
📖 <strong>Title:</strong> "{pub['title']}"  

🖊️ <strong>Authors:</strong> <em>{pub['authors'].replace("Demaria M", "<strong>Demaria M</strong>")}</em>  

🏛️ <strong>Published in:</strong> <em>{pub['journal']}</em>  

🎉 Congratulations to the authors!  

🔗 <a href="https://pubmed.ncbi.nlm.nih.gov/{pub['pubmed_id']}/">View on PubMed</a>  

![](/assets/posts/pubmed_{pub['pubmed_id']}.png)
"""
            file_name = f"{formatted_date}-paper_{pub['pubmed_id']}.md"
            file_path = os.path.join(get_dir_path(site_dir, constants.POSTS_DIR), file_name)

            with open(file_path, 'w', encoding="utf-8") as md_file:
                md_file.write(content)


def process(args):
    print("Processing publications")
    site_dir = args[constants.ARG_SITE_DIR]
    fetch_and_save_publications(get_dir_path(site_dir, constants.DATA_DIR), args)
    export_news(site_dir)
    produce_screenshots(site_dir)
