import html, json, re, subprocess, sys
from pathlib import Path

here = Path(__file__).parent
svgs = json.loads(subprocess.check_output([sys.executable, str(here / "build.py")]))
guide = (here.parent / "project-guide.md").read_text()

sections = [
    ("architecture", "01 · Where everything runs", "One cluster inside Docker",
     "Everything runs in one k3s node inside Docker. Traefik owns port 443 and sends each path to the right service. The gateway is the only part on the request path, and it reads its APIs from MongoDB, not from the Management API.",
     [("coral", "Key points", ["The gateway never calls the Management API to serve traffic.", "If the Management API stops, /ping still works.", "The Console is only a web page. The browser loads it from /console, then calls the Management API through /management.", "Two gateway pods and a PodDisruptionBudget keep /ping up during a rolling update."]),
      ("ink", "Why Traefik", ["It ships with k3s, so there is nothing extra to install.", "ingress-nginx is archived.", "One entrypoint serves the Console and the gateway."]),
      ("muted", "Numbers", ["1.6 CPU and 2.5 GB requested.", "About 3.9 GB used when idle.", "About 1.9 GB of images."])]),
    ("request", "02 · One request", "GET /ping, step by step",
     "Traefik decrypts TLS and passes plain HTTP to a gateway pod. The gateway finds the API by its path, checks the flow, and calls pong. A POST matches no flow, and matchRequired: true makes the gateway answer 404.",
     [("coral", "Key points", ["Anyone can call /ping. The caller sends no API key or password.", "The flow is a filter that only matches GET.", "The body is exactly pong, with no newline, because nginx uses return 200 'pong'."]),
      ("ink", "Edge cases", ["/ping/extra reaches pong, which answers its own 404.", "/pingx matches no API, so the gateway answers 404.", "POST /ping gets 404 from the gateway."])]),
    ("config", "03 · How the API gets there", "From YAML to the gateway",
     "The API is a Kubernetes object, so it lives in git like everything else. The operator turns it into a REST call to the Management API, which saves it in MongoDB. Every gateway polls MongoDB and loads the new API within seconds.",
     [("coral", "Key points", ["syncFrom: MANAGEMENT puts the API in MongoDB, so it also shows in the Console.", "The operator writes processingStatus: Completed, and up.sh waits for it.", "If it fails, up.sh prints the operator's own error message."]),
      ("ink", "If MongoDB stops", ["Gateways keep serving the APIs they already loaded.", "New or changed APIs do not arrive.", "Sync errors show in the gateway logs."])]),
    ("make-up", "04 · One command up", "What make up does, in order",
     "Every step waits for the one before it. Each step either installs with helm upgrade --install, applies a file, or creates a secret only if it is missing. That is what makes the script safe to run twice.",
     [("coral", "Key points", ["make test runs make up again and checks that no pod restarted.", "Every kubectl and helm call names --context k3d-gravitee, so no other cluster is touched.", "Helm keeps its cache and config in .helm/ inside the project."]),
      ("ink", "Two waits that matter", ["The operator creates its CRDs only when it starts, so step 6 waits for them.", "The operator's webhook can refuse calls for a few seconds after start. Step 8 retries only that error."])]),
    ("security", "05 · Security", "Who may talk to whom",
     "Port 443 listens only on 127.0.0.1, so other machines cannot reach it. Inside the cluster, NetworkPolicies decide who may connect. make test proves it with two probe pods: one has the gateway labels, one does not.",
     [("coral", "Key points", ["Only the gateway may call pong, so nobody can bypass it.", "Only Gravitee pods may reach MongoDB on 27017.", "The MongoDB password and the token key are generated on the first run and never touch git."]),
      ("ink", "Also hardened", ["Every pod runs as non-root with all capabilities dropped.", "The chart's sample users are removed.", "The chart's public token signing key is replaced with a random one."]),
      ("muted", "Honest gap", ["Console login is still admin/admin, the chart default.", "It is item 1 on the production list."])]),
    ("production", "06 · Before production", "Today versus production",
     "The demo uses production settings where they fit on one laptop. These four changes and two additions are what a real environment still needs. Each number in the CHANGES list matches the same number on a box or a line in the right panel.",
     [("coral", "First week in production", ["Replace the default logins and put the Console behind SSO.", "Run MongoDB as a replica set with backups.", "Alert on the 5xx ratio and on sync errors."]),
      ("ink", "Why not now", ["Changing the admin password needs a bcrypt hash and more secret wiring, which did not fit the 3 to 4 hour box.", "Elasticsearch is the heaviest part and was optional in the brief."])]),
]

