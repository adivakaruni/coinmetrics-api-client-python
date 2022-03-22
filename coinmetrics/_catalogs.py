from dateutil.parser import isoparse
from typing import Iterable
from coinmetrics._typing import DataFrameType, List, Any, Optional
from logging import getLogger

logger = getLogger("cm_client")

try:
    import pandas as pd  # type: ignore
except ImportError:
    pd = None
    logger.warning(
        "Pandas export is unavailable. Install pandas to unlock dataframe functions."
    )


def _convert_utc(x: Any) -> DataFrameType:
    try:
        return isoparse(x)
    except TypeError:
        return None


def _expand_df(key: str, iterable: Iterable[Any]) -> List[Any]:
    def _assign_value(row: Any) -> Any:
        try:
            return row[key]
        except (KeyError, TypeError):
            return None

    return list(map(_assign_value, iterable))


def convert_catalog_dtypes(df: DataFrameType) -> DataFrameType:
    df = df.convert_dtypes()
    columns = df.columns
    datetime_cols = [c for c in columns if c.endswith("_time") or c == "time"]
    for col in datetime_cols:
        df[col] = df[col].apply(_convert_utc)
    return df


class CatalogAssetsData(List[Any]):
    def to_dataframe(self, secondary_level: Optional[str] = None) -> DataFrameType:
        """
        Transforms catalog data in list form into a dataframe

        :param secondary_level: Second level of aggregation next to exchanges. One of "markets" or "metrics"; raises ValueError if neither.
        :type secondary_level: str
        :return: Catalog Data
        """
        df_assets = pd.DataFrame(self)
        if secondary_level is None:
            pass
        elif secondary_level == "markets":
            df_assets = (
                df_assets.explode("markets")
                .fillna({"markets": ""})
                .rename({"markets": "market"}, axis=1)
                .assign(
                    exchange=lambda x: x["market"].apply(lambda row: row.split("-")[0])
                )
                .drop("exchanges", axis=1)
                .reset_index(drop=True)
            )

        elif secondary_level == "metrics":
            asset_mapper = df_assets.asset.to_dict()

            def _assign_metric(x: Any) -> Any:
                try:
                    return x["metric"]
                except TypeError:
                    return None

            df_assets = df_assets.explode("metrics").assign(
                metrics=lambda x: pd.Series(x["metrics"])
            )
            df_assets["metric"] = df_assets["metrics"].apply(_assign_metric)
            df_assets_metrics = df_assets.dropna(subset=["metrics"]).metrics.apply(
                pd.Series
            )
            df_assets_metrics["asset"] = df_assets_metrics.index.map(asset_mapper)
            df_assets_metrics = (
                df_assets_metrics.explode("frequencies")
                .assign(
                    frequency=lambda df: _expand_df(
                        key="frequency", iterable=df.frequencies
                    )
                )
                .assign(
                    min_time=lambda df: _expand_df(
                        key="min_time", iterable=df.frequencies
                    )
                )
                .assign(
                    max_time=lambda df: _expand_df(
                        key="max_time", iterable=df.frequencies
                    )
                )
                .assign(
                    min_height=lambda df: _expand_df(
                        key="min_height", iterable=df.frequencies
                    )
                )
                .assign(
                    max_height=lambda df: _expand_df(
                        key="max_height", iterable=df.frequencies
                    )
                )
                .assign(
                    min_hash=lambda df: _expand_df(
                        key="min_hash", iterable=df.frequencies
                    )
                )
                .assign(
                    max_hash=lambda df: _expand_df(
                        key="max_hash", iterable=df.frequencies
                    )
                )
                .drop(["frequencies"], axis=1)
            )
            df_assets = (
                df_assets.drop(["metrics"], axis=1)
                .merge(df_assets_metrics, on=["metric", "asset"], how="left")
                .reset_index(drop=True)
            )

        else:
            raise ValueError(
                "secondary_level must be one of None, 'markets' or 'metrics"
            )
        df_assets = convert_catalog_dtypes(df_assets)
        return df_assets


