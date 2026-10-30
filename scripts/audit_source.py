"""Bounded, credential-free inventory of published AIHW aggregate sources.

This reads document structure; it neither trains a model nor infers suppressed cells.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import posixpath
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

AIHW = "https://www.aihw.gov.au"
API = "https://myhospitalsapi.aihw.gov.au"
SOURCES = {
    "monthly-topic.html": AIHW + "/hospitals/topics/emergency-departments/emergency-department-care-over-time",
    "downloads.html": AIHW + "/hospitals/latest-updates-and-downloads/data",
    "measures.json": API + "/api/v1/measures",
    "download-codes.json": API + "/api/v1/measure-downloads/measure-download-codes",
    "simple-codes.json": API + "/api/v1/simple-downloads/download-codes",
    "ed-datasets.json": API + "/api/v1/datasets?measure_code=MYH0035",
    "emergency-2024-25.xlsx": AIHW + "/getmedia/9cd61a84-27f4-48aa-aa52-8bccd82e4851/Emergency-department-care-2024-25.xlsx",
}
QLD_SOURCES = {
    "qld-catalog.json": "https://www.data.qld.gov.au/api/3/action/package_show?id=emergency-departments-quarterly-data",
    "qld-data.json": "https://www.data.qld.gov.au/api/3/action/datastore_search?resource_id=a9634f60-dd88-4d40-8e80-efaf9b6135c5&limit=1000",
}
MAX_DOWNLOAD = 8 * 1024 * 1024
MAX_EXPANDED = 40 * 1024 * 1024
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
QLD_FIELDS = {
    '_id', 'Facility/HHS Code', 'Facility/HHS Desc', 'Last Month in QTR',
    'Triage_Category', 'Number of Attendances', 'Variation in the number of attendances (%)',
    'Patients Seen within clinically recommended times (%)',
    'Median Waiting time to treatment (minutes)', 'Patients who did not wait for treatment (%)',
    'Patients admitted from the Emergency Department (%)', 'Admissions to hospital within 4 hours (%)',
    'Patients whose ED stay was within 4 hours (%)',
    'Number of patients who left after treatment commenced',
    'Percentage of patients who left after treatment commenced (%)',
    'Number of patients who did not wait for treatment',
}


class AuditError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def xml(body: bytes) -> ET.Element:
    # Workbook XML is UTF-8. Reject alternative encodings/entities rather than
    # attempting to support all valid OOXML variants in this narrow inventory.
    if b"\x00" in body or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise AuditError("unsupported_xml")
    body.decode("utf-8-sig", errors="strict")
    return ET.fromstring(body)


def workbook_inventory(body: bytes, *, preview_rows: int = 6) -> dict:
    """Read ZIP members in memory; never extract paths or evaluate formulas."""
    if type(preview_rows) is not int or not 1 <= preview_rows <= 30:
        raise AuditError('preview_limit')
    if len(body) > MAX_DOWNLOAD:
        raise AuditError("download_limit")
    with zipfile.ZipFile(io.BytesIO(body)) as book:
        infos = book.infolist()
        names = [i.filename for i in infos]
        if len(infos) > 500 or len(names) != len(set(names)):
            raise AuditError("member_limit_or_duplicate")
        if sum(i.file_size for i in infos) > MAX_EXPANDED:
            raise AuditError("expanded_limit")
        for item in infos:
            if item.flag_bits & 1 or item.filename.startswith("/") or ".." in item.filename.split("/"):
                raise AuditError("unsupported_member")
        shared = []
        if "xl/sharedStrings.xml" in names:
            for item in xml(book.read("xl/sharedStrings.xml")).findall("s:si", NS):
                shared.append("".join(item.itertext()))
        relationships = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in xml(book.read("xl/_rels/workbook.xml.rels"))
            if r.attrib.get("TargetMode") != "External"
        }
        inventory = []
        for sheet in xml(book.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS):
            relation = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = relationships[relation]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            if not member.startswith("xl/worksheets/") or member not in names:
                raise AuditError("unsupported_sheet")
            root = xml(book.read(member))
            rows, preview, notes, formulas = 0, [], [], 0
            for row in root.findall("s:sheetData/s:row", NS):
                rows += 1
                texts = []
                for cell in row.findall("s:c", NS):
                    if cell.find("s:f", NS) is not None:
                        formulas += 1
                        continue
                    value = cell.findtext("s:v", default="", namespaces=NS)
                    if cell.attrib.get("t") == "s":
                        value = shared[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(cell.find("s:is", NS).itertext())
                    texts.append(value)
                if rows <= preview_rows:
                    preview.append(texts[:15])
                joined = " | ".join(texts)
                if any(s in joined.lower() for s in ("copyright", "creative commons", "licence", "license", "monthly", "by month", "not available", "suppressed")):
                    if len(notes) < 8:
                        notes.append(joined[:1500])
            inventory.append({"sheet": sheet.attrib["name"], "rows": rows,
                              "formula_cells": formulas, "preview": preview, "notes": notes})
        return {"sheets": inventory, "members": len(infos),
                "expanded_bytes": sum(i.file_size for i in infos)}


class PublicLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag not in {"a", "iframe", "param"}:
            return
        for key, value in attrs:
            if key in {"href", "src", "value"} and value:
                url = urllib.parse.urljoin(AIHW, value)
                parsed = urllib.parse.urlsplit(url)
                if parsed.scheme == "https" and any(x in url.lower() for x in (".xlsx", "tableau", "powerbi", "download")):
                    self.links.add(url)


def summarize(name: str, body: bytes) -> dict:
    if name.endswith(".xlsx"):
        return workbook_inventory(body)
    if name.endswith(".html"):
        parser = PublicLinks()
        parser.feed(body.decode("utf-8"))
        return {"public_links": sorted(parser.links)[:60]}
    if name.endswith('.csv'):
        reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig'), newline=''))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise AuditError('invalid_csv_header')
        rows = list(reader)
        if len(rows) > 20000 or any(None in row or None in row.values() for row in rows):
            raise AuditError('invalid_csv_shape')
        return {'columns': reader.fieldnames, 'rows': len(rows),
                'periods': sorted({row.get('Last Month in QTR', '') for row in rows}),
                'triage_categories': sorted({row.get('Triage_Category', '') for row in rows}),
                'facilities_or_hhs': len({row.get('Facility/HHS Code', '') for row in rows})}
    data = json.loads(body)
    result = data.get("result", data)
    if name.startswith('qld-') and data.get('success') is not True:
        raise AuditError('api_did_not_succeed')
    if name == 'qld-catalog.json':
        return {'title': result.get('title'), 'license_id': result.get('license_id'),
                'license_title': result.get('license_title'), 'notes': result.get('notes'),
                'resources': [{'id': r.get('id'), 'name': r.get('name'), 'url': r.get('url')}
                              for r in result.get('resources', [])][:100]}
    if name == 'qld-data.json':
        records = result['records']
        fields = result['fields']
        if {x['id'] for x in fields} != QLD_FIELDS or len(fields) != len(QLD_FIELDS):
            raise AuditError('unexpected_qld_schema')
        if not isinstance(records, list) or len(records) > 1000:
            raise AuditError('record_limit')
        if any(not isinstance(r, dict) or set(r) != QLD_FIELDS for r in records):
            raise AuditError('unexpected_qld_record_fields')
        total = result.get('total')
        if type(total) is not int or total < len(records):
            raise AuditError('invalid_total')
        return {'fields': result['fields'], 'rows_returned': len(records),
                'total_rows': result.get('total'), 'limit': result.get('limit'),
                'complete_page_as_reported': total == len(records),
                'periods': sorted({str(r.get('Last Month in QTR', '')) for r in records}),
                'triage_categories': sorted({str(r.get('Triage_Category', '')) for r in records}),
                'facilities_or_hhs': len({str(r.get('Facility/HHS Code', '')) for r in records}),
                'sample_field_names': list(records[0]) if records else []}
    if name == "measures.json":
        return {"version_information": data.get("version_information"),
                "ed_measures": [x for x in result if "emergency department" in x.get("measure_name", "").lower()]}
    if name == "ed-datasets.json":
        return {"version_information": data.get("version_information"),
                "dataset_count": len(result), "datasets": result[:100]}
    return {"version_information": data.get("version_information"), "catalog": result}


def acquire(out: Path, *, catalog_only: bool = False, qld_only: bool = False) -> dict:
    # Fixed URLs only; no credentials, URL arguments, redirects, cookies or retries.
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    records = []
    for name, url in (QLD_SOURCES if qld_only else SOURCES).items():
        if catalog_only and not name.endswith('.json'):
            continue
        record = {"name": name, "url": url, "requested_at": datetime.now(timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(url, headers={"Accept": "*/*", "User-Agent": "aus-health-forecast-lab-source-audit/0.1"})
            with opener.open(request, timeout=20) as response:
                if response.status != 200:
                    raise AuditError("unexpected_status")
                body = response.read(MAX_DOWNLOAD + 1)
                if len(body) > MAX_DOWNLOAD:
                    raise AuditError("download_limit")
                record.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                              content_type=response.headers.get("Content-Type"),
                              acquired_at=datetime.now(timezone.utc).isoformat())
            # Validate structure before retaining a source body. No network
            # response is executed or selected as a forecasting dataset here.
            inventory = summarize(name, body)
            fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
            record["inventory"] = inventory
            record["status"] = "inventoried"
        except urllib.error.HTTPError as exc:
            record.update(status="http_error", http_status=exc.code)
        except AuditError as exc:
            record.update(status='refused', reason=str(exc))
        except (OSError, ValueError, KeyError, IndexError, csv.Error, zipfile.BadZipFile, ET.ParseError) as exc:
            record.update(status="failed", error_type=type(exc).__name__)
        records.append(record)
    report = {"schema_version": 1, "purpose": "public_source_inventory_not_forecast",
              "mode": "qld_quarterly" if qld_only else "catalog_only" if catalog_only else "documents_and_catalog",
              "completed_at": datetime.now(timezone.utc).isoformat(), "sources": records}
    payload = json.dumps(report, ensure_ascii=True, allow_nan=False)
    fd = os.open(out / "inventory.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(payload + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new directory under a trusted parent")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--catalog-only", action="store_true", help="inspect API metadata only; does not obtain forecasting data")
    mode.add_argument("--qld-only", action="store_true", help="inspect one published Queensland quarterly DataStore table and catalogue")
    args = parser.parse_args()
    report = acquire(args.out, catalog_only=args.catalog_only, qld_only=args.qld_only)
    print("SOURCE_INVENTORY=" + json.dumps(report, ensure_ascii=True, allow_nan=False))
    if args.catalog_only or args.qld_only:
        if any(r["status"] != "inventoried" for r in report["sources"]):
            raise SystemExit(2)
    elif not any(r["status"] == "inventoried" and r["name"].endswith(".xlsx") for r in report["sources"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
