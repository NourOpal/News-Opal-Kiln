#!/usr/bin/env python3
"""Rebuild Launch Video sections from X/Good side and X/Bad Side folders."""

import os, re, urllib.parse  # noqa

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
        elif low.endswith('.rtf'):
            # Extract first URL from RTF (people drop links into Notes/TextEdit)
            try:
                with open(os.path.join(folder_path, f), 'rb') as fh:
                    rtf = fh.read().decode('utf-8', errors='ignore')
                m = re.search(r'https?://[^\s}\\"\']+', rtf)
                if m and not link:
                    link = m.group(0).rstrip('?,.;')
            except: pass

    # Find PDF as fallback source link
    pdf_link = None
    for f in os.listdir(folder_path):
        if f.lower().endswith('.pdf'):
            pdf_link = f'{base_url_path}/{urllib.parse.quote(f)}'
            break

    cards = []
    if len(videos) > 1:
        # Multi-video folder (e.g. TikTok Videos) — one card per video
        for i, vid in enumerate(videos):
            cards.append({
                'label': name,
                'sub': f'{i+1:02d}',
                'image': None,
                'video': f'{base_url_path}/{urllib.parse.quote(vid)}',
                'link': link or pdf_link or f'{base_url_path}/{urllib.parse.quote(vid)}',
                'caption': caption,
            })
    elif len(images) > 1 and not videos:
        # Multi-image folder (Terminal etc.) — ONE clustered card with an internal grid
        cards.append({
            'label': name,
            'sub': f'{len(images)} images',
            'cluster': [f'{base_url_path}/{urllib.parse.quote(img)}' for img in images],
            'image': f'{base_url_path}/{urllib.parse.quote(images[0])}',
            'video': None,
            'link': link or pdf_link or f'{base_url_path}/{urllib.parse.quote(images[0])}',
            'caption': caption,
        })
    elif images or videos:
        cards.append({
            'label': name,
            'sub': '',
            'image': f'{base_url_path}/{urllib.parse.quote(images[0])}' if images else None,
            'video': f'{base_url_path}/{urllib.parse.quote(videos[0])}' if videos else None,
            'link': link or pdf_link or (f'{base_url_path}/{urllib.parse.quote(videos[0])}' if videos else f'{base_url_path}/{urllib.parse.quote(images[0])}' if images else '#'),
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

    # CLUSTERED card: multiple images inside a single tile (Terminal etc.)
    if c.get('cluster'):
        urls_json = '[' + ','.join(f'"{u}"' for u in c['cluster']) + ']'
        title_attr = c['label'].replace('"', '&quot;')
        # Clicking any thumb opens the cluster lightbox showing all images + download buttons
        cluster_thumbs = ''.join(
            f'<div onclick="openCluster({urls_json}, &quot;{title_attr}&quot;)" style="cursor:pointer;aspect-ratio:1/1;overflow:hidden;background:#000;border-radius:2px"><img src="{u}" loading="lazy" alt="" style="width:100%;height:100%;object-fit:cover;display:block"></div>'
            for u in c['cluster']
        )
        n = len(c['cluster'])
        col_count = min(n, 3)
        sub_label = f'<span>{c["sub"]}</span>'
        dl_buttons = ''.join(
            f'<a href="{u}" download class="card-btn">↓ {i+1:02d}</a>'
            for i, u in enumerate(c['cluster'])
        )
        return f'''<div class="card cluster-card"><div onclick='openCluster({urls_json}, "{title_attr}")' style="cursor:pointer;display:grid;grid-template-columns:repeat({col_count},1fr);gap:4px;background:#1a1a18;padding:4px;border-radius:4px">{cluster_thumbs}</div><div class="card-meta mono" style="margin-top:10px"><strong>{c["label"]}</strong>{sub_label}</div><div class="card-btns"><a href="#" onclick='openCluster({urls_json}, "{title_attr}"); return false;' class="card-btn">⊞ Open all</a>{dl_buttons}</div></div>'''

    # Pick the image: prefer screenshot, else video thumbnail
    img_src = c['image']
    if not img_src and c['video']:
        img_src = video_thumb_url(c['video'])

    img_html = f'<img src="{img_src}" loading="lazy" alt="" style="width:100%;height:100%;object-fit:cover;display:block">' if img_src else ''
    caption_html = f'<div style="margin-top:5px;font-size:12px;color:#666;line-height:1.4">{c["caption"]}</div>' if c['caption'] else ''
    sub_label = f'<span>{c["sub"] or num}</span>'

    # Two explicit buttons: Video + Source (X/article)
    buttons = []
    if c['video']:
        buttons.append(f'<a href="{c["video"]}" target="_blank" rel="noopener" class="card-btn">▶ Video</a>')
    if c['link']:
        # Detect source label from URL
        link = c['link']
        if 'x.com' in link or 'twitter.com' in link:
            label = '𝕏 Tweet'
        elif 'reddit.com' in link:
            label = 'Reddit'
        elif 'tiktok.com' in link:
            label = 'TikTok'
        elif 'apps.apple.com' in link:
            label = 'App Store'
        elif 'theguardian.com' in link:
            label = 'Guardian'
        elif 'nytimes.com' in link:
            label = 'NYT'
        else:
            label = 'Source'
        buttons.append(f'<a href="{link}" target="_blank" rel="noopener" class="card-btn">↗ {label}</a>')
    btns_html = f'<div class="card-btns">{"".join(buttons)}</div>' if buttons else ''

    # Card image opens the image full-size; buttons handle video + link
    image_href = img_src or c['video'] or c['link'] or '#'
    return f'''<div class="card"><a href="{image_href}" target="_blank" rel="noopener"><div class="card-img {ratio}" style="position:relative;background:#1a1a18">{img_html}</div></a><div class="card-meta mono"><strong>{c["label"]}</strong>{sub_label}</div>{caption_html}{btns_html}</div>'''


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
  <h2 class="sec-title">Half 1, the winners.</h2>
  <p class="sec-blurb"><strong>B-roll for "they work at superhuman speed, make money in their sleep, learn faster, time again."</strong> Fast patchwork, tasteful, not chaotic.</p>
  <div style="background:#fff;border-radius:8px;padding:20px 24px;margin-bottom:24px;max-width:780px;font-size:13.5px;line-height:1.55;color:#1a1a1a">
    <div class="mono" style="color:#888;margin-bottom:10px">Editing direction</div>
    <p style="margin-bottom:8px"><strong>Highlight one number or phrase per card.</strong> "$4,200 in one weekend", "raised $1 million", "$1.8 billion company".</p>
    <p style="margin-bottom:8px"><strong>How:</strong> highlight however reads best (underline, box, zoom, dim the rest). 0.5 to 1 second, then cut.</p>
    <p style="margin-bottom:0"><strong>Cards with video:</strong> show the tweet, cut into the video, or layer the video over the tweet. Mix it up. See Algo folder for inspo.</p>
  </div>
  <div class="masonry">
{winners_html}
  </div>
</section>

<section class="sec" id="used">
  <div class="sec-bar"><span class="sec-label mono">C / The Used</span><span class="sec-count mono">{len(used)} refs</span></div>
  <h2 class="sec-title">Half 2, the used.</h2>
  <p class="sec-blurb"><strong>B-roll for "tired, behind, distracted, scrolling through someone else's life on a phone or a terminal window they can't put down."</strong> Fast patchwork, tasteful, not chaotic.</p>
  <div style="background:#fff;border-radius:8px;padding:20px 24px;margin-bottom:24px;max-width:780px;font-size:13.5px;line-height:1.55;color:#1a1a1a">
    <div class="mono" style="color:#888;margin-bottom:10px">Editing direction</div>
    <p style="margin-bottom:8px"><strong>Highlight one phrase per article.</strong> "today's teenagers are sleeping less than ever", "birth rates falling everywhere all at once", "Jury finds Meta and Google negligent".</p>
    <p style="margin-bottom:8px"><strong>How:</strong> highlight however reads best (underline, box, zoom, dim the rest). 0.5 to 1 second, then cut.</p>
    <p style="margin-bottom:0"><strong>Stack:</strong> bed-scroll video underneath, article headlines fading over it. Terminal montage, five screens fast. Cut.</p>
  </div>
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
