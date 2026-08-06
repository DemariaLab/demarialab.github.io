import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, quote_plus
from xml.etree import ElementTree as ET

import requests
import yaml
from playwright.sync_api import sync_playwright

from python_generator import constants
from python_generator.utils import get_dir_path, read_published_google_sheet, sanitize_title


PUBLICATION_TEMPLATE_FILENAME = "publication_template.html"
PUBLICATION_RENDER_EXTENSION = "svg"


def resolve_final_url(url):
    if url.startswith("doi:"):
        doi = url[4:].strip()
        doi_url = f"https://doi.org/{quote(doi)}"
        try:
            response = requests.head(doi_url, allow_redirects=True)
            return response.url
        except requests.exceptions.RequestException as error:
            print(f"Publications: Error resolving DOI URL: {error}")
            return doi_url
    return url


def _as_author_list(publication):
    authors = publication.get("display_authors") or publication.get("authors") or []
    if isinstance(authors, str):
        return [author.strip() for author in authors.split(",") if author.strip()]
    return [str(author).strip() for author in authors if str(author).strip()]


def _as_abstract_sections(publication):
    abstract = publication.get("abstract") or []
    if isinstance(abstract, str):
        abstract = [{"label": "", "text": abstract}]

    sections = []
    for section in abstract:
        if isinstance(section, str):
            label = ""
            text = section
        else:
            label = str(section.get("label") or "").strip()
            text = str(section.get("text") or "").strip()

        if text:
            sections.append({"label": label, "text": text})
    return sections


def _populate_publication_template(page, publication):
    payload = {
        "title": str(publication.get("title") or "").strip(),
        "authors": _as_author_list(publication),
        "journal": str(
            publication.get("journal_title")
            or publication.get("journal")
            or ""
        ).strip(),
        "publication_type": str(
            publication.get("publication_type") or "Journal Article"
        ).strip(),
        "publication_date": str(publication.get("year") or "").strip(),
        "abstract": _as_abstract_sections(publication),
    }

    page.evaluate(
        r'''(data) => {
            const setText = (id, value) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value || "";
                }
                return element;
            };

            document.title = data.title || "Publication";
            setText("publication-type", data.publication_type);
            setText("journal", data.journal);
            setText("publication-date", data.publication_date);
            setText("publication-title", data.title);

            const meta = document.getElementById("publication-meta");
            const type = document.getElementById("publication-type");
            const journal = document.getElementById("journal");
            const date = document.getElementById("publication-date");

            if (type && !data.publication_type) type.hidden = true;
            if (journal && !data.journal) journal.hidden = true;
            if (date && !data.publication_date) date.hidden = true;
            if (meta && !data.publication_type && !data.journal && !data.publication_date) {
                meta.hidden = true;
            }

            const authors = document.getElementById("authors");
            if (authors) {
                authors.replaceChildren();
                if (data.authors.length === 0) {
                    authors.hidden = true;
                } else {
                    data.authors.forEach((author, index) => {
                        const item = document.createElement("span");
                        item.className = "author";
                        item.textContent = author;
                        authors.appendChild(item);

                        if (index < data.authors.length - 1) {
                            authors.appendChild(document.createTextNode(", "));
                        }
                    });
                }
            }

            const abstractSection = document.getElementById("abstract-section");
            const abstractContent = document.getElementById("abstract-content");
            if (abstractSection && abstractContent) {
                abstractContent.replaceChildren();
                if (data.abstract.length === 0) {
                    abstractSection.hidden = true;
                } else {
                    data.abstract.forEach((section) => {
                        const paragraph = document.createElement("p");
                        if (section.label) {
                            const label = document.createElement("strong");
                            label.className = "abstract-label";
                            label.textContent = section.label.endsWith(":")
                                ? section.label
                                : `${section.label}:`;
                            paragraph.appendChild(label);
                            paragraph.appendChild(document.createTextNode(` ${section.text}`));
                        } else {
                            paragraph.textContent = section.text;
                        }
                        abstractContent.appendChild(paragraph);
                    });
                }
            }

            window.scrollTo(0, 0);
        }''',
        payload,
    )


def _ensure_xhtml_namespace(serialized_html):
    if 'xmlns="http://www.w3.org/1999/xhtml"' in serialized_html:
        return serialized_html
    return serialized_html.replace("<html", '<html xmlns="http://www.w3.org/1999/xhtml"', 1)


