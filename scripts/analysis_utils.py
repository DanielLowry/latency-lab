#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import json
from typing import Iterable, Sequence

import pandas as pd

PATH_COLUMNS = [
    "run_dir",
    "summary_path",
    "meta_path",
    "stdout_path",
    "raw_csv_path",
    "raw_llr_path",
    "bench_path",
]


def abs_repo_path(value: object, repo_root: Path) -> object:
    if not isinstance(value, str) or not value:
        return value
    path = Path(value)
    if path.is_absolute():
        return value
    return str((repo_root / path).resolve())


def resolve_index_paths(index, repo_root: Path, path_columns: Sequence[str] = PATH_COLUMNS):
    if not hasattr(index, "columns"):
        return index
    for col in path_columns:
        if col in index.columns:
            index[col] = index[col].apply(lambda value: abs_repo_path(value, repo_root))
    return index


def ensure_dataframe(index) -> pd.DataFrame:
    if hasattr(index, "columns"):
        return index
    return pd.DataFrame(index)


def parse_json_list(value: object) -> list[str]:
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return [value]


def format_json_list(value: object, sep: str = ",") -> str:
    items = [item for item in parse_json_list(value) if item]
    return sep.join(items)


def shorten_label(value: object, max_len: int = 40) -> str:
    text = str(value)
    if len(text) <= max_len:
        return text
    if max_len <= 6:
        return text[:max_len]
    head = max_len // 2 - 1
    tail = max_len - head - 3
    return f"{text[:head]}...{text[-tail:]}"


def unique_short_labels(values: Iterable[object], max_len: int = 40) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for value in values:
        label = shorten_label(value, max_len=max_len)
        count = seen.get(label, 0)
        if count:
            count += 1
            seen[label] = count
            out.append(f"{label}#{count}")
        else:
            seen[label] = 1
            out.append(label)
    return out


def build_hue_display(
    df: pd.DataFrame,
    hue_col: str,
    *,
    label_max: int = 40,
) -> tuple[pd.DataFrame, str | None]:
    if hue_col not in df.columns:
        return df, None
    raw = df[hue_col].astype(str)
    if hue_col in ("tags", "bench_args"):
        raw = raw.apply(format_json_list)
    out = df.copy()
    out["hue_display"] = unique_short_labels(raw, max_len=label_max)
    return out, "hue_display"


def prepare_summary(
    index,
    metric: str,
    *,
    filter_lab: str | None = None,
    filter_tag: str | None = None,
    max_cases: int | None = None,
) -> dict:
    df = ensure_dataframe(index).copy()
    if filter_lab and "lab" in df.columns:
        df = df[df["lab"] == filter_lab]
    if filter_tag and "tags" in df.columns:
        df = df[df["tags"].astype(str).str.contains(filter_tag)]

    if "case" not in df.columns:
        raise ValueError("Index is missing the 'case' column.")
    if metric not in df.columns:
        raise ValueError(f"Metric not found: {metric}")

    df[metric] = pd.to_numeric(df[metric], errors="coerce")
    df = df.dropna(subset=[metric])

    unit_label = None
    if "unit" in df.columns and len(df):
        unit_label = df["unit"].mode().iloc[0]

    case_order = (
        df.groupby("case")[metric]
        .median()
        .sort_values()
        .index.tolist()
    )

    if max_cases and len(case_order) > max_cases:
        case_order = case_order[:max_cases]
        df = df[df["case"].isin(case_order)]

    summary_table = (
        df.groupby("case")[metric]
        .agg(run_count="count", median="median", min="min", max="max")
        .sort_values("median")
    )

    return {
        "df": df,
        "case_order": case_order,
        "summary_table": summary_table,
        "unit_label": unit_label,
    }


def _format_tags_and_args(df: pd.DataFrame) -> pd.DataFrame:
    if "tags" in df.columns:
        df["tags_str"] = df["tags"].apply(format_json_list)
    else:
        df["tags_str"] = ""
    if "bench_args" in df.columns:
        df["bench_args_str"] = df["bench_args"].apply(format_json_list)
    else:
        df["bench_args_str"] = ""
    return df


