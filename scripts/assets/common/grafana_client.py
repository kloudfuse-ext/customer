import json
import sys
import os
from typing import List, Optional
from typing import Tuple

import requests
from loguru import logger as log
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

# Set logging level to INFO
log.remove()
log.add(sink=sys.stderr, level="INFO")


class GrafanaClient:
    def __init__(self, grafana_server, grafana_username=None, grafana_password=None, auth_token=None, verify_ssl=True):
        # Validate authentication method
        if not auth_token and not (grafana_username and grafana_password):
            raise ValueError("Authentication required: provide either username/password or auth_token")
        
        parsed_url = urlparse(grafana_server)
        self._scheme = parsed_url.scheme or "https"  # Default to HTTPS if no scheme provided
        self._server = parsed_url.netloc 
        self._base_path = parsed_url.path.rstrip("/") if parsed_url.path else "" 
        self._server = self._server + self._base_path
        self._username = grafana_username
        self._password = grafana_password
        self._auth_token = auth_token
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        # Add Bearer token to headers if provided
        if self._auth_token:
            self._headers["Authorization"] = f"Bearer {self._auth_token}"
        self.verify = verify_ssl

    def _handle_http_request_to_grafana(self, **kwargs) -> Tuple:
        path = kwargs.get("path", "")
        request_fn = kwargs.get("request_fn", None)
        if request_fn is None:
            return {'status': 'invalid request function'}, False
        request_type = kwargs.get("request_type", "")
        request_body = kwargs.get("request_body", None)
        full_url = f"{self._scheme}://{self._server}{path}"
        # Use HTTPBasicAuth only if not using token authentication
        auth = None if self._auth_token else HTTPBasicAuth(self._username, self._password)
        success = True
        response = request_fn(full_url, auth=auth, data=request_body, headers=self._headers, timeout=30, verify=self.verify)
        # log.error("http {0} returned status {1}".format(response.status_code, response.content))
        if response.status_code >= 300:
            log.error("http {0} returned an error for url {1}; status = {2}, content={3}".format(
                request_type,
                full_url,
                response.status_code,
                response.content)
            )
            success = False
        log.info("http {0} to url {1}".format(request_type, full_url))
        return response, success

    def _http_get_request_to_grafana(self, path: str) -> Tuple:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.get,
                                                                 path=path,
                                                                 request_type="get")
        if not success:
            return {'status': response.status_code}, success
        return response.json(), success

    def _http_post_request_to_grafana(self, path: str, post_data: str = None) -> bool:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.post,
                                                                 path=path,
                                                                 request_type="post",
                                                                 request_body=post_data)
        log.debug("POST response={0}, success={1}".format(response, success))
        return success

    def _http_delete_request_to_grafana(self, path: str) -> Tuple:
        response, success = self._handle_http_request_to_grafana(request_fn=requests.delete,
                                                                 path=path,
                                                                 request_type="delete")
        if not success:
            return {'status': response.status_code}, success
        # Handle empty response body for successful DELETE requests
        if response.status_code == 204:  # No Content
            return {'status': 'success'}, success
        try:
            return response.json(), success
        except:
            return {'status': 'success'}, success

    def _check_if_folder_exists(self, folder: str) -> Tuple:
        path = "/api/folders"
        folder_list, status = self._http_get_request_to_grafana(path=path)
        if not status:
            log.error("Folder API returned an error; folder = {0}".format(folder))
            return None, False
        log.debug("FolderList={0}".format(folder_list))
        folder_info = next((f for f in folder_list if f["title"] == folder), None)
        return folder_info, folder_info is not None

    def _create_alert_folder_if_not_exists(self, folder: str):
        """
        Create a new alert folder and returns the automatically created internal folderID

        :param folder: name of the folder to be created
        :return
            bool: True: if folder was created/exists, False otherwise
            FolderUID: In case successful, else None
        """
        folder_info, exists = self._check_if_folder_exists(folder)
        if exists:
            log.debug("Folder already exists; folder = {0}".format(folder_info))
            return True, folder_info["uid"]

        path = "/api/folders"
        data = json.dumps({"title": f"{folder}"})
        status = self._http_post_request_to_grafana(path=path, post_data=data)
        if not status:
            log.error("Failed to create folder; folder = {0}".format(folder))
            return status, None

        log.debug("Folder={0} created...".format(folder))
        return True, self._get_alert_folder_uid(folder)

    def _get_alert_folder_uid(self, folder_name):
        """
        Create a new folder or return existing folder's UID

        :param folder_name: Name of the folder to create/retrieve
        :return: Folder UID or None
        """
        # First, try to find existing folder
        find_folder_api = "/api/folders"
        folders_response = self._http_get_request_to_grafana(find_folder_api)
        for f in folders_response[0]:
            if f['title'] == folder_name or f["title"] is None:
                return f['uid']

        return None

    def create_alert(self, folder, alert_data_json) -> bool:
        """Create alert using sample data for testing.

        Returns
            True: Success
            False: Failure
        """
        log.debug("Alert data={0}".format(alert_data_json))
        created, folder_uid = self._create_alert_folder_if_not_exists(folder)
        if not created:
            log.error("Failed to create folder={0}".format(folder))
            return False

        log.debug("Folder UID={0}, Name={1}".format(folder_uid, folder))

        
        alert_data_json = json.loads(alert_data_json)
        group_name = alert_data_json["name"]
        rule_group_response, success = self._http_get_request_to_grafana(path=f"/api/ruler/grafana/api/v1/rules/{folder_uid}/{group_name}")
        if success:
        
            # If rule group response rules list is not empty process rule group
            if rule_group_response["rules"]:
                # Create a map of alert names to their corresponding rules from alert_data_json
                alert_map = {alert["grafana_alert"]["title"]: alert for alert in alert_data_json["rules"]}

                # For each alert in the existing rule group, check if it exists in alert_data_json and overwrite the rule in rule_group_response
                for i, existing_alert in enumerate(rule_group_response["rules"]):
                    alert_name = existing_alert["grafana_alert"]["title"]
                    if alert_name in alert_map:
                        rule_group_response["rules"][i] = alert_map[alert_name]
                        #Remove alerts from alert_data_json that are already in rule_group_response
                        del alert_map[alert_name]
                # Add any remaining alerts from alert_data_json that were not in rule_group_response
                for remaining_alert in alert_map.values():
                    rule_group_response["rules"].append(remaining_alert)
            else:
                # If the rule group response is empty, add all alerts from alert_data_json
                rule_group_response["rules"] = alert_data_json["rules"]
        else:
            log.debug("Rule group not found, using the alert json as is.")
            rule_group_response = alert_data_json

        path = f"/api/ruler/grafana/api/v1/rules/{folder_uid}"

        return self._http_post_request_to_grafana(path=path, post_data=json.dumps(rule_group_response))

    def _list_alerts(self, folder_name: str) -> tuple[Optional[List], Optional[str]]:
        """List all alerts in a Grafana folder.
        
        Args:
            folder_name: Name of the folder to list alerts from
            
        Returns:
            tuple: (alerts_list, error_message)
                - alerts_list: List of alerts if successful, None if failed
                - error_message: Error description if failed, None if successful
        """
        folder_uid = self._get_alert_folder_uid(folder_name)
        if not folder_uid:
            return None, f"Folder not found: {folder_name}"

        log.debug("[ListAlert] Folder UID={0}, Name={1}".format(folder_uid, folder_name))
        path = f"/api/ruler/grafana/api/v1/rules/{folder_uid}"
        response = self._http_get_request_to_grafana(path)
        log.debug("Response=\n{}", json.dumps(response, indent=2, sort_keys=True))
        if not response:
            return None, f"Failed to fetch alerts from folder: {folder_name}"

        return response, None

    def _post_rule_group(self, folder_uid: str, rule_group_data: dict) -> bool:
        """Post a rule group to Grafana using the Ruler API.
        
        This method handles the posting of rule groups, including empty ones for deletion.
        
        Args:
            folder_uid: The UID of the folder
            rule_group_data: The rule group data containing name, interval, and rules
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Ensure the rule group has required fields
        if "name" not in rule_group_data:
            log.error("Rule group data missing 'name' field")
            return False
            
        group_name = rule_group_data["name"]
        log.info("Posting rule group '{0}' to folder UID '{1}' with {2} rules".format(
            group_name, 
            folder_uid, 
            len(rule_group_data.get("rules", []))
        ))
        
        # The Ruler API expects the rule group data directly
        path = f"/api/ruler/grafana/api/v1/rules/{folder_uid}"
        
        # Post the rule group
        success = self._http_post_request_to_grafana(path=path, post_data=json.dumps(rule_group_data))
        
        if success:
            if len(rule_group_data.get("rules", [])) == 0:
                log.info("Successfully posted empty rule group '{0}' (effectively deleting it)".format(group_name))
            else:
                log.info("Successfully updated rule group '{0}'".format(group_name))
        else:
            log.error("Failed to post rule group '{0}'".format(group_name))
            
        return success

    def delete_alert(self, folder_name, alert_name, delete_all=False):
        """Delete alert from Grafana folder using the Ruler API.
        
        Args:
            folder_name: Name of the Grafana folder containing the alert
            alert_name: Name of the specific alert to delete (ignored if delete_all=True)
            delete_all: If True, deletes all alerts in the folder
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        log.info("delete_alert called: alert_name={0}, folder_name={1}, delete_all={2}".format(
            alert_name,
            folder_name,
            delete_all
        ))
        
        # Get folder UID
        folder_uid = self._get_alert_folder_uid(folder_name)
        if folder_uid is None:
            log.error("Folder not found: {0}".format(folder_name))
            return False
            
        # List existing alerts
        existing_alerts, error = self._list_alerts(folder_name)
        if error:
            log.error(error)
            return False
        
        # Handle case where no alerts exist
        if existing_alerts is None or existing_alerts[0] == {} or folder_name not in existing_alerts[0]:
            if delete_all:
                log.info("No alerts found in folder '{0}' - nothing to delete".format(folder_name))
                return True
            else:
                log.warning("Alert '{0}' was not found - no alerts in folder '{1}'".format(alert_name, folder_name))
                return False
            
        success_count = 0
        total_groups = len(existing_alerts[0][folder_name])
        
        # Process each rule group in the folder
        for group_index, rule_group in enumerate(existing_alerts[0][folder_name]):
            group_name = rule_group.get("name", f"group_{group_index}")
            
            if delete_all:
                # For delete_all, empty the rules array
                log.info("Deleting all alerts from rule group '{0}'".format(group_name))
                rule_group["rules"] = []
                
                # Post the empty rule group
                if self._post_rule_group(folder_uid, rule_group):
                    success_count += 1
                else:
                    log.error("Failed to delete alerts from rule group '{0}'".format(group_name))
            else:
                # For single alert deletion, filter out the specific alert
                new_rules = []
                alert_found = False
                
                for rule in rule_group.get("rules", []):
                    rule_title = rule.get("grafana_alert", {}).get("title", "")
                    if rule_title != alert_name:
                        new_rules.append(rule)
                    else:
                        log.info("Found alert '{0}' in group '{1}'".format(rule_title, group_name))
                        alert_found = True
                
                # Only update if we found the alert
                if alert_found:
                    # Update the rule group with remaining rules (even if empty)
                    rule_group["rules"] = new_rules
                    
                    # Post the updated rule group
                    if self._post_rule_group(folder_uid, rule_group):
                        success_count += 1
                    else:
                        log.error("Failed to update rule group '{0}'".format(group_name))
                        return False
                            
        # Check results
        if delete_all:
            if success_count == total_groups:
                log.info("Successfully deleted all alerts from {0} rule groups in folder '{1}'".format(
                    total_groups, folder_name))
                return True
            else:
                log.error("Failed to delete alerts from some rule groups: {0}/{1} succeeded".format(
                    success_count, total_groups))
                return False
        else:
            if success_count == 0:
                log.warning("Alert '{0}' was not found in any rule group in folder '{1}'".format(
                    alert_name, folder_name))
                return False
            else:
                log.info("Successfully deleted alert '{0}' from folder '{1}'".format(alert_name, folder_name))
                return True

    def download_alert(self, folder_name, alert_name, all_alerts=False):
        """Download alert."""
        log.debug("Download alert: {0} from folder={1}".format(
            alert_name,
            folder_name,
        ))
        folder_uid = self._get_alert_folder_uid(folder_name)
        if folder_uid is None:
            log.error("Folder not found: {0}".format(folder_name))
            return None, False
        existing_alerts, error = self._list_alerts(folder_name)
        if error:
            log.error(error)
            return None, False

        new_rules = []

        rule_group_index = 0
        try: 
            for index, group in enumerate(existing_alerts[0][folder_name]):
                for r in group["rules"]:
                    rule_title = r["grafana_alert"]["title"]
                    if all_alerts or rule_title == alert_name:
                        log.debug("Keeping alert: {0}".format(rule_title))
                        new_rules.append(r)
                        rule_group_index = index
                    else:
                        log.debug("Skipping alert: {0}".format(rule_title))
        except KeyError:
            # Skip this if the key does not exist
            log.debug("KeyError: Skipping folder_name={} as it does not exist in existing_alerts", folder_name)
            return None, False

        if len(new_rules) == 0:
            log.warning("Alert not found: {0}".format(alert_name))
            return None, False            

        existing_alerts[0][folder_name][rule_group_index]["rules"] = new_rules
        return existing_alerts[0][folder_name][rule_group_index], True
    
    def download_alerts_folder(self, folder_name):
        log.debug("Download all alerts from folder={0}".format(
            folder_name,
        ))
        folder_uid = self._get_alert_folder_uid(folder_name)
        if folder_uid is None:
            log.error("Folder not found: {0}".format(folder_name))
            return None, False
        existing_alerts, error = self._list_alerts(folder_name)
        if error:
            log.error(error)
            return None, False
        
        return existing_alerts, True
    
    def _get_datasource_uid_map(self):
        """Fetch all datasources and return a map of name (lowercase) to UID."""
        datasources, success = self._http_get_request_to_grafana("/api/datasources")
        if not success:
            log.error("Failed to fetch datasources from Grafana")
            return {}
        return {ds["name"].lower(): ds["uid"] for ds in datasources if "name" in ds and "uid" in ds}
    
    def upload_dashboard(self, dashboard_data, folder_name):
        """Uploads a single dashboard to the specified Grafana folder."""
        created, folder_id = self._create_alert_folder_if_not_exists(folder_name)
        if not created:
            log.error("Failed to create folder={0}".format(folder_name))
            return False
        # folder_id = self._get_alert_folder_uid(folder_name)
        if folder_id is None:
            log.error("Invalid folder name. Aborting upload.")
            return
        
        # with open(dashboard_path, "r") as file:
        #     dashboard_data = json.load(file)
        
        # Ensure the dashboard structure
        dashboard_data["id"] = "null"
        payload = {
            "dashboard": dashboard_data,
            "folderUid": folder_id,
            "overwrite": True
        }
        
        status = self._http_post_request_to_grafana(f"/api/dashboards/db", post_data=json.dumps(payload))
        # response = requests.post(f"{GRAFANA_URL}/api/dashboards/db", headers=HEADERS, json=payload)
        
        if status:
            title = dashboard_data.get("title", "Untitled")
            log.info(f"Successfully uploaded '{title}'. to folder '{folder_name}'.")
        else:
            log.error(f"Failed to upload dashboard")

    def __get_dashboard_uid_by_name(self, dashboard_name):
        """Fetches the UID of a dashboard given its name."""
        response, status = self._http_get_request_to_grafana(path="/api/search")
        try:
            
            dashboards = response
            for dashboard in dashboards:
                if dashboard["title"] == dashboard_name:
                    return dashboard["uid"]
        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching dashboards: {e}")
        except json.JSONDecodeError:
            log.error("Error: Received unexpected response format (not JSON). Check authentication and API URL.")
        return None
    
    def get_dashboard_uids_by_folder(self, folder_name):
        """Fetches the UIDs of all dashboards in a given folder."""
        folder_id = self._get_alert_folder_uid(folder_name)
        response, status = self._http_get_request_to_grafana(path=f"/api/search?folderUIDs={folder_id}")
        if status:
            return [dashboard["uid"] for dashboard in response]
        else:
            log.error(f"Error fetching dashboards in folder {folder_id}")
            return []


    def download_dashboard(self, dashboard_identifier, is_uid=False):
        """Downloads a single dashboard by UID or name."""
        # if by_name:
        if not is_uid:
            dashboard_uid = self.__get_dashboard_uid_by_name(dashboard_identifier)
        else:
            dashboard_uid = dashboard_identifier
        
        response_json, status = self._http_get_request_to_grafana(path=(f"/api/dashboards/uid/{dashboard_uid}"))
        if status:
            return response_json, True
        else:   
            log.error("Failed to fetch dashboard data from Grafana")
            return None, False
