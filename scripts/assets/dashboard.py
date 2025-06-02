#!/usr/bin/python

import argparse
import json
import os
import sys
from typing import Optional, Union, Tuple

from loguru import logger as log

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
        "-v",
        "--verify-ssl",
        action='store_false',
        help="Verify SSL certificate (default: True)"
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
        help='Path to directory containing multiple dashboards'
    )
    upload_mode.add_argument(
        '-m',
        '--multi-directory',
        help='Path to parent directory containing multiple folders of dashboards'
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
        help='Output file path to save dashboard configuration'
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
        help='Download dashboards from all Grafana folders'
    )

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

class UploadDashboard(DashboardManager):
    def __init__(self, grafana_client: GrafanaClient, dashboard_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )

    def _replace_datasource_uids(self, dashboard_json, ds_uid_map):
        # Ensure ds_uid_map is not None, though process_args should handle this.
        if ds_uid_map is None:
            ds_uid_map = {} # Default to empty map if None is passed for some reason

        def process(obj):
            if isinstance(obj, dict):
                if "datasource" in obj:
                    ds_value = obj["datasource"] # Use a different variable name 'ds_value'
                    if isinstance(ds_value, dict) and "uid" in ds_value:
                        uid = ds_value.get("uid") # Use .get for uid as well for safety
                        if uid == "" or uid is None:
                            if "kfdatasource" in ds_uid_map:
                                # Using direct assignment as per last attempt to make test pass/fail informatively
                                ds_value["uid"] = ds_uid_map["kfdatasource"] 
                        elif isinstance(uid, str) and uid.startswith("${DS_") and uid.endswith("}"):
                            var_name = uid[5:-1].lower()
                            if var_name in ds_uid_map: # Check if var_name exists
                                ds_value["uid"] = ds_uid_map[var_name]
                    elif isinstance(ds_value, str) and ds_value.startswith("${DS_") and ds_value.endswith("}"):
                        var_name = ds_value[5:-1].lower()
                        if var_name in ds_uid_map:
                             obj["datasource"] = ds_uid_map[var_name]
                
                # Recurse for all values in the dictionary
                for k, v_item in obj.items():
                    obj[k] = process(v_item) # Assign back the result of process
            elif isinstance(obj, list):
                # Process each item in the list and assign it back
                return [process(item) for item in obj] # Ensure list items are updated
            return obj
        return process(dashboard_json)


    def process_args(self, single_file, directory, multi_directory):
        ds_uid_map = self.gc._get_datasource_uid_map()
        if ds_uid_map is None: 
            log.error("Could not retrieve datasource UID map from Grafana. Aborting.")
            exit(1) 
        log.info("ds_uid_map={}", ds_uid_map)
        if single_file:
            self._create_dashboard_from_one_file(single_file, ds_uid_map)
        elif directory:
            self._create_dashboards_from_dir(directory, ds_uid_map, self.dashboard_folder_name)
        elif multi_directory:
            self._create_dashboards_from_root_dir(multi_directory, ds_uid_map)
        else:
            log.error("Invalid arguments provided.") 
            exit(1)
    
    def _create_dashboard_from_one_file(self, single_file, ds_uid_map):
        content, err = self._valid_single_file_arg(single_file)
        if err:
            exit(err)
        content = self._replace_datasource_uids(content, ds_uid_map)
        response = self.gc.upload_dashboard(content, self.dashboard_folder_name) 
        if response and response.get("status") == "success":
            log.info("Dashboard {} uploaded successfully to folder {}. UID: {}", single_file, self.dashboard_folder_name, response.get("uid"))
        else:
            log.error("Failed to upload dashboard {} to folder {}. Error: {}", single_file, self.dashboard_folder_name, response.get("message", "Unknown error"))

    def _create_dashboards_from_dir(self, dir_path, ds_uid_map, folder_name): 
        self.dashboard_folder_name = folder_name 
        for file in os.listdir(dir_path):
            if file.endswith(".json"):
                self._create_dashboard_from_one_file(os.path.join(dir_path, file), ds_uid_map)

    def _create_dashboards_from_root_dir(self, multi_directory_root_path, ds_uid_map): 
        for item_name in os.listdir(multi_directory_root_path): 
            item_path = os.path.join(multi_directory_root_path, item_name)
            if os.path.isdir(item_path):
                self._create_dashboards_from_dir(item_path, ds_uid_map, item_name)
            else:
                log.warning("Skipping non-directory file in multi-directory mode: {}", item_path)