class CatalogAssetAlertsData(List[Any]):
    def to_dataframe(self) -> DataFrameType:
        """
        Transforms catalog data in list form into a dataframe
        :return: Catalog Data
        """
        return convert_catalog_dtypes(pd.DataFrame(self).explode("constituents"))


class CatalogAssetPairsData(List[Any]):
    def to_dataframe(self) -> DataFrameType:
        """
        Transforms catalog data in list form into a dataframe
        :return: Catalog Data
        """
        df_asset_pairs = (
            pd.DataFrame(self)
            .explode("metrics")
            .assign(metric=lambda df: _expand_df(key="metric", iterable=df.metrics))
            .assign(
                frequencies=lambda df: _expand_df(
                    key="frequencies", iterable=df.metrics
                )
            )
            .explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(
                min_time=lambda df: _expand_df(key="min_time", iterable=df.frequencies)
            )
            .assign(
                max_time=lambda df: _expand_df(key="max_time", iterable=df.frequencies)
            )
            .reset_index(drop=True)
            .drop(["metrics", "frequencies"], axis=1)
        )
        return convert_catalog_dtypes(df_asset_pairs)


class CatalogExchangesData(List[Any]):
    def to_dataframe(self, secondary_level: Optional[str] = None) -> DataFrameType:
        """
        Transforms catalog data in list form into a dataframe

        :param secondary_level: Second level of aggregation next to exchanges. One of "markets" or "metrics"; raises ValueError if neither.
        :type secondary_level: str
        :return: Catalog Data
        """
        df_exchanges = pd.DataFrame(self)
        if secondary_level is None:
            pass
        elif secondary_level == "markets":
            df_exchanges = df_exchanges.explode("markets").rename(
                {"markets": "market"}, axis=1
            )
        elif secondary_level == "metrics":
            df_exchanges = (
                df_exchanges.explode("metrics")
                .assign(metric=lambda df: _expand_df(key="metric", iterable=df.metrics))
                .assign(
                    frequencies=lambda df: _expand_df(
                        key="frequencies", iterable=df.metrics
                    )
                )
                .explode("frequencies")
                .assign(
                    frequency=lambda df: _expand_df(
                        key="frequency", iterable=df.frequencies
                    )
                )
                .assign(
                    min_time=lambda df: _expand_df(
                        key="min_time", iterable=df.frequencies
                    )
                )
                .assign(
                    max_time=lambda df: _expand_df(
                        key="max_time", iterable=df.frequencies
                    )
                )
                .reset_index(drop=True)
                .drop(["metrics", "frequencies"], axis=1)
            )
        else:
            raise ValueError("secondary_level must be one of 'markets' or 'metrics")
        df_exchanges = convert_catalog_dtypes(df_exchanges)
        return df_exchanges


class CatalogExchangeAssetsData(List[Any]):
    def to_dataframe(self) -> DataFrameType:
        """
        Transforms catalog data in list form into a dataframe
        :return: Catalog Data
        """
        df_exchange_assets = pd.DataFrame(self)
        df_exchange_assets = (
            df_exchange_assets.explode("metrics")
            .assign(metric=lambda df: _expand_df(key="metric", iterable=df.metrics))
            .assign(
                frequencies=lambda df: _expand_df(
                    key="frequencies", iterable=df.metrics
                )
            )
            .explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(
                min_time=lambda df: _expand_df(key="min_time", iterable=df.frequencies)
            )
            .assign(
                max_time=lambda df: _expand_df(key="max_time", iterable=df.frequencies)
            )
            .reset_index(drop=True)
            .drop(["metrics", "frequencies"], axis=1)
        )
        return convert_catalog_dtypes(df_exchange_assets)


class CatalogIndexesData(List[Any]):
    """
    Transforms catalog data in list form into a dataframe
    :return: Catalog Data
    """

    def to_dataframe(self) -> DataFrameType:
        df_indexes = pd.DataFrame(self)
        df_indexes = (
            df_indexes.explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(
                min_time=lambda df: _expand_df(key="min_time", iterable=df.frequencies)
            )
            .assign(
                max_time=lambda df: _expand_df(key="max_time", iterable=df.frequencies)
            )
            .reset_index(drop=True)
            .drop(["frequencies"], axis=1)
        )
        return convert_catalog_dtypes(df_indexes)


