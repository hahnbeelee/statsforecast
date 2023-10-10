# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/src/core/distributed.fugue.ipynb.

# %% auto 0
__all__ = ['FugueBackend']

# %% ../../nbs/src/core/distributed.fugue.ipynb 4
import inspect
from typing import Any, Dict, List

import fugue.api as fa
import numpy as np
import pandas as pd
from fugue import transform, DataFrame, FugueWorkflow, ExecutionEngine
from fugue.collections.yielded import Yielded
from fugue.constants import FUGUE_CONF_WORKFLOW_EXCEPTION_INJECT
from ..core import _StatsForecast, ParallelBackend, make_backend
from triad import Schema

# %% ../../nbs/src/core/distributed.fugue.ipynb 5
def _cotransform(
    df1: Any,
    df2: Any,
    using: Any,
    schema: Any = None,
    params: Any = None,
    partition: Any = None,
    engine: Any = None,
    engine_conf: Any = None,
    force_output_fugue_dataframe: bool = False,
    as_local: bool = False,
) -> Any:
    dag = FugueWorkflow(compile_conf={FUGUE_CONF_WORKFLOW_EXCEPTION_INJECT: 0})

    src = dag.create_data(df1).zip(dag.create_data(df2), partition=partition)
    tdf = src.transform(
        using=using,
        schema=schema,
        params=params,
        pre_partition=partition,
    )
    tdf.yield_dataframe_as("result", as_local=as_local)
    dag.run(engine, conf=engine_conf)
    result = dag.yields["result"].result  # type:ignore
    if force_output_fugue_dataframe or isinstance(df1, (DataFrame, Yielded)):
        return result
    return result.as_pandas() if result.is_local else result.native  # type:ignore

