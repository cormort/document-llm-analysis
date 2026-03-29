import logging
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from statsmodels.tsa.seasonal import seasonal_decompose

from app.models.modeling import (
    ClassificationRequest,
    ClassificationResponse,
    RegressionRequest,
    RegressionResponse,
    TimeSeriesRequest,
    TimeSeriesResponse,
)
from app.services.modeling_core import (
    train_linear_regression,
    train_logistic_regression,
)
from app.utils.file_resolver import convert_numpy_types, load_dataframe

router = APIRouter()
DATA_DIR = Path("data")


def get_df(file_path_str: str) -> pd.DataFrame:
    """Helper to load dataframe from path."""
    df = load_dataframe(file_path_str)
    if df is None:
        raise HTTPException(status_code=404, detail=f"檔案未找到: {file_path_str}")
    return df


@router.post("/regression", response_model=RegressionResponse)
async def perform_regression(request: RegressionRequest) -> RegressionResponse:
    """Train a Linear Regression model and return metrics + predictions."""
    df = get_df(request.file_path)

    # Validate columns
    missing_cols = [c for c in request.feature_cols if c not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"特徵欄位不存在: {missing_cols}")
    if request.target_col not in df.columns:
        raise HTTPException(
            status_code=400, detail=f"目標欄位不存在: {request.target_col}"
        )

    try:
        result = train_linear_regression(
            df=df,
            feature_cols=request.feature_cols,
            target_col=request.target_col,
            test_size=request.test_size,
        )
        return RegressionResponse(**convert_numpy_types(result))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.exception("迴歸訓練失敗")
        raise HTTPException(status_code=500, detail=f"迴歸訓練失敗: {str(e)}") from e


@router.post("/classification", response_model=ClassificationResponse)
async def perform_classification(
    request: ClassificationRequest,
) -> ClassificationResponse:
    """Train a Logistic Regression model for classification."""
    df = get_df(request.file_path)

    # Validate columns
    missing_cols = [c for c in request.feature_cols if c not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"特徵欄位不存在: {missing_cols}")
    if request.target_col not in df.columns:
        raise HTTPException(
            status_code=400, detail=f"目標欄位不存在: {request.target_col}"
        )

    try:
        result = train_logistic_regression(
            df=df,
            feature_cols=request.feature_cols,
            target_col=request.target_col,
            test_size=request.test_size,
        )
        return ClassificationResponse(**convert_numpy_types(result))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.exception("分類訓練失敗")
        raise HTTPException(status_code=500, detail=f"分類訓練失敗: {str(e)}") from e


@router.post("/timeseries", response_model=TimeSeriesResponse)
async def perform_timeseries(request: TimeSeriesRequest) -> TimeSeriesResponse:
    """Decompose time series and generate simple forecast."""
    df = get_df(request.file_path)

    # Validate columns
    if request.date_col not in df.columns:
        raise HTTPException(
            status_code=400, detail=f"日期欄位不存在: {request.date_col}"
        )
    if request.value_col not in df.columns:
        raise HTTPException(
            status_code=400, detail=f"數值欄位不存在: {request.value_col}"
        )

    # Prepare data
    ts_df = df[[request.date_col, request.value_col]].dropna()
    ts_df[request.date_col] = pd.to_datetime(ts_df[request.date_col], errors="coerce")
    ts_df = ts_df.dropna().sort_values(by=request.date_col)
    ts_df = ts_df.set_index(request.date_col)

    if len(ts_df) < 24:
        raise HTTPException(
            status_code=400,
            detail="時間序列資料量不足，至少需要 24 筆資料進行季節性分解",
        )

    # Determine period (try to infer from data frequency)
    try:
        ts_index = cast(pd.DatetimeIndex, ts_df.index)
        inferred_freq = pd.infer_freq(ts_index)
        if inferred_freq and inferred_freq.startswith("M"):
            period = 12
        elif inferred_freq and inferred_freq.startswith("Q"):
            period = 4
        elif inferred_freq and inferred_freq.startswith("W"):
            period = 52
        else:
            period = min(12, len(ts_df) // 2)
    except Exception:
        period = min(12, len(ts_df) // 2)

    # Seasonal Decomposition
    try:
        decomposition = seasonal_decompose(
            ts_df[request.value_col], model="additive", period=period
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"季節性分解失敗: {e!s}") from e

    # Simple Moving Average Forecast
    forecast_values: list[float] = []
    last_values = ts_df[request.value_col].tail(period).tolist()
    for _ in range(request.forecast_periods):
        next_val = float(np.mean(last_values[-period:]))
        forecast_values.append(next_val)
        last_values.append(next_val)

    # Generate forecast dates
    ts_index = cast(pd.DatetimeIndex, ts_df.index)
    last_date = ts_index[-1]
    try:
        freq = pd.infer_freq(ts_index) or "MS"
        forecast_dates = pd.date_range(
            start=last_date, periods=request.forecast_periods + 1, freq=freq
        )[1:]
        forecast_dates_str = [d.strftime("%Y-%m-%d") for d in forecast_dates]
    except Exception:
        forecast_dates_str = [f"T+{i + 1}" for i in range(request.forecast_periods)]

    return TimeSeriesResponse(
        trend=convert_numpy_types(decomposition.trend.tolist()),
        seasonal=convert_numpy_types(decomposition.seasonal.tolist()),
        residual=convert_numpy_types(decomposition.resid.tolist()),
        dates=[d.strftime("%Y-%m-%d") for d in ts_index],
        values=convert_numpy_types(ts_df[request.value_col].tolist()),
        forecast=forecast_values,
        forecast_dates=forecast_dates_str,
        interpretation=None,
    )
