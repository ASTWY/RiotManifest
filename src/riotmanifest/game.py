# -*- coding: utf-8 -*-
# @Author  : Virace
# @Email   : Virace@aliyun.com
# @Site    : x-item.com
# @Software: Pycharm
# @Create  : 2024/9/5 12:02
# @Update  : 2024/9/5 13:39
# @Detail  : RiotGameData

from dataclasses import dataclass
from typing import List, Optional, Dict
from loguru import logger
import requests


@dataclass
class Release:
    """
    表示 GAME 每个版本的配置信息。

    :param version: 版本号
    :param url: 补丁下载地址
    """

    version: str
    url: str

    @staticmethod
    def from_json(release_json: dict) -> Optional["Release"]:
        """
        从 JSON 数据创建 Release 对象。

        :param release_json: JSON 格式的发布数据
        :return: Release 对象
        """
        try:
            labels = release_json["release"]["labels"]
            kind = labels["riot:artifact_type_id"]["values"][0]
            platform = labels["platform"]["values"]
            version = labels["riot:artifact_version_id"]["values"][0].split("+")[0]
            url = release_json["download"]["url"]

            if kind == "lol-game-client" and "windows" in platform:
                return Release(version=version, url=url)
        except KeyError:
            logger.error(f"解析 Release 数据失败: {release_json}")
            return None


@dataclass
class Configuration:
    """
    表示 LCU 每个区域的配置信息。

    :param id: 区域 ID
    :param version: 版本号
    :param patch_url: 补丁下载地址
    """

    id: str
    version: str
    patch_url: str

    @staticmethod
    def from_json(config_json: dict) -> "Configuration":
        """
        从 JSON 数据创建 LCU Configuration 对象。

        :param config_json: JSON 格式的配置数据
        :return: Configuration 对象
        """
        version = config_json["metadata"]["theme_manifest"].split("/")[-3]
        return Configuration(id=config_json["id"], version=version, patch_url=config_json["patch_url"])


class LCUData:
    """
    LCU 数据管理类，支持通过区域访问 LCU 配置信息。
    """

    def __init__(self):
        self.configurations: Dict[str, Configuration] = {}

    def load_data(self, url: str):
        """
        加载 LCU 数据。
        """
        logger.debug("正在加载 LCU 数据...")
        lcu_data = requests.get(url).json()
        for name, patchline in lcu_data.items():
            for config_json in patchline["platforms"]["win"]["configurations"]:
                config = Configuration.from_json(config_json)
                self.configurations[config.id] = config
        logger.debug("LCU 数据加载完成")

    def __getattr__(self, region: str) -> Optional[Configuration]:
        """
        支持通过点号访问 LCU 数据，例如 riot_game_data.lcu.euw。
        """
        if region in self.configurations:
            return self.configurations[region]
        raise AttributeError(f"未找到区域 {region} 的配置")

    def available_regions(self) -> List[str]:
        """
        返回当前可用的 LCU 区域列表。
        """
        return list(self.configurations.keys())


class GameData:
    """
    GAME 数据管理类，支持通过区域访问 GAME 配置信息。
    """

    def __init__(self):
        self.releases: Dict[str, List[Release]] = {}

    def load_data(self, url_template: str, regions: List[str]):
        """
        加载 GAME 数据。
        """
        logger.debug(f"正在加载 GAME 数据，区域: {regions}...")
        for region in regions:
            url = url_template.format(region=region)
            game_data = requests.get(url).json()
            self.releases[region] = [
                Release.from_json(release) for release in game_data.get("releases", []) if Release.from_json(release)
            ]
        logger.debug("GAME 数据加载完成")

    def __getitem__(self, region: str) -> List[Release]:
        """
        支持通过下标访问 GAME 数据，例如 riot_game_data.game['EUW1']。
        """
        if region in self.releases:
            return self.releases[region]
        raise KeyError(f"未找到区域 {region} 的数据")

    def available_regions(self) -> List[str]:
        """
        返回当前可用的 GAME 区域列表。
        """
        return list(self.releases.keys())


class RiotGameData:
    """
    整合 LCU 和 GAME 数据的管理类。
    """

    LCU_URL = "https://clientconfig.rpg.riotgames.com/api/v1/config/public?namespace=keystone.products.league_of_legends.patchlines"
    GAME_URL_TEMPLATE = (
        "https://sieve.services.riotcdn.net/api/v1/products/lol/version-sets/{region}?q[platform]=windows"
    )

    def __init__(self):
        self.lcu = LCUData()
        self.game = GameData()

    def load_lcu_data(self):
        """
        加载 LCU 数据。
        """
        self.lcu.load_data(self.LCU_URL)

    def load_game_data(self, regions=None):
        """
        加载 GAME 数据。
        """
        if regions is None:
            regions = ["EUW1", "PBE1"]
        self.game.load_data(self.GAME_URL_TEMPLATE, regions)

    def latest_game(self, region: str = "EUW1") -> Optional[Release]:
        """
        获取指定区域的最新版本的 Release。
        """
        if region in self.game.releases:
            sorted_releases = sorted(self.game.releases[region], key=lambda r: [int(v) for v in r.version.split(".")])
            return sorted_releases[-1] if sorted_releases else None
        raise KeyError(f"未找到区域 {region} 的数据")

    def available_lcu_regions(self) -> List[str]:
        """
        返回当前可用的 LCU 区域列表。
        """
        return self.lcu.available_regions()

    def available_game_regions(self) -> List[str]:
        """
        返回当前可用的 GAME 区域列表。
        """
        return self.game.available_regions()
