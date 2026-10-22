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
    """Grafana Alert Management Tool

    Common Arguments:
        -f, --alert-folder-name  Alert folder name in Grafana
        -a, --grafana-address    Grafana server address
        -u, --grafana-username   Grafana username (default: admin)
        -p, --grafana-password   Grafana password (default: password)

    Examples:
        # Upload Alerts Operations
        # ----------------
        # Upload single alert file to a folder named "My Alert Folder":
        python alert.py upload -s /path/to/alert.json \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload all alerts from directory to a folder named "My Alert Folder":
        python alert.py upload -d /path/to/alerts/directory \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Upload alerts from all folders (only one level down) within a root directory:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the upload.
        python alert.py upload -m /path/to/root_directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "placeholder"

        # Download Alerts Operations
        # ----------------
        # Download single alert named "Alert Name" from a folder named "My Alert Folder" in Grafana/Alerts tab:
        python alert.py download -s "Alert Name" \
            -o /path/to/alert.json \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download all alerts from a folder named "My Alert Folder" in Grafana/Alerts tab to alerts_file_name.json:
        python alert.py download -d -o /path/to/alerts/download/directory/ \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Download alerts from all Grafana folders:
        # NOTE: Only for this specific command, the -f flag value is required BUT it does not have any use. It is just a placeholder and will not affect the download.
        python alert.py download -m -o /path/to/alerts/download/directory \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password \
            -f "placeholder"

        # Compressed bundles (.zip, .tar.gz, .tgz) work for -d/-m uploads and any download:
        python alert.py download -m -o /path/to/alerts.zip -f placeholder -a ... -u admin -p password
        python alert.py upload -m /path/to/alerts.zip -f placeholder -a ... -u admin -p password

        # Delete Operations
        # ----------------
        # Delete single alert named "Alert Name" from a folder named "My Alert Folder" in Grafana/Alerts tab:
        python alert.py delete -s "Alert Name" \
            -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password

        # Delete all alerts in folder named "My Alert Folder" in Grafana/Alerts tab:
        python alert.py delete -d -f "My Alert Folder" \
            -a http://<your-kloudfuse-instance>.kloudfuse.io/grafana \
            -u admin \
            -p password
    """
    # Create parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parent_parser.add_argument(
        "-f",
        "--alert-folder-name",
        required=True,
        help="Alert folder name in Grafana"
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
        description="Grafana Alert Management Tool"
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
        help='Upload alerts to Grafana',
        parents=[parent_parser]
    )
    upload_mode = upload_parser.add_mutually_exclusive_group(
        required=True
    )
    upload_mode.add_argument(
        '-s',
        '--single-file',
        help='Upload alert(s) from a single JSON file'
    )
    upload_mode.add_argument(
        '-d',
        '--directory',
        help='Upload all JSON files from a directory or .zip/.tar.gz/.tgz archive into the -f folder'
    )
    upload_mode.add_argument(
        '-m',
        '--multi-directory',
        help='Directory or .zip/.tar.gz/.tgz archive holding a folder tree; each directory path becomes a (nested) Grafana folder'
    )

    # Download command (similar structure)
    download_parser = subparsers.add_parser(
        'download',
        help='Download alerts from Grafana',
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
        '--alert-name',
        metavar='ALERT_NAME',
        help='Download single alert to file'
    )
    download_mode.add_argument(
        '-d',
        '--directory',
        action='store_true',
        help='Download all alerts of the -f folder (nested path like parent/child allowed)'
    )
    download_mode.add_argument(
        '-m',
        '--multi-directory',
        action='store_true',
        help='Download alerts from all Grafana folders, preserving the nested folder tree'
    )

    # Delete command (similar structure)
    delete_parser = subparsers.add_parser(
        'delete',
        help='Delete alerts from Grafana',
        parents=[parent_parser]
    )
    delete_mode = delete_parser.add_mutually_exclusive_group(
        required=True
    )
    delete_mode.add_argument(
        '-s',
        '--alert-name',
        metavar='ALERT_NAME',
        help='Name of single alert to delete'
    )
    delete_mode.add_argument(
        '-d',
        '--directory',
        action='store_true',
        help='Delete all alerts in folder'
    )

    return parser.parse_args()


