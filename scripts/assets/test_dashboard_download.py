import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from common.grafana_client import GrafanaClient
from dashboard import DownloadDashboard


class DashboardDownloadTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock(spec=GrafanaClient)
        self.payload = {'dashboard': {'uid': 'dashboard-1', 'title': 'Test dashboard'}}
        self.client.get_dashboards_in_folder_recursive.return_value = ['dashboard-1']
        self.client.download_dashboard.return_value = (self.payload, True)
        self.output = tempfile.TemporaryDirectory()
        self.addCleanup(self.output.cleanup)

    def download(self, folder):
        DownloadDashboard(self.client, folder).process_args(
            dashboard_name=None, directory=True, output=self.output.name,
            multi_directory=None,
        )

    def assert_downloaded(self):
        path = Path(self.output.name) / 'Test_dashboard.json'
        self.assertEqual(json.loads(path.read_text()), self.payload)

    def test_nested_path_downloads_without_scanning_unrelated_folders(self):
        self.client._get_folder_uid_by_path.return_value = 'target-folder'
        self.client.get_all_folders_recursive.side_effect = AssertionError('Global scan')

        self.download('parent/child')

        self.client._get_folder_uid_by_path.assert_called_once_with('parent/child')
        self.client.get_dashboards_in_folder_recursive.assert_called_once_with('target-folder')
        self.assert_downloaded()

    def test_missing_path_does_not_scan_or_download_other_folders(self):
        self.client._get_folder_uid_by_path.return_value = None

        self.download('parent/missing')

        self.client.get_all_folders_recursive.assert_not_called()
        self.client.get_dashboards_in_folder_recursive.assert_not_called()
        self.client.download_dashboard.assert_not_called()
        self.assertEqual(list(Path(self.output.name).iterdir()), [])

    def test_plain_name_and_uid_keep_existing_matching(self):
        self.client.get_all_folders_recursive.return_value = [
            {'uid': 'target-folder', 'title': 'child', 'path': 'parent/child'},
        ]
        for selector in ('child', 'target-folder'):
            with self.subTest(selector=selector):
                self.client.reset_mock()

                self.download(selector)

                self.client._get_folder_uid_by_path.assert_not_called()
                self.client.get_dashboards_in_folder_recursive.assert_called_once_with('target-folder')
                self.assert_downloaded()


if __name__ == '__main__':
    unittest.main()
