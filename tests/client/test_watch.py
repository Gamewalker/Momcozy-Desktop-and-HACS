import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"client"))

class WatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["MOMCOZY_DATA_DIR"] = cls.temp.name
        cls.watch = importlib.import_module("watch")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        for path in Path(self.temp.name).glob("*.json"):
            path.unlink()

    def write_config(self,index,port=18554):
        path=Path(self.temp.name)/f"bridge-{index}.private.json"
        path.write_text(json.dumps({"port":str(port),"camera-name":f"bm04_{index}"}))
        return path

    def test_no_configuration(self):
        with self.assertRaises(ValueError):
            self.watch.camera_configs()

    def test_duplicate_ports_rejected(self):
        self.write_config(1)
        self.write_config(2)
        with self.assertRaises(ValueError):
            self.watch.camera_configs()

    def test_manifest_excludes_stale_configuration(self):
        self.write_config(1)
        self.write_config(2)
        (Path(self.temp.name)/"cameras.private.json").write_text('["bridge-1.private.json"]')
        self.assertEqual(len(self.watch.camera_configs()),1)

    def test_manifest_cannot_escape_state_directory(self):
        (Path(self.temp.name)/"cameras.private.json").write_text('["../outside.json"]')
        with self.assertRaises(ValueError):
            self.watch.camera_configs()

    def test_invalid_port_rejected(self):
        self.write_config(1,80)
        with self.assertRaises(ValueError):
            self.watch.camera_configs()

if __name__=="__main__":
    unittest.main()