# %% ../../nbs/src/core/distributed.fugue.ipynb 6
class FugueBackend(ParallelBackend):
    """FugueBackend for Distributed Computation.
    [Source code](https://github.com/Nixtla/statsforecast/blob/main/statsforecast/distributed/fugue.py).

    This class uses [Fugue](https://github.com/fugue-project/fugue) backend capable of distributing
    computation on Spark, Dask and Ray without any rewrites.

    **Parameters:**<br>
    `engine`: fugue.ExecutionEngine, a selection between Spark, Dask, and Ray.<br>
    `conf`: fugue.Config, engine configuration.<br>
    `**transform_kwargs`: additional kwargs for Fugue's transform method.<br>

    **Notes:**<br>
    A short introduction to Fugue, with examples on how to scale pandas code to Spark, Dask or Ray
     is available [here](https://fugue-tutorials.readthedocs.io/tutorials/quick_look/ten_minutes.html).
    """

    def __init__(self, engine: Any = None, conf: Any = None, **transform_kwargs: Any):
        self._engine = engine
        self._conf = conf
        self._transform_kwargs = dict(transform_kwargs)

    def __getstate__(self) -> Dict[str, Any]:
        return {}

    def forecast(
        self,
        df,
        models,
        freq,
        fallback_model=None,
        X_df=None,
        **kwargs: Any,
    ) -> Any:
        """Memory Efficient core.StatsForecast predictions with FugueBackend.

        This method uses Fugue's transform function, in combination with
        `core.StatsForecast`'s forecast to efficiently fit a list of StatsForecast models.

        **Parameters:**<br>
        `df`: pandas.DataFrame, with columns [`unique_id`, `ds`, `y`] and exogenous.<br>
        `freq`: str, frequency of the data, [pandas available frequencies](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases).<br>
        `models`: List[typing.Any], list of instantiated objects `StatsForecast.models`.<br>
        `fallback_model`: Any, Model to be used if a model fails.<br>
        `X_df`: pandas.DataFrame, with [unique_id, ds] columns and df’s future exogenous.
        `**kwargs`: Additional `core.StatsForecast` parameters. Example forecast horizon `h`.<br>

        **Returns:**<br>
        `fcsts_df`: pandas.DataFrame, with `models` columns for point predictions and probabilistic
        predictions for all fitted `models`.<br>

        **References:**<br>
        For more information check the
        [Fugue's transform](https://fugue-tutorials.readthedocs.io/tutorials/beginner/transform.html)
        tutorial.<br>
        The [core.StatsForecast's forecast](https://nixtla.github.io/statsforecast/core.html#statsforecast.forecast)
        method documentation.<br>
        Or the list of available [StatsForecast's models](https://nixtla.github.io/statsforecast/src/core/models.html).
        """
        level = kwargs.get("level", [])
        schema = self._get_output_schema(df, models, level)
        if X_df is None:
            return transform(
                df,
                self._forecast_series,
                params=dict(
                    models=models,
                    freq=freq,
                    kwargs=kwargs,
                    fallback_model=fallback_model,
                ),
                schema=schema,
                partition={"by": "unique_id"},
                engine=self._engine,
                engine_conf=self._conf,
                **self._transform_kwargs,
            )
        return _cotransform(
            df,
            X_df,
            self._forecast_series_X,
            params=dict(
                models=models, freq=freq, kwargs=kwargs, fallback_model=fallback_model
            ),
            schema=schema,
            partition={"by": "unique_id"},
            engine=self._engine,
            engine_conf=self._conf,
            **self._transform_kwargs,
        )

    def cross_validation(
        self,
        df,
        models,
        freq,
        fallback_model=None,
        **kwargs: Any,
    ) -> Any:
        """Temporal Cross-Validation with core.StatsForecast and FugueBackend.

        This method uses Fugue's transform function, in combination with
        `core.StatsForecast`'s cross-validation to efficiently fit a list of StatsForecast
        models through multiple training windows, in either chained or rolled manner.

        `StatsForecast.models`' speed along with Fugue's distributed computation allow to
        overcome this evaluation technique high computational costs. Temporal cross-validation
        provides better model's generalization measurements by increasing the test's length
        and diversity.

        **Parameters:**<br>
        `df`: pandas.DataFrame, with columns [`unique_id`, `ds`, `y`] and exogenous.<br>
        `freq`: str, frequency of the data, [panda's available frequencies](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases).<br>
        `models`: List[typing.Any], list of instantiated objects `StatsForecast.models`.<br>
        `fallback_model`: Any, Model to be used if a model fails.<br>

        **Returns:**<br>
        `fcsts_df`: pandas.DataFrame, with `models` columns for point predictions and probabilistic
        predictions for all fitted `models`.<br>

        **References:**<br>
        The [core.StatsForecast's cross validation](https://nixtla.github.io/statsforecast/core.html#statsforecast.cross_validation)
        method documentation.<br>
        [Rob J. Hyndman and George Athanasopoulos (2018). "Forecasting principles and practice, Temporal Cross-Validation"](https://otexts.com/fpp3/tscv.html).
        """
        level = kwargs.get("level", [])
        schema = self._get_output_schema(df, models, level, mode="cv")
        return transform(
            df,
            self._cv,
            params=dict(
                models=models, freq=freq, kwargs=kwargs, fallback_model=fallback_model
            ),
            schema=schema,
            partition={"by": "unique_id"},
            engine=self._engine,
            engine_conf=self._conf,
            **self._transform_kwargs,
        )

    def _forecast_series(
        self, df: pd.DataFrame, models, freq, fallback_model, kwargs
    ) -> pd.DataFrame:
        model = _StatsForecast(
            df=df, models=models, freq=freq, fallback_model=fallback_model, n_jobs=1
        )
        return model.forecast(**kwargs).reset_index()

    # schema: unique_id:str, ds:str, *
    def _forecast_series_X(
        self, df: pd.DataFrame, X_df: pd.DataFrame, models, freq, fallback_model, kwargs
    ) -> pd.DataFrame:
        model = _StatsForecast(
            df=df, models=models, freq=freq, fallback_model=fallback_model, n_jobs=1
        )
        if len(X_df) != kwargs["h"]:
            raise Exception(
                "Please be sure that your exogenous variables `X_df` "
                "have the same length than your forecast horizon `h`"
            )
        return model.forecast(X_df=X_df, **kwargs).reset_index()

    def _cv(
        self, df: pd.DataFrame, models, freq, fallback_model, kwargs
    ) -> pd.DataFrame:
        model = _StatsForecast(
            df=df, models=models, freq=freq, fallback_model=fallback_model, n_jobs=1
        )
        return model.cross_validation(**kwargs).reset_index()

    def _get_output_schema(self, df, models, level=None, mode="forecast") -> Schema:
        keep_schema = fa.get_schema(df).extract(["unique_id", "ds"])
        cols: List[Any] = []
        if level is None:
            level = []
        for model in models:
            has_levels = (
                "level" in inspect.signature(getattr(model, "forecast")).parameters
                and len(level) > 0
            )
            cols.append((repr(model), np.float32))
            if has_levels:
                cols.extend(
                    [(f"{repr(model)}-lo-{l}", np.float32) for l in reversed(level)]
                )
                cols.extend([(f"{repr(model)}-hi-{l}", np.float32) for l in level])
        if mode == "cv":
            cols = [("cutoff", keep_schema["ds"].type), ("y", np.float32)] + cols
        return Schema(keep_schema) + Schema(cols)


@make_backend.candidate(lambda obj, *args, **kwargs: isinstance(obj, ExecutionEngine))
def _make_fugue_backend(obj: ExecutionEngine, *args, **kwargs) -> ParallelBackend:
    return FugueBackend(obj, **kwargs)
