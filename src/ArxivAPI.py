import logging
import time
from datetime import datetime

import bs4
import requests

import util

_logger = logging.getLogger(__name__)
_API_BASE_URL = "https://export.arxiv.org/api/query"
_SRC_DL_BASE_URL = "https://export.arxiv.org/src/"
_DELAY_API_QUERY_MS = 3000
# theoretically bursts of 4 per second and then 1-second delay. since the download mostly takes longer we just use a
# delay of a second and no bursts
_DELAY_EXPORT_DL_MS = 1000


def _get_current_ms():
    return time.time_ns() // 1_000_000  # not all systems provide time with better precision than 1 second!


def _find_entries(xml: str) -> bs4.ResultSet:
    xml = bs4.BeautifulSoup(xml, features="xml")
    entries = xml.find_all("entry")
    return entries


class ArxivAPI:
    def __init__(self):
        self._last_request_ms: int = -1

    def query(self, category: str, max_results: int, chunk_size: int) -> list[bs4.Tag]:
        total_results = self._get_total_results(category)
        max_results = total_results if max_results > total_results else max_results
        all_entries = []
        start = 0
        while start < max_results:
            # do not request last page with chunk_size entries if there aren't that many requested by max_results
            chunk = max_results - start if (start + chunk_size) > max_results else chunk_size
            feed_entries = self._retrieve_query_response(category, max_results, start, chunk)
            all_entries += feed_entries
            start += chunk

        return all_entries

    def get(self, url: str, delay_ms: int, max_retries=5, delay_factor=10):
        attempts = 0
        while True:
            try:
                self._wait_for_delay(delay_ms)
                response = requests.get(url)
                self._update_last_request()
                return response
            except requests.RequestException:
                _logger.debug("Retrying (%s/%s). ", attempts + 1, max_retries)

                if attempts < max_retries:
                    attempts += 1
                    # fail on 1. attempt: wait delay + 10s, on 5. attempt: wait delay + 50s
                    self._wait_for_delay(attempts * delay_factor * 1000)
                    continue
                else:
                    raise

    def get_src(self, arxiv_id: str, max_retries=5, delay_factor=10):
        paper_src_url = _SRC_DL_BASE_URL + arxiv_id
        return self.get(paper_src_url, _DELAY_EXPORT_DL_MS, max_retries=max_retries, delay_factor=delay_factor)

    def _update_last_request(self) -> None:
        self._last_request_ms = _get_current_ms()

    def _wait_for_delay(self, delay_ms: int) -> None:
        next_request = self._last_request_ms + delay_ms
        curr_ms = _get_current_ms()
        if curr_ms < next_request:
            wait_s = (next_request - curr_ms) / 1000
            time.sleep(wait_s)

    def _send_request(self, params: dict) -> requests.Response:
        url = requests.Request("GET", _API_BASE_URL, params=params).prepare().url  # only get encoded url
        response = self.get(url, _DELAY_API_QUERY_MS)
        response.encoding = util.ARXIV_ENCODING
        return response

    def _send_query(self, category: str, chunk_size: int, start: int) -> str:
        query_params = {
            "search_query": f"cat:{category}",
            # "sortBy": "lastUpdatedDate",
            # "sortOrder": "descending",
            "start": start,
            "max_results": chunk_size
        }
        response = self._send_request(query_params)
        return response.text

    def _retrieve_query_response(self, category: str, max_results: int, start: int, chunk_size: int) -> bs4.ResultSet:
        # database of export.arxiv.org gets updated once a day, no use in calling it more often and discouraged by ArXiv
        date = datetime.today().strftime('%Y-%m-%d')
        request_file = f"{date}_{category.replace(".", "_")}_r{max_results}_s{start}_cs{chunk_size}.xml"
        if not (response := util.read_file(util.get_requests_dir(), request_file)):
            response = self._send_query(category, chunk_size, start)

        entries = _find_entries(response)
        while len(entries) == 0:
            # retry as we received a response without entries
            response = self._send_query(category, chunk_size, start)
            entries = _find_entries(response)

        util.write_to_file(util.get_requests_dir(), request_file, response)
        return entries

    def _get_total_results(self, category: str) -> int:
        # requesting 1 result will still populate the opensearch:totalResults value
        response = self._send_query(category, 1, 0)
        xml = bs4.BeautifulSoup(response, features="xml")
        return int(xml.find("opensearch:totalResults").text)
