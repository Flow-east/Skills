"""Fail-closed source/output aspect decision, before encoding any frames."""
from fractions import Fraction


def source_display_ratio(video_stream):
    sw, sh = int(video_stream['width']), int(video_stream['height'])
    if sw <= 0 or sh <= 0:
        raise ValueError('Invalid source video dimensions')
    sar = video_stream.get('sample_aspect_ratio', '1:1')
    try:
        num, den = (int(v) for v in sar.split(':')) if sar and sar != 'N/A' else (1, 1)
        if num <= 0 or den <= 0: raise ValueError()
    except (ValueError, AttributeError):
        raise ValueError('Unrecognized source sample aspect ratio; inspect video before choosing frame_fit')
    rotation = int(video_stream.get('tags', {}).get('rotate', 0))
    for side in video_stream.get('side_data_list', []):
        if 'rotation' in side: rotation = int(side['rotation'])
    ratio = Fraction(sw * num, sh * den)
    if rotation % 180: ratio = 1 / ratio
    return ratio, (sw,sh), f'{num}:{den}', rotation


def audit(plan, video_stream):
    ratio,(sw,sh),sar,rotation=source_display_ratio(video_stream)
    target = Fraction(plan.get('width', 720), plan.get('height', 1280))
    mismatch = abs(float(ratio / target) - 1) > 0.005
    fit = plan.get('frame_fit')
    if mismatch and fit is None:
        raise ValueError('Source/output aspect mismatch: explicitly choose frame_fit native (matching dimensions), cover (crop) or contain (bars); no silent padding')
    if fit == 'native' and mismatch:
        raise ValueError('frame_fit native requires output aspect ratio matching source')
    if mismatch and fit in ('cover', 'contain') and not str(plan.get('frame_fit_reason', '')).strip():
        raise ValueError('Aspect-changing cover/contain requires frame_fit_reason with visual justification')
    return dict(source_dimensions=[sw, sh], source_sar=sar, source_rotation=rotation,
                source_display_ratio=round(float(ratio), 6), output_dimensions=[plan.get('width', 720), plan.get('height', 1280)],
                mode=fit or 'native', mismatch=mismatch, reason=plan.get('frame_fit_reason'),
                legacy_default=fit is None)