PITCH = "make up builds a one-node Kubernetes cluster in Docker with k3d and installs Gravitee API Management Community Edition: the gateway, the Management API and the Console, with MongoDB as the database. The API itself is a Kubernetes resource that the Gravitee operator publishes. An operator is a small controller program that runs as a pod in the cluster. It reads one kind of Kubernetes object and makes Gravitee's own state match it. So everything is code, and re-running changes nothing. A small nginx backend answers pong, and only the gateway may reach it. TLS comes from cert-manager with a local CA and renews by itself. make test proves the README's claims, and make down removes everything."

CODE_TERMS = sorted(["make up", "make test", "make down", "GET /ping", "POST /ping", "/ping/extra", "/pingx", "/ping",
                     "/console", "/management", "matchRequired: true", "syncFrom: MANAGEMENT", "processingStatus: Completed",
                     "up.sh", "helm upgrade --install", "--context k3d-gravitee", ".helm/", "return 200 'pong'", "admin/admin"],
                    key=len, reverse=True)
CODE_PATTERN = re.compile(r"(?<![\w/-])(" + "|".join(re.escape(term) for term in CODE_TERMS) + r")(?![\w/])")

def prose(text):
    return CODE_PATTERN.sub(r"<code>\1</code>", html.escape(text, quote=False))

def cards(items):
    widths = ["1.15fr", "1fr", "0.85fr"][: len(items)]
    out = [f'<div class="cards" style="grid-template-columns: {" ".join(widths)}">']
    for dot, title, lines in items:
        out.append(f'<div class="card"><div class="card-header"><span class="card-dot {dot}"></span><h3>{title}</h3></div><ul>')
        out += [f"<li>{prose(line)}</li>" for line in lines]
        out.append("</ul></div>")
    out.append("</div>")
    return "\n".join(out)

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

QUESTION = re.compile(r"\*\*[^*]+\*\*( \(.+\))?")

def markdown(source):
    """Covers the subset study-guide.md uses: headings, lists, tables, quotes, fences."""
    out, toc, lines, index = [], [], source.splitlines(), 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            end = lines.index("```", index + 1)
            out.append("<pre>" + html.escape("\n".join(lines[index + 1:end])) + "</pre>")
            index = end + 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip("|").split(" | ")])
                index += 1
            head = "".join(f"<th>{inline(cell)}</th>" for cell in rows[0])
            body_rows = "".join("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in rows[2:])
            out.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>')
            continue
        list_match = re.match(r"(\d+\.|-) ", line)
        if list_match:
            tag = "ol" if line[0].isdigit() else "ul"
            items = []
            while index < len(lines) and re.match(r"(\d+\.|-) ", lines[index]):
                items.append(re.sub(r"^(\d+\.|-) ", "", lines[index]))
                index += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in items) + f"</{tag}>")
            continue
        heading = re.match(r"(#{2,3}) (.+)", line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2)
            anchor = slugify(text)
            if level == 2:
                toc.append((anchor, text))
            out.append(f'<h{level + 1} id="{anchor}">{inline(text)}</h{level + 1}>')
        elif QUESTION.fullmatch(line):
            out.append(f'<p class="question">{inline(line)}</p>')
        elif line.startswith("> "):
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        elif line.strip() and line != "---":
            paragraph = [line]
            while index + 1 < len(lines) and lines[index + 1].strip() and not re.match(r"(#|>|\||```|\d+\. |- )", lines[index + 1]) and not QUESTION.fullmatch(lines[index + 1]):
                index += 1
                paragraph.append(lines[index])
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
        index += 1
    return "\n".join(out), toc

