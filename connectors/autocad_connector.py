#!/usr/bin/env python3
"""
connectors/autocad_connector.py
GlacierEQ APEX Stack | APEX Ring 0
Author: Casey Barton
Purpose: Programmatic AutoCAD control via COM (Windows) + ezdxf (cross-platform)
         Generates CCL-002 Underfloor Piping Plan — DXF, PDF, SVG, PNG outputs.

MCP Integration: Expose draw_ccl002() as a Notion-triggered MCP action.
Dependency: pip install ezdxf matplotlib
Optional COM path: pip install pywin32 pyautocad  (Windows + licensed AutoCAD only)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import ezdxf
from ezdxf import colors

logger = logging.getLogger("CONNECTOR-AUTOCAD")

LAYERS = {
    "CCL-PIPE-SUPPLY": {
        "color": colors.BLUE,
        "linetype": "CONTINUOUS",
        "lineweight": 50,
    },
    "CCL-PIPE-RETURN": {
        "color": colors.RED,
        "linetype": "CONTINUOUS",
        "lineweight": 50,
    },
    "CCL-PIPE-DRAIN": {"color": colors.YELLOW, "linetype": "DASHED", "lineweight": 25},
    "CCL-EQUIPMENT": {
        "color": colors.GREEN,
        "linetype": "CONTINUOUS",
        "lineweight": 35,
    },
    "CCL-ANNOTATIONS": {
        "color": colors.WHITE,
        "linetype": "CONTINUOUS",
        "lineweight": 18,
    },
    "CCL-DIMENSIONS": {
        "color": colors.CYAN,
        "linetype": "CONTINUOUS",
        "lineweight": 18,
    },
    "CCL-GRID": {"color": 8, "linetype": "DOTTED", "lineweight": 13},
    "CCL-TITLEBLOCK": {
        "color": colors.WHITE,
        "linetype": "CONTINUOUS",
        "lineweight": 70,
    },
    "_SHADOW_VALIDATION": {"color": 8, "linetype": "CONTINUOUS", "lineweight": 0},
}


@dataclass
class PipeRun:
    start: tuple
    end: tuple
    layer: str
    diameter_mm: float
    label: str = ""


@dataclass
class CCL002Config:
    sheet_width: float = 841.0
    sheet_height: float = 594.0
    scale: float = 50.0
    zone_rows: int = 4
    zone_cols: int = 8
    rack_spacing_x: float = 1200.0
    rack_spacing_y: float = 800.0
    supply_temp_c: float = 16.0
    return_temp_c: float = 26.0
    pipe_runs: list = field(default_factory=list)
    project_name: str = "xAI Colossus Cooling"
    sheet_number: str = "CCL-002"
    drawn_by: str = "Casey Barton / APEX"
    date: str = "2026-05-16"


class AutoCADConnector:
    """
    Dual-path AutoCAD connector.
    Path A: COM automation via pyautocad (Windows + licensed AutoCAD)
    Path B: ezdxf cross-platform DXF + PDF/SVG/PNG export (no license, any OS)
    """

    def __init__(self, prefer_com: bool = False):
        self.acad = None
        self.prefer_com = prefer_com
        if prefer_com:
            self._init_com()

    def _init_com(self):
        try:
            import win32com.client

            self.acad = win32com.client.Dispatch("AutoCAD.Application")
            self.acad.Visible = True
            logger.info("AutoCAD COM connection established.")
        except Exception as e:
            logger.warning(f"COM unavailable ({e}). Falling back to ezdxf.")
            self.acad = None

    def setup_layers(self, doc) -> None:
        for name, props in LAYERS.items():
            if name not in doc.layers:
                layer = doc.layers.new(name)
                layer.color = props["color"]
                layer.linetype = props.get("linetype", "CONTINUOUS")
                layer.lineweight = props.get("lineweight", 25)
        logger.info(f"Layers configured: {list(LAYERS.keys())}")

    def draw_title_block(self, msp, cfg: CCL002Config) -> None:
        tb = "CCL-TITLEBLOCK"
        msp.add_lwpolyline(
            [
                (0, 0),
                (cfg.sheet_width, 0),
                (cfg.sheet_width, cfg.sheet_height),
                (0, cfg.sheet_height),
            ],
            close=True,
            dxfattribs={"layer": tb},
        )
        msp.add_lwpolyline(
            [
                (cfg.sheet_width - 180, 0),
                (cfg.sheet_width, 0),
                (cfg.sheet_width, 55),
                (cfg.sheet_width - 180, 55),
            ],
            close=True,
            dxfattribs={"layer": tb},
        )
        for text, x, y in [
            (cfg.project_name, cfg.sheet_width - 90, 42),
            (f"Sheet: {cfg.sheet_number}", cfg.sheet_width - 90, 30),
            (f"Scale 1:{int(cfg.scale)}", cfg.sheet_width - 90, 19),
            (f"Date: {cfg.date}", cfg.sheet_width - 90, 9),
            (f"By: {cfg.drawn_by}", cfg.sheet_width - 90, 2),
        ]:
            msp.add_text(
                text,
                height=3.5,
                dxfattribs={"layer": "CCL-ANNOTATIONS", "insert": (x, y)},
            )

    def draw_rack_grid(self, msp, cfg: CCL002Config) -> None:
        origin_x, origin_y = 25.0, 70.0
        sf = 1.0 / cfg.scale
        for row in range(cfg.zone_rows):
            for col in range(cfg.zone_cols):
                x = origin_x + col * (cfg.rack_spacing_x * sf + 5)
                y = origin_y + row * (cfg.rack_spacing_y * sf + 5)
                w = cfg.rack_spacing_x * sf
                h = cfg.rack_spacing_y * sf
                msp.add_lwpolyline(
                    [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                    close=True,
                    dxfattribs={"layer": "CCL-EQUIPMENT"},
                )
                msp.add_text(
                    f"R{row + 1:02d}-{col + 1:02d}",
                    height=2.5,
                    dxfattribs={
                        "layer": "CCL-ANNOTATIONS",
                        "insert": (x + w / 2, y + h / 2),
                    },
                )

    def draw_pipe_runs(self, msp, cfg: CCL002Config) -> None:
        sf = 1.0 / cfg.scale
        origin_x, origin_y = 25.0, 70.0
        if not cfg.pipe_runs:
            col_end = origin_x + cfg.zone_cols * (cfg.rack_spacing_x * sf + 5)
            cfg.pipe_runs = [
                PipeRun(
                    (origin_x - 10, origin_y),
                    (origin_x - 10, origin_y + cfg.zone_rows * 25),
                    "CCL-PIPE-SUPPLY",
                    250.0,
                    f"DN250 CWS {cfg.supply_temp_c}C",
                ),
                PipeRun(
                    (col_end + 5, origin_y),
                    (col_end + 5, origin_y + cfg.zone_rows * 25),
                    "CCL-PIPE-RETURN",
                    250.0,
                    f"DN250 CWR {cfg.return_temp_c}C",
                ),
            ]
            for row in range(cfg.zone_rows):
                y = origin_y + row * 25 + 8
                cfg.pipe_runs.append(
                    PipeRun(
                        (origin_x - 10, y),
                        (col_end + 5, y),
                        "CCL-PIPE-SUPPLY",
                        100.0,
                        f"DN100 Row {row + 1}",
                    )
                )
        for run in cfg.pipe_runs:
            msp.add_line(run.start, run.end, dxfattribs={"layer": run.layer})
            if run.label:
                mid_x = (run.start[0] + run.end[0]) / 2
                mid_y = (run.start[1] + run.end[1]) / 2 + 1.5
                msp.add_text(
                    run.label,
                    height=2.0,
                    dxfattribs={"layer": "CCL-ANNOTATIONS", "insert": (mid_x, mid_y)},
                )

    def export_pdf(self, doc, output_path: str) -> str:
        """Export DXF doc to print-ready A3 PDF via matplotlib backend."""
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

            with PdfPages(output_path) as pdf:
                fig = plt.figure(
                    figsize=(16.54, 11.69), facecolor="white"
                )  # A3 landscape
                ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
                ax.set_facecolor("white")
                ctx = RenderContext(doc)
                out = MatplotlibBackend(ax)
                Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)
                ax.set_title(
                    "CCL-002 Underfloor Piping Plan | GlacierEQ APEX | Casey Barton",
                    fontsize=8,
                    color="#333333",
                    pad=4,
                )
                pdf.savefig(fig, dpi=300, bbox_inches="tight")
                plt.close(fig)
            logger.info(f"PDF blueprint exported: {output_path}")
            return output_path
        except ImportError as e:
            logger.warning(f"PDF export skipped (pip install matplotlib): {e}")
            return ""

    def export_svg(self, doc, output_path: str) -> str:
        """Export DXF doc to SVG via matplotlib backend."""
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

            fig = plt.figure(figsize=(16.54, 11.69), facecolor="white")
            ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
            ax.set_facecolor("white")
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)
            fig.savefig(output_path, format="svg", dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info(f"SVG blueprint exported: {output_path}")
            return output_path
        except ImportError as e:
            logger.warning(f"SVG export skipped (pip install matplotlib): {e}")
            return ""

    def export_png(self, doc, output_path: str, dpi: int = 300) -> str:
        """Export DXF doc to high-res PNG."""
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

            fig = plt.figure(figsize=(16.54, 11.69), facecolor="white")
            ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
            ax.set_facecolor("white")
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)
            fig.savefig(output_path, format="png", dpi=dpi, bbox_inches="tight")
            plt.close(fig)
            logger.info(f"PNG blueprint exported: {output_path} @ {dpi}dpi")
            return output_path
        except ImportError as e:
            logger.warning(f"PNG export skipped (pip install matplotlib): {e}")
            return ""

    def draw_ccl002(
        self,
        output_path: str = "CCL-002_Underfloor_Piping_Plan.dxf",
        cfg: Optional[CCL002Config] = None,
        export_formats: list = None,
    ) -> dict:
        """Generate CCL-002 Underfloor Piping Plan. MCP-callable.
        Returns dict with paths for all requested formats.
        export_formats: list of 'dxf','pdf','svg','png' — default ['dxf','pdf','png']
        """
        if cfg is None:
            cfg = CCL002Config()
        if export_formats is None:
            export_formats = ["dxf", "pdf", "png"]

        doc = ezdxf.new(dxfversion="R2018")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        self.setup_layers(doc)
        self.draw_title_block(msp, cfg)
        self.draw_rack_grid(msp, cfg)
        self.draw_pipe_runs(msp, cfg)
        msp.add_text(
            "SHADOW_OK:RING-3:APEX",
            height=1.0,
            dxfattribs={"layer": "_SHADOW_VALIDATION", "insert": (0, -5)},
        )

        base = str(Path(output_path).with_suffix(""))
        outputs = {}

        if "dxf" in export_formats:
            dxf_path = base + ".dxf"
            doc.saveas(dxf_path)
            outputs["dxf"] = dxf_path
            logger.info(f"DXF saved: {dxf_path}")

        if "pdf" in export_formats:
            outputs["pdf"] = self.export_pdf(doc, base + ".pdf")

        if "svg" in export_formats:
            outputs["svg"] = self.export_svg(doc, base + ".svg")

        if "png" in export_formats:
            outputs["png"] = self.export_png(doc, base + ".png")

        return outputs


def mcp_action_draw_ccl002(params: dict) -> dict:
    """APEX MCP / CLI callable.
    params: {output_path, supply_temp_c, return_temp_c, zone_rows, zone_cols,
             prefer_com, export_formats}
    """
    cfg = CCL002Config(
        supply_temp_c=params.get("supply_temp_c", 16.0),
        return_temp_c=params.get("return_temp_c", 26.0),
        zone_rows=params.get("zone_rows", 4),
        zone_cols=params.get("zone_cols", 8),
    )
    connector = AutoCADConnector(prefer_com=params.get("prefer_com", False))
    outputs = connector.draw_ccl002(
        output_path=params.get("output_path", "CCL-002_Underfloor_Piping_Plan.dxf"),
        cfg=cfg,
        export_formats=params.get("export_formats", ["dxf", "pdf", "png"]),
    )
    return {"status": "success", "outputs": outputs, "ring": 0}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = mcp_action_draw_ccl002({})
    print("\n=== APEX BLUEPRINT GENERATOR ===")
    for fmt, path in result["outputs"].items():
        if path:
            print(f"  [{fmt.upper()}] {path}")
    print("================================")
