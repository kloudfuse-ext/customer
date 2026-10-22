#!/usr/bin/python

import argparse
import json
import os
import sys
import tarfile
import zipfile
from typing import Optional, Union, Tuple

from loguru import logger as log

from common.archive import extracted, is_archive, output_target, safe_name
from common.datasources import DatasourceRemapper, parse_overrides
from common.grafana_client import GrafanaClient

def parse_args():
    """Grafana Dashboard Management Tool

    Common Arguments:
        -f, --dashboard-folder-name  dashboard folder name in Grafana
        -a, --grafana-address    Grafana server address
        -u, --grafana-username   Grafana username (default: admin)
        -p, --grafana-password   Grafana password (default: password)

    Examples:
        # Upload dashboards Operations
        # ----------------
        # Upload single dashboard file to a folder named "My dashboard Folder":
        python dashboard.py upload -s /path/to/dashboard.json \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload all dashboards from directory to a folder named "My dashboard Folder":
        python dashboard.py upload -d /path/to/dashboards/directory \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload dashboards from all folders (only one level down) within a root directory:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the upload.
        python dashboard.py upload -m /path/to/dashboards_root_directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "all"

        # Download dashboards Operations
        # ----------------
        # Download single dashboard named "dashboard Name" from a folder named "My dashboard Folder" in Grafana/dashboards tab:
        python dashboard.py download -s "dashboard Name" \
            -o /path/to/dashboard.json \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download all dashboards from a folder named "My dashboard Folder" in Grafana/dashboards tab to dashboards_file_name.json:
        python dashboard.py download -d -o /path/to/dashboards/download/directory \
            -f "My dashboard Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download dashboards from all Grafana folders:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the download.
        python dashboard.py download -m -o /path/to/dashboards/download/directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "all"


        # Compressed bundles (.zip, .tar.gz, .tgz) work for -d/-m uploads and any download:
        python dashboard.py download -m -o /path/to/dashboards.zip -f all -a ... -u admin -p password
        python dashboard.py upload -m /path/to/dashboards.zip -f all -a ... -u admin -p password

    """


    parser = argparse.ArgumentParser(description="Grafana Dashboard Management Script")

    # Create parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parent_parser.add_argument(
        "-f",
        "--dashboard-folder-name",
        required=True,
        help="dashboard folder name in Grafana"
    )
    parent_parser.add_argument(
        "-a",
        "--grafana-address",
        required=True,
        help="Grafana server address (e.g., http://grafana.example.com)"
    )
    parent_parser.add_argument(
        "-u",
        "--grafana-username",
        default="admin",
        help="Grafana username"
    )
    parent_parser.add_argument(
        "-p",
        "--grafana-password",
        default="password",
        help="Grafana password"
    )
    parent_parser.add_argument(
        "--auth-token",
        help="Grafana service account token (alternative to username/password)"
    )
    parent_parser.add_argument(
        "-v",
        "--verify-ssl",
        action='store_false',
        help="Verify SSL certificate (default: True)"
    )

    parent_parser.add_argument(
        "--datasource-uid-map",
        action="append",
        metavar="OLD_UID=NEW_UID",
        help="Rewrite datasource UID OLD_UID to NEW_UID on upload (repeatable)"
    )

    # Main parser
    parser = argparse.ArgumentParser(
        description="Grafana Dashboard Management Tool"
    )

    # Create command subparsers
    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
        help='Command to execute (upload/download/delete)'
    )

    # Upload command
    upload_parser = subparsers.add_parser(
        'upload',
        help='Upload dashboards to Grafana',
        parents=[parent_parser]
    )
    upload_mode = upload_parser.add_mutually_exclusive_group(
        required=True
    )
    upload_mode.add_argument(
        '-s',
        '--single-file',
        help='Path to single dashboard JSON file'
    )
    upload_mode.add_argument(
        '-d',
        '--directory',
        help='Directory or .zip/.tar.gz/.tgz archive of dashboards to upload into the -f folder'
    )
    upload_mode.add_argument(
        '-m',
        '--multi-directory',
        help='Directory or .zip/.tar.gz/.tgz archive holding a folder tree; each directory path becomes a (nested) Grafana folder'
    )

    # Download command (similar structure)
    download_parser = subparsers.add_parser(
        'download',
        help='Download dashboards from Grafana',
        parents=[parent_parser]
    )
    # Add required output file argument
    download_parser.add_argument(
        '-o',
        '--output',
        required=True,
        help='Output file, or directory for -d/-m. A .zip/.tar.gz/.tgz path writes a compressed archive'
    )
    download_mode = download_parser.add_mutually_exclusive_group(
        required=True
    )
    download_mode.add_argument(
        '-s',
        '--dashboard-name',
        metavar='DASHBOARD_NAME',
        help='Download single dashboard to file'
    )
    download_mode.add_argument(
        '-d',
        '--directory',
        action='store_true',
        help='Download all dashboard from a grafana folder (directory)'
    )
    download_mode.add_argument(
        '-m',
        '--multi-directory',
        action='store_true',
        help='Download dashboards from all Grafana folders, preserving the nested folder tree'
    )

    # Delete command (similar structure)
    # delete_parser = subparsers.add_parser(
    #     'delete',
    #     help='Delete alerts from Grafana',
    #     parents=[parent_parser]
    # )
    # delete_mode = delete_parser.add_mutually_exclusive_group(
    #     required=True
    # )
    # delete_mode.add_argument(
    #     '-s',
    #     '--dashboard-name',
    #     metavar='ALERT_NAME',
    #     help='Name of single alert to delete'
    # )
    # delete_mode.add_argument(
    #     '-d',
    #     '--directory',
    #     action='store_true',
    #     help='Delete all alerts in folder'
    # )


    return parser.parse_args()

