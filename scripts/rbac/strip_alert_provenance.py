#!/usr/bin/env python3
"""
Strip provenance from Grafana alert rule groups.

Connects to Grafana through the platform proxy (nginx → user-mgmt-service),
fetches all alerts via the Ruler API, filters those with 'ruleType' in
annotations and data length 3 or 4, checks if any alert in the group has
provenance, and PUTs the group back via the provisioning API with
X-Disable-Provenance: true to strip it.

Auth is handled via X-Auth-Request-* headers that the platform proxy
normally sets.  When running locally or via port-forward, the script sets
these headers directly.
"""

import argparse
import sys
import urllib.parse
from dataclasses import dataclass, field

import requests

# Kloudfuse alerts have 3 data entries (query, reduce, threshold) or 4 (adds a
# no-data/error handler).  Other Grafana-native alerts use different structures,
# so the data-array length serves as a lightweight Kloudfuse-origin check.
KLOUDFUSE_ALERT_DATA_LENGTHS = (3, 4)


@dataclass
class APICall:
    method: str
    url: str
    status_code: int


@dataclass
class GroupChange:
    folder_name: str
    folder_uid: str
    group_name: str
    matching_alert_titles: list
    total_alerts_in_group: int
    provenance_values: list
    success: bool = False
    error: str = ""


@dataclass
class Summary:
    total_folders: int = 0
    total_groups: int = 0
    total_alerts: int = 0
    groups_with_matching_alerts: int = 0
    groups_with_provenance: int = 0
    groups_changed: int = 0
    groups_failed: int = 0
    alerts_affected: int = 0
    api_calls: list = field(default_factory=list)
    group_changes: list = field(default_factory=list)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Strip provenance from Grafana alert rule groups"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Platform URL (e.g. http://localhost:9000 or https://playground.kloudfuse.io)",
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Username for X-Auth-Request-User header",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email for X-Auth-Request-Email header (used for audit logging)",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Only process this folder name (optional, for targeted runs)",
    )
    parser.add_argument(
        "--group",
        default=None,
        help="Only process this group name (requires --folder)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making PUT calls",
    )
    parser.add_argument(
        "--include-non-kloudfuse",
        action="store_true",
        help=(
            "Also process alerts that don't look Kloudfuse-originated "
            "(no ruleType annotation, or non-3/4 data length). "
            "Requires --folder; not allowed globally."
        ),
    )
    args = parser.parse_args()
    if args.group and not args.folder:
        parser.error("--group requires --folder")
    if args.include_non_kloudfuse and not args.folder:
        parser.error(
            "--include-non-kloudfuse requires --folder "
            "(this flag is not allowed globally)"
        )
    return args


def check_grafana_reachable(session, base_url):
    """Verify Grafana is running and reachable via the platform. Exit with error if not."""
    url = f"{base_url}/grafana/api/health"
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"ERROR: Grafana health check returned status {resp.status_code} at {url}")
            sys.exit(1)
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to {url}. Is the platform running?")
        sys.exit(1)
    except requests.Timeout:
        print(f"ERROR: Grafana health check timed out at {url}")
        sys.exit(1)


def make_request(session, method, url, summary, **kwargs):
    """Make an HTTP request and track it in the summary."""
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30
    resp = session.request(method, url, **kwargs)
    summary.api_calls.append(APICall(method=method, url=url, status_code=resp.status_code))
    return resp


def fetch_all_rules(session, base_url, summary):
    """Fetch all alert rules via the Ruler API."""
    url = f"{base_url}/grafana/api/ruler/grafana/api/v1/rules?subtype=cortex"
    headers = {"X-Kloudfuse-Enrich-Alert": "false"}
    resp = make_request(session, "GET", url, summary, headers=headers)
    if resp.status_code != 200:
        print(f"ERROR: Failed to fetch rules: {resp.status_code} {resp.text}")
        sys.exit(1)
    return resp.json()


def rule_matches_filter(rule, include_non_kloudfuse=False):
    """Check if a rule has 'ruleType' in annotations and data length 3 or 4."""
    if include_non_kloudfuse:
        return True
    annotations = rule.get("annotations", {}) or {}
    grafana_alert = rule.get("grafana_alert", {}) or {}
    data = grafana_alert.get("data", []) or []
    return "ruleType" in annotations and len(data) in KLOUDFUSE_ALERT_DATA_LENGTHS


