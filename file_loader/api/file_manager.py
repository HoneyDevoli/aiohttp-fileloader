import logging
import os
from typing import Union
from pathlib import Path
from hashlib import md5
from uuid import uuid4

import aiofiles
from aiohttp import BodyPartReader, MultipartReader

logger = logging.getLogger(__name__)


class EmptyFileError(Exception):
    """
    Exception raised when a file shouldn't be empty.
    """
    pass


class FileManager:
    """Class for managing file handling
    :param path_store: directory for saving incoming files
    :param chunk_size: the size of slice of file for reading-writing by part
    """

    def __init__(self, path_store: Path, chunk_size: int = 64 * 1024):
        self.path_store = path_store
        self.chunk_size = chunk_size

    async def save_file(self,
                        file_stream: Union[BodyPartReader, MultipartReader])\
            -> str:
        """Saves the file coming in reader
           :param file_stream: the request stream
           :return: str: md5 hash of the received file
           :raise EmptyFileError: the stream contained an empty (0 byte) file
           """
        file_tmp_name = f'id{uuid4()}'

        async with aiofiles.open(self.path_store / file_tmp_name,
                                 'wb') as file_tmp:
            file_hash = md5()
            file_size = 0

            while True:
                chunk = await file_stream.read_chunk(size=self.chunk_size)
                if not chunk:
                    break

                file_size += await file_tmp.write(chunk)
                file_hash.update(chunk)

        if file_size == 0:
            await aiofiles.os.remove(self.path_store / file_tmp_name)
            raise EmptyFileError

        new_dir_path = self.path_store / file_hash.hexdigest()[:2]
        if not os.path.isdir(new_dir_path):
            await aiofiles.os.mkdir(new_dir_path)

        # on Unix system silently replace existing file
        try:
            await aiofiles.os.rename(self.path_store / file_tmp_name,
                                     new_dir_path / file_hash.hexdigest())
        except FileExistsError:
            logger.info("File with hash %s has already existed",
                        file_hash.hexdigest())
            return file_hash.hexdigest()

        logger.info('File was save by path %s',
                    new_dir_path / file_hash.hexdigest())
        return file_hash.hexdigest()

    async def get_file_reader(self, file_hash: str) -> ():
        """Saves the file coming in reader
            :param file_hash: hash of the file to read
            :return: AsyncGenerator: reads the file hash of the file,
            chunk by chunk
            :raise FileNotFoundError: file not found by file hash
            """
        file_path = self.path_store / file_hash[:2] / file_hash
        if not file_path.exists():
            raise FileNotFoundError

        async def read_file():
            async with aiofiles.open(file_path, 'rb') as file:
                while True:
                    data = await file.read(self.chunk_size)
                    if not data:
                        break
                    yield data

        return read_file

    async def delete_file(self, file_hash: str) -> None:
        """Delete file by hash of file from directory
            :param file_hash: hash of the file to read
            :return: None
            :raise FileNotFoundError: file not found by file hash
            """

        file_path = self.path_store / file_hash[:2] / file_hash
        if not file_path.exists():
            logger.warning('File with hash %s not found', file_hash)
            raise FileNotFoundError

        await aiofiles.os.remove(file_path)
        logger.info('Delete file with path %s', file_path)
