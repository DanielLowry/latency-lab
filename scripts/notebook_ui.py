#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import asyncio

import ipywidgets as widgets
from IPython.display import clear_output, display

import notebook_runner as nb


DEFAULT_ITERS = 10000
# Warmup iterations are discarded before measurement to stabilize caches, CPU state, etc.
DEFAULT_WARMUP = 1000
DEFAULT_PIN_CPU = 0

CHECKBOX_WIDTH = "28px"
CASE_WIDTH = "180px"
ITERS_WIDTH = "120px"
WARMUP_WIDTH = "120px"
AFFINITY_WIDTH = "190px"
PIN_WIDTH = "110px"
INPUT_STYLE = {"description_width": "0px"}


class RunnerUI:
    def __init__(
        self,
        *,
        bench_path: Path,
        results_dir: Path,
        auto_load: bool = True,
    ) -> None:
        self.bench_path = Path(bench_path)
        self.results_dir = Path(results_dir)
        self.case_rows: dict[str, dict] = {}
        self.output = widgets.Output()

        self.status = widgets.HTML("")
        self.filter_text = widgets.Text(value="", description="Filter")
        self.lab = widgets.Text(value="os", description="Lab")
        self.tags = widgets.Text(value="", description="Tags (csv)")
        self.tags_help = widgets.HTML(
            "Tags are free-form labels used only for naming runs and filtering results."
        )
        self.noise_off = widgets.Checkbox(value=True, description="off")
        self.noise_free = widgets.Checkbox(value=False, description="free")
        self.noise_same = widgets.Checkbox(value=False, description="same (pinned)")
        self.noise_other = widgets.Checkbox(value=False, description="other (pinned)")
        self.noise_box = widgets.HBox(
            [
                widgets.HTML("<b>Noise</b>"),
                self.noise_off,
                self.noise_free,
                self.noise_same,
                self.noise_other,
            ],
            layout=widgets.Layout(align_items="center", gap="10px"),
        )
        self.noise_help = widgets.HTML(
            "Noise runs a background spinner during warmup/measurement. "
            "Same/other require pinned runs."
        )
        self.update_mode = widgets.RadioButtons(
            options=[
                ("Append (default)", "append"),
                ("Skip summary/index", "skip"),
                ("Replace matching in index", "replace"),
            ],
            value="append",
            description="Update",
        )
        self.warmup_help = widgets.HTML(
            "Warmup runs are discarded before measurement to stabilize CPU/cache state."
        )
        self.select_all = widgets.Button(description="Select all")
        self.deselect_all = widgets.Button(description="Deselect all")
        self.run_button = widgets.Button(description="Run selected")

        self.rows_box = widgets.VBox(
            [],
            layout=widgets.Layout(
                max_height="260px",
                overflow_y="auto",
                overflow_x="hidden",
            ),
        )
        self.cases_header = widgets.HBox(
            [
                widgets.HTML("&nbsp;", layout=widgets.Layout(width=CHECKBOX_WIDTH)),
                widgets.HTML("<b>Case</b>", layout=widgets.Layout(width=CASE_WIDTH)),
                widgets.HTML("<b>Iters</b>", layout=widgets.Layout(width=ITERS_WIDTH)),
                widgets.HTML("<b>Warmup</b>", layout=widgets.Layout(width=WARMUP_WIDTH)),
                widgets.HTML(
                    "<b>Affinity</b>", layout=widgets.Layout(width=AFFINITY_WIDTH)
                ),
                widgets.HTML("<b>Pin CPU</b>", layout=widgets.Layout(width=PIN_WIDTH)),
            ],
            layout=widgets.Layout(align_items="center"),
        )

        if auto_load:
            self._load_cases()
        self._wire_events()

    def load_cases(self) -> None:
        self._load_cases()

    def _load_cases(self) -> None:
        self.status.value = "<em>Loading cases...</em>"
        try:
            cases = nb.list_cases(self.bench_path)
        except Exception as exc:
            cases = ["noop"]
            self.status.value = (
                f"<b>Could not list cases:</b> {exc}<br>"
                f"Build bench at {self.bench_path} to populate the list."
            )
        else:
            self.status.value = ""

        self.case_rows = {name: self._make_case_row(name) for name in cases}
        self.rows_box.children = [entry["row"] for entry in self.case_rows.values()]
        self._apply_filter()

    def _make_affinity_group(self, label: str, value: bool):
        checkbox = widgets.Checkbox(
            value=value,
            description="",
            indent=False,
            layout=widgets.Layout(width="18px", margin="0px"),
        )
        text = widgets.Label(
            value=label,
            layout=widgets.Layout(margin="0px 6px 0px 0px"),
        )
        group = widgets.HBox(
            [checkbox, text],
            layout=widgets.Layout(align_items="center", gap="2px"),
        )
        return checkbox, group

    def _make_case_row(self, name: str) -> dict:
        enabled = widgets.Checkbox(
            value=False,
            description="",
            layout=widgets.Layout(width=CHECKBOX_WIDTH),
        )
        case_label = widgets.Label(
            value=name,
            layout=widgets.Layout(width=CASE_WIDTH),
        )
        iters = widgets.IntText(
            value=DEFAULT_ITERS,
            description="",
            layout=widgets.Layout(width=ITERS_WIDTH),
            style=INPUT_STYLE,
        )
        warmup = widgets.IntText(
            value=DEFAULT_WARMUP,
            description="",
            layout=widgets.Layout(width=WARMUP_WIDTH),
            style=INPUT_STYLE,
        )

        affinity_unpinned, unpinned_group = self._make_affinity_group("unpinned", True)
        affinity_pinned, pinned_group = self._make_affinity_group("pinned", True)
        affinity_box = widgets.HBox(
            [unpinned_group, pinned_group],
            layout=widgets.Layout(
                width=AFFINITY_WIDTH,
                justify_content="flex-start",
                align_items="center",
                gap="4px",
                overflow="visible",
            ),
        )

        pin_cpu = widgets.IntText(
            value=DEFAULT_PIN_CPU,
            description="",
            layout=widgets.Layout(width=PIN_WIDTH),
            style=INPUT_STYLE,
        )

        def sync_affinity(_=None):
            needs_pin = affinity_pinned.value
            pin_cpu.disabled = not needs_pin
            if needs_pin and pin_cpu.value < 0:
                pin_cpu.value = 0

        affinity_pinned.observe(sync_affinity, names="value")
        sync_affinity()

        row = widgets.HBox(
            [enabled, case_label, iters, warmup, affinity_box, pin_cpu],
            layout=widgets.Layout(align_items="center", overflow="visible"),
        )
        return {
            "name": name,
            "row": row,
            "enabled": enabled,
            "iters": iters,
            "warmup": warmup,
            "affinity_unpinned": affinity_unpinned,
            "affinity_pinned": affinity_pinned,
            "pin_cpu": pin_cpu,
        }

    def _apply_filter(self, _=None) -> None:
        query = self.filter_text.value.strip().lower()
        if not query:
            visible = [entry["row"] for entry in self.case_rows.values()]
        else:
            visible = [
                entry["row"]
                for name, entry in self.case_rows.items()
                if query in name.lower()
            ]
        self.rows_box.children = visible

    def _select_all_clicked(self, _):
        for entry in self.case_rows.values():
            entry["enabled"].value = True

    def _deselect_all_clicked(self, _):
        for entry in self.case_rows.values():
            entry["enabled"].value = False

    @staticmethod
    def _affinity_variants(unpinned: bool, pinned: bool, pin_value: int):
        variants = []
        if unpinned:
            variants.append(("unpinned", None))
        if pinned:
            variants.append((f"pinned cpu {pin_value}", pin_value))
        return variants

    def _noise_variants(self):
        variants = []
        if self.noise_off.value:
            variants.append(("noise off", "off"))
        if self.noise_free.value:
            variants.append(("noise free", "free"))
        if self.noise_same.value:
            variants.append(("noise same", "same"))
        if self.noise_other.value:
            variants.append(("noise other", "other"))
        return variants

    def _run_clicked(self, _):
        with self.output:
            clear_output()
            selected = [
                entry for entry in self.case_rows.values() if entry["enabled"].value
            ]
            if not selected:
                print("No cases selected.")
                return
            tag_list = [t.strip() for t in self.tags.value.split(",") if t.strip()]
            noise_variants = self._noise_variants()
            if not noise_variants:
                print("Select at least one noise option.")
                return

            total_runs = 0
            for entry in selected:
                variants = self._affinity_variants(
                    entry["affinity_unpinned"].value,
                    entry["affinity_pinned"].value,
                    entry["pin_cpu"].value,
                )
                for _label, pin in variants:
                    for _noise_label, noise_mode in noise_variants:
                        if noise_mode in ("same", "other") and pin is None:
                            continue
                        total_runs += 1
            if total_runs == 0:
                print("No valid combinations (noise same/other require pinning).")
                return

            run_idx = 0
            for entry in selected:
                case_name = entry["name"]
                iters_value = entry["iters"].value
                warmup_value = entry["warmup"].value
                unpinned = entry["affinity_unpinned"].value
                pinned = entry["affinity_pinned"].value
                pin_value = entry["pin_cpu"].value
                if pinned and pin_value < 0:
                    print(
                        f"{case_name}: Pin CPU must be >= 0 when affinity includes pinned."
                    )
                    continue
                variants = self._affinity_variants(unpinned, pinned, pin_value)
                if not variants:
                    print(f"{case_name}: Select at least one affinity option.")
                    continue
                for label, pin in variants:
                    for noise_label, noise_mode in noise_variants:
                        if noise_mode in ("same", "other") and pin is None:
                            continue
                        run_idx += 1
                        suffix_parts = [label, noise_label]
                        suffix = (
                            f" ({', '.join(suffix_parts)})"
                            if total_runs > 1
                            else ""
                        )
                        print(f"[{run_idx}/{total_runs}] {case_name}{suffix}")
                        try:
                            result = nb.run_case(
                                bench_path=self.bench_path,
                                lab=self.lab.value,
                                case=case_name,
                                results_dir=self.results_dir,
                                iters=iters_value,
                                warmup=warmup_value,
                                pin_cpu=pin,
                                noise_mode=noise_mode,
                                tags=tag_list,
                                update_mode=self.update_mode.value,
                            )
                        except Exception as exc:
                            print(f"Run failed for {case_name}: {exc}")
                            continue
                        print(f"Run dir: {result.run_dir}")
                        print(result.read_stdout())

    def _wire_events(self) -> None:
        self.filter_text.observe(self._apply_filter, names="value")
        self.select_all.on_click(self._select_all_clicked)
        self.deselect_all.on_click(self._deselect_all_clicked)
        self.run_button.on_click(self._run_clicked)

    def build(self) -> tuple[widgets.Widget, widgets.Output]:
        ui = widgets.VBox(
            [
                self.status,
                self.filter_text,
                widgets.HBox([self.select_all, self.deselect_all, self.run_button]),
                self.cases_header,
                self.rows_box,
                self.warmup_help,
                self.lab,
                self.tags,
                self.tags_help,
                self.noise_box,
                self.noise_help,
                self.update_mode,
            ]
        )
        return ui, self.output


def build_runner_ui(*, bench_path: Path, results_dir: Path, auto_load: bool = True) -> tuple[widgets.Widget, widgets.Output, RunnerUI]:
    runner = RunnerUI(bench_path=bench_path, results_dir=results_dir, auto_load=auto_load)
    ui, output = runner.build()
    return ui, output, runner


def display_runner_ui(*, bench_path: Path, results_dir: Path, auto_load: bool = True) -> tuple[widgets.Widget, widgets.Output, RunnerUI]:
    ui, output, runner = build_runner_ui(
        bench_path=bench_path,
        results_dir=results_dir,
        auto_load=auto_load,
    )
    display(ui, output)
    if auto_load:
        return ui, output, runner
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.call_soon(runner.load_cases)
        else:
            runner.load_cases()
    except RuntimeError:
        runner.load_cases()
    return ui, output, runner
