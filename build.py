#!/usr/bin/env python3
"""Rebuild Launch Video sections from X/Good side and X/Bad Side folders."""

import os, re, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
VID_EXT = ('.mp4', '.mov', '.webm', '.m4v')


def scan_named_folder(folder_path, base_url_path):
    """Scan a named subfolder (e.g. 'HeyClicky') for screenshot + video.
    Returns one card dict, or multiple if the folder has many images (e.g. Reddit posts/).
    """
    if not os.path.isdir(folder_path):
        return []
    name = os.path.basename(folder_path)
    images = []
    videos = []
    link = ''
    caption = ''
    for f in sorted(os.listdir(folder_path)):
        if f.startswith('.'):
            continue
        low = f.lower()
        if low.endswith(IMG_EXT):
            images.append(f)
        elif low.endswith(VID_EXT):
            videos.append(f)
        elif low == 'link.txt':
            try:
                with open(os.path.join(folder_path, f)) as fh:
                    link = fh.read().strip().split('\n')[0]
            except: pass
        elif low == 'caption.txt':
            try:
                with open(os.path.join(folder_path, f)) as fh:
                    caption = fh.read().strip()
            except: pass

    cards = []
    if len(images) > 1 and not videos:
        # Treat each image as separate card (e.g. Reddit posts/1.png, 2.png...)
        for i, img in enumerate(images):
            cards.append({
                'label': name,
                'sub': f'{i+1:02d}',
                'image': f'{base_url_path}/{urllib.parse.quote(img)}',
                'video': None,
                'link': link or f'{base_url_path}/{urllib.parse.quote(img)}',
                'caption': caption,
            })
    elif images or videos:
        cards.append({
            'label': name,
            'sub': '',
            'image': f'{base_url_path}/{urllib.parse.quote(images[0])}' if images else None,
            'video': f'{base_url_path}/{urllib.parse.quote(videos[0])}' if videos else None,
            'link': link or (f'{base_url_path}/{urllib.parse.quote(videos[0])}' if videos else f'{base_url_path}/{urllib.parse.quote(images[0])}' if images else '#'),
            'caption': caption,
        })
    return cards


def scan_side(side_dir):
    """Scan e.g. X/Good side/ — each subfolder is a tweet/source."""
    if not os.path.isdir(side_dir):
        return []
    cards = []
    for entry in sorted(os.listdir(side_dir)):
        sub = os.path.join(side_dir, entry)
        if not os.path.isdir(sub) or entry.startswith('.'):
            continue
        base_url = f'X/{urllib.parse.quote(os.path.basename(side_dir))}/{urllib.parse.quote(entry)}'
        cards.extend(scan_named_folder(sub, base_url))
    return cards


def video_thumb_url(video_url):
    """Map X/foo/bar/baz.mp4 → X-thumbs/foo/bar/baz.jpg (with URL-decoding then re-encoding)."""
    if not video_url:
        return None
    decoded = urllib.parse.unquote(video_url)
    if not decoded.startswith('X/'):
        return None
    rel = decoded[2:]  # strip X/
    base = rel.rsplit('.', 1)[0]
    candidate_path = os.path.join('X-thumbs', base + '.jpg')
    if os.path.exists(candidate_path):
        return 'X-thumbs/' + urllib.parse.quote(base + '.jpg')
    return None


