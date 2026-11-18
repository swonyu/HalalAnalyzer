"""Pure real-file union fixtures; payloads are synthetic, never native evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("new_current_r11_original_union", HERE / "current_original_union.py")
UNION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UNION)


class CurrentOriginalUnionBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(strict=True)
        self.inputs = self.root / "Originals"; self.inputs.mkdir()
        self.destination = self.root / "DerivedCompleteUnion"

    def original_rows(self, first_count):
        folders, manifests = {}, {}
        for case in UNION.CASE_ORDER:
            folder = self.inputs / case; folder.mkdir(); folders[case] = folder
            entries = []
            count = first_count if case == UNION.CASE_ORDER[0] else 1
            for index in range(count):
                suffix = ".unknown-opaque-format" if index == count - 1 else ".raw"
                name = f"{case}-original-{index:04d}{suffix}"
                data = b"SYNTHETIC FILE FIXTURE\x00\xff\x01" + case.encode() + str(index).encode()
                path = folder / name; path.write_bytes(data); path.chmod(0o640 if index % 2 else 0o644)
                entries.append({"exportedFileName": name, "suggestedHumanReadableName": name,
                                "isAssociatedWithFailure": False, "fixture_only": True})
            manifest = [{"testIdentifier": "SyntheticOriginalFixture/" + case,
                         "testIdentifierURL": "test://synthetic-file-fixture/" + case,
                         "attachments": entries}]
            (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            manifests[case] = manifest
        return folders, manifests

    def snapshot(self):
        result = {}
        for path in sorted(self.inputs.rglob("*")):
            name = path.relative_to(self.inputs).as_posix()
            if path.is_dir():
                result[name] = {"type": "directory", "mode": stat.S_IMODE(path.stat().st_mode)}
            else:
                raw = path.read_bytes()
                result[name] = {"type": "file", "mode": stat.S_IMODE(path.stat().st_mode),
                                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        return result

    def assert_complete_copy(self, folders, manifests, result, before):
        self.assertEqual(before, self.snapshot())
        self.assertEqual([row["case_id"] for row in result["cases"]], list(UNION.CASE_ORDER))
        expected_rows, expected_names = [], {"manifest.json"}
        total = 0
        for case in UNION.CASE_ORDER:
            expected_rows.extend(manifests[case])
            binding = next(row for row in result["cases"] if row["case_id"] == case)
            self.assertEqual(binding["original_manifest_sha256"], hashlib.sha256((folders[case] / "manifest.json").read_bytes()).hexdigest())
            self.assertEqual(len(binding["files"]), len(manifests[case][0]["attachments"]))
            for entry in manifests[case][0]["attachments"]:
                name = entry["exportedFileName"]; expected_names.add(name)
                original, copied = folders[case] / name, self.destination / name
                self.assertEqual(copied.read_bytes(), original.read_bytes())
                self.assertEqual(stat.S_IMODE(copied.stat().st_mode), stat.S_IMODE(original.stat().st_mode))
                total += original.stat().st_size
        self.assertEqual({path.name for path in self.destination.iterdir()}, expected_names)
        self.assertEqual(json.loads((self.destination / "manifest.json").read_bytes()), expected_rows)
        self.assertEqual(result["total_attachment_bytes"], total)
        self.assertFalse(result["original_results_replaced"])
        self.assertFalse(result["image_transformations"])

    def test_601_real_original_files_and_unknown_payload_are_all_copied_unchanged(self):
        folders, manifests = self.original_rows(601); before = self.snapshot()
        result = UNION.combine_original_attachments(folders, self.destination, attachment_limit=2944)
        self.assert_complete_copy(folders, manifests, result, before)
        self.assertEqual(len(result["cases"][0]["files"]), 601)
        unknown = "dark-large-original-0600.unknown-opaque-format"
        self.assertEqual((self.destination / unknown).read_bytes(), (folders["dark-large"] / unknown).read_bytes())

    def test_exact_2944_real_original_file_row_is_retained_completely(self):
        folders, manifests = self.original_rows(2944); before = self.snapshot()
        result = UNION.combine_original_attachments(folders, self.destination, attachment_limit=2944)
        self.assert_complete_copy(folders, manifests, result, before)
        self.assertEqual(len(result["cases"][0]["files"]), 2944)
        self.assertEqual(len(list(self.destination.iterdir())), 2947)

    def test_2945_actual_original_files_are_rejected_without_changing_sources(self):
        folders, _ = self.original_rows(2945); before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Unbounded attachment row"):
            UNION.combine_original_attachments(folders, self.destination, attachment_limit=2944)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(self.destination.is_dir())
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_other_requested_limits_fail_before_destination_creation_and_leave_sources_unchanged(self):
        folders, _ = self.original_rows(1); before = self.snapshot()
        for value in (600, 2943, 2945, 0, -1, True, 2944.0, "2944", None):
            with self.subTest(limit=value), self.assertRaisesRegex(ValueError, "exact current R11 attachment limit"):
                UNION.combine_original_attachments(folders, self.destination, attachment_limit=value)
            self.assertFalse(self.destination.exists())
            self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main(verbosity=2)