def group_has_provenance(rules):
    """Check if any rule in the group has provenance set."""
    for rule in rules:
        grafana_alert = rule.get("grafana_alert", {}) or {}
        provenance = grafana_alert.get("provenance", "")
        if provenance:
            return True
    return False


def get_provenance_values(rules):
    """Collect all unique provenance values from rules in a group."""
    values = set()
    for rule in rules:
        grafana_alert = rule.get("grafana_alert", {}) or {}
        provenance = grafana_alert.get("provenance", "")
        if provenance:
            values.add(provenance)
    return sorted(values)


def get_folder_uid_from_group(rules):
    """Extract folder UID from the first rule's grafana_alert.namespace_uid."""
    for rule in rules:
        grafana_alert = rule.get("grafana_alert", {}) or {}
        uid = grafana_alert.get("namespace_uid", "")
        if uid:
            return uid
    return ""


def fetch_provisioning_rule_group(session, base_url, folder_uid, group_name, summary):
    """Fetch a rule group via the provisioning API."""
    encoded_group = urllib.parse.quote(group_name, safe="")
    url = f"{base_url}/grafana/api/v1/provisioning/folder/{folder_uid}/rule-groups/{encoded_group}"
    resp = make_request(session, "GET", url, summary)
    if resp.status_code != 200:
        return None, f"GET failed: {resp.status_code} {resp.text}"
    return resp.json(), None


def put_provisioning_rule_group(session, base_url, folder_uid, group_name, body, summary):
    """PUT a rule group via the provisioning API with X-Disable-Provenance."""
    encoded_group = urllib.parse.quote(group_name, safe="")
    url = f"{base_url}/grafana/api/v1/provisioning/folder/{folder_uid}/rule-groups/{encoded_group}"
    headers = {
        "Content-Type": "application/json",
        "X-Disable-Provenance": "true",
        "X-Kloudfuse-Passthrough-Rule-Group": "true",
    }
    resp = make_request(session, "PUT", url, summary, headers=headers, json=body)
    if resp.status_code >= 300:
        return False, f"PUT failed: {resp.status_code} {resp.text}"
    return True, None