brief_start = guide.index("## What was asked")
brief_end = guide.index("\n---\n", brief_start)
brief_html, _ = markdown(guide[guide.index("\n", brief_start):brief_end])
guide_html, guide_toc = markdown(guide[brief_end + 5:])

body = []
for slug, eyebrow, heading, lead, items in sections:
    body.append(f'''<section id="{slug}">
<p class="eyebrow">{eyebrow}</p>
<h2>{heading}</h2>
<p class="lead">{prose(lead)}</p>
<div class="diagram-container">
{svgs[slug]}
</div>
{cards(items)}
</section>''')

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gravitee-ping: Gravitee API Management on local Kubernetes</title>
<meta name="description" content="How gravitee-ping runs Gravitee API Management on a local Kubernetes cluster: six diagrams and a full written guide.">
<meta name="author" content="Kamil Lelonek">
<meta name="robots" content="noindex">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --color-paper: #f5f5f5; --color-ink: #2d3142; --color-muted: #4f5d75; --color-soft: #5a6580;
  --color-rule: rgba(45,49,66,0.12); --color-accent: #bf4520; --color-link: #2e5aa8;
  --font-sans: 'Geist', system-ui, sans-serif;
  --font-mono: 'Geist Mono', ui-monospace, Menlo, monospace;
}}
body {{ font-family: var(--font-sans); background: var(--color-paper); color: var(--color-ink); padding: 3rem 2rem; }}
.container {{ max-width: 1440px; margin: 0 auto; }}
.eyebrow {{ font-size: 0.78rem; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; color: var(--color-muted); margin-bottom: 0.75rem; }}
h1 {{ font-size: clamp(2rem, 3vw + 1rem, 2.75rem); font-weight: 600; letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 0.75rem; }}
h2 {{ font-size: 1.75rem; font-weight: 600; letter-spacing: -0.01em; margin-bottom: 0.5rem; }}
.subtitle, .lead {{ font-size: 1.1rem; line-height: 1.6; color: var(--color-muted); max-width: 72ch; }}
.lead {{ margin-bottom: 1.5rem; }}
header {{ margin-bottom: 2rem; }}
nav {{ display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; margin: 1.5rem 0 0; font-size: 0.85rem; letter-spacing: 0.04em; }}
nav a {{ color: var(--color-link); text-decoration: none; }}
nav a:hover {{ text-decoration: underline; }}
.pitch {{ background: #ffffff; border: 1px solid var(--color-rule); border-left: 3px solid var(--color-accent); border-radius: 6px; padding: 1.25rem 1.5rem; margin-bottom: 3.5rem; }}
.pitch .quote {{ font-size: 1.15rem; line-height: 1.5; color: var(--color-ink); }}
section {{ margin-bottom: 4rem; padding-top: 2rem; border-top: 1px solid rgba(45,49,66,0.10); }}
.diagram-container {{ width: 100%; overflow-x: auto; }}
svg {{ width: 100%; display: block; }}
@media print {{ .diagram-container {{ overflow-x: visible; }} svg {{ min-width: 0 !important; }} section {{ break-inside: avoid; }} }}
.cards {{ display: grid; gap: 1rem; margin-top: 1.25rem; }}
@media (max-width: 900px) {{ .cards {{ grid-template-columns: 1fr !important; }} }}
.card {{ background: #ffffff; border-radius: 6px; border: 1px solid var(--color-rule); padding: 1.25rem; }}
.card-header {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.875rem; padding-bottom: 0.875rem; border-bottom: 1px solid rgba(45,49,66,0.08); }}
.card-dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}
.card-dot.ink {{ background: var(--color-ink); }} .card-dot.muted {{ background: var(--color-muted); }} .card-dot.coral {{ background: var(--color-accent); }}
.card h3 {{ font-size: 1rem; font-weight: 600; }}
.card ul {{ list-style: none; color: var(--color-ink); font-size: 0.95rem; line-height: 1.6; }}
.card li {{ margin-bottom: 0.35rem; padding-left: 0.875rem; position: relative; }}
.card li::before {{ content: '-'; position: absolute; left: 0; color: rgba(45,49,66,0.35); }}
.toc {{ flex-direction: column; gap: 0.4rem; margin: 0 0 2rem; padding: 1rem 1.25rem; background: #ffffff; border: 1px solid var(--color-rule); border-radius: 6px; max-width: 72ch; }}
article.wide {{ max-width: none; }}
article {{ max-width: 80ch; font-size: 1.02rem; line-height: 1.65; }}
article h3 {{ font-size: 1.4rem; font-weight: 600; margin: 2.75rem 0 0.75rem; padding-top: 1.25rem; border-top: 1px solid rgba(45,49,66,0.10); }}
article h4 {{ font-size: 1.05rem; font-weight: 600; margin: 1.75rem 0 0.5rem; }}
article p, article ul, article ol, article pre, article blockquote, article .table-wrap {{ margin-bottom: 0.9rem; }}
article ul, article ol {{ padding-left: 1.4rem; }}
article li {{ margin-bottom: 0.3rem; }}
code {{ font-family: var(--font-mono); font-size: 0.86em; background: rgba(45,49,66,0.06); padding: 0.05em 0.3em; border-radius: 3px; }}
article pre {{ font-family: var(--font-mono); font-size: 0.82rem; line-height: 1.5; background: #ffffff; border: 1px solid var(--color-rule); border-radius: 6px; padding: 0.9rem 1rem; overflow-x: auto; }}
article blockquote {{ border-left: 3px solid var(--color-accent); padding: 0.25rem 0 0.25rem 1rem; color: var(--color-muted); }}
article .question {{ margin: 1.4rem 0 0.3rem; }}
article strong {{ font-weight: 600; }}
.table-wrap {{ overflow-x: auto; }}
article table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; background: #ffffff; }}
article th, article td {{ border: 1px solid var(--color-rule); padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
article th {{ font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--color-muted); background: var(--color-paper); }}
footer {{ margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(45,49,66,0.10); font-size: 0.72rem; letter-spacing: 0.06em; color: var(--color-soft); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }}
</style>
</head>
<body>
<div class="container">
<header>
<p class="eyebrow">gravitee-ping · Platform engineer exercise · Kamil Lelonek</p>
<h1>Gravitee API Management on local Kubernetes</h1>
<nav><a href="#brief">00 · The brief</a> {" ".join(f'<a href="#{slug}">{eyebrow}</a>' for slug, eyebrow, *_ in sections)} <a href="#knowledge-base">07 · Knowledge base</a></nav>
</header>
<div class="pitch">
<p class="eyebrow">In one paragraph</p>
<p class="quote">{prose(PITCH)}</p>
</div>
<section id="brief">
<p class="eyebrow">00 · The brief</p>
<h2>What was asked, and what was delivered</h2>
<p class="lead">Every requirement from the exercise, how it is met, and the file to open to check it.</p>
<article class="wide">
{brief_html}
</article>
</section>
{"".join(body)}
<section id="knowledge-base" class="knowledge">
<p class="eyebrow">07 · Knowledge base</p>
<h2>Everything in words</h2>
<p class="lead">What Gravitee is, the Kubernetes terms, how each part works and why, what production still needs, the problems solved while building it, and answers to design questions and edge cases.</p>
<nav class="toc">{"".join(f'<a href="#{anchor}">{inline(text)}</a>' for anchor, text in guide_toc)}</nav>
<article>
{guide_html}
</article>
</section>
<footer><span>gravitee-ping · Kamil Lelonek · October 2026</span><span>source: github.com/KamilLelonek/gravitee-ping (private, access on request)</span></footer>
</div>
</body>
</html>
'''
open(sys.argv[1], "w").write(page)
