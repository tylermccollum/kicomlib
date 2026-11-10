"""Embedded models must survive the normal upload/download sync path."""

from unittest.mock import MagicMock

import pytest

from KiComLibClient.Canonical import canonicalFootprintText, sha256Text
from KiComLibClient.MetaFile import emptyMeta, load as loadMeta, save as saveMeta
from KiComLibClient.Misc import ActionType, getSymbolValue
from KiComLibClient.SyncFootprints import SyncFootprints
from KiComLibClient.sexpdata import loads


# Zstandard/base64 of a synthetic ISO-10303-21 document, with its SHA-256.
# The model is test data, not a third-party STEP file.
PAYLOAD = (
    "KLUv/SBqvQIAIgUTF4DpAcDHw10Crk+OmD/8qtRzQ4SMOmcEy+fDC/10fOvzTyvU2qFA"
    "IYwoSZMPgMF5wQhKaVJ5C1mjfTeekMLp+g5/ON3ceuyxtqiVAQIAX5DkBDzN"
)
CHECKSUM = "082a3ba4b2ec89ca4aa4814a96152ea19c1d1dee8f147474c3828cc124c76834"
EMBEDDED_PATH = "kicad-embed://fixture.step"


def footprint(mixed=False):
    before = '(model "${LOCAL_3DMODEL_DIR}/Models/first.step")' if mixed else ""
    after = '(model "${LOCAL_3DMODEL_DIR}/Models/last.wrl" (rotate (xyz 0 0 90)))' if mixed else ""
    return f'''(footprint "Embedded"
      (version 20260206) (generator "pcbnew") (layer "F.Cu") (attr smd)
      {before}
      (model "{EMBEDDED_PATH}"
        (offset (xyz 1 2 3)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 45)))
      {after}
      (embedded_files (file (name "fixture.step") (type model)
        (data |\n{PAYLOAD[:76]}\n{PAYLOAD[76:]}\n|) (checksum "{CHECKSUM}"))))
    '''


def model_paths(parsed):
    return [model[1] for model in getSymbolValue(parsed, "model")]


def plan(action, **details):
    return {
        "lib_dirs": [{"id": 1, "filename": "TestLib"}],
        "lib_dir_sync_actions": {
            "TestLib": [{"type": action, "file": "Embedded", **details}],
        },
    }


def test_canonicalization_preserves_embedded_reference_payload_and_placement():
    original = loads(footprint())
    canonical = canonicalFootprintText(original)
    captured = loads(canonical)

    assert model_paths(captured) == [EMBEDDED_PATH]
    assert getSymbolValue(captured, "embedded_files") == getSymbolValue(original, "embedded_files")
    assert getSymbolValue(captured, "model") == getSymbolValue(original, "model")
    assert canonicalFootprintText(captured) == canonical
    assert "${PLACEHOLDER}" not in canonical


@pytest.mark.parametrize("mixed", [False, True])
def test_sync_roundtrip_keeps_embedded_data_and_external_source_positions(tmp_path, monkeypatch, capsys, mixed):
    config = {
        "output_path": str(tmp_path),
        "api_url": "http://unused.invalid/api",
        "api_user_token": "",
        "path_key": "TEST",
    }
    saveMeta(tmp_path, emptyMeta())
    file = tmp_path / "Footprints" / "TestLib.pretty" / "Embedded.kicad_mod"
    file.parent.mkdir(parents=True)
    source = footprint(mixed)
    file.write_text(source, encoding="utf-8")
    sync = SyncFootprints(config)
    sync._api = MagicMock()

    # No preview process or server is needed to exercise the sync serialization.
    monkeypatch.setattr(sync, "_SyncFootprints__getPreviewImage", lambda *args: "")
    lookup = MagicMock(side_effect=lambda meta, directory, filename: {
        ("Models", "first.step"): "11111111-1111-1111-1111-111111111111",
        ("Models", "last.wrl"): "22222222-2222-2222-2222-222222222222",
    }[(directory, filename)])
    monkeypatch.setattr(sync, "_resolveModel3dUuid", lookup)

    [upload] = sync.sync(plan(ActionType.Upload), MagicMock())
    uploaded = next(blob["bytes"].decode("utf-8") for blob in upload.blobs
                    if blob["hash"] == upload.change["blobHash"])
    expected_paths = [EMBEDDED_PATH]
    if mixed:
        expected_paths = ["${PLACEHOLDER}/Models/first.step", EMBEDDED_PATH, "${PLACEHOLDER}/Models/last.wrl"]
    assert model_paths(loads(uploaded)) == expected_paths
    assert getSymbolValue(loads(uploaded), "embedded_files") == getSymbolValue(loads(source), "embedded_files")
    assert upload.change["blobHash"] == sha256Text(uploaded)
    assert [model["position"] for model in upload.change["models"]] == ([0, 2] if mixed else [])
    assert lookup.call_count == (2 if mixed else 0)
    assert "unknown 3D model" not in capsys.readouterr().out
    if mixed:
        assert upload.change["models"][1]["rotate"] == [0.0, 0.0, 90.0]

    # Simulate the server returning the uploaded blob and external associations.
    sync._api.get.return_value = {
        "data": uploaded,
        "models": [{"position": model["position"], "directory": "Models", "filename": filename}
                   for model, filename in zip(upload.change["models"], ["first.step", "last.wrl"])],
    }
    file.unlink()
    assert sync.sync(plan(ActionType.Download, id=1, uuid="footprint-id",
                          file_hash=upload.change["blobHash"], revision_id=1), MagicMock()) == []
    downloaded = file.read_text(encoding="utf-8")
    expected_paths = (["${TEST_3DMODEL_DIR}/Models/first.step", EMBEDDED_PATH,
                       "${TEST_3DMODEL_DIR}/Models/last.wrl"] if mixed else [EMBEDDED_PATH])
    assert model_paths(loads(downloaded)) == expected_paths
    assert canonicalFootprintText(loads(downloaded)) == uploaded
    saved = loadMeta(tmp_path)["footprints"]["TestLib"]["footprint-id"]
    assert saved["content_hash"] == saved["hash"] == upload.change["blobHash"]