def _page_dimensions(page):
    return page.evaluate(
        """() => {
            const root = document.documentElement;
            const body = document.body;
            return {
                width: Math.ceil(Math.max(
                    root.scrollWidth,
                    body.scrollWidth,
                    root.clientWidth,
                    body.clientWidth
                )),
                height: Math.ceil(Math.max(
                    root.scrollHeight,
                    body.scrollHeight,
                    root.clientHeight,
                    body.clientHeight
                ))
            };
        }"""
    )


def _write_page_svg(page, output_path):
    dimensions = _page_dimensions(page)
    serialized_html = page.evaluate(
        "() => new XMLSerializer().serializeToString(document.documentElement)"
    )
    serialized_html = _ensure_xhtml_namespace(serialized_html)

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{dimensions['width']}" height="{dimensions['height']}" viewBox="0 0 {dimensions['width']} {dimensions['height']}">
  <rect width="100%" height="100%" fill="white"/>
  <foreignObject x="0" y="0" width="{dimensions['width']}" height="{dimensions['height']}">
    {serialized_html}
  </foreignObject>
</svg>
'''

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(svg_content)


def take_screenshots_of_publications(
    publications,
    output_dir,
    template_path=None,
    width=960,
    height=1100,
):
    """
    Render publication summaries from a local HTML template and save them as SVG.

    Note: the SVG uses <foreignObject> to preserve the rendered HTML/CSS layout.
    This keeps the output visually 1:1 with the template in modern browsers, but
    some non-browser SVG consumers may support it only partially.
    """
    os.makedirs(output_dir, exist_ok=True)

    template_path = Path(
        template_path or Path(__file__).with_name(PUBLICATION_TEMPLATE_FILENAME)
    )
    if not template_path.exists():
        raise FileNotFoundError(
            f"Publication template not found: {template_path}. "
            f"Place {PUBLICATION_TEMPLATE_FILENAME} next to this Python file."
        )

    template_html = template_path.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        chromium_executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if chromium_executable:
            launch_options["executable_path"] = chromium_executable

        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            java_script_enabled=True,
            color_scheme="light",
        )
        page = context.new_page()

        try:
            for publication in publications:
                pubmed_id = str(publication.get("pubmed_id") or "").strip()
                if not pubmed_id or pubmed_id == "null":
                    continue

                output_path = os.path.join(
                    output_dir,
                    f"pubmed_{pubmed_id}.{PUBLICATION_RENDER_EXTENSION}",
                )
                if os.path.exists(output_path):
                    continue

                page.set_content(
                    template_html,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                _populate_publication_template(page, publication)
                _write_page_svg(page, output_path)
        finally:
            context.close()
            browser.close()


def produce_screenshots(site_dir, publications=None, template_path=None):
    if publications is None:
        publications_file = os.path.join(
            get_dir_path(site_dir, constants.DATA_DIR),
            constants.FILE_ALL_PUBLICATIONS,
        )
        with open(publications_file, "r", encoding="utf-8") as file:
            publications = yaml.safe_load(file) or []

    take_screenshots_of_publications(
        publications,
        get_dir_path(site_dir, "assets", "posts"),
        template_path=template_path,
    )


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


def _element_text(element):
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _normalise_pubmed_month(month):
    month = str(month or "").strip()
    month_lookup = {
        "1": "Jan", "01": "Jan", "2": "Feb", "02": "Feb",
        "3": "Mar", "03": "Mar", "4": "Apr", "04": "Apr",
        "5": "May", "05": "May", "6": "Jun", "06": "Jun",
        "7": "Jul", "07": "Jul", "8": "Aug", "08": "Aug",
        "9": "Sep", "09": "Sep", "10": "Oct", "11": "Nov",
        "12": "Dec",
    }
    if month in month_lookup:
        return month_lookup[month]
    if len(month) >= 3:
        return month[:3].title()
    return ""


def _extract_pubmed_date(article):
    pub_date = article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate")
    if pub_date is not None:
        year = (pub_date.findtext("Year") or "").strip()
        month = _normalise_pubmed_month(pub_date.findtext("Month"))
        day = (pub_date.findtext("Day") or "").strip()
        if year:
            return " ".join(part for part in (year, month, day) if part)

        medline_date = (pub_date.findtext("MedlineDate") or "").strip()
        year_match = re.search(r"\b(19|20)\d{2}\b", medline_date)
        month_match = re.search(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
            medline_date,
            flags=re.IGNORECASE,
        )
        if year_match:
            parts = [year_match.group(0)]
            if month_match:
                parts.append(month_match.group(0).title())
            return " ".join(parts)

    article_date = article.find("./MedlineCitation/Article/ArticleDate")
    if article_date is not None:
        year = (article_date.findtext("Year") or "").strip()
        month = _normalise_pubmed_month(article_date.findtext("Month"))
        day = (article_date.findtext("Day") or "").strip()
        if year:
            return " ".join(part for part in (year, month, day) if part)

    return ""


def _parse_pubmed_article(article):
    pubmed_id = (article.findtext("./MedlineCitation/PMID") or "").strip()
    article_node = article.find("./MedlineCitation/Article")
    if not pubmed_id or article_node is None:
        return None

    summary_authors = []
    display_authors = []
    for author in article_node.findall("./AuthorList/Author"):
        collective_name = (author.findtext("CollectiveName") or "").strip()
        if collective_name:
            summary_authors.append(collective_name)
            display_authors.append(collective_name)
            continue

        last_name = (author.findtext("LastName") or "").strip()
        initials = (author.findtext("Initials") or "").strip()
        fore_name = (author.findtext("ForeName") or "").strip()
        suffix = (author.findtext("Suffix") or "").strip()

        summary_name = " ".join(part for part in (last_name, initials) if part)
        display_name = " ".join(part for part in (fore_name, last_name, suffix) if part)
        if summary_name:
            summary_authors.append(summary_name)
        if display_name or summary_name:
            display_authors.append(display_name or summary_name)

    if "Demaria" not in ", ".join(summary_authors):
        return None

    abstract_sections = []
    for abstract_text in article_node.findall("./Abstract/AbstractText"):
        content = _element_text(abstract_text)
        if content:
            abstract_sections.append({
                "label": (abstract_text.get("Label") or "").strip(),
                "text": content,
            })

    doi = ""
    for article_id in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if (article_id.get("IdType") or "").lower() == "doi":
            doi = _element_text(article_id)
            break
    if not doi:
        for location_id in article_node.findall("./ELocationID"):
            if (location_id.get("EIdType") or "").lower() == "doi":
                doi = _element_text(location_id)
                break

    publication_types = [
        _element_text(item)
        for item in article_node.findall("./PublicationTypeList/PublicationType")
        if _element_text(item)
    ]

    journal = (
        article_node.findtext("./Journal/ISOAbbreviation")
        or article_node.findtext("./Journal/Title")
        or ""
    ).strip()
    journal_title = (article_node.findtext("./Journal/Title") or journal).strip()
    pages = (
        article_node.findtext("Pagination/MedlinePgn")
        or article_node.findtext("ELocationID")
        or ""
    ).strip()

    return {
        "pubmed_id": pubmed_id,
        "title": _element_text(article_node.find("ArticleTitle")),
        "authors": summary_authors,
        "display_authors": display_authors,
        "year": _extract_pubmed_date(article),
        "journal": journal,
        "journal_title": journal_title,
        "abstract": abstract_sections,
        "publication_type": publication_types[0] if publication_types else "Journal Article",
        "publication_types": publication_types,
        "doi": doi,
        "volume": (article_node.findtext("./Journal/JournalIssue/Volume") or "").strip(),
        "issue": (article_node.findtext("./Journal/JournalIssue/Issue") or "").strip(),
        "pages": pages,
        "details_fetched": True,
    }


def _request_pubmed_xml(pubmed_ids):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pubmed_ids),
        "retmode": "xml",
    }

    sleep_time = 5
    max_sleep_time = 60
    while True:
        response = requests.get(base_url, params=params, timeout=60)
        if response.status_code == 200:
            return response.content
        if response.status_code == 429:
            print(f"Too many requests. Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            sleep_time = min(max_sleep_time, sleep_time * 2)
            continue

        print(
            "Publications: Error fetching publication details. "
            f"Status code: {response.status_code}"
        )
        return None


def get_publication_details(pubmed_id_or_ids):
    """
    Fetch one or more PubMed records with efetch.

    A single ID returns one publication dictionary for backwards compatibility.
    An iterable of IDs returns a dictionary keyed by PubMed ID. IDs are fetched
    in batches, so the same API response can feed YAML generation and SVG output.
    """
    single_id = isinstance(pubmed_id_or_ids, (str, int))
    if single_id:
        pubmed_ids = [str(pubmed_id_or_ids)]
    else:
        pubmed_ids = [str(pubmed_id) for pubmed_id in pubmed_id_or_ids]

    pubmed_ids = list(dict.fromkeys(pubmed_id for pubmed_id in pubmed_ids if pubmed_id))
    details_by_id = {}
    batch_size = 200

    for index in range(0, len(pubmed_ids), batch_size):
        batch = pubmed_ids[index:index + batch_size]
        xml_content = _request_pubmed_xml(batch)
        if not xml_content:
            continue

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as error:
            print(f"Publications: Error parsing PubMed XML: {error}")
            continue

        for article in root.findall(".//PubmedArticle"):
            details = _parse_pubmed_article(article)
            if details:
                details_by_id[details["pubmed_id"]] = details

        if index + batch_size < len(pubmed_ids):
            time.sleep(0.35)

    if single_id:
        return details_by_id.get(pubmed_ids[0]) if pubmed_ids else None
    return details_by_id


def fetch_and_save_publications(data_dir, args):
    selected_pubmed_ids = [
        str(item.get("pubmed_id"))
        for item in read_published_google_sheet(
            args[constants.ARG_SELECTED_PUBLICATIONS_SHEET_ID]
        )["data"]
        if item.get("pubmed_id")
    ]
    if selected_pubmed_ids:
        selected_pubmed_ids_search_appendix = " " + " ".join(
            ["OR " + item for item in selected_pubmed_ids]
        )
    else:
        selected_pubmed_ids_search_appendix = ""

    output_file = os.path.join(data_dir, constants.FILE_ALL_PUBLICATIONS)
    existing_publications = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as file:
            existing_publications = yaml.safe_load(file) or []

    existing_by_id = {
        str(publication["pubmed_id"]): {
            **publication,
            "pubmed_id": str(publication["pubmed_id"]),
        }
        for publication in existing_publications
        if publication.get("pubmed_id")
    }

    pubmed_ids = fetch_publications_by_term(
        '(("demaria m"[Author] or "m demaria"[Author] or "Marco Demaria"[Author]) '
        'AND (groningen[Affiliation])) OR (demaria[Author] AND '
        '(Campisi[Author] OR Poli[Author]))'
        + selected_pubmed_ids_search_appendix
    )
    pubmed_ids = [str(pubmed_id) for pubmed_id in pubmed_ids]

    ids_needing_details = [
        pubmed_id
        for pubmed_id in pubmed_ids
        if pubmed_id not in existing_by_id
        or not existing_by_id[pubmed_id].get("details_fetched")
    ]

    details_by_id = get_publication_details(ids_needing_details) if ids_needing_details else {}

    for pubmed_id, details in details_by_id.items():
        publication = {
            **existing_by_id.get(pubmed_id, {}),
            **details,
            "authors": ", ".join(details["authors"]),
            "pubmed_id": pubmed_id,
        }
        existing_by_id[pubmed_id] = publication

    if not ids_needing_details:
        print("Publications: No new or incomplete items to fetch")

    publications = list({
        pubmed_id: {
            **publication,
            "pubmed_id": pubmed_id,
            "is_selected": pubmed_id in selected_pubmed_ids,
        }
        for pubmed_id, publication in existing_by_id.items()
    }.values())

    publications = sorted(
        publications,
        key=lambda publication: parse_year(publication["year"]),
        reverse=True,
    )

    with open(output_file, "w", encoding="utf-8") as file:
        yaml.safe_dump(publications, file, default_flow_style=False, allow_unicode=True)

    return publications


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
        with open(publications_file, 'r', encoding='utf-8') as file:
            publications = yaml.safe_load(file)

        date_pattern = re.compile(r'^\d{4} \w{3}( \d{1,2})?$')
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
thumbnail: "'/assets/posts/pubmed_{pub['pubmed_id']}.{PUBLICATION_RENDER_EXTENSION}'"
---
📖 <strong>Title:</strong> \"{pub['title']}\"  

🖊️ <strong>Authors:</strong> <em>{pub['authors'].replace("Demaria M", "<strong>Demaria M</strong>")}</em>  

🏛️ <strong>Published in:</strong> <em>{pub['journal']}</em>  

🎉 Congratulations to the authors!  

🔗 <a href="https://pubmed.ncbi.nlm.nih.gov/{pub['pubmed_id']}/">View on PubMed</a>  

![](/assets/posts/pubmed_{pub['pubmed_id']}.{PUBLICATION_RENDER_EXTENSION})
"""
            file_name = f"{formatted_date}-paper_{pub['pubmed_id']}.md"
            file_path = os.path.join(get_dir_path(site_dir, constants.POSTS_DIR), file_name)

            with open(file_path, 'w', encoding='utf-8') as md_file:
                md_file.write(content)


def process(args):
    print("Processing publications")
    site_dir = args[constants.ARG_SITE_DIR]
    publications = fetch_and_save_publications(
        get_dir_path(site_dir, constants.DATA_DIR), args
    )
    export_news(site_dir)
    produce_screenshots(site_dir, publications=publications)
