import unittest
from unittest import mock
import sys
import os
import json

# Add the parent directory (assets) to the Python path
scripts_assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if scripts_assets_path not in sys.path:
    sys.path.insert(0, scripts_assets_path)

# Import modules under test
from alert import AlertManager, UploadAlert, DownloadAlert, DeleteAlert
from dashboard import DashboardManager, UploadDashboard, DownloadDashboard 
from common.grafana_client import GrafanaClient

# Mock loggers before classes are defined or tests run
mock_alert_log = mock.Mock()
mock_dashboard_log = mock.Mock()

try:
    alert_module = sys.modules['alert']
    alert_module.log = mock_alert_log
except KeyError:
    pass 

try:
    dashboard_module_actual = __import__('dashboard') 
    dashboard_module_actual.log = mock_dashboard_log
except (ImportError, AttributeError) as e:
    pass


class TestAlertScript(unittest.TestCase):
    def setUp(self):
        self.mock_grafana_client = mock.Mock(spec=GrafanaClient)
        self.patch_isfile = mock.patch('os.path.isfile'); self.mock_isfile = self.patch_isfile.start()
        self.patch_isdir = mock.patch('os.path.isdir'); self.mock_isdir = self.patch_isdir.start()
        self.patch_listdir = mock.patch('os.listdir'); self.mock_listdir = self.patch_listdir.start()
        self.patch_walk = mock.patch('os.walk'); self.mock_walk = self.patch_walk.start()
        self.patch_makedirs = mock.patch('os.makedirs'); self.mock_makedirs = self.patch_makedirs.start()
        self.patch_exists = mock.patch('os.path.exists'); self.mock_exists = self.patch_exists.start()
        self.patch_remove = mock.patch('os.remove'); self.mock_remove = self.patch_remove.start()
        self.mock_open_patch = mock.patch('builtins.open', new_callable=mock.mock_open); self.mock_open = self.mock_open_patch.start()
        self.patch_json_load = mock.patch('json.load'); self.mock_json_load = self.patch_json_load.start()
        self.patch_json_dump = mock.patch('json.dump'); self.mock_json_dump = self.patch_json_dump.start()
        self.patch_sys_exit = mock.patch('sys.exit'); self.mock_sys_exit = self.patch_sys_exit.start()
        mock_alert_log.reset_mock(); mock_dashboard_log.reset_mock()

    def tearDown(self):
        mock.patch.stopall()

    # --- UploadAlert Tests ---
    def test_upload_valid_single_file_arg_file_not_found(self):
        self.mock_isfile.return_value = False
        ua = UploadAlert(grafana_client=self.mock_grafana_client, alert_folder_name="dummy_folder")
        result, error_code = ua._valid_single_file_arg("dummy_path.json")
        self.assertIsNone(result); self.assertEqual(error_code, 1)
        mock_alert_log.error.assert_called_once_with("File not found: {}", "dummy_path.json")

    def test_upload_valid_single_file_arg_invalid_json(self):
        self.mock_isfile.return_value = True
        self.mock_json_load.side_effect = json.JSONDecodeError("Error", "doc", 0)
        ua = UploadAlert(grafana_client=self.mock_grafana_client, alert_folder_name="dummy_folder")
        result, error_code = ua._valid_single_file_arg("dummy_path.json")
        self.assertIsNone(result); self.assertEqual(error_code, 1)
        mock_alert_log.error.assert_called_once_with("Invalid JSON in file {}: {}", "dummy_path.json", "Error: line 1 column 1 (char 0)")

    def test_upload_valid_single_file_arg_success(self):
        self.mock_isfile.return_value = True
        sample_alert_dict = {"name": "TG", "rules": [{"g": {"t": "R1"}}]}
        self.mock_open.return_value = mock.mock_open(read_data=json.dumps(sample_alert_dict))()
        self.mock_json_load.return_value = sample_alert_dict
        ua = UploadAlert(grafana_client=self.mock_grafana_client, alert_folder_name="dummy")
        result, error_code = ua._valid_single_file_arg("dummy.json")
        self.assertEqual(result, sample_alert_dict); self.assertIsNone(error_code)

    def test_process_rules_removes_uids(self):
        i={"name": "TG", "rules": [{"grafana_alert": {"title": "R1", "uid": "abc", "namespace_uid": "def"}}]}
        e={"name": "TG", "rules": [{"grafana_alert": {"title": "R1"}}]}
        self.assertEqual(UploadAlert._process_rules(json.loads(json.dumps(i))), e)

    def test_process_rules_handles_missing_grafana_alert(self):
        i = {"name": "TG", "rules": [{"sok": "v"}]}
        self.assertEqual(UploadAlert._process_rules(json.loads(json.dumps(i))), i)
        mock_alert_log.debug.assert_has_calls([mock.call("No uid or  found in alert config."), mock.call("No namespace_uid or  found in alert config.")])

    def test_process_rules_handles_empty_rules_list(self):
        with self.assertRaises(SystemExit) as cm: UploadAlert._process_rules({"name":"TG", "rules":[]})
        self.assertEqual(cm.exception.code, 1); mock_alert_log.error.assert_called_once_with("No rules found in alert config.")

    def test_process_rules_no_rules_key(self):
        with self.assertRaises(SystemExit) as cm: UploadAlert._process_rules({"name":"TG"})
        self.assertEqual(cm.exception.code, 1); mock_alert_log.error.assert_called_once_with("No rules found in alert config.")

    @mock.patch.object(UploadAlert, '_valid_single_file_arg')
    @mock.patch.object(UploadAlert, '_process_rules')
    def test_upload_single_alert_success(self, mock_pr, mock_vsf):
        mock_vsf.return_value = ({"n":"TG"},None); mock_pr.return_value = {"n":"TGP"}
        self.mock_grafana_client.create_alert.return_value = True
        ua = UploadAlert(self.mock_grafana_client, "TF")
        self.assertTrue(ua._create_alert_from_one_file("d.json"))
        self.mock_grafana_client.create_alert.assert_called_once_with("TF",json.dumps({"n":"TGP"}))

    @mock.patch.object(UploadAlert, '_valid_single_file_arg')
    def test_upload_single_alert_file_read_fails(self, mock_vsf):
        mock_vsf.return_value = (None,1)
        ua = UploadAlert(self.mock_grafana_client, "TF")
        self.assertFalse(ua._create_alert_from_one_file("d.json"))

    def test_upload_alerts_from_dir_success_with_subdir_arg(self):
        ua=UploadAlert(self.mock_grafana_client,"Fallback")
        self.mock_isdir.return_value=True
        self.mock_walk.return_value=[("alerts_dir/sub",[],["a1.json","a2.json","not.txt"])]
        c1={"name":"AS1","interval":"1m","rules":[{"grafana_alert":{"title":"R1"}}]} 
        c2={"name":"AS2","interval":"2m","rules":[{"grafana_alert":{"title":"R2"}}]} 
        p1={"name":"AS1","interval":"1m","rules":[{"grafana_alert":{"title":"R1"}}]} 
        p2={"name":"AS2","interval":"2m","rules":[{"grafana_alert":{"title":"R2"}}]}
        def vsf(p): return (c1,None) if "a1" in p else ((c2,None) if "a2" in p else (None,1))
        def ps(c): return p1 if c["name"]=="AS1" else (p2 if c["name"]=="AS2" else c)
        with mock.patch.object(UploadAlert,'_valid_single_file_arg',side_effect=vsf), \
             mock.patch.object(UploadAlert,'_process_rules',side_effect=ps):
            ua._create_alert_from_dir(directory="alerts_dir/sub",subdir="TargetFolder")
            self.assertEqual(self.mock_grafana_client.create_alert.call_count,2)
            actual_calls = self.mock_grafana_client.create_alert.call_args_list
            expected_payload_dicts = [p1, p2]
            called_payload_dicts = [json.loads(call[0][1]) for call in actual_calls]
            for payload_dict in expected_payload_dicts: self.assertIn(payload_dict, called_payload_dicts)
            for call_obj in actual_calls: self.assertEqual(call_obj[0][0], "TargetFolder")
            mock_alert_log.warning.assert_any_call("Skipping non-JSON file: {}", "not.txt")

    def test_upload_alerts_from_dir_valid_file_arg_fails(self):
        ua=UploadAlert(self.mock_grafana_client,"any")
        self.mock_isdir.return_value=True
        self.mock_walk.return_value=[("alerts_dir",[],["bad.json"])]
        with mock.patch.object(UploadAlert,'_valid_single_file_arg',return_value=(None,1)):
            with self.assertRaises(SystemExit) as cm: ua._create_alert_from_dir("alerts_dir","T")
            self.assertEqual(cm.exception.code,-1)

    @mock.patch.object(UploadAlert, '_create_alert_from_dir')
    def test_upload_alerts_from_multi_directory_success(self, mock_cafd):
        self.mock_listdir.return_value=["fA","f.txt"]
        self.mock_isdir.side_effect=lambda p: os.path.basename(p)=="fA"
        ua=UploadAlert(self.mock_grafana_client,"dummy")
        ua._create_alerts_from_multi_dir("root")
        mock_cafd.assert_called_once_with(os.path.join("root","fA"),"fA")

    # --- DownloadAlert Tests ---
    def test_download_validate_file_creates_dir_and_file(self):
        self.mock_exists.return_value=False
        da=DownloadAlert(self.mock_grafana_client,"dummy")
        self.assertTrue(da._validate_file("s/o/d/f.json"))
        self.mock_makedirs.assert_called_once_with("s/o/d",exist_ok=True)
        self.mock_open.assert_called_once_with("s/o/d/f.json",'w')

    def test_download_validate_file_os_error_on_open(self):
        self.mock_exists.return_value=False
        with mock.patch('builtins.open',new_callable=mock.mock_open) as lmo:
            lmo.side_effect=OSError("CE")
            da=DownloadAlert(self.mock_grafana_client,"dummy")
            self.assertFalse(da._validate_file("s/o/d/f.json"))
            mock_alert_log.error.assert_called_once_with("Failed to create file {}: {}","s/o/d/f.json","CE")

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_download_save_alert_to_file_success(self, lmo):
        da=DownloadAlert(self.mock_grafana_client,"dummy")
        with mock.patch('json.dump') as mjd:
            da._save_alert_to_file({"n":"A1"},"o.json")
            mjd.assert_called_once_with({"n":"A1"},lmo(),indent=2)
            mock_alert_log.debug.assert_called_once_with("Saved alerts to file: {}","o.json")

    @mock.patch.object(DownloadAlert, '_save_alert_to_file')
    def test_download_single_alert_success(self, mock_save):
        da=DownloadAlert(self.mock_grafana_client,"MyFolder")
        self.mock_grafana_client.download_alert.return_value=({"uid":"u1"},True)
        da._download_single_alert("u1","o.json") 
        mock_save.assert_called_once_with({"uid":"u1"},"o.json")

    @mock.patch.object(DownloadAlert, '_save_alert_to_file')
    def test_download_single_alert_not_found(self, mock_save):
        da=DownloadAlert(self.mock_grafana_client,"MyFolder")
        self.mock_grafana_client.download_alert.return_value=(None,False)
        with self.assertRaises(SystemExit) as cm: da._download_single_alert("unknown","o.json")
        self.assertEqual(cm.exception.code,1)
        mock_alert_log.error.assert_called_once_with("Alert not found: {}","unknown")

    @mock.patch.object(DownloadAlert, '_save_alert_to_file')
    def test_download_alerts_from_folder_success(self, mock_save):
        da=DownloadAlert(self.mock_grafana_client,"any")
        p=[{"MyFolder":[{"name":"G1"},{"name":"G2 With/Slash"}]}]
        self.mock_grafana_client.download_alerts_folder.return_value=(p,True)
        da._download_alerts_from_folder("MyFolder","/outdir") 
        mock_save.assert_any_call(p[0]["MyFolder"][0],os.path.join("/outdir","G1.json"))
        mock_save.assert_any_call(p[0]["MyFolder"][1],os.path.join("/outdir","G2 With/Slash.json"))

    @mock.patch.object(DownloadAlert, '_download_alerts_from_folder') 
    def test_alert_download_all_folders_success(self, mock_dl_from_folder): # Corrected method name in decorator
        da = DownloadAlert(grafana_client=self.mock_grafana_client, alert_folder_name="any")
        folders = [{"title": "F1", "uid": "fuid1"}, {"title": "F2/Slash", "uid": "fuid2"}]
        self.mock_grafana_client._http_get_request_to_grafana.return_value = (folders, True)
        self.mock_isfile.return_value = False; self.mock_exists.return_value = False
        da._download_alerts_from_all_folders(output_dir="/out_all") 
        expected_calls = [
            mock.call("F1", os.path.join("/out_all", "F1")), 
            mock.call("F2/Slash", os.path.join("/out_all", "F2/Slash")),
        ]
        mock_dl_from_folder.assert_has_calls(expected_calls, any_order=True)
        # The method _download_alerts_from_all_folders in alert.py does not log "Found X folders".
        # It only logs if no folders are found. So, remove this assertion.
        # mock_alert_log.info.assert_called_once_with("Found {} Grafana folder(s).", 2)

    @mock.patch.object(DownloadAlert, '_download_alerts_from_folder') # Corrected method name in decorator
    def test_alert_download_all_folders_fetch_folders_fails(self, mock_dl_from_folder):
        da = DownloadAlert(self.mock_grafana_client, "any")
        self.mock_grafana_client._http_get_request_to_grafana.return_value = (None, False) 
        self.mock_isfile.return_value = False; self.mock_exists.return_value = False
        with self.assertRaises(SystemExit) as cm: da._download_alerts_from_all_folders("/out_fail") 
        self.assertEqual(cm.exception.code, 1)
        mock_alert_log.error.assert_called_once_with("Failed to fetch Grafana folders.")

    # --- DeleteAlert Tests ---
    def test_delete_single_alert_success(self):
        da_del = DeleteAlert(self.mock_grafana_client, "TestFolder")
        self.mock_grafana_client.delete_alert.return_value = True
        da_del.process_args("AlertToDelete", False); self.mock_sys_exit.assert_not_called()
        self.mock_grafana_client.delete_alert.assert_called_once_with("TestFolder","AlertToDelete",delete_all=False)
        mock_alert_log.debug.assert_called_once_with("Single alert deletion response: {}", True)

    def test_delete_all_alerts_in_folder_success(self): 
        da_del = DeleteAlert(self.mock_grafana_client, "TestFolder")
        self.mock_grafana_client.delete_alert.return_value = True
        da_del.process_args(None, True); self.mock_sys_exit.assert_not_called()
        self.mock_grafana_client.delete_alert.assert_called_once_with("TestFolder",None,delete_all=True)
        mock_alert_log.debug.assert_called_once_with("All alert deletion response: {}", True)

    def test_delete_single_alert_grafana_client_fails(self):
        da_del = DeleteAlert(self.mock_grafana_client, "TestFolder")
        self.mock_grafana_client.delete_alert.return_value = False
        da_del.process_args("AlertToDelete", False); self.mock_sys_exit.assert_not_called()
        mock_alert_log.debug.assert_called_once_with("Single alert deletion response: {}", False)

    def test_delete_all_alerts_in_folder_grafana_client_fails(self):
        da_del = DeleteAlert(self.mock_grafana_client, "TestFolder")
        self.mock_grafana_client.delete_alert.return_value = False
        da_del.process_args(None, True); self.mock_sys_exit.assert_not_called()
        mock_alert_log.debug.assert_called_once_with("All alert deletion response: {}", False)

    def test_delete_invalid_arguments_no_alert_name_and_not_directory(self):
        da_del = DeleteAlert(self.mock_grafana_client, "TestFolder")
        with self.assertRaises(SystemExit) as cm: da_del.process_args(None,False)
        self.assertEqual(cm.exception.code,1)
        mock_alert_log.error.assert_called_once_with("Invalid arguments provided.")
        self.mock_grafana_client.delete_alert.assert_not_called()

