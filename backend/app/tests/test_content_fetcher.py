import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import GitHubNotFoundError
from app.integrations.github.client import GitHubContentData
from app.services.content_fetcher import FileContentFetcher


@pytest.mark.asyncio
async def test_content_fetcher_successful_decoding():
    mock_client = MagicMock()
    encoded_text = base64.b64encode(b"print('hello world')\nline2").decode("utf-8")
    mock_client.get_file_content = AsyncMock(
        return_value=GitHubContentData(
            name="main.py",
            path="app/main.py",
            sha="abc1234",
            size=27,
            encoding="base64",
            content=encoded_text,
            type="file",
        )
    )

    fetcher = FileContentFetcher(mock_client)
    result = await fetcher.fetch_and_decode("owner", "repo", "app/main.py")

    assert result == "print('hello world')\nline2"
    mock_client.get_file_content.assert_called_once_with(
        "owner", "repo", "app/main.py", ref="main"
    )


@pytest.mark.asyncio
async def test_content_fetcher_binary_file_decoding_failure():
    mock_client = MagicMock()
    # Invalid UTF-8 byte sequence after base64 decode
    invalid_utf8_base64 = base64.b64encode(bytes([0x80, 0x81, 0x82, 0xFF])).decode("utf-8")
    mock_client.get_file_content = AsyncMock(
        return_value=GitHubContentData(
            name="binary.dat",
            path="binary.dat",
            sha="abc1234",
            size=4,
            encoding="base64",
            content=invalid_utf8_base64,
            type="file",
        )
    )

    fetcher = FileContentFetcher(mock_client)
    result = await fetcher.fetch_and_decode("owner", "repo", "binary.dat")

    assert result is None


@pytest.mark.asyncio
async def test_content_fetcher_file_not_found():
    mock_client = MagicMock()
    mock_client.get_file_content = AsyncMock(side_effect=GitHubNotFoundError("File not found"))

    fetcher = FileContentFetcher(mock_client)
    result = await fetcher.fetch_and_decode("owner", "repo", "nonexistent.py")

    assert result is None


@pytest.mark.asyncio
async def test_content_fetcher_oversized_file():
    mock_client = MagicMock()
    mock_client.get_file_content = AsyncMock(
        return_value=GitHubContentData(
            name="huge.py",
            path="huge.py",
            sha="abc1234",
            size=1_000_000,
            encoding="base64",
            content="",
            type="file",
        )
    )

    fetcher = FileContentFetcher(mock_client)
    result = await fetcher.fetch_and_decode("owner", "repo", "huge.py", max_bytes=500_000)

    assert result is None
