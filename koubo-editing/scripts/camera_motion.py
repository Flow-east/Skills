"""Output-clock camera states: semantic holds, explicit cuts, C2 transitions, subpixel sampling.
Does not infer speech semantics or conceal source jump cuts. Captions stay screen-fixed.
"""
import math
from PIL import Image


def smootherstep(x):
    x=max(0.,min(1.,x))
    return x*x*x*(x*(x*6-15)+10)


def validate(track,duration):
    if not isinstance(track,dict) or track.get('time_space')!='output':
        raise ValueError('camera_motion requires explicit output time_space')
    if track.get('curve','smootherstep')!='smootherstep':
        raise ValueError('Unsupported camera curve')
    def finite(n):
        return isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n)
    anchor=track.get('anchor',[.5,.42])
    if not isinstance(anchor,list) or len(anchor)!=2 or not all(finite(x) and 0<=x<=1 for x in anchor):
        raise ValueError('Invalid camera anchor')
    limit=track.get('max_zoom',1.15)
    if not finite(limit) or not 1<=limit<=1.35:
        raise ValueError('Explicit camera max_zoom must stay within 1..1.35')
    keys=track.get('keyframes',[])
    if len(keys)<2: raise ValueError('Camera requires at least two keyframes')
    last=-1.
    for k in keys:
        t=k.get('time');z=k.get('zoom')
        if not finite(t) or not last<t<=duration+1e-6 or t<0:
            raise ValueError('Camera times must be strictly increasing in output duration')
        if not finite(z) or not 1<=z<=limit:
            raise ValueError('Camera zoom exceeds the declared framing limit')
        if k.get('transition','smootherstep') not in ('smootherstep','cut'):
            raise ValueError('Unsupported incoming camera transition')
        last=t
    if abs(keys[0]['time'])>1e-6 or abs(keys[-1]['time']-duration)>1e-6:
        raise ValueError('Camera keyframes must cover the entire output')


def zoom_at(track,t):
    keys=track['keyframes']
    if t<=keys[0]['time']:return keys[0]['zoom']
    for a,b in zip(keys,keys[1:]):
        if t<=b['time']:
            if b.get('transition')=='cut':
                return a['zoom'] if t<b['time'] else b['zoom']
            u=smootherstep((t-a['time'])/(b['time']-a['time']))
            return a['zoom']+(b['zoom']-a['zoom'])*u
    return keys[-1]['zoom']


def crop_box(size,zoom,anchor):
    w,h=size;cw=w/zoom;ch=h/zoom
    # Scaling about this fixed image point keeps it fixed in the output.
    x=(w-cw)*anchor[0];y=(h-ch)*anchor[1]
    return x,y,x+cw,y+ch


def apply(image,track,t):
    z=zoom_at(track,t)
    if abs(z-1)<1e-12:return image
    # float source box avoids integer crop changes on consecutive slow-motion frames.
    return image.resize(image.size,Image.Resampling.LANCZOS,
                        box=crop_box(image.size,z,track.get('anchor',[.5,.42])))


def audit(track,duration,fps,cut_times=()):
    validate(track,duration)
    values=[zoom_at(track,i/fps) for i in range(round(duration*fps))]
    delta=[b-a for a,b in zip(values,values[1:])]
    acceleration=[b-a for a,b in zip(delta,delta[1:])]
    return {'time_space':'output','curve':'per_transition_smootherstep_or_cut',
            'authored_cuts':[k['time'] for k in track['keyframes'] if k.get('transition')=='cut'],
            'declared_max_zoom':track.get('max_zoom',1.15),'sampling':'floating_point_source_box_lanczos',
            'zoom_range':[min(values),max(values)],'max_zoom_step_per_frame':max(map(abs,delta),default=0),
            'max_zoom_second_difference':max(map(abs,acceleration),default=0),
            'cut_boundaries':[{'output_time':t,'zoom_before':zoom_at(track,max(0,t-1/fps)),
                               'zoom_at_cut':zoom_at(track,t),'zoom_after':zoom_at(track,t+1/fps)} for t in cut_times],
            'scope':'Camera transform continuity only; source movement and editorial cuts remain visible'}


def build_track(duration,decisions,recipe,anchor=None):
    """Compile reviewed OUTPUT-time camera decisions; hold until the next decision.
    No automatic return, per-clip resets, or inference of semantics from keywords.
    Each decision: start, level (or zoom), kind=punch/glide/reframe/cut, reason.
    """
    levels=recipe.get('levels',{'normal':1.0})
    current=levels.get('normal',1.0); keys=[dict(time=0.,zoom=current)]
    previous_end=0.; events=[]
    for ev in decisions:
        start=float(ev['start']); kind=ev.get('kind','punch')
        if kind not in ('punch','glide','reframe','cut'):raise ValueError('Unknown camera move kind')
        target=ev.get('zoom',levels.get(ev.get('level')))
        if target is None:raise ValueError('Camera decision needs a known level or zoom')
        if not str(ev.get('reason','')).strip():raise ValueError('Camera decision needs editorial reason')
        if not math.isfinite(start) or start<previous_end or start<0:raise ValueError('Overlapping or unordered camera decisions')
        dt=0. if kind=='cut' else float(ev.get('duration',recipe.get('transitions',{}).get(kind,{}).get('seconds',.4)))
        end=start+dt
        if kind!='cut' and (not math.isfinite(dt) or dt<=0):raise ValueError('Camera transition duration must be positive')
        if end>duration:raise ValueError('Camera decision exceeds final duration')
        if kind=='cut':
            if start<=keys[-1]['time']:raise ValueError('Cut must follow previous camera keyframe')
            keys.append(dict(time=start,zoom=target,transition='cut'))
        else:
            if start>keys[-1]['time']:keys.append(dict(time=start,zoom=current))
            keys.append(dict(time=end,zoom=target,transition='smootherstep'))
        events.append(dict(ev,end=end,from_zoom=current,to_zoom=target))
        current=target;previous_end=end
    if keys[-1]['time']<duration:keys.append(dict(time=duration,zoom=current))
    track=dict(time_space='output',curve='smootherstep',max_zoom=recipe.get('max_zoom',1.15),
               anchor=anchor or recipe.get('anchor',[.5,.42]),keyframes=keys,events=events,
               policy='hold_until_next_authored_decision')
    validate(track,duration)
    return track