def build_config_label(row: pd.Series, config_cols: Sequence[str]) -> str:
    parts: list[str] = []
    if "pin_cpu" in config_cols:
        parts.append(f"pin={row.get('pin_cpu')}")
    if "tags" in config_cols:
        tags = row.get("tags_str") or "-"
        parts.append(f"tags={tags}")
    if "iters" in config_cols:
        parts.append(f"iters={row.get('iters')}")
    if "warmup" in config_cols:
        parts.append(f"warmup={row.get('warmup')}")
    if "bench_args" in config_cols:
        args = row.get("bench_args_str") or "-"
        parts.append(f"args={args}")
    return " | ".join(parts) or "default"


def prepare_case(
    index,
    case_name: str | None,
    *,
    config_columns: Sequence[str],
    primary_metric: str,
    metrics: Sequence[str],
) -> dict:
    df = ensure_dataframe(index).copy()
    if not len(df):
        return {
            "case_name": case_name or "",
            "df": df,
            "config_order": [],
            "summary_table": None,
            "unit_label": None,
        }

    if case_name is None:
        case_name = str(df["case"].iloc[0]) if "case" in df.columns else ""

    df = df[df["case"] == case_name].copy()
    if not len(df):
        return {
            "case_name": case_name,
            "df": df,
            "config_order": [],
            "summary_table": None,
            "unit_label": None,
        }

    df = _format_tags_and_args(df)
    config_cols = [col for col in config_columns if col in df.columns]
    df["config"] = df.apply(lambda row: build_config_label(row, config_cols), axis=1)

    if primary_metric not in df.columns:
        raise ValueError(f"Primary metric not found: {primary_metric}")

    metric_set = set([primary_metric, *metrics])
    for col in metric_set:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=[primary_metric])

    unit_label = None
    if "unit" in df.columns and len(df):
        unit_label = df["unit"].mode().iloc[0]

    config_order = (
        df.groupby("config")[primary_metric]
        .median()
        .sort_values()
        .index.tolist()
    )

    summary_table = (
        df.groupby("config")[primary_metric]
        .agg(run_count="count", median="median", min="min", max="max")
        .sort_values("median")
    )

    return {
        "case_name": case_name,
        "df": df,
        "config_order": config_order,
        "summary_table": summary_table,
        "unit_label": unit_label,
    }


def apply_config_display(
    df: pd.DataFrame,
    config_order: Sequence[str],
    *,
    label_max: int = 40,
) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    label_map = dict(zip(config_order, unique_short_labels(config_order, max_len=label_max)))
    out = df.copy()
    out["config_display"] = out["config"].map(label_map)
    display_order = [label_map[cfg] for cfg in config_order]
    return out, display_order, label_map


def build_profile(
    df: pd.DataFrame,
    *,
    configs: Sequence[str],
    metrics: Sequence[str],
) -> pd.DataFrame:
    if not configs or not metrics:
        return pd.DataFrame()
    return (
        df[df["config"].isin(configs)]
        .groupby("config")[list(metrics)]
        .median()
        .reset_index()
        .melt(id_vars=["config"], var_name="metric", value_name="value")
    )


