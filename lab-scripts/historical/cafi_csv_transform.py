#!/usr/bin/env python3
"""
CAFI historical CSV → canonical fields for console + Security Report.

Reads one or more source CSVs, maps columns to the schemas the console
ingest() path and report template expect, writes cleaned CSVs.

Usage:
  python cafi_csv_transform.py --kind events --in raw_events.csv --out clean_events.csv
  python cafi_csv_transform.py --kind all --indir ./raw --outdir ./clean

Kinds: events, explanations, fed, assets, maint, changes, aiusage
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Target schemas (must match console TEMPLATES / ingest)
# ---------------------------------------------------------------------------
SCHEMAS: Dict[str, List[str]] = {
    "events": [
        "TimeGenerated", "EventSource", "DeviceRef", "DeviceId",
        "Severity", "EventDetail",
    ],
    "explanations": [
        "TimeGenerated", "DeviceRef", "AnomalyScore", "ContextStatus",
        "NarrativeSummary", "PivotSteps",
        "Driver1_Feature", "Driver1_SHAPValue",
        "Driver2_Feature", "Driver2_SHAPValue",
        "Driver3_Feature", "Driver3_SHAPValue",
        "Driver4_Feature", "Driver4_SHAPValue",
        "Driver5_Feature", "Driver5_SHAPValue",
    ],
    "fed": [
        "round", "global_offset", "accepted_nodes", "rejected_nodes",
    ],
    "assets": [
        "DeviceId", "Hostname", "AssetRole", "CriticalityTier",
        "OwningSector", "SiteCode", "Vendor", "Protocol",
    ],
    "maint": [
        "WindowId", "SiteCode", "OwningSector", "StartTime", "EndTime",
        "WindowType", "Description", "ApprovedBy",
    ],
    "changes": [
        "ContextId", "DeviceId", "ChangeType", "ChangeTimestamp",
        "ChangedBy", "ChangeDetail",
    ],
    "aiusage": [
        "TimeGenerated", "UserId", "Department", "AITool", "Endpoint",
        "Action", "DataClassification", "SensitiveDetected", "Logged", "Detail",
    ],
}

# Common alternate header names → canonical (case-insensitive match)
ALIASES: Dict[str, List[str]] = {
    "TimeGenerated": [
        "timegenerated", "timestamp", "time", "eventtime", "event_time",
        "created", "createdat", "created_at", "datetime", "date_time",
        "@timestamp", "ingestiontime",
    ],
    "EventSource": [
        "eventsource", "source", "logsource", "log_source", "origin",
        "provider", "product", "sensor",
    ],
    "DeviceRef": [
        "deviceref", "device", "computer", "hostname", "host", "hostname",
        "assetname", "asset_name", "machinename", "machine_name", "fqdn",
    ],
    "DeviceId": [
        "deviceid", "device_id", "assetid", "asset_id", "hostid", "host_id",
        "resourceid", "agentid", "endpointid",
    ],
    "Severity": [
        "severity", "alertseverity", "logseverity", "level", "priority",
        "sev", "urgency",
    ],
    "EventDetail": [
        "eventdetail", "detail", "description", "message", "syslogmessage",
        "activity", "summary", "title", "alertname", "event",
    ],
    "AnomalyScore": [
        "anomalyscore", "anomaly_score", "score", "mlscore", "iforest_score",
    ],
    "ContextStatus": [
        "contextstatus", "context_status", "context", "ctxstatus",
    ],
    "NarrativeSummary": [
        "narrativesummary", "narrative", "explanation", "summary", "rationale",
    ],
    "PivotSteps": [
        "pivotsteps", "pivot_steps", "pivots", "investigationsteps",
    ],
    "round": ["round", "round_id", "fedround", "epoch", "iteration"],
    "global_offset": [
        "global_offset", "globaloffset", "global", "global_loss",
        "loss", "residual",
    ],
    "accepted_nodes": [
        "accepted_nodes", "accepted", "acceptednodes", "nodes_accepted",
    ],
    "rejected_nodes": [
        "rejected_nodes", "rejected", "rejectednodes", "nodes_rejected",
    ],
    "Hostname": ["hostname", "host", "computer", "devicename", "name"],
    "AssetRole": ["assetrole", "role", "device_role", "function", "type"],
    "CriticalityTier": [
        "criticalitytier", "tier", "criticality", "crit", "importance",
    ],
    "OwningSector": [
        "owningsector", "sector", "agency", "entity", "organization", "org",
    ],
    "SiteCode": ["sitecode", "site", "location", "facility", "plant"],
    "Vendor": ["vendor", "manufacturer", "make", "oem"],
    "Protocol": ["protocol", "proto", "transport"],
    "WindowId": ["windowid", "window_id", "maintid", "id"],
    "StartTime": ["starttime", "start", "begin", "window_start"],
    "EndTime": ["endtime", "end", "finish", "window_end"],
    "WindowType": ["windowtype", "type", "maint_type", "category"],
    "Description": ["description", "detail", "notes", "summary"],
    "ApprovedBy": ["approvedby", "approver", "approved_by", "owner"],
    "ContextId": ["contextid", "context_id", "changeid", "id"],
    "ChangeType": ["changetype", "change_type", "type", "category"],
    "ChangeTimestamp": [
        "changetimestamp", "change_time", "timestamp", "timegenerated",
    ],
    "ChangedBy": ["changedby", "changed_by", "actor", "user"],
    "ChangeDetail": ["changedetail", "detail", "description", "notes"],
    "UserId": ["userid", "user_id", "user", "upn", "account"],
    "Department": ["department", "dept", "businessunit", "team"],
    "AITool": ["aitool", "ai_tool", "tool", "application", "app"],
    "Endpoint": ["endpoint", "url", "api", "destination"],
    "Action": ["action", "operation", "activity", "verb"],
    "DataClassification": [
        "dataclassification", "classification", "data_class", "sensitivity",
    ],
    "SensitiveDetected": [
        "sensitivedetected", "sensitive", "has_sensitive", "dlp_hit",
    ],
    "Logged": ["logged", "is_logged", "audited"],
    "Detail": ["detail", "description", "message", "notes"],
}

# Driver columns for explanations (DriverN_Feature / DriverN_SHAPValue)
for i in range(1, 6):
    ALIASES[f"Driver{i}_Feature"] = [
        f"driver{i}_feature", f"driver{i}feature", f"feature{i}",
        f"shap_feature_{i}", f"top{i}_feature",
    ]
    ALIASES[f"Driver{i}_SHAPValue"] = [
        f"driver{i}_shapvalue", f"driver{i}_shap", f"shap{i}",
        f"shap_value_{i}", f"top{i}_shap",
    ]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())


def build_header_map(headers: List[str], kind: str) -> Dict[str, Optional[str]]:
    """Map canonical field → source header (or None if missing)."""
    norm_headers = {norm(h): h for h in headers}
    mapping: Dict[str, Optional[str]] = {}
    for field in SCHEMAS[kind]:
        aliases = ALIASES.get(field, [field])
        found = None
        # exact canonical first
        for a in [field] + aliases:
            key = norm(a)
            if key in norm_headers:
                found = norm_headers[key]
                break
        mapping[field] = found
    return mapping


def transform_rows(
    rows: List[Dict[str, str]], kind: str, header_map: Dict[str, Optional[str]]
) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in rows:
        item: Dict[str, str] = {}
        for field in SCHEMAS[kind]:
            src = header_map.get(field)
            val = (r.get(src, "") if src else "") or ""
            item[field] = val.strip()
        # Drop completely empty rows
        if any(item.values()):
            out.append(item)
    return out


def read_csv(path: Path) -> tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t|;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return headers, rows


def write_csv(path: Path, kind: str, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = SCHEMAS[kind]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def process_one(kind: str, src: Path, dst: Path) -> None:
    headers, rows = read_csv(src)
    header_map = build_header_map(headers, kind)
    missing = [f for f, s in header_map.items() if s is None]
    mapped = {f: s for f, s in header_map.items() if s is not None}

    print(f"[{kind}] {src.name}")
    print(f"  source columns: {len(headers)}")
    print(f"  mapped: {len(mapped)}/{len(SCHEMAS[kind])}")
    for f, s in header_map.items():
        print(f"    {f:24} <- {s or '(missing)'}")
    if missing:
        print(f"  WARNING: missing fields will be empty: {', '.join(missing)}")

    cleaned = transform_rows(rows, kind, header_map)
    write_csv(dst, kind, cleaned)
    print(f"  wrote {len(cleaned)} rows -> {dst}")


def guess_kind(name: str) -> Optional[str]:
    n = name.lower()
    rules = [
        ("explain", "explanations"),
        ("shap", "explanations"),
        ("fed", "fed"),
        ("anomaly", "events"),
        ("event", "events"),
        ("alert", "events"),
        ("asset", "assets"),
        ("inventory", "assets"),
        ("maint", "maint"),
        ("window", "maint"),
        ("change", "changes"),
        ("context", "changes"),
        ("aiusage", "aiusage"),
        ("ai_usage", "aiusage"),
        ("casb", "aiusage"),
    ]
    for needle, kind in rules:
        if needle in n:
            return kind
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="CAFI historical CSV transform")
    p.add_argument("--kind", choices=list(SCHEMAS.keys()) + ["all"], required=True)
    p.add_argument("--in", dest="infile", help="Input CSV (single-file mode)")
    p.add_argument("--out", dest="outfile", help="Output CSV (single-file mode)")
    p.add_argument("--indir", help="Input directory (kind=all or batch)")
    p.add_argument("--outdir", default="./clean", help="Output directory")
    args = p.parse_args()

    if args.kind != "all":
        if not args.infile:
            print("--in is required when --kind is not all", file=sys.stderr)
            return 2
        src = Path(args.infile)
        dst = Path(args.outfile) if args.outfile else Path(args.outdir) / f"CAFI_{args.kind}_clean.csv"
        process_one(args.kind, src, dst)
        return 0

    indir = Path(args.indir or ".")
    outdir = Path(args.outdir)
    files = sorted(indir.glob("*.csv"))
    if not files:
        print(f"No CSV files in {indir}", file=sys.stderr)
        return 1
    for src in files:
        kind = guess_kind(src.name)
        if not kind:
            print(f"Skip (unknown kind): {src.name}")
            continue
        dst = outdir / f"CAFI_{kind}_clean.csv"
        process_one(kind, src, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
