"""Inspect the packaged sticker library and resolve self-authored transparent assets."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
CATALOG_PATH=ROOT/'assets/stickers/catalog.json'


def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding='utf8'))


def resolve(sticker_id):
    entries=[item for section in catalog().values() for item in section]
    found=[item for item in entries if item['id']==sticker_id]
    if len(found)!=1:raise ValueError('Unknown or duplicated sticker id')
    item=dict(found[0]);relative=item.get('path')
    if relative:
        path=(ROOT/relative).resolve()
        if ROOT not in path.parents or not path.is_file():raise ValueError('Sticker asset missing or outside skill')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Sticker asset hash mismatch')
        with Image.open(path) as image:
            if image.mode!='RGBA':raise ValueError('Sticker needs transparent RGBA art')
            alpha=image.getchannel('A')
            if alpha.getextrema()!=(0,255):raise ValueError('Sticker needs transparent RGBA art')
            corners=((0,0),(image.width-1,0),(0,image.height-1),
                     (image.width-1,image.height-1))
            if any(alpha.getpixel(p)!=0 for p in corners):
                raise ValueError('Sticker corners must be fully transparent')
            if sum(alpha.histogram()[:255]) < image.width*image.height*.1:
                raise ValueError('Sticker appears to have a flattened background')
        item['path']=str(path)
    return item


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('list','resolve','validate'))
    p.add_argument('id',nargs='?');p.add_argument('--section',choices=('privacy','emphasis','decorative'))
    args=p.parse_args();c=catalog()
    if args.command=='resolve':
        if not args.id:p.error('resolve requires an id')
        result=resolve(args.id)
    elif args.command=='list':
        result=[{'section':section,**entry} for section,entries in c.items()
                if not args.section or args.section==section for entry in entries]
    else:
        ids=[x['id'] for items in c.values() for x in items]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate sticker id')
        for ident in ids:resolve(ident)
        result={'valid':True,'entries':len(ids),'privacy':len(c['privacy']),'decorative':len(c['decorative'])}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
