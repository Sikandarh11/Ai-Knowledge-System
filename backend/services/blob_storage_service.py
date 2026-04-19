from __future__ import annotations

from pathlib import Path

from azure.core.exceptions import AzureError, ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings

from backend.core.config import settings


class BlobStorageService:
    def __init__(self) -> None:
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING.strip()
        container_name = settings.AZURE_STORAGE_CONTAINER_NAME.strip()

        if not connection_string:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not configured")
        if not container_name:
            raise RuntimeError("AZURE_STORAGE_CONTAINER_NAME is not configured")

        self._container_name = container_name
        self._client = BlobServiceClient.from_connection_string(connection_string)
        self._container_client = self._client.get_container_client(container_name)

        try:
            self._container_client.create_container()
        except ResourceExistsError:
            pass

    def upload_file(self, *, file_path: str, blob_name: str, content_type: str | None = None) -> dict:
        blob_client = self._container_client.get_blob_client(blob_name)
        blob_settings = ContentSettings(content_type=content_type or "application/octet-stream")

        try:
            with open(file_path, "rb") as file_handle:
                blob_client.upload_blob(file_handle, overwrite=True, content_settings=blob_settings)
        except (OSError, AzureError) as exc:
            raise RuntimeError(f"Failed to upload file to blob storage: {exc}") from exc

        return {
            "container_name": self._container_name,
            "blob_name": blob_name,
            "blob_path": f"{self._container_name}/{blob_name}",
            "download_url": blob_client.url,
        }

    def delete_blob(self, blob_name: str) -> None:
        try:
            blob_client = self._container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
        except AzureError:
            pass