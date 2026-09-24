#!/usr/bin/env python3
"""Inspectable template variants; design_status distinguishes a design from review.
A name or a font swap alone is not evidence of an independently designed template."""
import json
from pathlib import Path

def catalog():
    return json.loads((Path(__file__).resolve().parent.parent/'assets/template_catalog.json').read_text())

def get(name):
    c=catalog()
    if name not in c:
        name=next((k for k,v in c.items() if v.get('display_name')==name or v.get('family')==name),name)
    if name not in c: raise ValueError(f'Unknown template variant: {name}; use list_names()')
    from template_contracts import bind
    return bind(dict(c[name],id=name))

def list_names():
    return [{'id':k,'name':v.get('display_name',k),'family':v.get('family','')} for k,v in catalog().items()]
