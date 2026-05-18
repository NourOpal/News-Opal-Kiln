#!/usr/bin/env python3
"""Rebuild HTML: scans references/winners, references/used, references/X for files.
Runs before each push. Replaces the LAUNCH-VIDEO section in index.html."""

import os, re, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

def list_media(folder):
    if not os.path.isdir(folder):
        return []
    files = []
    for f in sorted(os.listdir(folder)):
        if f.startswith('.'):
            continue
        ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
        if ext in ('mp4', 'mov', 'webm', 'gif', 'jpg', 'jpeg', 'png', 'webp'):
            files.append(f)
    return files


def list_x_folders():
    base = 'references/X'
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        sub = os.path.join(base, name)
        if not os.path.isdir(sub) or name.startswith('.'):
            continue
        screenshot = None
        video = None
        link = ''
        caption = ''
        for f in sorted(os.listdir(sub)):
            low = f.lower()
            if low.startswith('screenshot') or low.startswith('image'):
                screenshot = f
            elif low.startswith('video'):
                video = f
            elif low == 'link.txt':
                with open(os.path.join(sub, f)) as fh:
                    link = fh.read().strip().split('\n')[0]
            elif low == 'caption.txt':
                with open(os.path.join(sub, f)) as fh:
                    caption = fh.read().strip()
        # Fallback: first image/video in folder
        if not screenshot:
            for f in sorted(os.listdir(sub)):
                low = f.lower()
                if low.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                    screenshot = f
                    break
        if not video:
            for f in sorted(os.listdir(sub)):
                if f.lower().endswith(('.mp4', '.mov', '.webm')):
                    video = f
                    break
        if screenshot or video:
            out.append({'name': name, 'screenshot': screenshot, 'video': video, 'link': link, 'caption': caption})
    return out


def card_for_media(path, label, num, kind='media'):
    ext = path.rsplit('.', 1)[-1].lower()
    is_video = ext in ('mp4', 'mov', 'webm')
    encoded = urllib.parse.quote(path)
    if is_video:
        # We'd need a thumbnail. For now show video tag with controls.
        media = f'<video src="{encoded}" controls muted playsinline preload="metadata" style="width:100%;height:100%;object-fit:cover;display:block;background:#000"></video>'
    else:
        media = f'<img src="{encoded}" loading="lazy" alt="" style="width:100%;height:100%;object-fit:cover;display:block">'
    return f'''<a class="card" href="{encoded}" target="_blank" rel="noopener"><div class="card-img r-tall" style="position:relative;background:#1a1a18">{media}</div><div class="card-meta mono"><strong>{label}</strong><span>{num}</span></div></a>'''


def card_for_xfolder(item, idx):
    name = item['name']
    num = f'{idx+1:02d}'
    label = name
    href = item['link'] or f"references/X/{urllib.parse.quote(name)}/"
    screenshot = item['screenshot']
    video = item['video']

    media_parts = []
    if screenshot:
        s_url = f"references/X/{urllib.parse.quote(name)}/{urllib.parse.quote(screenshot)}"
        media_parts.append(f'<img src="{s_url}" loading="lazy" alt="" style="width:100%;height:100%;object-fit:cover;display:block">')
    if video:
        v_url = f"references/X/{urllib.parse.quote(name)}/{urllib.parse.quote(video)}"
        media_parts.append(f'<a href="{v_url}" target="_blank" rel="noopener" style="position:absolute;bottom:10px;right:10px;background:rgba(0,0,0,.78);color:#fff;padding:5px 10px;border-radius:999px;font-family:monospace;font-size:10px;text-decoration:none">▶ video</a>')
    caption_html = f'<div style="margin-top:4px;font-size:12px;color:#666;line-height:1.4">{item["caption"]}</div>' if item['caption'] else ''
    return f'''<a class="card" href="{href}" target="_blank" rel="noopener"><div class="card-img r-tall" style="position:relative;background:#1a1a18">{"".join(media_parts)}</div><div class="card-meta mono"><strong>X / {label}</strong><span>{num}</span></div>{caption_html}</a>'''


winners = list_media('references/winners')
used = list_media('references/used')
xfolders = list_x_folders()

winners_html = '\n'.join(card_for_media(f'references/winners/{f}', 'Win', f'{i+1:02d}') for i, f in enumerate(winners)) or '<p style="color:#999;font-size:13px">Empty. Drop files into references/winners/ to populate.</p>'
used_html = '\n'.join(card_for_media(f'references/used/{f}', 'Used', f'{i+1:02d}') for i, f in enumerate(used)) or '<p style="color:#999;font-size:13px">Empty. Drop files into references/used/ to populate.</p>'
x_html = '\n'.join(card_for_xfolder(x, i) for i, x in enumerate(xfolders)) or '<p style="color:#999;font-size:13px">Empty. Create one folder per tweet inside references/X/ to populate. See README inside that folder for naming convention.</p>'


# Inject into index.html — find the launch-video markers and replace between them
with open('index.html') as f:
    html = f.read()

block = f'''<!-- BEGIN AUTO-GENERATED LAUNCH VIDEO -->
<section class="sec" id="winners">
  <div class="sec-bar"><span class="sec-label mono">B / Winners</span><span class="sec-count mono">{len(winners)} files</span></div>
  <h2 class="sec-title">Half 1 — the people winning the AI era.</h2>
  <p class="sec-blurb">B-roll for Kenneth's "they work at superhuman speed, make money in their sleep" beats. Indie hackers shipping, founders making real money, productivity wins, solo entrepreneurs.</p>
  <div class="masonry">
{winners_html}
  </div>
</section>

<section class="sec" id="used">
  <div class="sec-bar"><span class="sec-label mono">C / The Used</span><span class="sec-count mono">{len(used)} files</span></div>
  <h2 class="sec-title">Half 2 — the people being used by it.</h2>
  <p class="sec-blurb">B-roll for "tired, behind, distracted, scrolling through someone else's life on a phone or a terminal window they can't put down." AI burnout, doomscroll exhaustion, Claude usage cap complaints, screen time confessions.</p>
  <div class="masonry">
{used_html}
  </div>
</section>

<section class="sec" id="xfolders">
  <div class="sec-bar"><span class="sec-label mono">X / Tweet refs</span><span class="sec-count mono">{len(xfolders)} tweets</span></div>
  <h2 class="sec-title">X tweets — screenshots and videos saved.</h2>
  <p class="sec-blurb">One folder per tweet under <code>references/X/&lt;handle&gt;/</code>. Drop a screenshot.png, optional video.mp4, optional link.txt + caption.txt. They auto-render.</p>
  <div class="masonry">
{x_html}
  </div>
</section>
<!-- END AUTO-GENERATED LAUNCH VIDEO -->'''

new_html = re.sub(r'<!-- BEGIN AUTO-GENERATED LAUNCH VIDEO -->.*?<!-- END AUTO-GENERATED LAUNCH VIDEO -->', block, html, count=1, flags=re.DOTALL)
if new_html == html:
    # Markers not in file yet — inject after the part-one divider
    new_html = re.sub(r'(<section class="part-divider" id="part-one">.*?</section>)', r'\1\n\n' + block, html, count=1, flags=re.DOTALL)

with open('index.html', 'w') as f:
    f.write(new_html)

print(f'Built: {len(winners)} winners, {len(used)} used, {len(xfolders)} X folders')