class AlertManager(object):
    from common.grafana_client import GrafanaClient

    def __init__(
            self,
            grafana_client: Optional[GrafanaClient] = None,
            alert_folder_name: Optional[str] = None,
    ):
        self.gc = grafana_client
        self.alert_folder_name = alert_folder_name

    def _valid_single_file_arg(self, file_path: str) -> Tuple[Union[dict, None], Union[int, None]]:
        """Validate and load alert configuration from a JSON file.

        Args:
            file_path (str): Path to the JSON file containing alert configuration

        Returns:
            tuple: A tuple containing:
                - dict | None: Alert configuration if successful, None if failed
                - int | None: Error code (1) if failed, None if successful

        Example:
            >>> content, err = valid_single_file_arg("path/to/alert.json")
            >>> if err:
            >>>     print(f"Failed to load alert config: {err}")
        """
        if not os.path.isfile(file_path):
            log.error("[X] File not found: {}", file_path)
            return None, 1
        try:
            with open(file_path, "r") as f:
                alert_content = json.load(f)
                log.debug(
                    "Successfully loaded alert configuration from {}",
                    file_path)
                return alert_content, None
        except json.JSONDecodeError as e:
            log.error("[X] Invalid JSON in file {}: {}", file_path, str(e))
            return None, 1
        except IOError as e:
            log.error("[X] Error reading file {}: {}", file_path, str(e))
            return None, 1


class UploadAlert(AlertManager):
    # Rule fields introduced in newer Grafana majors. They are dropped when the
    # target runs an older major so a bundle exported from a newer Kloudfuse
    # release can still be imported.
    NEWER_RULE_FIELDS = {"missing_series_evals_to_resolve": 12}

    def __init__(self, grafana_client: GrafanaClient, alert_folder_name: str, datasource_overrides=None):
        super().__init__(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )
        self._overrides = datasource_overrides or {}
        self._remapper = None
        self._grafana_major = None
        self._contact_points = None
        self._missing_receivers = set()

    def _prepare_target_info(self):
        """Look up what is needed to adapt rules to the target Grafana (once)."""
        if self._remapper is not None:
            return
        ds_uid_map = self.gc._get_datasource_uid_map()
        if not ds_uid_map:
            log.warning("[!] Could not list datasources on the target; datasource UIDs will not be remapped")
        self._remapper = DatasourceRemapper(ds_uid_map, self._overrides)
        self._grafana_major = self.gc.get_major_version()
        log.debug("Target Grafana major version: {}", self._grafana_major)
        self._contact_points = self.gc.get_contact_point_names()

    def process_args(self, single_file, directory, multi_directory):
        try:
            if single_file:
                if is_archive(single_file):
                    log.error("[X] -s takes a single JSON file; use -d or -m for archives.")
                    exit(1)
                ok = self._create_alert_from_one_file(single_file)
            elif directory:
                with extracted(directory) as path:
                    ok = self._create_alert_from_dir(path)
            elif multi_directory:
                with extracted(multi_directory) as path:
                    ok = self._create_alerts_from_multi_dir(path)
            else:
                log.error("Invalid arguments provided.")
                exit(1)
        except (ValueError, OSError, zipfile.BadZipFile, tarfile.TarError) as e:
            log.error("[X] Cannot read archive: {}", e)
            exit(1)
        if self._missing_receivers:
            log.warning("[!] Contact point(s) not found on the target: {}. Alerts routed to them will not notify "
                        "until they are created.", ", ".join(sorted(self._missing_receivers)))
        if ok is False:
            log.error("[X] Alert upload failed; see errors above.")
            exit(1)

    def _process_rules(self, file_content: dict) -> dict:
        rules = file_content.get("rules")
        if not rules:
            log.error("No rules found in alert config.")
            exit(1)
        self._prepare_target_info()
        for rule in rules:
            grafana_alert = rule.get("grafana_alert")
            if not isinstance(grafana_alert, dict):
                continue
            # uid & namespace_uid tie a rule to the source instance and would stop
            # the rule from overriding an existing one by title.
            grafana_alert.pop("uid", None)
            grafana_alert.pop("namespace_uid", None)
            if self._grafana_major is not None:
                for field, since in self.NEWER_RULE_FIELDS.items():
                    if self._grafana_major < since and field in grafana_alert:
                        log.warning("[!] Dropping '{}' from '{}': not supported by Grafana {}",
                                    field, grafana_alert.get("title"), self._grafana_major)
                        grafana_alert.pop(field)
            receiver = (grafana_alert.get("notification_settings") or {}).get("receiver")
            if receiver and self._contact_points is not None and receiver not in self._contact_points:
                self._missing_receivers.add(receiver)
        self._remapper.process(file_content)
        self._remapper.warn_unknown("Alert group '{}'".format(file_content.get("name")))
        return file_content

    def _upload_group(self, content: dict, folder: str, source: str) -> bool:
        """Post one rule group to `folder`; returns success."""
        stripped = self._process_rules(content)
        success = self.gc.create_alert(folder, json.dumps(stripped))
        if success:
            log.info("[+] Uploaded alert group '{}' to folder '{}' ({} alert(s)) from {}",
                     stripped.get("name"), folder, len(stripped.get("rules", [])), source)
        else:
            log.error("[X] Failed to upload alert group from {} to folder '{}'", source, folder)
        return success

    def _create_alert_from_one_file(self, file_path: str) -> bool:
        file_content, err = self._valid_single_file_arg(file_path)
        if err:
            return False
        log.debug("file content: {}", file_content)
        return self._upload_group(file_content, self.alert_folder_name, file_path)

    def _upload_files(self, file_paths, target_folder) -> bool:
        all_ok = True
        uploaded = 0
        for file_path in file_paths:
            if not file_path.endswith(".json"):
                log.warning("[!] Skipping non-JSON file: {}", file_path)
                continue
            file_content, err = self._valid_single_file_arg(file_path)
            if err:
                log.error("[X] Failed to load alert config from {}. Err={}", file_path, err)
                all_ok = False
                continue
            if self._upload_group(file_content, target_folder, file_path):
                uploaded += 1
            else:
                all_ok = False
        if uploaded:
            log.info("[=] Uploaded {} alert group(s) to folder '{}'", uploaded, target_folder)
        return all_ok

    def _create_alert_from_dir(self, directory, subdir=None):
        log.debug("Processing directory: {} {}", directory, subdir)
        if not os.path.isdir(directory):
            log.error("[X] Directory not found: {}", directory)
            return False
        file_paths = sorted(
            os.path.join(root, f) for root, _, files in os.walk(directory) for f in files
        )
        return self._upload_files(file_paths, subdir if subdir else self.alert_folder_name)

    def _create_alerts_from_multi_dir(self, root_directory: str):
        """Upload a tree of folders; each directory's relative path becomes a (nested) Grafana folder."""
        if not os.path.exists(root_directory):
            log.error("[X] Root directory not found: {}", root_directory)
            return False
        if not os.path.isdir(root_directory):
            log.error("[X] Root directory is not a directory: {}", root_directory)
            return False
        all_ok = True
        found = False
        for current, dirs, files in os.walk(root_directory):
            dirs.sort()
            json_files = [os.path.join(current, f) for f in sorted(files) if f.endswith(".json")]
            if not json_files:
                continue
            rel = os.path.relpath(current, root_directory)
            if rel == ".":
                log.warning("[!] Ignoring {} JSON file(s) at the top level; put them in a folder directory",
                            len(json_files))
                continue
            found = True
            folder = "/".join(rel.split(os.sep))
            if not self._upload_files(json_files, folder):
                all_ok = False
        if not found:
            log.warning("[!] No alert JSON files found under {}", root_directory)
        return all_ok


