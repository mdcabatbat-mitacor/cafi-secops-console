#!/usr/bin/env python3
"""
CAFI historical → CAFI-LAW transform

Inputs:
  - CAFI_*_sample.csv  (exact schema contract for report + console)
  - ISCX CIC flow CSVs / XLSX (Label column)
  - IoT feature CSVs (filename encodes attack class)
  - ToN_IoT Modbus CSV (date,time,label,type)

Outputs (./out by default):
  CAFI_events_clean.csv
  CAFI_explanations_clean.csv
  CAFI_fed_clean.csv
  CAFI_assets_clean.csv
  CAFI_maint_clean.csv
  CAFI_changes_clean.csv
  CAFI_aiusage_clean.csv
  CAFI_aitools_clean.csv
  CAFI_aiendpoints_clean.csv

Every output column set matches console TEMPLATES / ingest() exactly so
CAFI-LAW load + auto-sync populates the Security Report with no mismatched fields.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Canonical schemas (must match console TEMPLATES)
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
    "fed": ["round", "global_offset", "accepted_nodes", "rejected_nodes"],
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
    "aitools": ["AITool", "Vendor", "Status", "Endpoint", "Notes"],
    "aiendpoints": ["Endpoint", "Type", "Controlled", "Gateway"],
}

# Lab asset pool (from sample) used when synthesizing DeviceRef/DeviceId
LAB_ASSETS = [
    ("AST-001", "DC01", "IT"),
    ("AST-002", "plc-reactor-01", "OT"),
    ("AST-003", "FIN-SVR-02", "IT"),
    ("AST-004", "WKS-JSMITH", "IT"),
    ("AST-005", "hmi-scada-02", "OT"),
    ("AST-006", "VPN-GW-01", "IT"),
    ("AST-007", "WEB-PROD-01", "IT"),
    ("AST-008", "eng-ws-07", "OT"),
]

SEVERITY_FROM_LABEL = {
    "BENIGN": "Low",
    "DDoS": "Critical",
    "DoS": "Critical",
    "PortScan": "High",
    "Port Scan": "High",
    "Bot": "High",
    "Brute Force": "High",
    "FTP-Patator": "High",
    "SSH-Patator": "High",
    "Web Attack": "High",
    "Infiltration": "Critical",
    "Heartbleed": "Critical",
    "injection": "Critical",
    "xss": "High",
    "password": "High",
    "ddos": "Critical",
    "scanning": "High",
    "backdoor": "Critical",
    "ransomware": "Critical",
    "mitm": "Critical",
    "ARP Spoofing": "Critical",
    "MQTT DDoS": "Critical",
    "Recon Port Scan": "High",
    "TCP SYN Flood": "Critical",
}

BASE_TS = datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc)


def norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").strip().lower())


def write_csv(path: Path, kind: str, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = SCHEMAS[kind]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"  wrote {len(rows):6d} rows → {path.name}")


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v).strip()
    return str(v).strip()


def read_csv_rows(path: Path, limit: Optional[int] = None) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        headers = [h for h in (reader.fieldnames or []) if h is not None]
        rows: List[Dict[str, str]] = []
        for i, row in enumerate(reader):
            cleaned = {}
            for k, v in row.items():
                if k is None:
                    continue
                cleaned[str(k).strip()] = _cell(v)
            rows.append(cleaned)
            if limit and i + 1 >= limit:
                break
    return headers, rows


def pass_through_sample(sample: Path, kind: str, outdir: Path) -> int:
    if not sample.exists():
        print(f"  skip missing sample: {sample.name}")
        return 0
    headers, rows = read_csv_rows(sample)
    # Accept if all required fields present (case-insensitive)
    have = {norm_header(h) for h in headers}
    need = [f for f in SCHEMAS[kind] if norm_header(f) not in have]
    if need:
        print(f"  WARN {sample.name}: missing {need}")
    # Rebuild with exact column order / names
    cleaned = []
    header_map = {}
    for f in SCHEMAS[kind]:
        for h in headers:
            if norm_header(h) == norm_header(f):
                header_map[f] = h
                break
    for r in rows:
        cleaned.append({f: r.get(header_map.get(f, f), "") for f in SCHEMAS[kind]})
    write_csv(outdir / f"CAFI_{kind}_clean.csv", kind, cleaned)
    return len(cleaned)


def pick_asset(seed: str) -> Tuple[str, str, str]:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return LAB_ASSETS[h % len(LAB_ASSETS)]


def severity_for(label: str) -> str:
    if not label:
        return "Medium"
    for k, v in SEVERITY_FROM_LABEL.items():
        if k.lower() in label.lower():
            return v
    if label.upper() == "BENIGN":
        return "Low"
    return "High"


def ts_from_index(i: int, day_offset: int = 0) -> str:
    t = BASE_TS + timedelta(days=day_offset, seconds=i * 17)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# ISCX CIC flows → events
# ---------------------------------------------------------------------------
def transform_iscx(path: Path, out_events: List[Dict[str, str]], max_per_label: int = 40) -> None:
    print(f"[ISCX] {path.name}")
    counts: Dict[str, int] = {}
    total = 0
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        # normalize field access
        for row in reader:
            # Label column may have leading space
            label = ""
            port = ""
            for k, v in row.items():
                nk = norm_header(k or "")
                if nk == "label":
                    label = (v or "").strip()
                elif nk == "destinationport":
                    port = (v or "").strip()
            if not label:
                continue
            # Prefer attacks; still take some BENIGN
            cap = max_per_label if label.upper() != "BENIGN" else max(8, max_per_label // 5)
            if counts.get(label, 0) >= cap:
                continue
            counts[label] = counts.get(label, 0) + 1
            total += 1
            device_id, device_ref, src = pick_asset(f"{label}-{port}-{total}")
            sev = severity_for(label)
            detail = (
                f"Network flow alert ({label}) dest_port={port or 'n/a'} "
                f"from historical CIC/ISCX capture {path.name}"
            )
            out_events.append({
                "TimeGenerated": ts_from_index(total, day_offset=0),
                "EventSource": src,
                "DeviceRef": device_ref,
                "DeviceId": device_id,
                "Severity": sev,
                "EventDetail": detail,
            })
    print(f"  extracted {total} events from labels: {dict(counts)}")


def transform_iscx_xlsx(path: Path, out_events: List[Dict[str, str]], max_per_label: int = 40) -> None:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        print(f"  skip {path.name}: openpyxl not installed")
        return
    print(f"[ISCX-XLSX] {path.name}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(c).strip() if c is not None else "" for c in next(rows_iter)]
    idx = {norm_header(h): i for i, h in enumerate(headers)}
    li = idx.get("label")
    pi = idx.get("destinationport")
    if li is None:
        print("  no Label column")
        return
    counts: Dict[str, int] = {}
    total = 0
    for row in rows_iter:
        label = str(row[li] or "").strip()
        port = str(row[pi] or "").strip() if pi is not None else ""
        if not label:
            continue
        cap = max_per_label if label.upper() != "BENIGN" else max(8, max_per_label // 5)
        if counts.get(label, 0) >= cap:
            continue
        counts[label] = counts.get(label, 0) + 1
        total += 1
        device_id, device_ref, src = pick_asset(f"xlsx-{label}-{port}-{total}")
        out_events.append({
            "TimeGenerated": ts_from_index(total, day_offset=1),
            "EventSource": src,
            "DeviceRef": device_ref,
            "DeviceId": device_id,
            "Severity": severity_for(label),
            "EventDetail": (
                f"Network flow alert ({label}) dest_port={port or 'n/a'} "
                f"from historical CIC/ISCX workbook {path.name}"
            ),
        })
    print(f"  extracted {total} events from labels: {dict(counts)}")


# ---------------------------------------------------------------------------
# IoT feature CSVs (no Label — attack from filename)
# ---------------------------------------------------------------------------
IOT_FILE_ATTACK = [
    (re.compile(r"arp.?spoof", re.I), "ARP Spoofing", "Critical"),
    (re.compile(r"mqtt.?ddos|connect.?flood", re.I), "MQTT DDoS Connect Flood", "Critical"),
    (re.compile(r"recon.?port|port.?scan", re.I), "Recon Port Scan", "High"),
    (re.compile(r"tcp.?ip.?ddos.?syn|syn.?flood", re.I), "TCP SYN Flood", "Critical"),
    (re.compile(r"benign", re.I), "BENIGN", "Low"),
]


def attack_from_name(name: str) -> Tuple[str, str]:
    for rx, label, sev in IOT_FILE_ATTACK:
        if rx.search(name):
            return label, sev
    return "IoT anomaly", "High"


def transform_iot_features(path: Path, out_events: List[Dict[str, str]], max_rows: int = 50) -> None:
    label, sev = attack_from_name(path.name)
    print(f"[IoT-feat] {path.name} → {label}")
    n = 0
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if n >= max_rows:
                break
            n += 1
            rate = ""
            proto = ""
            for k, v in row.items():
                nk = norm_header(k or "")
                if nk == "rate":
                    rate = (v or "").strip()
                elif nk in ("protocoltype", "protocol"):
                    proto = (v or "").strip()
            device_id, device_ref, src = pick_asset(f"iot-{label}-{n}")
            # Prefer OT for industrial-ish attacks
            if "MQTT" in label or "ARP" in label or "SYN" in label:
                src = "OT" if n % 3 else "IT"
                if src == "OT":
                    device_id, device_ref, _ = LAB_ASSETS[1 + (n % 3)]  # PLC/HMI/eng
            out_events.append({
                "TimeGenerated": ts_from_index(n, day_offset=2),
                "EventSource": src,
                "DeviceRef": device_ref,
                "DeviceId": device_id,
                "Severity": sev,
                "EventDetail": (
                    f"{label} feature-window rate={rate or 'n/a'} "
                    f"proto={proto or 'n/a'} source={path.name}"
                ),
            })
    print(f"  extracted {n} events")


# ---------------------------------------------------------------------------
# ToN_IoT Modbus → OT events
# ---------------------------------------------------------------------------
def transform_ton_modbus(path: Path, out_events: List[Dict[str, str]], max_per_type: int = 30) -> None:
    print(f"[ToN-Modbus] {path.name}")
    counts: Dict[str, int] = {}
    total = 0
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # headers: date,time,FC1...,label,type
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            atype = r.get("type") or "modbus"
            label = r.get("label") or "1"
            if counts.get(atype, 0) >= max_per_type:
                continue
            counts[atype] = counts.get(atype, 0) + 1
            total += 1
            date_s = r.get("date") or "25-Apr-19"
            time_s = r.get("time") or "00:00:00"
            try:
                dt = datetime.strptime(f"{date_s.strip()} {time_s.strip()}", "%d-%b-%y %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
                # shift into 2026 lab window for console freshness
                dt = dt.replace(year=2026, month=7, day=21 + (total % 5))
                ts = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                ts = ts_from_index(total, day_offset=3)
            # OT devices
            device_id, device_ref, _ = LAB_ASSETS[1 + (total % 3)]
            sev = severity_for(atype)
            if label in ("0", "benign"):
                sev = "Low"
            out_events.append({
                "TimeGenerated": ts,
                "EventSource": "OT",
                "DeviceRef": device_ref,
                "DeviceId": device_id,
                "Severity": sev,
                "EventDetail": (
                    f"Modbus {atype} activity FC1={r.get('fc1_read_input_register','')} "
                    f"FC3={r.get('fc3_read_holding_register','')} "
                    f"from ToN_IoT capture"
                ),
            })
    print(f"  extracted {total} events from types: {dict(counts)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="CAFI historical → LAW clean CSVs")
    ap.add_argument("--indir", default="/home/workdir/attachments", help="Source folder")
    ap.add_argument("--outdir", default="/home/workdir/artifacts/law-live-wiring/historical-scripts/out")
    ap.add_argument("--max-iscx-per-label", type=int, default=40)
    ap.add_argument("--max-iot-rows", type=int, default=50)
    ap.add_argument("--max-modbus-per-type", type=int, default=30)
    args = ap.parse_args()

    indir = Path(args.indir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("=== 1) Pass-through CAFI samples (report schema contract) ===")
    sample_map = {
        "events": "CAFI_Events_sample.csv",
        "explanations": "CAFI_Explanations_sample.csv",
        "fed": "CAFI_FedAudit_sample.csv",
        "assets": "CAFI_AssetInventory_sample.csv",
        "maint": "CAFI_MaintenanceWindows_sample.csv",
        "changes": "CAFI_ContextCatalogue_sample.csv",
        "aiusage": "CAFI_AIUsage_sample.csv",
        "aitools": "CAFI_ApprovedAITools_sample.csv",
        "aiendpoints": "CAFI_ControlledAIEndpoints_sample.csv",
    }
    sample_rows: Dict[str, List[Dict[str, str]]] = {}
    for kind, fname in sample_map.items():
        # pass_through writes file; also keep events/explanations to merge
        n = pass_through_sample(indir / fname, kind, outdir)
        if kind in ("events", "explanations") and n:
            _, rows = read_csv_rows(outdir / f"CAFI_{kind}_clean.csv")
            sample_rows[kind] = rows

    print("\n=== 2) Transform historical captures → events ===")
    hist_events: List[Dict[str, str]] = []

    # ISCX CSVs (any *ISCX*.csv)
    for p in sorted(indir.glob("*ISCX*.csv")):
        transform_iscx(p, hist_events, max_per_label=args.max_iscx_per_label)

    # ISCX XLSX (Wednesday, Tuesday, …)
    for p in sorted(indir.glob("*ISCX*.xlsx")):
        transform_iscx_xlsx(p, hist_events, max_per_label=args.max_iscx_per_label)

    # IoT feature sets
    for name in [
        "ARP_Spoofing_test.pcap.csv",
        "Benign_test.pcap.csv",
        "MQTT-DDoS-Connect_Flood_test.pcap.csv",
        "Recon-Port_Scan_test.pcap.csv",
        "TCP_IP-DDoS-SYN_test.pcap.csv",
    ]:
        p = indir / name
        if p.exists():
            transform_iot_features(p, hist_events, max_rows=args.max_iot_rows)

    # ToN Modbus
    ton = indir / "ToN_IoT_Train_Test_IoT_Modbus.csv"
    if ton.exists():
        transform_ton_modbus(ton, hist_events, max_per_type=args.max_modbus_per_type)

    print("\n=== 3) Merge sample events + historical events ===")
    merged_events = list(sample_rows.get("events", [])) + hist_events
    # de-dup by TimeGenerated+DeviceRef+EventDetail prefix
    seen = set()
    unique: List[Dict[str, str]] = []
    for e in merged_events:
        key = (e.get("TimeGenerated"), e.get("DeviceRef"), e.get("EventDetail", "")[:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    write_csv(outdir / "CAFI_events_clean.csv", "events", unique)

    print("\n=== 4) Summary ===")
    for p in sorted(outdir.glob("CAFI_*_clean.csv")):
        with p.open() as f:
            n = sum(1 for _ in f) - 1
        print(f"  {p.name}: {n} data rows")

    print("\nDone. Load CAFI_*_clean.csv into cafi-law (tables/watchlists) or")
    print("Manual Upload in the console. Schemas match report template fields.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
