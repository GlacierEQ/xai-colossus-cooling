#!/usr/bin/env python3
"""
apex_cli.py
GlacierEQ APEX Stack | APEX Ring 0
Author: Casey Barton

APEX Command-Line Interface — Blueprint generation engine.
Runs cross-platform (Mac, Linux, Windows). No AutoCAD license required.

Usage:
  python apex_cli.py blueprint           # Generate all formats (DXF + PDF + PNG)
  python apex_cli.py blueprint --pdf     # PDF only
  python apex_cli.py blueprint --svg     # SVG only
  python apex_cli.py blueprint --all     # DXF + PDF + SVG + PNG
  python apex_cli.py blueprint --sheet CCL-003 --rows 6 --cols 10
  python apex_cli.py sherlock            # Start SHERLOCK-SUPERNOVA live pipeline
  python apex_cli.py status              # Check repo + connector health
  python apex_cli.py --help
"""

from __future__ import annotations
import argparse
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='[APEX] %(levelname)s -- %(message)s'
)
logger = logging.getLogger('APEX-CLI')

APEX_BANNER = """
╔═════════════════════════════════════════════╗
║  ⚡ APEX SOVEREIGN STACK — GlacierEQ             ║
║  Author : Casey Barton                           ║
║  Mission: xAI Colossus Cooling — Ring 0         ║
╚═════════════════════════════════════════════╝
"""


def cmd_blueprint(args):
    """Generate engineering blueprints from APEX parameters."""
    sys.path.insert(0, os.path.dirname(__file__))
    from connectors.autocad_connector import mcp_action_draw_ccl002

    formats = []
    if args.all:
        formats = ['dxf', 'pdf', 'svg', 'png']
    elif args.pdf:
        formats = ['pdf']
    elif args.svg:
        formats = ['svg']
    elif args.png:
        formats = ['png']
    elif args.dxf:
        formats = ['dxf']
    else:
        formats = ['dxf', 'pdf', 'png']  # default

    sheet = args.sheet or 'CCL-002'
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_base = args.output or f"{sheet}_Underfloor_Piping_Plan"

    print(APEX_BANNER)
    print(f"  Generating blueprint: {sheet}")
    print(f"  Formats: {', '.join(f.upper() for f in formats)}")
    print(f"  Zone grid: {args.rows} rows x {args.cols} cols")
    print(f"  Supply: {args.supply}°C  |  Return: {args.ret}°C")
    print(f"  Output base: {output_base}\n")

    result = mcp_action_draw_ccl002({
        "output_path":     output_base + ".dxf",
        "supply_temp_c":   args.supply,
        "return_temp_c":   args.ret,
        "zone_rows":       args.rows,
        "zone_cols":       args.cols,
        "prefer_com":      False,
        "export_formats":  formats,
    })

    print("\n=== BLUEPRINT OUTPUTS ===")
    for fmt, path in result['outputs'].items():
        if path and os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"  ✅ [{fmt.upper():4s}] {path}  ({size_kb:.1f} KB)")
        elif path:
            print(f"  ⚠️  [{fmt.upper():4s}] {path}  (not found)")
    print("=========================")
    print("\n⚡ APEX Blueprint generation complete.\n")


def cmd_sherlock(args):
    """Start SHERLOCK-SUPERNOVA live anomaly detection pipeline."""
    print(APEX_BANNER)
    print("  🔍 Starting SHERLOCK-SUPERNOVA...")
    print("  Subscribing to Supabase colossus_thermal_events")
    print("  Ring: -3 | Observe only | Physics gate downstream\n")
    sys.path.insert(0, os.path.dirname(__file__))
    from connectors.sherlock_supernova_webhook import SherlockWebhookPipeline
    pipeline = SherlockWebhookPipeline()
    pipeline.subscribe()


def cmd_status(args):
    """Check APEX connector health."""
    print(APEX_BANNER)
    print("  📊 APEX Stack Status\n")
    checks = [
        ("ezdxf",        "import ezdxf"),
        ("matplotlib",   "import matplotlib"),
        ("supabase",     "from supabase import create_client"),
        ("duckdb",       "import duckdb"),
        ("notion-client","import notion_client"),
        ("sklearn",      "from sklearn.ensemble import IsolationForest"),
        ("numpy",        "import numpy"),
        ("pandas",       "import pandas"),
    ]
    all_ok = True
    for name, imp in checks:
        try:
            exec(imp)
            print(f"  ✅  {name}")
        except ImportError:
            print(f"  ❌  {name}  (pip install {name})")
            all_ok = False

    env_checks = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'NOTION_TOKEN', 'MOTHERDUCK_TOKEN']
    print()
    for var in env_checks:
        val = os.getenv(var)
        status = "✅" if val else "❌  NOT SET"
        print(f"  {status}  {var}")

    print()
    if all_ok:
        print("  ⚡ All systems nominal. APEX is ready.\n")
    else:
        print("  ⚠️  Some dependencies missing. Run: pip install -r requirements.txt\n")


def main():
    parser = argparse.ArgumentParser(
        prog='apex',
        description='APEX APEX Stack CLI — GlacierEQ / xAI Colossus Cooling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python apex_cli.py blueprint
  python apex_cli.py blueprint --all --sheet CCL-003
  python apex_cli.py blueprint --pdf --rows 6 --cols 12
  python apex_cli.py sherlock
  python apex_cli.py status"""
    )
    subparsers = parser.add_subparsers(dest='command', help='APEX command')

    # --- blueprint ---
    bp = subparsers.add_parser('blueprint', help='Generate engineering blueprints')
    bp.add_argument('--all',    action='store_true', help='Export all formats: DXF+PDF+SVG+PNG')
    bp.add_argument('--pdf',    action='store_true', help='PDF output only')
    bp.add_argument('--svg',    action='store_true', help='SVG output only')
    bp.add_argument('--png',    action='store_true', help='PNG output only')
    bp.add_argument('--dxf',    action='store_true', help='DXF output only')
    bp.add_argument('--sheet',  type=str,   default='CCL-002', help='Sheet number (default: CCL-002)')
    bp.add_argument('--rows',   type=int,   default=4,    help='Zone rows (default: 4)')
    bp.add_argument('--cols',   type=int,   default=8,    help='Zone cols (default: 8)')
    bp.add_argument('--supply', type=float, default=16.0, help='Supply temp °C (default: 16.0)')
    bp.add_argument('--ret',    type=float, default=26.0, help='Return temp °C (default: 26.0)')
    bp.add_argument('--output', type=str,   default=None, help='Output base filename')
    bp.set_defaults(func=cmd_blueprint)

    # --- sherlock ---
    sh = subparsers.add_parser('sherlock', help='Start SHERLOCK-SUPERNOVA anomaly detection')
    sh.set_defaults(func=cmd_sherlock)

    # --- status ---
    st = subparsers.add_parser('status', help='Check APEX stack health')
    st.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        print(APEX_BANNER)
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == '__main__':
    main()