def print_summary(summary, dry_run):
    """Print the final summary report."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"\nMode: {mode}")
    print(f"\nScan Results (after applying filters):")
    print(f"  Folders processed:                        {summary.total_folders}")
    print(f"  Groups processed:                         {summary.total_groups}")
    print(f"  Alerts processed:                         {summary.total_alerts}")
    print(f"  Groups with matching Kloudfuse alerts:     {summary.groups_with_matching_alerts}")
    print(f"  Groups with provenance:                   {summary.groups_with_provenance}")

    if dry_run:
        print(f"\n  Groups that WOULD be changed:             {summary.groups_with_provenance}")
        print(f"  Alerts that WOULD be affected:            {summary.alerts_affected}")
    else:
        print(f"\n  Groups changed successfully:              {summary.groups_changed}")
        print(f"  Groups failed:                            {summary.groups_failed}")
        print(f"  Total alerts affected:                    {summary.alerts_affected}")

    if summary.group_changes:
        print(f"\n{'─' * 70}")
        print("GROUP DETAILS")
        print(f"{'─' * 70}")

        # Group by folder to avoid repeating folder info
        folders = {}
        for gc in summary.group_changes:
            key = (gc.folder_name, gc.folder_uid)
            folders.setdefault(key, []).append(gc)

        for (folder_name, folder_uid), groups in folders.items():
            print(f"\n  Folder: {folder_name} (UID: {folder_uid})")
            print(f"  Groups: {len(groups)}")
            for gc in groups:
                status = ""
                if not dry_run:
                    status = " [OK]" if gc.success else f" [FAILED: {gc.error}]"
                print(f"    - {gc.group_name} ({gc.total_alerts_in_group} alerts, provenance: {', '.join(gc.provenance_values)}){status}")
                for title in gc.matching_alert_titles:
                    print(f"        {title}")

    print(f"\n{'─' * 70}")
    print("API CALLS")
    print(f"{'─' * 70}")
    for call in summary.api_calls:
        print(f"  {call.method:6s} {call.status_code} {call.url}")
    print(f"\n  Total API calls: {len(summary.api_calls)}")
    print("=" * 70)


def main():
    args = parse_args()
    summary = Summary()

    base_url = args.url.rstrip("/")

    session = requests.Session()
    session.headers["X-Auth-Request-User"] = args.username
    session.headers["X-Auth-Request-Email"] = args.email
    session.headers["X-Auth-Request-Role"] = "Admin"
    session.headers["X-Auth-Request-Auth-Type"] = "basic"

    print(f"Platform URL: {base_url}")
    print(f"Auth user:    {args.username}")
    print(f"Auth email:   {args.email}")
    if args.folder:
        print(f"Filter folder: {args.folder}")
    if args.group:
        print(f"Filter group:  {args.group}")
    if args.include_non_kloudfuse:
        print("Filter:        INCLUDING non-Kloudfuse alerts")
    if args.dry_run:
        print("Mode:         DRY RUN (no changes will be made)")
    print()

    # Step 0: Verify Grafana is reachable
    check_grafana_reachable(session, base_url)

    # Step 1: Fetch all rules via Ruler API
    print("Fetching all alert rules via Ruler API...")
    all_rules = fetch_all_rules(session, base_url, summary)

    print(f"Found {len(all_rules)} folder(s)\n")

    # Step 2: Iterate and filter
    processed_folders = set()
    for folder_name, rule_groups in all_rules.items():
        if args.folder and folder_name != args.folder:
            continue
        processed_folders.add(folder_name)
        for group in rule_groups:
            group_name = group.get("name", "")
            if args.group and group_name != args.group:
                continue
            summary.total_groups += 1
            rules = group.get("rules", [])
            summary.total_alerts += len(rules)

            # Find matching alerts in this group
            matching_titles = []
            for rule in rules:
                if rule_matches_filter(rule, args.include_non_kloudfuse):
                    ga = rule.get("grafana_alert", {}) or {}
                    matching_titles.append(ga.get("title", "(untitled)"))

            if not matching_titles:
                continue

            summary.groups_with_matching_alerts += 1

            # Check provenance
            if not group_has_provenance(rules):
                continue

            summary.groups_with_provenance += 1
            folder_uid = get_folder_uid_from_group(rules)
            provenance_values = get_provenance_values(rules)

            if not folder_uid:
                gc = GroupChange(
                    folder_name=folder_name,
                    folder_uid="",
                    group_name=group_name,
                    matching_alert_titles=matching_titles,
                    total_alerts_in_group=len(rules),
                    provenance_values=provenance_values,
                    error="Could not determine folder UID from rules",
                )
                print(f"  SKIP: folder={folder_name}, group={group_name} — missing folder UID")
                summary.groups_failed += 1
                summary.group_changes.append(gc)
                continue

            gc = GroupChange(
                folder_name=folder_name,
                folder_uid=folder_uid,
                group_name=group_name,
                matching_alert_titles=matching_titles,
                total_alerts_in_group=len(rules),
                provenance_values=provenance_values,
            )

            summary.alerts_affected += len(rules)

            if args.dry_run:
                print(f"[DRY RUN] Would strip provenance: folder={folder_name}, group={group_name} ({len(rules)} alerts)")
                gc.success = True
                summary.group_changes.append(gc)
                continue

            # Step 3: Fetch the group via provisioning API
            print(f"Processing: folder={folder_name}, group={group_name}...")
            prov_group, err = fetch_provisioning_rule_group(
                session, base_url, folder_uid, group_name, summary
            )
            if err:
                print(f"  ERROR fetching group: {err}")
                gc.error = err
                summary.groups_failed += 1
                summary.group_changes.append(gc)
                continue

            # Step 4: PUT back with X-Disable-Provenance: true
            ok, err = put_provisioning_rule_group(
                session, base_url, folder_uid, group_name, prov_group, summary
            )
            if not ok:
                print(f"  ERROR updating group: {err}")
                gc.error = err
                summary.groups_failed += 1
                summary.group_changes.append(gc)
                continue

            print(f"  OK - provenance stripped ({len(rules)} alerts)")
            gc.success = True
            summary.groups_changed += 1
            summary.group_changes.append(gc)

    summary.total_folders = len(processed_folders)
    print_summary(summary, args.dry_run)


if __name__ == "__main__":
    main()
