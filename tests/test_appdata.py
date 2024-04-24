from gitramble.app_data import APP_DATA_DIR, AppData


def test_appdata_created(tmp_path):
    app_data = AppData(tmp_path, "https://bogusoft.com/")
    assert app_data
    data_path = tmp_path / APP_DATA_DIR
    assert data_path.exists()