def render_card(c, idx):
    ratios = ['r-tall', 'r-portrait', 'r-square', 'r-landscape', 'r-tall', 'r-portrait', 'r-landscape', 'r-square']
    ratio = ratios[idx % len(ratios)]
    num = f'{idx+1:02d}'
    href = c['link']

    # Pick the image: prefer screenshot, else video thumbnail
    img_src = c['image']
    if not img_src and c['video']:
        img_src = video_thumb_url(c['video'])

    img_html = f'<img src="{img_src}" loading="lazy" alt="" style="width:100%;height:100%;object-fit:cover;display:block">' if img_src else ''
    video_badge = ''
    if c['video']:
        video_badge = f'<a href="{c["video"]}" target="_blank" rel="noopener" style="position:absolute;bottom:10px;right:10px;background:rgba(0,0,0,.85);color:#fff;padding:6px 11px;border-radius:999px;font-family:monospace;font-size:10px;text-decoration:none;letter-spacing:0.08em;text-transform:uppercase">▶ video</a>'
    caption_html = f'<div style="margin-top:5px;font-size:12px;color:#666;line-height:1.4">{c["caption"]}</div>' if c['caption'] else ''
    sub_label = f'<span>{c["sub"] or num}</span>'
    return f'''<a class="card" href="{href}" target="_blank" rel="noopener"><div class="card-img {ratio}" style="position:relative;background:#1a1a18">{img_html}{video_badge}</div><div class="card-meta mono"><strong>{c["label"]}</strong>{sub_label}</div>{caption_html}</a>'''


winners = scan_side('X/Good side')
used = scan_side('X/Bad Side')

# Also include any media in references/winners and references/used (free-drop files)
def scan_loose(folder, label):
    if not os.path.isdir(folder):
        return []
    cards = []
    for f in sorted(os.listdir(folder)):
        if f.startswith('.'):
            continue
        low = f.lower()
        if low.endswith(IMG_EXT + VID_EXT):
            url = f'{folder}/{urllib.parse.quote(f)}'
            cards.append({
                'label': label,
                'sub': '',
                'image': url if low.endswith(IMG_EXT) else None,
                'video': url if low.endswith(VID_EXT) else None,
                'link': url,
                'caption': '',
            })
    return cards

winners += scan_loose('references/winners', 'Win')
used += scan_loose('references/used', 'Used')

winners_html = '\n'.join(render_card(c, i) for i, c in enumerate(winners)) or '<p style="color:#999;font-size:13px">Empty.</p>'
used_html = '\n'.join(render_card(c, i) for i, c in enumerate(used)) or '<p style="color:#999;font-size:13px">Empty.</p>'

with open('index.html') as f:
    html = f.read()

block = f'''<!-- BEGIN AUTO-GENERATED LAUNCH VIDEO -->
<section class="sec" id="winners">
  <div class="sec-bar"><span class="sec-label mono">B / Winners</span><span class="sec-count mono">{len(winners)} refs</span></div>
  <h2 class="sec-title">Half 1 — the people winning the AI era.</h2>
  <p class="sec-blurb">B-roll for Kenneth's "they work at superhuman speed, make money in their sleep" beats. Indie hackers shipping, founders making real money, productivity wins. Each card links to the saved file or source URL.</p>
  <div class="masonry">
{winners_html}
  </div>
</section>

<section class="sec" id="used">
  <div class="sec-bar"><span class="sec-label mono">C / The Used</span><span class="sec-count mono">{len(used)} refs</span></div>
  <h2 class="sec-title">Half 2 — the people being used by it.</h2>
  <p class="sec-blurb">B-roll for "tired, behind, distracted, scrolling through someone else's life on a phone or a terminal window they can't put down." AI burnout, doomscroll exhaustion, sleep-deprivation studies, Reddit phone-overuse confessions, screen-time stats.</p>
  <div class="masonry">
{used_html}
  </div>
</section>
<!-- END AUTO-GENERATED LAUNCH VIDEO -->'''

new_html = re.sub(r'<!-- BEGIN AUTO-GENERATED LAUNCH VIDEO -->.*?<!-- END AUTO-GENERATED LAUNCH VIDEO -->', block, html, count=1, flags=re.DOTALL)
if new_html == html:
    # Markers not in file — insert after part-one divider
    new_html = re.sub(r'(<section class="part-divider" id="part-one">.*?</section>)', r'\1\n\n' + block, html, count=1, flags=re.DOTALL)

with open('index.html', 'w') as f:
    f.write(new_html)

print(f'Built: {len(winners)} winners cards, {len(used)} used cards')
print('\nWinners:')
for c in winners:
    print(f'  {c["label"]}{(" #" + c["sub"]) if c["sub"] else ""}')
print('Used:')
for c in used:
    print(f'  {c["label"]}{(" #" + c["sub"]) if c["sub"] else ""}')