class DashboardManager(object):
    from common.grafana_client import GrafanaClient

    def __init__(
            self,
            grafana_client: Optional[GrafanaClient] = None,
            dashboard_folder_name: Optional[str] = None,
    ):
        self.gc = grafana_client
        self.dashboard_folder_name = dashboard_folder_name

    def _valid_single_file_arg(self, file_path: str) -> Tuple[Union[dict, None], Union[int, None]]:
        """Validate and load Dashboard configuration from a JSON file.

        Args:
            file_path (str): Path to the JSON file containing dashboard configuration

        Returns:
            tuple: A tuple containing:
                - dict | None: Dashboard configuration if successful, None if failed
                - int | None: Error code (1) if failed, None if successful

        Example:
            >>> content, err = valid_single_file_arg("path/to/dashboard.json")
            >>> if err:
            >>>     print(f"Failed to load dashboard config: {err}")
        """
        if not os.path.isfile(file_path):
            log.error("File not found: {}", file_path)
            return None, 1
        try:
            with open(file_path, "r") as f:
                dashboard_content = json.load(f)
                log.debug(
                    "Successfully loaded dashboard configuration from {}",
                    file_path)
                if dashboard_content.get("dashboard") is None:
                    return dashboard_content, None
                else:
                    return dashboard_content["dashboard"], None
        except json.JSONDecodeError as e:
            log.error("Invalid JSON in file {}: {}", file_path, str(e))
            return None, 1
        except IOError as e:
            log.error("Error reading file {}: {}", file_path, str(e))
            return None, 1

LIBRARY_PANELS_DIR = "_library_panels"


def find_library_panel_uids(obj, found=None):
    """Collect the UIDs of library panels referenced anywhere in a dashboard."""
    found = set() if found is None else found
    if isinstance(obj, dict):
        lib = obj.get("libraryPanel")
        if isinstance(lib, dict) and lib.get("uid"):
            found.add(lib["uid"])
        for value in obj.values():
            find_library_panel_uids(value, found)
    elif isinstance(obj, list):
        for item in obj:
            find_library_panel_uids(item, found)
    return found