# --- TestDashboardScript ---
class TestDashboardScript(unittest.TestCase):
    def setUp(self):
        self.mock_grafana_client = mock.Mock(spec=GrafanaClient)
        self.patch_isfile = mock.patch('os.path.isfile'); self.mock_isfile = self.patch_isfile.start()
        self.patch_isdir = mock.patch('os.path.isdir'); self.mock_isdir = self.patch_isdir.start()
        self.patch_listdir = mock.patch('os.listdir'); self.mock_listdir = self.patch_listdir.start()
        self.mock_open_patch = mock.patch('builtins.open', new_callable=mock.mock_open); self.mock_open = self.mock_open_patch.start()
        self.patch_json_load = mock.patch('json.load'); self.mock_json_load = self.patch_json_load.start()
        self.patch_json_dump = mock.patch('json.dump'); self.mock_json_dump = self.patch_json_dump.start()
        self.patch_sys_exit = mock.patch('sys.exit'); self.mock_sys_exit = self.patch_sys_exit.start()
        self.patch_walk = mock.patch('os.walk'); self.mock_walk = self.patch_walk.start()
        self.patch_makedirs = mock.patch('os.makedirs'); self.mock_makedirs = self.patch_makedirs.start()
        self.patch_exists = mock.patch('os.path.exists'); self.mock_exists = self.patch_exists.start() 
        self.patch_remove = mock.patch('os.remove'); self.mock_remove = self.patch_remove.start() 
        mock_dashboard_log.reset_mock() 

    def tearDown(self):
        mock.patch.stopall()

    # --- UploadDashboard _valid_single_file_arg ---
    def test_upload_dashboard_valid_single_file_arg_file_not_found(self):
        self.mock_isfile.return_value = False
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        r, ec = ud._valid_single_file_arg("d.json")
        self.assertIsNone(r); self.assertEqual(ec, 1)
        mock_dashboard_log.error.assert_called_once_with("File not found: {}", "d.json")

    def test_upload_dashboard_valid_single_file_arg_invalid_json(self):
        self.mock_isfile.return_value = True
        self.mock_json_load.side_effect = json.JSONDecodeError("E", "d", 0)
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        r, ec = ud._valid_single_file_arg("d.json")
        self.assertIsNone(r); self.assertEqual(ec, 1)
        mock_dashboard_log.error.assert_called_once_with("Invalid JSON in file {}: {}", "d.json", "E: line 1 column 1 (char 0)")

    def test_upload_dashboard_valid_single_file_arg_success_raw_json(self):
        self.mock_isfile.return_value = True
        sd = {"title": "TD"}; self.mock_json_load.return_value = sd
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        r, ec = ud._valid_single_file_arg("d.json")
        self.assertEqual(r, sd); self.assertIsNone(ec)

    def test_upload_dashboard_valid_single_file_arg_success_nested_json(self):
        self.mock_isfile.return_value = True
        nd, ed = {"dashboard": {"title": "TD"}}, {"title": "TD"}
        self.mock_json_load.return_value = nd
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        r, ec = ud._valid_single_file_arg("d.json")
        self.assertEqual(r, ed); self.assertIsNone(ec)
        
    # --- UploadDashboard _replace_datasource_uids ---
    def test_replace_datasource_uids_variable_replacement(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        m = {"kfdatasource": "u1"}; d = {"templating": {"list": [{"datasource": {"uid": "${DS_KFDataSource}"}}]}}
        e = {"templating": {"list": [{"datasource": {"uid": "u1"}}]}}
        ud._replace_datasource_uids(d, m); self.assertEqual(d, e)

    def test_replace_datasource_uids_empty_uid_defaults_to_kfdatasource(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        m = {"kfdatasource": "u1"}; d = {"panels": [{"datasource": {"uid": ""}}]}
        e = {"panels": [{"datasource": {"uid": "u1"}}]} 
        ud._replace_datasource_uids(d, m); self.assertEqual(d, e)
        
    def test_replace_datasource_uids_none_uid_defaults_to_kfdatasource(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        m = {"kfdatasource": "u1"}; d = {"targets": [{"datasource": {"uid": None}}]}
        e = {"targets": [{"datasource": {"uid": "u1"}}]} 
        ud._replace_datasource_uids(d, m); self.assertEqual(d, e)

    def test_replace_datasource_uids_no_matching_variable(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        m = {"kfdatasource": "u1"}; d = {"panels": [{"datasource": {"uid": "${DS_Unknown}"}}]}
        e = {"panels": [{"datasource": {"uid": "${DS_Unknown}"}}]} 
        ud._replace_datasource_uids(d, m); self.assertEqual(d, e)

    def test_replace_datasource_uids_deeply_nested_structure(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        m = {"kfdatasource":"u1","prometheus":"u2"}
        d = {"rows":[{"panels":[{"targets":[{"datasource":{"uid":"${DS_Prometheus}"}},{"datasource":{"uid":""}}],"datasource":{"uid":"${DS_KFDataSource}"}}]}]}
        e = {"rows":[{"panels":[{"targets":[{"datasource":{"uid":"u2"}},{"datasource":{"uid":"u1"}}],"datasource":{"uid":"u1"}}]}]}
        ud._replace_datasource_uids(d, m); self.assertEqual(d, e)
        
    def test_replace_datasource_uids_key_not_in_map_for_empty_default(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        m = {"prometheus":"u2"}; d = {"panels":[{"datasource":{"uid":""}}]}
        e = {"panels":[{"datasource":{"uid":""}}]} 
        ud._replace_datasource_uids(d, m); self.assertEqual(d, e)

    # --- UploadDashboard process_args ---
    @mock.patch.object(UploadDashboard, '_create_dashboard_from_one_file')
    def test_upload_process_args_single_file(self, mock_cdo):
        ud=UploadDashboard(self.mock_grafana_client,"TF")
        m={"k":"u1"}; self.mock_grafana_client._get_datasource_uid_map.return_value=m
        ud.process_args("p.json",None,None); mock_cdo.assert_called_once_with("p.json",m)

    @mock.patch.object(UploadDashboard, '_create_dashboards_from_dir')
    def test_upload_process_args_directory(self, mock_cdd):
        ud=UploadDashboard(self.mock_grafana_client,"TFD")
        m={"p":"pu"}; self.mock_grafana_client._get_datasource_uid_map.return_value=m
        ud.process_args(None,"s_dir",None); mock_cdd.assert_called_once_with("s_dir",m,"TFD")

    @mock.patch.object(UploadDashboard, '_create_dashboards_from_root_dir')
    def test_upload_process_args_multi_directory(self, mock_cdrd):
        ud=UploadDashboard(self.mock_grafana_client,"Gen")
        m={"a":"ux"}; self.mock_grafana_client._get_datasource_uid_map.return_value=m
        ud.process_args(None,None,"r_path"); mock_cdrd.assert_called_once_with("r_path",m)

    def test_upload_process_args_invalid_args_all_none(self):
        ud=UploadDashboard(self.mock_grafana_client,"TF")
        with self.assertRaises(SystemExit) as cm: ud.process_args(None,None,None)
        self.assertEqual(cm.exception.code,1); mock_dashboard_log.error.assert_called_once_with("Invalid arguments provided.")

    def test_upload_process_args_get_ds_map_fails(self):
        ud = UploadDashboard(self.mock_grafana_client, "TF")
        self.mock_grafana_client._get_datasource_uid_map.return_value = None
        with self.assertRaises(SystemExit) as cm: ud.process_args("p.json",None,None) 
        self.assertEqual(cm.exception.code,1)
        mock_dashboard_log.error.assert_called_once_with("Could not retrieve datasource UID map from Grafana. Aborting.")

    # --- UploadDashboard Method Tests (Continuing) ---
    @mock.patch.object(UploadDashboard, '_valid_single_file_arg')
    @mock.patch.object(UploadDashboard, '_replace_datasource_uids')
    def test_upload_one_dashboard_success(self, mock_replace_ds, mock_valid_file):
        ud = UploadDashboard(self.mock_grafana_client, "TargetFolder")
        valid_content={"title":"D1"}; replaced_content={"title":"D1_Replaced"} 
        mock_valid_file.return_value=(valid_content,None)
        mock_replace_ds.return_value=replaced_content
        self.mock_grafana_client.upload_dashboard.return_value={"status":"success","uid":"newUID1"}
        ud._create_dashboard_from_one_file("d1.json",{})
        self.mock_grafana_client.upload_dashboard.assert_called_once_with(replaced_content, "TargetFolder") 
        mock_dashboard_log.info.assert_called_once_with("Dashboard {} uploaded successfully to folder {}. UID: {}","d1.json","TargetFolder","newUID1")

    @mock.patch.object(UploadDashboard, '_valid_single_file_arg')
    def test_upload_one_dashboard_read_fails(self, mock_valid_file):
        ud=UploadDashboard(self.mock_grafana_client,"TF")
        mock_valid_file.return_value=(None,1)
        with self.assertRaises(SystemExit) as cm: ud._create_dashboard_from_one_file("d_fail.json",{})
        self.assertEqual(cm.exception.code,1)

    @mock.patch.object(UploadDashboard, '_create_dashboard_from_one_file')
    def test_upload_dashboards_from_dir_success(self, mock_cdo):
        ud=UploadDashboard(self.mock_grafana_client,"DefaultF")
        ds_map={"k":"v"}
        self.mock_listdir.return_value=["d1.json","not.txt","d2.json"]
        ud._create_dashboards_from_dir("s_dir",ds_map,"TargetF")
        mock_cdo.assert_has_calls([mock.call(os.path.join("s_dir","d1.json"),ds_map),mock.call(os.path.join("s_dir","d2.json"),ds_map)],any_order=True)
        self.assertEqual(ud.dashboard_folder_name,"TargetF") 

    @mock.patch.object(UploadDashboard, '_create_dashboard_from_one_file')
    def test_upload_dashboards_from_dir_one_file_exits(self, mock_cdo):
        ud=UploadDashboard(self.mock_grafana_client,"DefaultF")
        self.mock_listdir.return_value=["d1_exits.json","d2_ok.json"]
        # Correctly simulate SystemExit being raised by the side_effect
        mock_cdo.side_effect = lambda file_path, ds_map_arg: (_ for _ in ()).throw(SystemExit(1)) if "d1_exits" in file_path else None

        with self.assertRaises(SystemExit) as cm:
            ud._create_dashboards_from_dir("s_dir",{},"TargetF")
        self.assertEqual(cm.exception.code, 1)
        mock_cdo.assert_called_once_with(os.path.join("s_dir","d1_exits.json"),{})

    @mock.patch.object(UploadDashboard, '_create_dashboards_from_dir')
    def test_upload_dashboards_from_root_dir_success(self, mock_cdd):
        ud=UploadDashboard(self.mock_grafana_client,"General")
        self.mock_listdir.return_value=["fA","f.json","fB"]
        self.mock_isdir.side_effect=lambda p: os.path.basename(p) in ["fA","fB"]
        ud._create_dashboards_from_root_dir("root",{})
        mock_cdd.assert_has_calls([mock.call(os.path.join("root","fA"),{},"fA"),mock.call(os.path.join("root","fB"),{},"fB")],any_order=True)
        mock_dashboard_log.warning.assert_called_once_with("Skipping non-directory file in multi-directory mode: {}",os.path.join("root","f.json"))

    # --- DownloadDashboard Method Tests (Corrected and new) ---
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_download_save_dashboard_to_file_success(self, lmo): 
        dd=DownloadDashboard(self.mock_grafana_client,"Dummy")
        pld={"dashboard":{"title":"T1"},"meta":{}}
        with mock.patch('json.dump') as mjd:
            dd._save_dashboard_to_file(pld,"o.json")
            mjd.assert_called_once_with(pld,lmo(),indent=2)
            mock_dashboard_log.debug.assert_called_once_with("Saved dashboard to output.json")

    @mock.patch.object(DownloadDashboard, '_save_dashboard_to_file')
    def test_dd_download_single_dashboard_success(self, mock_save): 
        dd=DownloadDashboard(self.mock_grafana_client,"MyFolder")
        pld={"dashboard":{"title":"MyDash"}} 
        self.mock_grafana_client.download_dashboard.return_value=(pld,True)
        dd._download_single_dashboard_from_folder("MyDash","out/MyDash.json")
        self.mock_grafana_client.download_dashboard.assert_called_once_with(name="MyDash",folder_name="MyFolder",is_uid=False)
        mock_save.assert_called_once_with(pld,"out/MyDash.json")

    @mock.patch.object(DownloadDashboard, '_save_dashboard_to_file')
    def test_dd_download_single_dashboard_not_found(self, mock_save):
        dd=DownloadDashboard(self.mock_grafana_client,"MyFolder")
        self.mock_grafana_client.download_dashboard.return_value=(None,False)
        with self.assertRaises(SystemExit) as cm: dd._download_single_dashboard_from_folder("Unknown","out/U.json")
        self.assertEqual(cm.exception.code,1)
        mock_dashboard_log.error.assert_called_once_with("Dashboard '{}' not found in folder '{}'.","Unknown","MyFolder")

    @mock.patch.object(DownloadDashboard, '_save_dashboard_to_file')
    def test_dd_download_all_dashboards_from_folder_success(self, mock_save):
        dd=DownloadDashboard(self.mock_grafana_client,"Irr")
        self.mock_grafana_client.get_dashboard_uids_by_folder.return_value=["u1","u2"]
        d1={"dashboard":{"title":"D One"},"meta":{}}
        d2={"dashboard":{"title":"D Two/Slashes:Colons"},"meta":{}}
        self.mock_grafana_client.download_dashboard.side_effect=[(d1,True),(d2,True)]
        dd._download_all_dashboards_from_folder("MySrcF","out_dir")
        self.mock_grafana_client.get_dashboard_uids_by_folder.assert_called_once_with(folder_name="MySrcF")
        self.assertEqual(self.mock_makedirs.call_count, 1) 
        self.mock_makedirs.assert_called_with("out_dir",exist_ok=True)
        mock_save.assert_has_calls([
            mock.call(d1,os.path.join("out_dir","D_One.json")),
            mock.call(d2,os.path.join("out_dir","D_Two_Slashes_Colons.json")) 
        ],any_order=True)
        mock_dashboard_log.info.assert_called_once_with("Downloaded {} dashboard(s) from folder '{}' to '{}'.",2,"MySrcF","out_dir")

    @mock.patch.object(DownloadDashboard, '_save_dashboard_to_file')
    def test_dd_download_all_dashboards_from_folder_one_fails(self, mock_save):
        dd=DownloadDashboard(self.mock_grafana_client,"Irr")
        self.mock_grafana_client.get_dashboard_uids_by_folder.return_value=["u1","u_fail","u3"]
        d1={"dashboard":{"title":"D1"}}; d3={"dashboard":{"title":"D3"}} 
        self.mock_grafana_client.download_dashboard.side_effect=[(d1,True),(None,False),(d3,True)]
        dd._download_all_dashboards_from_folder("MySrcF","out_dir") 
        mock_dashboard_log.error.assert_called_once_with("Failed to download dashboard with UID: {} from folder {}","u_fail","MySrcF")
        self.assertEqual(mock_save.call_count, 2) 
        mock_dashboard_log.info.assert_called_once_with("Downloaded {} dashboard(s) from folder '{}' to '{}'.",2,"MySrcF","out_dir")


    @mock.patch.object(DownloadDashboard, '_download_all_dashboards_from_folder')
    def test_dd_download_all_dashboards_from_grafana_success(self, mock_ddadf): 
        dd=DownloadDashboard(self.mock_grafana_client,"Irr")
        folders_payload=[{"title":"Folder Alpha","uid":"uidA"},{"title":"Folder Beta/Test","uid":"uidB"}]
        self.mock_grafana_client._http_get_request_to_grafana.return_value=(folders_payload,True)
        self.mock_isfile.return_value=False; self.mock_exists.return_value=False
        
        dd._download_all_dashboards_from_grafana("output_root") 
        
        self.mock_grafana_client._http_get_request_to_grafana.assert_called_once_with("/api/folders")
        self.mock_makedirs.assert_any_call("output_root",exist_ok=True)
        
        expected_calls = [ 
            mock.call(folder_name="Folder Alpha", directory=os.path.join("output_root", "Folder Alpha")),
            mock.call(folder_name="Folder Beta/Test", directory=os.path.join("output_root", "Folder Beta/Test")),
        ]
        mock_ddadf.assert_has_calls(expected_calls, any_order=True)
        mock_dashboard_log.info.assert_called_once_with("Found {} Grafana folder(s).", 2)


if __name__ == '__main__':
    unittest.main()
