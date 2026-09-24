#!/usr/bin/env python3
"""Compatibility entrypoint. Now accepts plan.json --out-dir; never runs a baked-in example."""
import argparse
from render_template import render
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('plan'); p.add_argument('--out-dir',required=True); a=p.parse_args(); render(a.plan,a.out_dir)
