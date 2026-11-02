"""Gera os painéis dinâmicos do perfil (stats estilo neofetch + cobrinha numa moldura).

Roda no GitHub Actions. Uso: python profile_panels.py <user> <dist_dir>
Requer GITHUB_TOKEN no ambiente. Só usa a biblioteca padrão.
"""
import datetime, html, json, os, re, sys, urllib.request

USER, DIST = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = open(os.path.join(HERE, "jbm.b64")).read().strip()

BG = "#2A211C"
C = dict(p="#E8A0A8", n="#F4C2C2", g="#A8C69F", G="#7FA06E", b="#C9A27E", c="#F5E6D3",
         y="#E6C27A", t="#A68A64", m="#7D6656")
W, FS, CW, LH, PADX, PADY = 894, 13, 7.8, 19, 26, 20
STYLE = (f"<style>@font-face{{font-family:'JBM';src:url(data:font/woff2;base64,{FONT}) format('woff2');}}"
         f"text{{font-family:'JBM',monospace;font-size:{FS}px;white-space:pre;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0}}</style>")


def gql(query, variables):
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": query, "variables": variables}).encode(),
                                 headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        out = json.load(r)
    if "errors" in out:
        raise SystemExit(out["errors"])
    return out["data"]


def fetch():
    q = """query($login:String!){ user(login:$login){
      followers{totalCount}
      contributionsCollection{ totalCommitContributions totalPullRequestContributions restrictedContributionsCount }
      pullRequests{totalCount}
      repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
        totalCount
        nodes{ stargazerCount languages(first:10, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{name} } } }
      } } }"""
    u = gql(q, {"login": USER})["user"]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    cc = u["contributionsCollection"]
    return dict(repos=u["repositories"]["totalCount"],
                stars=sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
                followers=u["followers"]["totalCount"],
                prs=u["pullRequests"]["totalCount"],
                commits=cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
                langs=[(n, s / total) for n, s in top])


CAT = r"""       \`*-.
        )  _`-.
       .  : `. .
       : _   '  \
       ; *` _.   `*-._
       `-.-'          `-.
         ;       `       `.
         :.       .        \
         . \  .   :   .-'   .
         '  `+.;  ;  '      :
         :  '  |    ;       ;-.
         ; '   : :`-:     _.`* ;
 [bug] .*' /  .*' ; .*`- +'  `*'
       `*-*   `*-*  `*-*'""".split("\n")


def t(x, y, runs):
    spans = "".join(f'<tspan fill="{C[k]}">{html.escape(s)}</tspan>' for s, k in runs)
    return f'<text x="{x:.1f}" y="{y:.1f}">{spans}</text>'


def stats_svg(s):
    year = datetime.date.today().year
    rows = len(CAT) + 3
    H = PADY * 2 + rows * LH
    out = [t(PADX, PADY + LH - 5, [("~ $ ", "g"), ("neofetch --github", "c")])]
    y0 = PADY + LH * 3 - 5
    for i, line in enumerate(CAT):
        runs = [(line, "b")]
        if "[bug]" in line:
            a, b_ = line.split("[bug]")
            runs = [(a, "b"), ("[bug]", "p"), (b_, "b")]
        out.append(t(PADX, y0 + i * LH, runs))
    ix = PADX + 40 * CW
    info = [[(f"{USER}", "p"), ("@", "c"), ("github", "p")],
            [("-" * (len(USER) + 7), "m")],
            [("role       ", "g"), ("full-stack · UX/UI · AI", "c")],
            [("repos      ", "g"), (str(s["repos"]), "c")],
            [("stars      ", "g"), (str(s["stars"]), "c")],
            [("commits    ", "g"), (f"{s['commits']} in {year}", "c")],
            [("prs        ", "g"), (str(s["prs"]), "c")],
            [("followers  ", "g"), (str(s["followers"]), "c")],
            [("languages", "g")]]
    for i, r in enumerate(info):
        out.append(t(ix, y0 + i * LH, r))
    ly = y0 + len(info) * LH
    bar_x, bar_w = ix + 13 * CW, 220
    colors = [C["p"], C["g"], C["y"], C["b"], C["n"]]
    for i, (name, frac) in enumerate(s["langs"]):
        yy = ly + i * LH
        out.append(t(ix + 2 * CW, yy, [(name[:10], "c")]))
        out.append(f'<rect x="{bar_x:.1f}" y="{yy - 9}" width="{bar_w}" height="8" rx="4" fill="#3A2E27"/>')
        out.append(f'<rect x="{bar_x:.1f}" y="{yy - 9}" width="{max(6, bar_w * frac):.1f}" height="8" rx="4" fill="{colors[i % 5]}"/>')
        out.append(t(bar_x + bar_w + 12, yy, [(f"{frac * 100:4.1f}%", "t")]))
    py = ly + len(s["langs"]) * LH + 6
    for i, col in enumerate([C["p"], C["n"], C["c"], C["b"], C["g"], C["G"], C["y"]]):
        out.append(f'<rect x="{ix + i * 26:.1f}" y="{py}" width="20" height="12" rx="3" fill="{col}"/>')
    H = max(H, py + 12 + PADY)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{STYLE}'
            f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>{"".join(out)}</svg>')