class DownloadAlert(AlertManager):
    def __init__(self, grafana_client: GrafanaClient, alert_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )

    def _prepare_file(self, file_path: str) -> bool:
        try:
            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            return True
        except OSError as e:
            log.error("Failed to create directory for {}: {}", file_path, str(e))
            return False

    def process_args(self, alert_name, directory, output, multi_directory):
        try:
            if alert_name:
                with output_target(output, safe_name(alert_name) + ".json") as target:
                    if not self._prepare_file(target):
                        log.error("Invalid output file path: {}", output)
                        exit(1)
                    self._download_single_alert(alert_name, target)
            elif directory:
                with output_target(output) as target:
                    self._download_alerts_from_folder(self.alert_folder_name, target)
            elif multi_directory:
                with output_target(output) as target:
                    self._download_alerts_from_all_folders(target)
            else:
                log.error("No valid download option provided.")
        except OSError as e:
            log.error("[X] Cannot write output {}: {}", output, e)
            exit(1)

    def _download_single_alert(self, alert_name, output):
        log.debug("Downloading alert: {}", alert_name)
        alert_payload, found = self.gc.download_alert(
            self.alert_folder_name,
            alert_name,
        )
        if not found:
            log.error("[X] Alert not found: {}", alert_name)
            exit(1)
        self._save_alert_to_file(alert_payload, output)
        alert_count = len(alert_payload.get("rules", []))
        log.info("[+] Downloaded alert: {} ({} alert(s) in group)", alert_name, alert_count)

    def _save_groups(self, groups, folder_output_path, folder_label):
        os.makedirs(folder_output_path, exist_ok=True)
        log.info("[*] Downloading {} alert group(s) from folder: {}", len(groups), folder_label)
        for group in groups:
            group_name = group.get("name")
            output_path = os.path.join(folder_output_path, f"{safe_name(group_name or 'group')}.json")
            self._save_alert_to_file(group, output_path)
            log.info("[+] Downloaded alert group: {} ({} alert(s)) -> {}",
                     group_name, len(group.get("rules", [])), output_path)

    def _download_alerts_from_folder(self, folder_name, output):
        log.debug("Downloading alerts from folder: {}", folder_name)
        # Nested folders are addressed by path, e.g. "parent/child"
        groups, found = self.gc.download_alerts_folder(folder_name)
        if not found:
            log.error("[X] Could not download alerts from folder: {}", folder_name)
            exit(1)
        if not groups:
            log.warning("[!] No alerts in folder: {}", folder_name)
            return
        self._save_groups(groups, output, folder_name)

    def _download_alerts_from_all_folders(self, output_dir):
        log.debug("Downloading all alerts from Grafana")
        if os.path.isfile(output_dir):
            log.error("[X] Output path exists and is a file, expected a directory: {}", output_dir)
            exit(1)
        os.makedirs(output_dir, exist_ok=True)

        all_folders = self.gc.get_all_folders_recursive()
        if not all_folders:
            log.warning("[!] No folders found")
        processed_uids = set()
        failures = 0
        for folder in all_folders:
            if folder['uid'] in processed_uids:
                continue
            processed_uids.add(folder['uid'])

            # Query by UID: titles are not unique across nesting levels. The folder
            # path becomes the directory tree, so nested folders round-trip on upload.
            groups, found = self.gc.download_alerts_by_folder_uid(folder['uid'], folder['path'])
            if not found:
                failures += 1
                continue
            if groups:
                self._save_groups(groups, os.path.join(output_dir, *folder['path'].split('/')), folder['path'])
        if failures:
            log.error("[X] Failed to download alerts from {} folder(s)", failures)
            exit(1)

    def _save_alert_to_file(self, alert_payload, output_path):
        with open(output_path, 'w') as f:
            json.dump(alert_payload, f, indent=2)
        log.debug("Saved alerts to file: {}", output_path)


