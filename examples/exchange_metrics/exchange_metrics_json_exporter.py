import logging
import sys
import datetime as dt
from typing import List, Dict
from datetime import datetime
from multiprocessing import Pool
from os import environ, makedirs
from os.path import abspath, join

import requests

from coinmetrics.api_client import CoinMetricsClient
from coinmetrics.constants import PagingFrom

logger = logging.getLogger()
stream_handler = logging.StreamHandler()
level = logging.INFO
stream_handler.level = level
formatter = logging.Formatter(
    datefmt="[%Y-%m-%d %H:%M:%S]", fmt="%(asctime)-15s %(levelname)s %(message)s"
)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.level = level


api_key = (
    environ.get("CM_API_KEY") or sys.argv[1]
)  # sys.argv[1] is executed only if CM_API_KEY is not found

client = CoinMetricsClient(api_key)

DST_ROOT = "./data"

EXCHANGES = [
]

FREQUENCY = "1d"

START_DATE = dt.date(year=2018, month=1, day=1)
END_DATE = dt.date.today()


def get_exchange_metrics_mapping(exchanges: List[str]=[], frequency: str = "1d") -> Dict[str, List[str]]:
    """
    Gets a mapping of all the metrics available for provided exchnages at the specified frequency
    :param exchanges: List of str of support exchanges i.e. ["coinbase", "binance"]
    :parm frequency: frequency metrics is available at either "1d" or "1h"
    :return: Dictionary that maps name of exchange to a list of available metrics
    """
    result_dict = {}
    exchange_data = client.catalog_exchanges(exchanges=exchanges)
    for data in exchange_data:
        exchange_metrics = data.get("metrics")
        if exchange_metrics:
            metrics_filtered = []
            for metric in exchange_metrics:
                supported_frequencies = [frequency_metadata['frequency'] for frequency_metadata in metric['frequencies']]
                if frequency in supported_frequencies:
                    metrics_filtered.append(metric['metric'])
            result_dict[data['exchange']] = metrics_filtered
    return result_dict


def export_data(exchanges: List[str], frequency: str = "1d", start_date: datetime = START_DATE, end_date: datetime = END_DATE) -> None:
    logger.info("retrieving metric names")
    exchange_and_metrics = get_exchange_metrics_mapping(exchanges=exchanges, frequency=frequency)
    makedirs(DST_ROOT, exist_ok=True)
    for exchange, metrics in exchange_and_metrics.items():
        dst_file = join(DST_ROOT, "{}_exchange_metrics.json".format(exchange))
        logger.info(
            "exporting metrics into a json file (): %s",
            abspath(dst_file),
        )
        with open(dst_file, "wb") as dst_file_buffer:
            asset_metrics = client.get_exchange_metrics(
                exchanges=[exchange],
                metrics=metrics,
                frequency=frequency,
                paging_from=PagingFrom.START,
                page_size=1000,
                start_time=start_date,
                end_time=end_date
            )
            asset_metrics.export_to_json(dst_file_buffer)


if __name__ == "__main__":
    export_start_time = datetime.now()
    try:
        export_data(EXCHANGES, FREQUENCY, START_DATE, END_DATE)
    finally:
        logger.info("export took: %s", datetime.now() - export_start_time)