def snake_panel(path):
    src = open(path).read()
    m = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', src)
    vx, vy, vw, vh = map(float, m.groups())
    inner_w = W - 2 * PADX
    inner_h = inner_w * vh / vw
    top = PADY + LH + 12
    H = int(top + inner_h + PADY)
    src = re.sub(r"<\?xml[^>]*\?>", "", src)
    root = re.search(r"<svg\b[^>]*>", src).group(0)
    new = re.sub(r'\s(width|height)="[^"]*"', "", root)
    new = new.replace("<svg", f'<svg x="{PADX}" y="{top}" width="{inner_w}" height="{inner_h:.1f}"', 1)
    inner = src.replace(root, new, 1)
    head = t(PADX, PADY + LH - 5, [("~ $ ", "g"), ("./garden-snake --eat-contributions", "c")])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{STYLE}'
            f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>{head}{inner}</svg>')


GIFS = {
    "header-ascii.svg": ("https://i.pinimg.com/originals/c6/b2/6a/c6b26ac905cbd299d5011fb7c70e6377.jpg", 676, 104, 180, 175),
    # file in assets/      -> (gif url, x, y, width, height)
    "about.svg": ("https://i.pinimg.com/originals/ca/4e/da/ca4eda573c1568d20f14bf7eb9eecd4a.gif", 620, 36, 248, 290),
    "footer.svg": ("https://media.tenor.com/u3Qr_vUH0uUAAAAj/one-piece-pixel.gif", 36, 40, 136, 136),
}


def embed_gifs(assets_dir):
    import base64
    for name, (url, x, y, w, h) in GIFS.items():
        src = open(os.path.join(assets_dir, name)).read()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = base64.b64encode(urllib.request.urlopen(req, timeout=30).read()).decode()
        mime = "image/jpeg" if url.endswith(".jpg") else "image/gif"
        if mime == "image/jpeg":  # photo-like: rounded card
            cid = "clip" + name.split(".")[0].replace("-", "")
            img = (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16"/></clipPath>'
                   f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" '
                   f'clip-path="url(#{cid})" href="data:{mime};base64,{data}"/>'
                   f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="none" stroke="#F5E6D3" stroke-width="2"/>')
        else:
            img = (f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" '
                   f'style="image-rendering:pixelated" href="data:{mime};base64,{data}"/>')
        open(os.path.join(DIST, name), "w").write(src.replace("</svg>", img + "</svg>"))


if __name__ == "__main__":
    embed_gifs(os.path.join(HERE, "..", "..", "assets"))
    open(os.path.join(DIST, "stats.svg"), "w").write(stats_svg(fetch()))
    snake = os.path.join(DIST, "garden-snake-dark.svg")
    if os.path.exists(snake):
        open(os.path.join(DIST, "garden-snake-panel.svg"), "w").write(snake_panel(snake))
    print("ok")