class DeleteAlert(AlertManager):
    def __init__(self, grafana_client: GrafanaClient, alert_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )

    def process_args(self, alert_name, directory):
        if alert_name:
            res = self.gc.delete_alert(
                self.alert_folder_name,
                alert_name,
            )
            if res:
                log.info("[+] Successfully deleted alert '{}' using Ruler API", alert_name)
            else:
                log.error("[X] Failed to delete alert '{}'", alert_name)
                exit(1)
        elif directory:
            # Use the delete_alert method with delete_all=True
            # This will internally use the Provisioning API method
            res = self.gc.delete_alert(
                self.alert_folder_name,
                None,
                delete_all=True,
            )

            if res:
                log.info("[+] Successfully deleted all alerts in folder '{}'", self.alert_folder_name)
            else:
                log.error("[X] Failed to delete all alerts in folder '{}'", self.alert_folder_name)
                exit(1)
        else:
            log.error("[X] Invalid arguments provided.")
            exit(1)


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
        verify_ssl=args.verify_ssl,
    )
    alert_folder_name = args.alert_folder_name
    try:
        datasource_overrides = parse_overrides(getattr(args, "datasource_uid_map", None))
    except ValueError as e:
        log.error("[X] {}", e)
        exit(1)

    if args.command == "upload":
        i = UploadAlert(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name,
            datasource_overrides=datasource_overrides,
        )
        i.process_args(
            single_file=args.single_file,
            directory=args.directory,
            multi_directory=args.multi_directory,
        )
    elif args.command == "download":
        e = DownloadAlert(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )
        e.process_args(
            alert_name=args.alert_name,
            directory=args.directory,
            output=args.output,
            multi_directory=args.multi_directory,
        )
    elif args.command == "delete":
        d = DeleteAlert(
            grafana_client=grafana_client,
            alert_folder_name=alert_folder_name
        )
        d.process_args(
            alert_name=args.alert_name,
            directory=args.directory,
        )
    else:
        log.error("Invalid command provided.")
        exit(1)