class UploadDashboard(DashboardManager):
    def __init__(self, grafana_client: GrafanaClient, dashboard_folder_name: str, datasource_overrides=None):
        super().__init__(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )
        self._overrides = datasource_overrides or {}
        self._remapper = None
        self._library_panels = {}   # uid -> exported panel loaded from the bundle
        self._library_done = set()  # uids already ensured on the target
        self._failures = 0

    def _replace_datasource_uids(self, dashboard_json, ds_uid_map):
        """Rewrite datasource references (${DS_*} placeholders, empty UIDs, --datasource-uid-map overrides)."""
        if self._remapper is None:
            self._remapper = DatasourceRemapper(ds_uid_map, self._overrides)
        self._remapper.process(dashboard_json)
        self._remapper.warn_unknown("Dashboard '{}'".format(dashboard_json.get("title")))
        return dashboard_json

    def process_args(self, single_file, directory, multi_directory):
        ds_uid_map = self.gc._get_datasource_uid_map()
        log.info("ds_uid_map={}", ds_uid_map)
        if not ds_uid_map:
            log.warning("[!] Could not list datasources on the target; datasource UIDs will not be remapped")
        try:
            if single_file:
                if is_archive(single_file):
                    log.error("[X] -s takes a single JSON file; use -d or -m for archives.")
                    exit(1)
                self._create_dashboard_from_one_file(single_file, ds_uid_map)
            elif directory:
                with extracted(directory) as path:
                    self._load_library_panels(path)
                    self._create_dashboards_from_dir(path, ds_uid_map)
            elif multi_directory:
                with extracted(multi_directory) as path:
                    self._load_library_panels(path)
                    self._create_dashboards_from_root_dir(path, ds_uid_map)
            else:
                log.error("Invalid arguments provided.")
                exit(1)
        except (ValueError, OSError, zipfile.BadZipFile, tarfile.TarError) as e:
            log.error("[X] Cannot read archive: {}", e)
            exit(1)
        if self._failures:
            log.error("[X] {} dashboard(s) failed to upload; see errors above.", self._failures)
            exit(1)

    def _load_library_panels(self, root):
        lib_dir = os.path.join(root, LIBRARY_PANELS_DIR)
        if not os.path.isdir(lib_dir):
            return
        for name in sorted(os.listdir(lib_dir)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(lib_dir, name)) as f:
                panel = json.load(f)
            if panel.get("uid"):
                self._library_panels[panel["uid"]] = panel
        log.info("[*] Found {} library panel(s) in bundle", len(self._library_panels))

    def _ensure_library_panels(self, dashboard):
        """Create library panels the dashboard needs, or warn if they are missing on the target."""
        for uid in find_library_panel_uids(dashboard) - self._library_done:
            self._library_done.add(uid)
            if uid in self._library_panels:
                if self.gc.upsert_library_panel(self._library_panels[uid], None):
                    log.info("[+] Library panel '{}' available", self._library_panels[uid].get("name", uid))
                else:
                    log.error("[X] Failed to create library panel {}", uid)
            elif not self.gc.library_panel_exists(uid):
                log.warning("[!] Dashboard '{}' uses library panel {} which does not exist on the target "
                            "and is not in the bundle", dashboard.get("title"), uid)

    def _upload(self, content, ds_uid_map, folder_name):
        content = self._replace_datasource_uids(content, ds_uid_map)
        self._ensure_library_panels(content)
        if not self.gc.upload_dashboard(content, folder_name):
            self._failures += 1

    def _create_dashboard_from_one_file(self, single_file, ds_uid_map):
        content, err = self._valid_single_file_arg(single_file)
        if err:
            exit(err)
        self._upload(content, ds_uid_map, self.dashboard_folder_name)

    def _create_dashboards_from_dir(self, directory, ds_uid_map, folder_name=None):
        for file in sorted(os.listdir(directory)):
            if file.endswith(".json") and os.path.isfile(os.path.join(directory, file)):
                content, err = self._valid_single_file_arg(os.path.join(directory, file))
                if err:
                    exit(err)
                self._upload(content, ds_uid_map, folder_name or self.dashboard_folder_name)

    def _create_dashboards_from_root_dir(self, root_directory, ds_uid_map):
        """Upload a folder tree; each directory's relative path becomes a (nested) Grafana folder."""
        if not os.path.isdir(root_directory):
            log.error("[X] Root directory not found: {}", root_directory)
            self._failures += 1
            return
        found = False
        for current, dirs, files in os.walk(root_directory):
            dirs[:] = sorted(d for d in dirs if d != LIBRARY_PANELS_DIR)
            if not any(f.endswith(".json") for f in files):
                continue
            rel = os.path.relpath(current, root_directory)
            if rel == ".":
                log.warning("[!] Ignoring JSON file(s) at the top level; put them in a folder directory")
                continue
            found = True
            self._create_dashboards_from_dir(current, ds_uid_map, "/".join(rel.split(os.sep)))
        if not found:
            log.warning("[!] No dashboard JSON files found under {}", root_directory)


