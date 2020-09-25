import logging
from http import HTTPStatus

from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_urldispatcher import View

from file_loader.api.file_manager import FileManager, EmptyFileError
from file_loader.utils.exception import ValidationError

logger = logging.getLogger(__name__)


class FilesView(View):
    URL_PATH = r'/files/{file_hash:(\w*\d*)+}'

    async def get(self) -> StreamResponse:
        """Get file by hash of file from storage

        Request
        ------
        <file_hash> str: should be contain only numbers and letters
        ------
        Response
        ------
        streaming bytes data
        """
        file_hash = self.request.match_info['file_hash'].lower()
        if not file_hash:
            raise ValidationError

        file_manager = self._create_file_manager()
        try:
            file_reader = await file_manager.get_file_loader(file_hash)

            response = StreamResponse(
                status=HTTPStatus.OK,
                headers={
                    "Content-disposition": f"attachment; filename={file_hash}"
                })
            response.enable_chunked_encoding()

            await response.prepare(self.request)
            async for chunk in file_reader():
                await response.write(chunk)
            await response.write_eof()

            return response
        except FileNotFoundError:
            raise HTTPNotFound

    async def post(self) -> Response:
        """Uploads a file to storage

        Request
        ------
        should be contain multipart data
        ------
        Response
        ------
        <file_hash> str: new file name generated by hash function
        """
        if not self.request.can_read_body:
            raise ValidationError
        if 'multipart' not in self.request.content_type:
            raise ValidationError(
                message='Only multipart content is supported')

        reader = await self.request.multipart()

        file_manager = self._create_file_manager()
        try:
            async for file_stream in reader:
                if file_stream.filename:
                    file_hash = await file_manager.save_file(file_stream)
                break

            response = Response(
                body={'file_hash': file_hash},
                headers={
                    'Location': f'/files/{file_hash}'},
                status=HTTPStatus.CREATED)

            return response
        except EmptyFileError as e:
            logger.exception(e)
            raise ValidationError(message='File is empty') from e

    async def delete(self) -> Response:
        """Delete file by hash of file from storage

        Request
        ------
        <file_hash> str: should be contain only numbers and letters
        ------
        Response
        ------
        None
        """
        file_hash = self.request.match_info['file_hash']
        if not file_hash:
            raise ValidationError

        file_manager = self._create_file_manager()
        try:
            await file_manager.delete_file(file_hash)
            return Response(status=HTTPStatus.NO_CONTENT)
        except FileNotFoundError:
            raise HTTPNotFound

    def _create_file_manager(self):
        storage_path = self.request.app['storage_path']
        return FileManager(storage_path)
