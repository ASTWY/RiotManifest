# -*- coding: utf-8 -*-
# @Author  : Virace
# @Email   : Virace@aliyun.com
# @Site    : x-item.com
# @Software: Pycharm
# @Create  : 2024/9/6 7:21
# @Update  : 2024/9/6 7:26
# @Detail  : 

import subprocess
from contextlib import contextmanager
from typing import Iterator, List, Optional, Union

from loguru import logger

StrPath = Union[str, "os.PathLike[str]"]


@contextmanager
def execute_command(
    args: Union[str, List[str]], executable: Optional[str] = None, cwd: Optional[str] = None
) -> Iterator[subprocess.Popen]:
    """
    执行第三方命令并提供一个上下文管理器来处理其输出。

    :param args: 要执行的命令，可以是字符串或字符串列表。
    :param executable: 可执行文件的路径。如果为 None，则使用 args 中的第一个元素。
    :param cwd: 执行命令的工作目录。如果为 None，则使用当前目录。
    :yield: 提供一个子进程对象以供上下文管理。
    """
    if isinstance(args, str):
        # 如果 args 是字符串，则按空格分割为列表
        args = args.split()

    process = None  # 初始化 process 变量

    try:
        logger.debug(f"准备执行命令: {' '.join(args)}")

        # 启动子进程，并将 stderr 重定向到 stdout
        process = subprocess.Popen(
            args=args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            executable=executable,
            cwd=cwd,
            text=True,
            bufsize=1,  # 行缓冲
        )

        yield process

    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {e}")
    except Exception as e:
        logger.error(f"执行命令时发生未知错误: {e}")
    finally:
        if process and process.stdout:
            process.stdout.close()
        if process:
            process.wait()