class DownloadDashboard(DashboardManager):
    def __init__(self, grafana_client: GrafanaClient, dashboard_folder_name: str):
        super().__init__(
            grafana_client=grafana_client,
            dashboard_folder_name=dashboard_folder_name
        )

    def process_args(self, dashboard_name, directory, output, multi_directory):
        log.debug("dashboard_name={}, directory={}, output={}, multi_directory={}", dashboard_name, directory, output, multi_directory)
        if not (dashboard_name or directory or multi_directory):
            log.error("Invalid arguments. Must specify a dashboard name, directory, or multi_directory.")
            exit(1)
        if dashboard_name:
            if not output: log.error("Output path is required for single dashboard download."); exit(1)
            self._download_single_dashboard_from_folder(dashboard_name, output) 
        elif directory:
            if not output: log.error("Output path is required for directory download."); exit(1)
            self._download_all_dashboards_from_folder(self.dashboard_folder_name, output)
        elif multi_directory:
            if not output: log.error("Output path is required for multi-directory download."); exit(1)
            self._download_all_dashboards_from_grafana(output) 

    def _download_single_dashboard_from_folder(self, dashboard_name, output_file_path): 
        log.debug("Downloading dashboard: {}", dashboard_name)
        dashboard_payload, found = self.gc.download_dashboard(
            name=dashboard_name, folder_name=self.dashboard_folder_name, is_uid=False 
        )
        if not found or not dashboard_payload: 
            log.error("Dashboard '{}' not found in folder '{}'.", dashboard_name, self.dashboard_folder_name)
            exit(1)
        self._save_dashboard_to_file(dashboard_payload, output_file_path)

    def _download_all_dashboards_from_folder(self, folder_name, directory):
        log.debug("Downloading all dashboards from folder: {} to directory {}", folder_name, directory)
        dashboards_uids = self.gc.get_dashboard_uids_by_folder(folder_name=folder_name) 
        if dashboards_uids is None: 
            log.error("Failed to retrieve dashboards for folder: {}. UIDs list is None.", folder_name)
            exit(1) 
        if not dashboards_uids:
            log.info("No dashboards found in folder '{}'. Nothing to download.", folder_name)
            return
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            log.error("Error creating base directory {}: {}", directory, e)
            exit(1) 
        downloaded_count = 0
        for dashboard_uid in dashboards_uids:
            dashboard_payload, found = self.gc.download_dashboard(name=dashboard_uid, folder_name=folder_name, is_uid=True)
            if not found or not dashboard_payload:
                log.error("Failed to download dashboard with UID: {} from folder {}", dashboard_uid, folder_name)
                continue 
            title = dashboard_payload.get('dashboard', {}).get('title', 'Untitled_Dashboard')
            title = title.replace(" ", "_").replace("/", "_").replace(":", "_") 
            output_path = os.path.join(directory, f"{title}.json")
            self._save_dashboard_to_file(dashboard_payload, output_path)
            downloaded_count +=1
        if downloaded_count > 0:
            log.info("Downloaded {} dashboard(s) from folder '{}' to '{}'.", downloaded_count, folder_name, directory)

    def _download_all_dashboards_from_grafana(self, multi_directory_output_path): 
        log.debug("Downloading all dashboards from Grafana to root: {}", multi_directory_output_path)
        find_folder_api = "/api/folders"
        folders_response, success = self.gc._http_get_request_to_grafana(find_folder_api)
        if not success or not isinstance(folders_response, list): 
            log.error("Failed to fetch Grafana folders.")
            exit(1) 
        if not folders_response:
            log.info("No Grafana folders found.")
            return
        try:
            os.makedirs(multi_directory_output_path, exist_ok=True)
        except OSError as e:
            log.error("Error creating root output directory {}: {}", multi_directory_output_path, e)
            exit(1) 
        log.info("Found {} Grafana folder(s).", len(folders_response))
        for folder in folders_response:
            folder_title = folder.get("title", "Untitled_Folder") 
            folder_output_dir = os.path.join(multi_directory_output_path, folder_title) 
            self._download_all_dashboards_from_folder(folder_name=folder_title, directory=folder_output_dir)

    def _save_dashboard_to_file(self, dashboard_payload, output_path):
        try:
            with open(output_path, 'w') as f:
                json.dump(dashboard_payload, f, indent=2)
            log.debug("Saved dashboard to output.json") 
        except (OSError, TypeError) as e: 
            log.error("Error saving dashboard to {}: {}", output_path, e)

if __name__ == "__main__":
    log.info("Executing={}", ' '.join(sys.argv))
    args = parse_args()
    if args.debug: log.remove(); log.add(sys.stderr, level="DEBUG")
    # Corrected GrafanaClient instantiation
    grafana_client = GrafanaClient(
        args.grafana_address, # server
        args.grafana_username, # username
        args.grafana_password, # password
        verify_ssl=args.verify_ssl
    )
    dashboard_folder_name = args.dashboard_folder_name
    if args.command == "upload":
        i = UploadDashboard(grafana_client, dashboard_folder_name)
        i.process_args(args.single_file, args.directory, args.multi_directory)
    elif args.command == "download":
        e = DownloadDashboard(grafana_client, dashboard_folder_name)
        e.process_args(args.dashboard_name, args.directory, args.output, args.multi_directory)
    else:
        log.error("Invalid command provided."); exit(1)
