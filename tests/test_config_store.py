import json

from nightshift.config import store


def test_default_config_has_schema_and_known_fields():
    cfg = store.default_config()
    assert cfg["schema_version"] == store.SCHEMA_VERSION
    assert cfg["mode"] == "day"
    assert cfg["per_monitor_enabled"] is False
    assert cfg["extended_range"] is False
    assert cfg["global"] == {"day_k": store.DEFAULT_DAY_K,
                              "night_k": store.DEFAULT_NIGHT_K,
                              "single_k": store.DEFAULT_SINGLE_K}
    assert cfg["location"] == {"lat": store.DEFAULT_LAT, "lon": store.DEFAULT_LON}
    assert isinstance(cfg["presets"], list) and len(cfg["presets"]) == 4


def test_load_returns_default_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "config_path", lambda: tmp_path / "x.json")
    assert store.load() == store.default_config()


def test_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)

    cfg = store.default_config()
    cfg["global"]["night_k"] = 2700
    cfg["monitors"]["\\\\.\\DISPLAY1"] = {"day_k": 6000, "night_k": 3000,
                                           "single_k": 4000}
    cfg["extended_range"] = True
    cfg["mode"] = "single"
    store.save(cfg)

    assert path.exists()
    assert store.load() == cfg


def test_partial_config_is_merged_with_defaults(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    path.write_text(json.dumps({
        "schema_version": 1,
        "global": {"night_k": 2900},   # day_k missing
        "extended_range": True,
    }), encoding="utf-8")

    cfg = store.load()
    assert cfg["global"]["night_k"] == 2900
    assert cfg["global"]["day_k"] == store.DEFAULT_DAY_K
    assert cfg["global"]["single_k"] == store.DEFAULT_SINGLE_K  # v2 default backfilled
    assert cfg["extended_range"] is True
    assert cfg["per_monitor_enabled"] is False
    assert cfg["location"]["lat"] == store.DEFAULT_LAT
    assert cfg["schedule"]["night_start"] == "21:00"
    # v1 → v2 auto-migration:
    assert cfg["schema_version"] == 2
    assert cfg["mode"] == "day"
    assert len(cfg["presets"]) == 4


def test_unknown_keys_are_preserved(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    path.write_text(json.dumps({"future_feature": {"k": "v"}}), encoding="utf-8")
    cfg = store.load()
    assert cfg["future_feature"] == {"k": "v"}


def test_schema_version_preserved_on_save(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    store.save(store.default_config())
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == store.SCHEMA_VERSION


def test_corrupt_json_falls_back_to_defaults(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    path.write_text("{not json", encoding="utf-8")
    assert store.load() == store.default_config()


def test_ensure_monitor_entries_adds_missing_and_reports_change():
    cfg = store.default_config()
    cfg["global"]["day_k"] = 6400
    cfg["global"]["night_k"] = 3200
    cfg["global"]["single_k"] = 4100

    changed = store.ensure_monitor_entries(cfg, ["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"])
    assert changed is True
    assert cfg["monitors"]["\\\\.\\DISPLAY1"] == {"day_k": 6400, "night_k": 3200,
                                                    "single_k": 4100}
    assert cfg["monitors"]["\\\\.\\DISPLAY2"] == {"day_k": 6400, "night_k": 3200,
                                                    "single_k": 4100}

    assert store.ensure_monitor_entries(cfg, ["\\\\.\\DISPLAY1"]) is False


def test_config_path_uses_appdata_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert store.config_path() == tmp_path / "nightshift" / "config.json"


def test_config_path_falls_back_to_home_when_appdata_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
    assert store.config_path() == tmp_path / ".nightshift" / "config.json"


def test_builtin_presets_have_name_and_default_k():
    presets = store._builtin_presets()
    assert len(presets) == 4
    names = [p["name"] for p in presets]
    assert "주광 (6500K)" in names
    assert "촛불 (1900K)" in names
    for p in presets:
        assert isinstance(p["default_k"], int)
        assert p["kelvins"] == {}


def test_v1_monitor_entry_gets_single_k_backfilled(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    path.write_text(json.dumps({
        "schema_version": 1,
        "monitors": {
            "\\\\.\\DISPLAY1": {"day_k": 6000, "night_k": 2900},
        },
    }), encoding="utf-8")

    cfg = store.load()
    entry = cfg["monitors"]["\\\\.\\DISPLAY1"]
    assert entry["day_k"] == 6000
    assert entry["night_k"] == 2900
    assert entry["single_k"] == store.DEFAULT_SINGLE_K   # backfilled
    assert cfg["schema_version"] == 2


def test_v2_config_is_not_re_migrated(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    cfg_in = store.default_config()
    cfg_in["presets"] = [{"name": "X", "default_k": 5000, "kelvins": {}}]
    store.save(cfg_in)

    cfg_out = store.load()
    # presets stay as-is (no re-seed)
    assert cfg_out["presets"] == [{"name": "X", "default_k": 5000, "kelvins": {}}]
    assert cfg_out["schema_version"] == 2


def test_user_preset_round_trips(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(store, "config_path", lambda: path)
    cfg = store.default_config()
    cfg["presets"].append({
        "name": "내 작업용",
        "default_k": None,
        "kelvins": {"\\\\.\\DISPLAY1": 5500, "\\\\.\\DISPLAY2": 6000},
    })
    store.save(cfg)

    cfg2 = store.load()
    custom = next(p for p in cfg2["presets"] if p["name"] == "내 작업용")
    assert custom["kelvins"] == {"\\\\.\\DISPLAY1": 5500, "\\\\.\\DISPLAY2": 6000}