class DownloadDashboard(DashboardManager):
    def __init__(self, grafana_client: GrafanaClient, dashboard_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )

    def process_args(self, dashboard_name, directory, output, multi_directory):
        log.debug("dashboard_name={}, directory={}, multi_directory={}", dashboard_name, directory, multi_directory)
        try:
            if dashboard_name:
                with output_target(output, safe_name(dashboard_name) + ".json") as target:
                    self._download_single_dashboard_from_folder(dashboard_name, target)
            elif directory:
                with output_target(output) as target:
                    self._download_all_dashboards_from_folder(self.dashboard_folder_name, target)
            elif multi_directory:
                with output_target(output) as target:
                    self._download_all_dashboards_from_grafana(target)
            else:
                log.error("Invalid arguments provided.")
                exit(1)
        except OSError as e:
            log.error("[X] Cannot write output {}: {}", output, e)
            exit(1)

    def _download_single_dashboard_from_folder(self, dashboard_name, output):
        log.debug("Downloading dashboard: {}", dashboard_name)
        dashboard_payload, found = self.gc.download_dashboard(
            dashboard_name,
            folder_name=self.dashboard_folder_name,
        )
        if not found:
            log.error("Dashboard not found: {}", dashboard_name)
            exit(1)
        parent = os.path.dirname(output)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._save_dashboard_to_file(dashboard_payload, output)
        if find_library_panel_uids(dashboard_payload):
            log.warning("[!] Dashboard uses library panels, which are only exported with -d/-m downloads")

    def _save_library_panels(self, root, dashboard_payloads):
        uids = set()
        for payload in dashboard_payloads:
            find_library_panel_uids(payload, uids)
        for uid in sorted(uids):
            panel = self.gc.get_library_panel(uid)
            if panel is None:
                log.warning("[!] Could not export library panel {}", uid)
                continue
            lib_dir = os.path.join(root, LIBRARY_PANELS_DIR)
            os.makedirs(lib_dir, exist_ok=True)
            self._save_dashboard_to_file(panel, os.path.join(lib_dir, f"{safe_name(uid)}.json"))
            log.info("[+] Exported library panel: {}", panel.get("name", uid))

    def _download_to_dir(self, dashboard_uids, directory):
        """Save dashboards into directory (named by title); returns the payloads saved."""
        os.makedirs(directory, exist_ok=True)
        saved = []
        used_names = set()
        for dashboard_uid in dashboard_uids:
            dashboard_payload, found = self.gc.download_dashboard(dashboard_uid, is_uid=True)
            if not found:
                log.warning("[!] Skipping missing dashboard: {}", dashboard_uid)
                continue
            title = safe_name(dashboard_payload['dashboard']['title'])
            if title in used_names:
                title = f"{title}_{safe_name(dashboard_uid)}"
            used_names.add(title)
            self._save_dashboard_to_file(dashboard_payload, os.path.join(directory, f"{title}.json"))
            log.info("[+] Downloaded dashboard: {} -> {}", title, directory)
            saved.append(dashboard_payload)
        return saved

    def _download_all_dashboards_from_folder(self, folder_name, directory):
        log.debug("Downloading all dashboards from folder: {}", folder_name)

        # Find all folders that match the name, path, or UID (there might be multiple with same path but different UIDs)
        matching_folders = []
        all_folders = self.gc.get_all_folders_recursive()

        for folder in all_folders:
            # Match by title, path, or UID
            if (folder['title'] == folder_name or
                folder['path'] == folder_name or
                folder['uid'] == folder_name):
                matching_folders.append(folder)
                log.info("[>] Found folder: {} (UID: {})", folder['path'], folder['uid'])

        if not matching_folders:
            log.error("[X] Folder not found: {}", folder_name)
            exit(1)

        if len(matching_folders) > 1:
            log.info("[>>] Found {} folders with path '{}'", len(matching_folders), folder_name)

        all_dashboard_uids = []  # ordered, de-duplicated

        for folder in matching_folders:
            folder_uid = folder['uid']
            folder_path = folder['path']

            # Get all dashboards recursively (including from subfolders)
            dashboards_uids = self.gc.get_dashboards_in_folder_recursive(folder_uid)

            if dashboards_uids:
                log.info("[*] Found {} dashboard(s) in '{}' (UID: {})",
                        len(dashboards_uids), folder_path, folder_uid)
                all_dashboard_uids.extend(u for u in dashboards_uids if u not in all_dashboard_uids)
            else:
                log.debug("No dashboards in '{}' (UID: {})", folder_path, folder_uid)

        if not all_dashboard_uids:
            log.warning("[!] No dashboards found in any of the matching folders")
            return

        log.info("[=] Total unique dashboards to download: {}", len(all_dashboard_uids))
        saved = self._download_to_dir(all_dashboard_uids, directory)
        self._save_library_panels(directory, saved)

    def _download_all_dashboards_from_grafana(self, output_dir):
        """Download every dashboard into output_dir, mirroring the nested folder tree."""
        log.debug("Downloading all dashboards from Grafana")
        if os.path.isfile(output_dir):
            log.error("[X] Output path exists and is a file, expected a directory: {}", output_dir)
            exit(1)
        os.makedirs(output_dir, exist_ok=True)
        all_folders = self.gc.get_all_folders_recursive()

        processed_uids = set()  # Track processed folder UIDs to avoid duplicates
        saved = []

        for folder in all_folders:
            folder_uid = folder['uid']
            folder_path = folder['path']

            if folder_uid in processed_uids:
                continue
            processed_uids.add(folder_uid)

            folder_output_dir = os.path.join(output_dir, *folder_path.split("/"))

            # Dashboards of this folder only; subfolders are visited as their own entries
            response, status = self.gc._http_get_request_to_grafana(
                path=f"/api/search?folderUIDs={folder_uid}&type=dash-db&limit=5000")

            if status and response:
                dashboards_in_folder = [dash["uid"] for dash in response if dash.get("type") == "dash-db"]
                if dashboards_in_folder:
                    log.info("[*] Downloading {} dashboard(s) from folder: {}", len(dashboards_in_folder), folder_path)
                    saved.extend(self._download_to_dir(dashboards_in_folder, folder_output_dir))
        self._save_library_panels(output_dir, saved)

    def _save_dashboard_to_file(self, dashboard_payload, output_path):
        with open(output_path, 'w') as f:
            json.dump(dashboard_payload, f, indent=2)
        log.debug("Saved dashboard to file: {}", output_path)


if __name__ == "__main__":
    # Configure logger to show only time and message (no module/function names)
    log.remove()
    log.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}", level="INFO")

    log.info("Executing: {}", ' '.join(sys.argv))
    args = parse_args()

    if args.debug:
        log.remove()
        log.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}", level="DEBUG")

    grafana_client = GrafanaClient(
        grafana_server=args.grafana_address,
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        auth_token=args.auth_token,
        verify_ssl=args.verify_ssl
    )

    dashboard_folder_name = args.dashboard_folder_name
    try:
        datasource_overrides = parse_overrides(getattr(args, "datasource_uid_map", None))
    except ValueError as e:
        log.error("[X] {}", e)
        exit(1)

    if args.command == "upload":
        i = UploadDashboard(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name,
            datasource_overrides=datasource_overrides,
        )
        i.process_args(
            single_file=args.single_file,
            directory=args.directory,
            multi_directory=args.multi_directory,
        )
    elif args.command == "download":
        e = DownloadDashboard(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )
        e.process_args(
            dashboard_name=args.dashboard_name,
            directory=args.directory,
            output=args.output,
            multi_directory=args.multi_directory,
        )
    else:
        log.error("Invalid command provided.")
        exit(1)
