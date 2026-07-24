import json

from config.settings import ConfigManager


def test_config_merges_user_values_with_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(ConfigManager, "_get_config_dir", staticmethod(lambda: tmp_path))
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"ui": {"window_width": 1440}}), encoding="utf-8")

    manager = ConfigManager()

    assert manager.get("ui.window_width") == 1440
    assert manager.get("ui.window_height") is not None
    assert manager.get("download.parallel_workers") == 2


def test_corrupt_config_is_backed_up(monkeypatch, tmp_path):
    monkeypatch.setattr(ConfigManager, "_get_config_dir", staticmethod(lambda: tmp_path))
    config_file = tmp_path / "config.json"
    config_file.write_text("{broken json", encoding="utf-8")

    manager = ConfigManager()

    assert manager.get("ui.window_width") is not None
    assert (tmp_path / "config.json.bak").exists()
