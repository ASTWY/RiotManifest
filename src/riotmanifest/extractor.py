# -*- coding: utf-8 -*-
# @Author  : Virace
# @Email   : Virace@aliyun.com
# @Site    : x-item.com
# @Software: Pycharm
# @Create  : 2024/9/2 11:54
# @Update  : 2024/9/3 5:55
# @Detail  : 

from typing import Dict, List

from league_tools.formats import WAD, WadHeaderAnalyzer
from loguru import logger

from riotmanifest.manifest import PatcherFile, PatcherManifest


class WADExtractor:

    V3_HEADER_MINI_SIZE = 4 + 268 + 4

    def __init__(self, manifest_file: str, bundle_url: str = None, output_dir: str = None):
        """
        初始化WADExtractor实例。

        :param manifest_file: 清单文件路径或URL（必须）。
        :param bundle_url: 资源文件的基础URL（可选）。
        :param output_dir: 文件保存的目录（可选）。
        """
        self.manifest_file = manifest_file
        self.bundle_url = bundle_url
        self.output_dir = output_dir

        # 构建传递给 PatcherManifest 的参数字典
        manifest_kwargs = {"file": manifest_file, "path": ""}
        if output_dir:
            manifest_kwargs["path"] = output_dir
        if bundle_url:
            manifest_kwargs["bundle_url"] = bundle_url

        # 初始化 PatcherManifest
        self.manifest = PatcherManifest(**manifest_kwargs)
        logger.debug(
            f"WADExtractor实例已初始化 - 清单文件: {manifest_file}, 资源URL: {bundle_url}, 输出目录: {output_dir}"
        )

    def extract_files(self, wad_file_paths: Dict[str, List[str]]) -> Dict[str, Dict[str, bytes]]:
        """
        从多个WAD文件中提取多个文件。

        :param wad_file_paths: 字典结构，键是WAD文件名，值是需要提取的内部文件路径列表。
        :return: 提取的文件字节内容字典，外层字典的键是WAD文件路径，内层字典的键是WAD内部文件路径，值是文件字节内容。
        """
        extracted_files = {}
        logger.info("开始提取WAD文件中的内容。")

        for wad_filename, target_paths in wad_file_paths.items():
            logger.debug(f"处理WAD文件: {wad_filename}，目标路径: {target_paths}")

            # todo: 做错误处理，如果没找到文件
            wad_file = list(self.manifest.filter_files(pattern=wad_filename))[0]

            wad_header = self.get_wad_header(wad_file)
            files = {file.path_hash: file for file in wad_header.files}

            extracted_files[wad_filename] = {}

            for _path in target_paths:
                path_hash = WAD.get_hash(_path)
                logger.debug(f"从WAD文件 {wad_filename} 中提取文件: {_path}, path_hash: {path_hash}")

                if path_hash not in files:
                    extracted_files[wad_filename][_path] = None
                    continue

                section = files[path_hash]
                logger.debug(f"section_offset: {section.offset}, section_size: {section.compressed_size}")
                required_chunks = []
                accumulated_size = 0

                chunk_index = 0

                #  两种情况
                #  第一种是 前一个chunk的开头正好是section.offset的位置，这样下一个chunk直接就可以添加
                #  第二种是 section.offset 在chunk中间
                for chunk in wad_file.chunks:

                    accumulated_size += chunk.target_size

                    # 只能是大于， 等于的话属于第一种情况
                    if accumulated_size > section.offset:

                        required_chunks.append(chunk)

                        # 第二种情况计算开头， 如果属于第一种情况， chunk_index会等于0
                        if len(required_chunks) == 0:
                            chunk_index = abs(accumulated_size - section.offset - chunk.target_size)

                    if accumulated_size >= section.offset + section.compressed_size:
                        break

                # 第二种情况的切片 要处理开头
                logger.trace(
                    f"chunk_index: {chunk_index}, chunk_end: {section.compressed_size}, section_size: {section.compressed_size}"
                )
                raw = wad_file.download_chunks(required_chunks)
                logger.trace(f"raw: {len(raw)}")
                raw = raw[chunk_index : section.compressed_size + 1]
                data = wad_header.extract_by_section(section, "", raw=True, data=raw)
                extracted_files[wad_filename][_path] = data

        logger.info("完成WAD文件内容提取。")
        return extracted_files

    @classmethod
    def _get_wad_header(cls, wad_file: PatcherFile, chunk_size: int):

        required_chunks = []
        accumulated_size = 0
        for chunk in wad_file.chunks:
            if accumulated_size >= chunk_size:
                break
            accumulated_size += chunk.size
            required_chunks.append(chunk)
        return wad_file.download_chunks(required_chunks)

    def get_wad_header(self, wad_file: PatcherFile):

        # 根据V3版本最小的文件头大小 下载WAD文件头
        wad_header_data = self._get_wad_header(wad_file, self.V3_HEADER_MINI_SIZE)

        # 将这部分数据传递给WadHeaderAnalyzer
        # 这部分数据是肯定可以分析到 文件数量的
        header_analyzer = WadHeaderAnalyzer(wad_header_data)

        # 根据上述提供的文件数量计算实际WAD文件头的大小
        # WAD文件头可以获取到所有 WAD内文件的偏移信息
        wad_header_data = self._get_wad_header(wad_file, header_analyzer.header_size)

        return WAD(wad_header_data)
