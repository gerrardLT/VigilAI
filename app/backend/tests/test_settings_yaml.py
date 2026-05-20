"""
测试 settings.py 中的 YAML 加载和重复键检测功能。
Validates: Requirements 10.2, 10.3, 10.4, 10.5
"""

import os
import tempfile

import pytest

from settings import DuplicateKeyError, Settings, _check_duplicate_keys


@pytest.fixture
def valid_yaml_file(tmp_path):
    """创建一个有效的 sources.yaml 文件。"""
    content = """
sources:
  devpost:
    name: "Devpost"
    type: firecrawl
    url: "https://devpost.com/hackathons"
    priority: high
    enabled: true
    category: hackathon
    description: "全球黑客松聚合平台"
  kaggle:
    name: "Kaggle"
    type: kaggle
    url: "https://www.kaggle.com/competitions"
    priority: medium
    enabled: true
    category: data_competition
    description: "数据科学竞赛平台"
"""
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return str(yaml_path)


@pytest.fixture
def duplicate_key_yaml_file(tmp_path):
    """创建一个包含重复键的 YAML 文件。"""
    content = """
sources:
  devpost:
    name: "Devpost"
    type: firecrawl
    url: "https://devpost.com/hackathons"
    priority: high
    enabled: true
    category: hackathon
    description: "全球黑客松聚合平台"
  devpost:
    name: "Devpost Duplicate"
    type: firecrawl
    url: "https://devpost.com/hackathons"
    priority: low
    enabled: false
    category: hackathon
    description: "重复的 devpost 条目"
"""
    yaml_path = tmp_path / "sources_dup.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return str(yaml_path)


@pytest.fixture
def malformed_yaml_file(tmp_path):
    """创建一个格式错误的 YAML 文件。"""
    content = """
sources:
  devpost:
    name: "Devpost"
    type: firecrawl
    url: [invalid yaml
    this is broken
"""
    yaml_path = tmp_path / "sources_bad.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return str(yaml_path)


@pytest.fixture
def missing_sources_key_yaml(tmp_path):
    """创建一个缺少 'sources' 键的 YAML 文件。"""
    content = """
config:
  version: 1
  name: "test"
"""
    yaml_path = tmp_path / "sources_no_key.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return str(yaml_path)


class TestSourcesConfigLoading:
    """测试 sources_config cached_property 的正常加载。"""

    def test_loads_valid_yaml(self, valid_yaml_file, monkeypatch):
        """有效 YAML 文件应正确加载并返回 sources 字典。"""
        monkeypatch.setenv("SOURCES_CONFIG_PATH", valid_yaml_file)
        s = Settings(sources_config_path=valid_yaml_file)
        config = s.sources_config
        assert isinstance(config, dict)
        assert "devpost" in config
        assert "kaggle" in config
        assert config["devpost"]["name"] == "Devpost"
        assert config["kaggle"]["priority"] == "medium"

    def test_loads_real_sources_yaml(self):
        """测试加载项目中实际的 sources.yaml 文件。"""
        real_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources.yaml")
        if not os.path.exists(real_path):
            pytest.skip("sources.yaml not found in project")
        s = Settings(sources_config_path=real_path)
        config = s.sources_config
        assert isinstance(config, dict)
        assert len(config) > 0


class TestDuplicateKeyDetection:
    """测试重复键检测功能。"""

    def test_raises_on_duplicate_keys(self, duplicate_key_yaml_file):
        """包含重复键的 YAML 应抛出 ValueError (DuplicateKeyError)。"""
        s = Settings(sources_config_path=duplicate_key_yaml_file)
        with pytest.raises(DuplicateKeyError, match="Duplicate key in sources config: 'devpost'"):
            _ = s.sources_config

    def test_duplicate_key_error_is_value_error(self):
        """DuplicateKeyError 应该是 ValueError 的子类。"""
        assert issubclass(DuplicateKeyError, ValueError)


class TestErrorHandling:
    """测试各种错误场景。"""

    def test_raises_on_file_not_found(self, tmp_path):
        """文件不存在时应抛出 ValueError。"""
        nonexistent = str(tmp_path / "nonexistent.yaml")
        s = Settings(sources_config_path=nonexistent)
        with pytest.raises(ValueError, match="Sources config file not found"):
            _ = s.sources_config

    def test_raises_on_malformed_yaml(self, malformed_yaml_file):
        """格式错误的 YAML 应抛出 ValueError。"""
        s = Settings(sources_config_path=malformed_yaml_file)
        with pytest.raises(ValueError, match="Malformed sources config"):
            _ = s.sources_config

    def test_raises_on_missing_sources_key(self, missing_sources_key_yaml):
        """缺少 'sources' 键时应抛出 ValueError。"""
        s = Settings(sources_config_path=missing_sources_key_yaml)
        with pytest.raises(ValueError, match="Sources config must contain a 'sources' key"):
            _ = s.sources_config

    def test_raises_on_empty_file(self, tmp_path):
        """空文件应抛出 ValueError。"""
        empty_path = tmp_path / "empty.yaml"
        empty_path.write_text("", encoding="utf-8")
        s = Settings(sources_config_path=str(empty_path))
        with pytest.raises(ValueError, match="Sources config must contain a 'sources' key"):
            _ = s.sources_config


class TestCachedProperty:
    """测试 cached_property 行为。"""

    def test_sources_config_is_cached(self, valid_yaml_file):
        """sources_config 应该被缓存，多次访问返回同一对象。"""
        s = Settings(sources_config_path=valid_yaml_file)
        config1 = s.sources_config
        config2 = s.sources_config
        assert config1 is config2