class CatalogInstitutionsData(List[Any]):
    """
    Transforms catalog data in list form into a dataframe
    :return: Catalog Data
    """

    def to_dataframe(self) -> DataFrameType:
        df_institutions = pd.DataFrame(self)
        df_institutions = (
            df_institutions.explode("metrics")
            .assign(metric=lambda df: _expand_df(key="metric", iterable=df.metrics))
            .assign(
                frequencies=lambda df: _expand_df(
                    key="frequencies", iterable=df.metrics
                )
            )
            .explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(
                min_time=lambda df: _expand_df(key="min_time", iterable=df.frequencies)
            )
            .assign(
                max_time=lambda df: _expand_df(key="max_time", iterable=df.frequencies)
            )
            .reset_index(drop=True)
            .drop(["metrics", "frequencies"], axis=1)
        )
        return convert_catalog_dtypes(df_institutions)


class CatalogMarketsData(List[Any]):
    """
    Transforms catalog data in list form into a dataframe
    :return: Catalog Data
    """

    def to_dataframe(self) -> DataFrameType:
        df_markets = pd.DataFrame(self)
        df_markets = df_markets.join(
            df_markets["trades"].apply(pd.Series).drop(0, axis=1, errors="ignore"),
            rsuffix="_trades",
        )
        metadata = ["funding_rates", "openinterest", "liquidations"]
        for col in metadata:
            if col in df_markets.columns:
                df_markets = df_markets.join(
                    df_markets[col].apply(pd.Series).drop(0, axis=1, errors="ignore"),
                    rsuffix=f"_{col}",
                )

        df_markets = df_markets.drop(
            ["trades", "funding_rates", "openinterest", "liquidations"],
            axis=1,
            errors="ignore",
        )
        return convert_catalog_dtypes(df_markets)


class CatalogMetricsData(List[Any]):
    """
    Transforms catalog data in list form into a dataframe
    :return: Catalog Data
    """

    def to_dataframe(self) -> DataFrameType:
        df_catalog_metrics = (
            pd.DataFrame(self)
            .explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(asset=lambda df: _expand_df(key="assets", iterable=df.frequencies))
            .explode("asset")
            .drop("frequencies", axis=1)
            .reset_index(drop=True)
        )
        return convert_catalog_dtypes(df_catalog_metrics)


class CatalogMarketMetricsData(List[Any]):
    """
    Transforms catalog data in list form into a dataframe
    :return: Catalog Data
    """

    def to_dataframe(self) -> DataFrameType:
        df_catalog_market_metrics = pd.DataFrame(self)
        df_catalog_market_metrics = (
            df_catalog_market_metrics.explode("metrics")
            .assign(metric=lambda df: _expand_df(key="metric", iterable=df.metrics))
            .assign(
                frequencies=lambda df: _expand_df(
                    key="frequencies", iterable=df.metrics
                )
            )
            .explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(
                min_time=lambda df: _expand_df(key="min_time", iterable=df.frequencies)
            )
            .assign(
                max_time=lambda df: _expand_df(key="max_time", iterable=df.frequencies)
            )
            .reset_index(drop=True)
            .drop(["metrics", "frequencies"], axis=1)
        )
        return convert_catalog_dtypes(df_catalog_market_metrics)


class CatalogMarketCandlesData(List[Any]):
    """
    Transforms catalog data in list form into a dataframe
    :return: Catalog Data
    """

    def to_dataframe(self) -> DataFrameType:
        df_catalog_market_candles = pd.DataFrame(self)
        df_catalog_market_candles = (
            df_catalog_market_candles.explode("frequencies")
            .assign(
                frequency=lambda df: _expand_df(
                    key="frequency", iterable=df.frequencies
                )
            )
            .assign(
                min_time=lambda df: _expand_df(key="min_time", iterable=df.frequencies)
            )
            .assign(
                max_time=lambda df: _expand_df(key="max_time", iterable=df.frequencies)
            )
            .reset_index(drop=True)
            .drop(["frequencies"], axis=1)
        )
        return convert_catalog_dtypes(df_catalog_market_candles)
