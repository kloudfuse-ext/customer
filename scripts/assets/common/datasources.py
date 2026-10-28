"""Datasource UID remapping shared by alert.py and dashboard.py.

Exported JSON refers to datasources by UID, and UIDs differ between Grafana
instances. Before upload we rewrite references so they point at datasources
that exist on the target.
"""
from typing import Dict, Iterable, Optional, Set

from loguru import logger as log

DEFAULT_DATASOURCE = "kfusedatasource"

# UIDs that are built into Grafana and never need remapping.
_BUILTIN_UIDS = {"__expr__", "__dashboard__", "grafana", "-- Grafana --", "-- Mixed --", "-- Dashboard --"}


def parse_overrides(pairs: Optional[Iterable[str]]) -> Dict[str, str]:
    """Turn ["old=new", ...] from --datasource-uid-map into {old: new}."""
    overrides = {}
    for pair in pairs or []:
        old, sep, new = pair.partition("=")
        if not sep or not old or not new:
            raise ValueError(f"Invalid --datasource-uid-map value '{pair}', expected OLD_UID=NEW_UID")
        overrides[old] = new
    return overrides


class DatasourceRemapper:
    def __init__(self, ds_uid_map: Dict[str, str], overrides: Optional[Dict[str, str]] = None):
        """ds_uid_map: lowercase datasource name -> uid on the target Grafana."""
        self.ds_uid_map = ds_uid_map or {}
        self.known_uids: Set[str] = set(self.ds_uid_map.values())
        self.overrides = overrides or {}
        self.unknown: Set[str] = set()

    def _resolve(self, uid: str) -> Optional[str]:
        """Return the replacement UID for `uid`, or None to leave it as is."""
        if uid in self.overrides:
            return self.overrides[uid]
        if uid.startswith("${DS_") and uid.endswith("}"):
            mapped = self.ds_uid_map.get(uid[5:-1].lower())
            if mapped is None:
                self.unknown.add(uid)
            return mapped
        if uid == "":
            return self.ds_uid_map.get(DEFAULT_DATASOURCE)
        if self.known_uids and uid not in self.known_uids \
                and uid not in _BUILTIN_UIDS and not uid.startswith("$"):
            self.unknown.add(uid)
        return None

    def process(self, obj):
        """Recursively rewrite datasource references in a dashboard or alert rule."""
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if key == "datasource":
                    if isinstance(value, dict) and isinstance(value.get("uid"), str):
                        new = self._resolve(value["uid"])
                        if new:
                            value["uid"] = new
                    elif isinstance(value, str) and value.startswith("${DS_"):
                        # Legacy string reference: promote to an object reference.
                        new = self._resolve(value)
                        if new:
                            obj[key] = {"uid": new}
                elif key == "datasourceUid" and isinstance(value, str):
                    # Alert rule query; "" is never valid here, unlike in dashboards.
                    new = self._resolve(value) if value else self.ds_uid_map.get(DEFAULT_DATASOURCE)
                    if new:
                        obj[key] = new
                self.process(obj[key] if key in obj else value)
        elif isinstance(obj, list):
            for item in obj:
                self.process(item)
        return obj

    def warn_unknown(self, what: str):
        if self.unknown:
            log.warning(
                "[!] {} references datasource UID(s) not found on the target: {}. "
                "Use --datasource-uid-map OLD=NEW to remap them.",
                what, ", ".join(sorted(self.unknown)))
            self.unknown.clear()