def plot_summary(
    result: dict,
    *,
    metric: str,
    hue_value: str | None = None,
    label_max: int = 32,
) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    df = result.get("df")
    if df is None or df.empty:
        return

    plot_df = df.copy()
    hue_col = None
    if hue_value:
        plot_df, hue_col = build_hue_display(
            plot_df,
            hue_value,
            label_max=label_max,
        )

    case_order = result.get("case_order") or []
    fig_width = max(8, 0.6 * len(case_order) + 4)
    plt.figure(figsize=(fig_width, 4))
    sns.boxplot(data=plot_df, x="case", y=metric, order=case_order, showfliers=False)
    sns.stripplot(
        data=plot_df,
        x="case",
        y=metric,
        order=case_order,
        hue=hue_col,
        dodge=bool(hue_col),
        size=4,
        alpha=0.8,
    )
    unit_label = result.get("unit_label")
    ylabel = metric + (f" ({unit_label})" if unit_label else "")
    plt.ylabel(ylabel)
    plt.title(f"Summary by case ({metric})")
    plt.xticks(rotation=25, ha="right")
    if hue_col:
        plt.legend(title=hue_value, bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    else:
        plt.legend([], [], frameon=False)
    plt.tight_layout()
    plt.show()


def render_summary(
    *,
    index,
    summary_out,
    summary_metric,
    summary_hue,
    summary_lab,
    summary_tag,
    summary_max_cases,
    summary_label_max,
) -> None:
    from IPython.display import display, clear_output

    with summary_out:
        clear_output(wait=True)
        metric = summary_metric.value
        if not metric:
            print("No metric selected.")
            return
        filter_lab = None if summary_lab.value == "(all)" else summary_lab.value
        filter_tag = summary_tag.value.strip() or None
        max_cases = int(summary_max_cases.value) if summary_max_cases.value else None

        try:
            result = prepare_summary(
                index,
                metric,
                filter_lab=filter_lab,
                filter_tag=filter_tag,
                max_cases=max_cases,
            )
        except Exception as exc:
            print(f"Summary error: {exc}")
            return

        if result["df"].empty:
            print("No rows to plot after filtering.")
            return

        display(result["summary_table"])

        hue_value = summary_hue.value
        plot_summary(
            result,
            metric=metric,
            hue_value=None if hue_value == "(none)" else hue_value,
            label_max=int(summary_label_max.value),
        )


def render_case(
    *,
    index,
    case_out,
    case_name_widget,
    case_primary_metric,
    case_metrics_widget,
    case_config_fields,
    case_max_configs,
    case_label_max,
) -> None:
    from IPython.display import display, clear_output

    with case_out:
        clear_output(wait=True)
        case_name = case_name_widget.value
        primary_metric = case_primary_metric.value
        metrics = list(case_metrics_widget.value)
        config_cols = list(case_config_fields.value)
        label_max = int(case_label_max.value)
        max_configs = int(case_max_configs.value)

        try:
            result = prepare_case(
                index,
                case_name,
                config_columns=config_cols,
                primary_metric=primary_metric,
                metrics=metrics,
            )
        except Exception as exc:
            print(f"Case analysis error: {exc}")
            return

        df = result["df"]
        case_name = result["case_name"]
        if df.empty:
            print(f"No runs found for case: {case_name!r}")
            return

        config_order = result["config_order"]
        label_map, _display_order = plot_case_distribution(
            df,
            config_order=config_order,
            primary_metric=primary_metric,
            unit_label=result["unit_label"],
            label_max=label_max,
            title=f"{case_name} by configuration ({primary_metric})",
        )

        summary_table = result["summary_table"]
        if summary_table is not None:
            table = summary_table.reset_index()
            table["config_display"] = table["config"].map(label_map)
            table = table[
                ["config_display", "config", "run_count", "median", "min", "max"]
            ]
            display(table)

        metrics = [m for m in metrics if m in df.columns]
        if metrics:
            top_configs = config_order[:max_configs] if max_configs else config_order
            profile = build_profile(df, configs=top_configs, metrics=metrics)
            if len(profile):
                profile["config_display"] = profile["config"].map(label_map)
                plot_profile(
                    profile,
                    unit_label=result["unit_label"],
                    title=f"{case_name} quantile profile (top {len(top_configs)})",
                )


def plot_case_distribution(
    df: pd.DataFrame,
    *,
    config_order: Sequence[str],
    primary_metric: str,
    unit_label: str | None = None,
    label_max: int = 40,
    title: str | None = None,
) -> tuple[dict[str, str], list[str]]:
    import matplotlib.pyplot as plt
    import seaborn as sns

    df, display_order, label_map = apply_config_display(
        df,
        config_order,
        label_max=label_max,
    )

    xlabel = primary_metric + (f" ({unit_label})" if unit_label else "")
    fig_height = max(3, 0.4 * len(display_order) + 2)
    plt.figure(figsize=(8, fig_height))
    sns.boxplot(
        data=df,
        y="config_display",
        x=primary_metric,
        order=display_order,
        showfliers=False,
    )
    sns.stripplot(
        data=df,
        y="config_display",
        x=primary_metric,
        order=display_order,
        size=4,
        alpha=0.8,
    )
    plt.xlabel(xlabel)
    plt.ylabel("")
    if title:
        plt.title(title)
    else:
        plt.title(f"{primary_metric} by configuration")
    plt.tight_layout()
    plt.show()

    return label_map, display_order


def plot_profile(
    profile: pd.DataFrame,
    *,
    unit_label: str | None = None,
    title: str | None = None,
) -> None:
    if profile.empty:
        return
    import matplotlib.pyplot as plt
    import seaborn as sns

    plt.figure(figsize=(8, 4))
    sns.lineplot(
        data=profile,
        x="metric",
        y="value",
        hue="config_display",
        marker="o",
    )
    plt.ylabel(unit_label or "ns")
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.show()
