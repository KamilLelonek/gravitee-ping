import html, sys

PAPER = "#f5f5f5"; INK = "#2d3142"; MUTED = "#4f5d75"; SOFT = "#5a6580"
ACCENT = "#bf4520"; LINK = "#2e5aa8"
SANS = "'Geist', system-ui, sans-serif"

STYLES = {
    "focal":    ("rgba(191,69,32,0.08)", ACCENT, "rgba(191,69,32,0.50)", ACCENT),
    "backend":  ("#ffffff", INK, "rgba(45,49,66,0.40)", INK),
    "store":    ("rgba(45,49,66,0.05)", MUTED, "rgba(79,93,117,0.50)", MUTED),
    "service":  ("rgba(45,49,66,0.03)", "rgba(45,49,66,0.30)", "rgba(45,49,66,0.22)", SOFT),
    "external": ("rgba(79,93,117,0.10)", SOFT, "rgba(90,101,128,0.40)", SOFT),
}

def esc(text):
    return html.escape(text, quote=True)

def label_width(text):
    return round(len(text) * 6.5 + 8, 1)

def node(x, y, w, h, kind, tag, name, subs=(), dashed=False, bounds_attr="", badge=None):
    fill, stroke, tag_stroke, tag_text = STYLES[kind]
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>',
           f'<rect{bounds_attr} x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"{dash}/>']
    if tag:
        tag_w = max(24, round(len(tag) * 6.2 + 10))
        out.append(f'<rect x="{x+8}" y="{y+6}" width="{tag_w}" height="13" rx="2" fill="transparent" stroke="{tag_stroke}" stroke-width="0.8"/>')
        out.append(f'<text x="{x+8+tag_w/2}" y="{y+15.5}" fill="{tag_text}" font-size="8" font-family="{SANS}" text-anchor="middle" letter-spacing="0.08em">{esc(tag)}</text>')
    if badge:
        out.append(f'<rect x="{x+w-22}" y="{y+6}" width="14" height="12" rx="2" fill="transparent" stroke="{INK}" stroke-width="0.8"/>')
        out.append(f'<text x="{x+w-15}" y="{y+15.5}" fill="{INK}" font-size="9" font-family="{SANS}" text-anchor="middle">{esc(badge)}</text>')
    center_x = x + w / 2
    count = len(subs)
    name_y = y + h / 2 + (8 if count == 0 else 4 - 8 * (count - 1))
    out.append(f'<text x="{center_x}" y="{name_y}" fill="{INK}" font-size="14" font-weight="600" font-family="{SANS}" text-anchor="middle">{esc(name)}</text>')
    for index, sub in enumerate(subs):
        color = MUTED if index == 0 else SOFT
        out.append(f'<text x="{center_x}" y="{name_y + 16 + 15 * index}" fill="{color}" font-size="10.5" font-family="{SANS}" text-anchor="middle">{esc(sub)}</text>')
    return "\n".join(out)

def arrow_attrs(slug, color, dashed, marker):
    marker_id = {"muted": "arrow", "accent": "arrow-accent", "link": "arrow-link", "stop": "stop", None: None}[marker]
    stroke = {"muted": MUTED, "accent": ACCENT, "link": LINK, "ink": INK}[color]
    dash = ' stroke-dasharray="5,4"' if dashed else ""
    end = f' marker-end="url(#{slug}-{marker_id})"' if marker_id else ""
    return f'fill="none" stroke="{stroke}" stroke-width="1.2"{dash}{end}'

def line(slug, x1, y1, x2, y2, color="muted", dashed=False, marker="muted"):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {arrow_attrs(slug, color, dashed, marker)}/>'

def path(slug, d, color="muted", dashed=False, marker="muted", extra=""):
    return f'<path{extra} d="{d}" {arrow_attrs(slug, color, dashed, marker)}/>'

def label_above(center_x, line_y, text, color=SOFT):
    width = label_width(text)
    return (f'<rect x="{center_x - width/2}" y="{line_y - 21}" width="{width}" height="14" rx="2" fill="{PAPER}"/>'
            f'<text x="{center_x}" y="{line_y - 10.5}" fill="{color}" font-size="9.5" font-family="{SANS}" text-anchor="middle" letter-spacing="0.06em">{esc(text)}</text>')

def label_right(line_x, center_y, text, color=SOFT):
    width = label_width(text)
    return (f'<rect x="{line_x + 8}" y="{center_y - 8}" width="{width}" height="14" rx="2" fill="{PAPER}"/>'
            f'<text x="{line_x + 12}" y="{center_y + 3}" fill="{color}" font-size="9.5" font-family="{SANS}" letter-spacing="0.06em">{esc(text)}</text>')

def zone(x, y, w, h, text):
    width = round(len(text) * 6.6 + 10)
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="rgba(45,49,66,0.02)" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>'
            f'<rect x="{x+8}" y="{y+4}" width="{width}" height="14" rx="2" fill="{PAPER}"/>'
            f'<text x="{x+13}" y="{y+14.5}" fill="{SOFT}" font-size="8.5" font-family="{SANS}" letter-spacing="0.14em">{esc(text)}</text>')

def region(x, y, w, h, text):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="transparent" stroke="rgba(45,49,66,0.18)" stroke-width="1" stroke-dasharray="6,4"/>'
            f'<text x="{x+12}" y="{y+17}" fill="{MUTED}" font-size="9.5" font-weight="500" font-family="{SANS}" letter-spacing="0.12em">{esc(text)}</text>')

def defs(slug):
    return f'''<defs>
<marker id="{slug}-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker>
<marker id="{slug}-arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{ACCENT}"/></marker>
<marker id="{slug}-arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{LINK}"/></marker>
<marker id="{slug}-stop" markerWidth="4" markerHeight="12" refX="2" refY="6" orient="auto"><rect x="1" y="0" width="2" height="12" fill="{INK}"/></marker>
</defs>'''

def svg(slug, width, height, title, desc, body, extra=""):
    return f'''<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc" style="min-width:{width}px"{extra}>
<title id="{slug}-title">{esc(title)}</title>
<desc id="{slug}-desc">{esc(desc)}</desc>
{defs(slug)}
<rect width="100%" height="100%" fill="{PAPER}"/>
{body}
</svg>'''

def legend(y, width, items):
    out = [f'<line x1="24" y1="{y-12}" x2="{width-24}" y2="{y-12}" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>',
           f'<text x="24" y="{y+8}" fill="{MUTED}" font-size="9" font-family="{SANS}" letter-spacing="0.14em">LEGEND</text>']
    x = 100
    for kind, text in items:
        if kind in STYLES or kind == "external-dashed":
            style = STYLES["external" if kind == "external-dashed" else kind]
            dash = ' stroke-dasharray="3,2"' if kind == "external-dashed" else ""
            out.append(f'<rect x="{x}" y="{y}" width="14" height="10" rx="2" fill="{style[0]}" stroke="{style[1]}" stroke-width="1"{dash}/>')
        else:
            color, dashed, marker = kind
            stroke = {"muted": MUTED, "accent": ACCENT, "link": LINK, "ink": INK}[color]
            dash = ' stroke-dasharray="4,3"' if dashed else ""
            out.append(f'<line x1="{x}" y1="{y+5}" x2="{x+16}" y2="{y+5}" stroke="{stroke}" stroke-width="1.2"{dash} marker-end="url(#{marker})"/>')
        out.append(f'<text x="{x+22}" y="{y+9}" fill="{MUTED}" font-size="11.5" font-family="{SANS}">{esc(text)}</text>')
        x += 44 + len(text) * 6.4 + 22
    return "\n".join(out)

# ---------------------------------------------------------------- 1 architecture
def architecture():
    slug = "architecture"
    body = [
        region(216, 24, 1040, 500, "K3D CLUSTER · ONE K3S NODE INSIDE DOCKER"),
        zone(24, 228, 176, 120, "YOUR LAPTOP"),
        zone(424, 56, 608, 388, "NAMESPACE GRAVITEE"),
        zone(1064, 228, 176, 176, "NAMESPACE PONG"),
        line(slug, 184, 288, 248, 288, "link", marker="link"), label_above(216, 288, "HTTPS", LINK),
        line(slug, 388, 288, 456, 288, "link", marker="link"), label_above(422, 288, "PATH /", LINK),
        path(slug, "M 340,260 V 164 Q 340,156 348,156 H 456"), label_above(402, 156, "/CONSOLE"),
        path(slug, "M 300,260 V 104 Q 300,96 308,96 H 752 Q 760,96 760,104 V 128"), label_above(620, 96, "/MANAGEMENT"),
        line(slug, 318, 436, 318, 316, dashed=True), label_right(318, 376, "TLS SECRET"),
        line(slug, 616, 288, 680, 288, dashed=True), label_above(648, 288, "SYNC"),
        line(slug, 760, 184, 760, 260), label_right(760, 222, "WRITE"),
        line(slug, 888, 156, 840, 156), label_above(864, 156, "PUSH"),
        line(slug, 616, 156, 680, 156, dashed=True), label_above(648, 156, "BROWSER"),
        path(slug, "M 536,316 V 368 Q 536,376 544,376 H 1144 Q 1152,376 1152,368 V 316", "link", marker="link"),
        label_above(944, 376, "PROXY /PING", LINK),
        node(40, 260, 144, 56, "external", "YOU", "You", ["curl, browser"]),
        node(248, 260, 140, 56, "backend", "EDGE", "Traefik", ["kube-system · TLS"]),
        node(248, 436, 140, 56, "service", "TLS", "cert-manager", ["24 h cert, renews"]),
        node(456, 128, 160, 56, "backend", "UI", "Console", ["runs in the browser"]),
        node(680, 128, 160, 56, "backend", "API", "Management API", ["creates APIs"]),
        node(888, 128, 120, 56, "service", "GKO", "Operator", ["watches CRDs"]),
        node(456, 260, 160, 56, "focal", "GW", "Gateway × 2", [":8082 · serves /ping"]),
        node(680, 260, 160, 56, "store", "DB", "MongoDB 8.0", ["APIs, users, plans"]),
        node(1080, 260, 144, 56, "backend", "APP", "pong", ["nginx × 2 · :8080"]),
        legend(560, 1280, [("focal", "Focal: the gateway"), ("backend", "Service"), ("store", "Database"),
                           ("external", "You"), (("link", False, f"{slug}-arrow-link"), "Request path"),
                           (("muted", True, f"{slug}-arrow"), "Sync, secret, browser call")]),
    ]
    return svg(slug, 1280, 600, "Where everything runs",
               "Architecture of the k3d cluster: Traefik routes HTTPS from the laptop to the Gravitee gateway, Console and Management API, and the Console page calls the Management API from the browser; the gateway syncs APIs from MongoDB and proxies /ping to the pong backend.",
               "\n".join(body))

# ---------------------------------------------------------------- sequence helpers
def actor(center_x, kind, tag, name, sub):
    return node(center_x - 80, 32, 160, 56, kind, tag, name, [sub])

def lifeline(center_x, top, bottom):
    return f'<line x1="{center_x}" y1="{top}" x2="{center_x}" y2="{bottom}" stroke="rgba(45,49,66,0.20)" stroke-width="1" stroke-dasharray="3,3"/>'

def activation(center_x, top, bottom):
    return f'<rect x="{center_x-4}" y="{top}" width="8" height="{bottom-top}" fill="rgba(45,49,66,0.06)" stroke="{MUTED}" stroke-width="0.8"/>'

def message(slug, x1, x2, y, text, color="muted", dashed=False):
    marker = {"muted": "muted", "link": "link", "accent": "accent"}[color]
    label_color = {"muted": SOFT, "link": LINK, "accent": ACCENT}[color]
    return line(slug, x1, y, x2, y, color, dashed, marker) + label_above((x1 + x2) / 2, y, text, label_color)

def self_message(slug, center_x, y, text):
    d = f"M {center_x+4},{y} H {center_x+28} Q {center_x+36},{y} {center_x+36},{y+8} V {y+16} Q {center_x+36},{y+24} {center_x+28},{y+24} H {center_x+4}"
    return path(slug, d) + label_right(center_x + 36, y + 12, text)

def fragment(x, y, w, h, operator, guards, divider=None, guard_offset=12):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="rgba(45,49,66,0.02)" stroke="rgba(45,49,66,0.22)" stroke-width="1"/>',
           f'<rect x="{x}" y="{y}" width="40" height="16" rx="2" fill="{PAPER}" stroke="rgba(45,49,66,0.22)" stroke-width="1"/>',
           f'<text x="{x+20}" y="{y+12}" fill="{MUTED}" font-size="9" font-family="{SANS}" text-anchor="middle" letter-spacing="0.12em">{operator}</text>']
    for guard_y, guard in guards:
        out.append(f'<text x="{x+guard_offset}" y="{guard_y}" fill="{MUTED}" font-size="9.5" font-family="{SANS}" letter-spacing="0.04em">{esc(guard)}</text>')
    if divider:
        out.append(f'<line x1="{x+8}" y1="{divider}" x2="{x+w-8}" y2="{divider}" stroke="rgba(45,49,66,0.20)" stroke-width="1" stroke-dasharray="4,3"/>')
    return "\n".join(out)

# ---------------------------------------------------------------- 2 request
def request():
    slug = "request"
    curl, traefik, gateway, pong = 160, 480, 800, 1120
    body = [
        fragment(440, 300, 720, 224, "ALT", [(330, "[method is GET]"), (462, "[POST, PUT or anything else]")], divider=444, guard_offset=60),
        *(lifeline(x, 88, 584) for x in (curl, traefik, gateway, pong)),
        activation(traefik, 132, 564), activation(gateway, 220, 508), activation(pong, 344, 396),
        message(slug, curl, traefik - 4, 132, "GET /PING TLS", "link"),
        self_message(slug, traefik, 160, "DECRYPT TLS"),
        message(slug, traefik + 4, gateway - 4, 220, "GET /PING", "link"),
        self_message(slug, gateway, 248, "FIND API /PING"),
        message(slug, gateway + 4, pong - 4, 356, "GET /PING", "link"),
        message(slug, pong - 4, gateway + 4, 388, "200 PONG", dashed=True),
        message(slug, gateway - 4, traefik + 4, 420, "200 PONG", "accent"),
        message(slug, gateway - 4, traefik + 4, 496, "404 NO FLOW", dashed=True),
        message(slug, traefik - 4, curl, 556, "SAME ANSWER", dashed=True),
        actor(curl, "external", "YOU", "You", "curl"),
        actor(traefik, "backend", "EDGE", "Traefik", "holds :443"),
        actor(gateway, "focal", "GW", "Gateway", "API rules"),
        actor(pong, "backend", "APP", "pong", "nginx :8080"),
        legend(620, 1280, [(("link", False, f"{slug}-arrow-link"), "Call"), (("muted", True, f"{slug}-arrow"), "Answer"),
                           (("accent", False, f"{slug}-arrow-accent"), "Happy path answer")]),
    ]
    return svg(slug, 1280, 648, "One GET /ping request",
               "Sequence of a GET /ping call: Traefik decrypts TLS, the gateway matches the ping API and its GET-only flow, calls pong and returns pong; any other method gets 404 from the gateway.",
               "\n".join(body))

# ---------------------------------------------------------------- 3 config
def config():
    slug = "config"
    you, operator, management, mongo, gateway = 128, 384, 640, 896, 1152
    body = [
        fragment(856, 300, 336, 160, "LOOP", [(330, "[every few seconds]")]),
        *(lifeline(x, 88, 484) for x in (you, operator, management, mongo, gateway)),
        activation(operator, 132, 280), activation(management, 164, 240), activation(gateway, 340, 444),
        message(slug, you, operator - 4, 132, "APPLY YAML"),
        message(slug, operator + 4, management - 4, 164, "PUSH API", "link"),
        message(slug, management + 4, mongo, 196, "SAVE"),
        message(slug, management - 4, operator + 4, 228, "OK", dashed=True),
        message(slug, operator - 4, you, 268, "COMPLETED", dashed=True),
        message(slug, gateway - 4, mongo, 356, "READ APIS", "link"),
        message(slug, mongo, gateway - 4, 388, "PING API", "accent"),
        self_message(slug, gateway, 412, "LOAD /PING"),
        actor(you, "external", "YOU", "You", "kubectl apply"),
        actor(operator, "service", "GKO", "Operator", "reads the CRD"),
        actor(management, "backend", "API", "Management API", ":8083"),
        actor(mongo, "store", "DB", "MongoDB", ":27017"),
        actor(gateway, "focal", "GW", "Gateway × 2", ":8082"),
        legend(520, 1280, [(("link", False, f"{slug}-arrow-link"), "HTTP or database call"), (("muted", True, f"{slug}-arrow"), "Answer"),
                           (("accent", False, f"{slug}-arrow-accent"), "The API reaches the gateway")]),
    ]
    return svg(slug, 1280, 548, "From YAML to the gateway",
               "Sequence showing how the ping API travels: kubectl applies the ApiV4Definition, the operator pushes it to the Management API, which saves it in MongoDB, and every gateway reads MongoDB on a short loop and loads it.",
               "\n".join(body))

# ---------------------------------------------------------------- 4 make up
def make_up():
    slug = "make-up"
    steps = [
        ("01", "Preflight", "tools + Docker", "fails fast"),
        ("02", "Cluster", "k3d + Traefik", "port 443 free?"),
        ("03", "TLS", "cert-manager", "issuer Ready"),
        ("04", "Secrets", "random, stdin", "only if missing"),
        ("05", "MongoDB", "helm + netpol", "pods ready"),
        ("06", "Operator", "GKO chart", "CRDs exist"),
        ("07", "APIM", "gateway, API, UI", "pods ready"),
        ("08", "ping API", "pong + CRD", "webhook retry"),
        ("09", "Verify", "curl /ping", "12 tries, 5 s"),
    ]
    body = []
    for index in range(len(steps) - 1):
        x = 20 + index * 140
        body.append(line(slug, x + 120, 100, x + 140, 100))
    for index, (number, name, what, check) in enumerate(steps):
        x = 20 + index * 140
        kind = "focal" if name == "ping API" else "backend"
        body.append(node(x, 48, 120, 104, kind, number, name, [what, check]))
    body.append(f'<text x="640" y="200" fill="{MUTED}" font-size="21" font-family="{SANS}" text-anchor="middle">Each step creates what is missing and leaves the rest alone, so a second run changes nothing.</text>')
    body.append(f'<text x="640" y="226" fill="{SOFT}" font-size="10.5" font-family="{SANS}" text-anchor="middle" letter-spacing="0.06em">FIRST RUN ABOUT 3-5 MIN · SECOND RUN ABOUT 18 S, NO POD RESTARTS</text>')
    body.append(legend(268, 1280, [("backend", "Step (second line: what it waits for)"), ("focal", "The step that publishes /ping")]))
    return svg(slug, 1280, 296, "What make up does, in order",
               "Process of scripts/up.sh in nine steps from preflight checks to the final curl, each step waiting for the one before it.",
               "\n".join(body))

# ---------------------------------------------------------------- 5 security
def security():
    slug = "security"
    body = [
        region(200, 40, 1056, 440, "YOUR LAPTOP · PORT 443 OPEN ONLY ON 127.0.0.1"),
        zone(588, 72, 416, 376, "NAMESPACE GRAVITEE"),
        zone(1032, 176, 208, 272, "NAMESPACE PONG"),
        line(slug, 128, 256, 192, 256, "ink", True, "stop"), label_above(160, 256, "BLOCKED", INK),
        line(slug, 352, 256, 408, 256, "link", marker="link"), label_above(380, 256, "HTTPS", LINK),
        line(slug, 548, 256, 612, 256, "link", marker="link"), label_above(580, 256, "HTTP", LINK),
        line(slug, 772, 256, 820, 256), label_above(796, 256, "27017"),
        path(slug, "M 772,132 H 892 Q 900,132 900,140 V 228"), label_above(836, 132, "ALLOWED"),
        path(slug, "M 692,284 V 312 Q 692,320 700,320 H 1016 Q 1024,320 1024,312 V 264 Q 1024,256 1032,256 H 1056", "accent", marker="accent"),
        label_above(860, 320, "ONLY GATEWAY", ACCENT),
        line(slug, 1136, 360, 1136, 296, "ink", True, "stop"), label_right(1136, 328, "DENIED", INK),
        node(16, 228, 112, 56, "external", "LAN", "Other device", ["same Wi-Fi"], dashed=True),
        node(224, 228, 128, 56, "external", "YOU", "You", ["curl / browser"]),
        node(408, 228, 140, 56, "focal", "GATE", "Traefik", ["TLS, local CA"]),
        node(612, 104, 160, 56, "backend", "API", "Management API", ["admin login"]),
        node(612, 228, 160, 56, "backend", "GW", "Gateway × 2", ["has gateway label"]),
        node(820, 228, 160, 56, "store", "DB", "MongoDB", ["password in Secret"]),
        node(1056, 228, 160, 56, "backend", "APP", "pong", [":8080"]),
        node(1056, 360, 160, 56, "external", "POD", "Other pod", ["no gateway label"], dashed=True),
        legend(520, 1280, [("focal", "TLS gate"), ("external-dashed", "Not allowed in"),
                           (("link", False, f"{slug}-arrow-link"), "Encrypted, then routed"),
                           (("accent", False, f"{slug}-arrow-accent"), "Only route to pong"),
                           (("ink", True, f"{slug}-stop"), "Blocked")]),
    ]
    return svg(slug, 1280, 548, "Who may talk to whom",
               "Security boundaries: port 443 listens only on 127.0.0.1, Traefik terminates TLS, NetworkPolicies let only the gateway reach pong and only Gravitee pods reach MongoDB, and other pods are refused.",
               "\n".join(body))

# ---------------------------------------------------------------- 6 production delta
def delta_node(object_id, status, signature, x, y, kind, tag, name, sub, badge=None):
    inner = node(x, y, 128, 56, kind, tag, name, [sub], bounds_attr=' data-role="bounds"', badge=badge)
    return f'<g data-kind="component" data-object-id="{object_id}" data-status="{status}" data-signature="{esc(signature)}">\n{inner}\n</g>'

def relation(slug, object_id, status, source, target, d, color="muted", dashed=False):
    extra = f' data-kind="relationship" data-object-id="{object_id}" data-status="{status}" data-signature="{object_id}" data-from="{source}" data-to="{target}"'
    marker = {"muted": "muted", "link": "link"}[color]
    return path(slug, d, color, dashed, marker, extra)

def number_marker(center_x, center_y, number):
    return (f'<circle cx="{center_x}" cy="{center_y}" r="7" fill="{INK}"/>'
            f'<text x="{center_x}" y="{center_y + 3}" fill="{PAPER}" font-size="8" font-weight="600" font-family="{SANS}" text-anchor="middle">{number}</text>')

def production():
    slug = "production"
    relations_before = [
        ("traefik-gateway", "traefik", "gateway", "M 144,68 H 168"),
        ("gateway-pong", "gateway", "pong", "M 296,68 H 320"),
        ("management-mongodb", "management", "mongodb", "M 144,332 H 168"),
        ("gateway-mongodb", "gateway", "mongodb", "M 232,96 V 304"),
        ("traefik-management", "traefik", "management", "M 144,84 H 148 Q 156,84 156,92 V 272 Q 156,280 148,280 H 108 Q 100,280 100,288 V 304"),
        ("operator-management", "operator", "management", "M 384,360 V 368 Q 384,376 376,376 H 88 Q 80,376 80,368 V 360"),
    ]
    relations_added = [
        ("prometheus-gateway", "prometheus", "gateway", "M 144,204 H 148 C 148,196 164,196 164,204 H 192 Q 200,204 200,196 V 96"),
        ("gateway-elasticsearch", "gateway", "elasticsearch", "M 264,96 V 196 Q 264,204 272,204 H 320"),
    ]

    def snapshot(name, after):
        parts = [relation(slug, oid, "unchanged", source, target, d) for oid, source, target, d in relations_before]
        if after:
            parts += [relation(slug, oid, "added", source, target, d, "link", dashed=True) for oid, source, target, d in relations_added]
        changed_badge = "Δ" if after else None
        parts += [
            delta_node("traefik", "changed", "issuer=acme" if after else "issuer=local-ca", 16, 40, "backend", "EDGE", "Traefik",
                       "Let's Encrypt" if after else "local CA", changed_badge),
            delta_node("gateway", "changed", "scale=hpa;nodes=3" if after else "scale=2;nodes=1", 168, 40, "backend", "GW", "Gateway",
                       "HPA · 3 nodes" if after else "2 pods · 1 node", changed_badge),
            delta_node("pong", "unchanged", "nginx-x2", 320, 40, "backend", "APP", "pong", "nginx × 2"),
            delta_node("operator", "unchanged", "gko", 320, 304, "service", "GKO", "Operator", "pushes APIs"),
            delta_node("management", "changed", "login=sso;internal" if after else "login=admin", 16, 304,
                       "focal" if after else "backend", "API", "Management API", "SSO, internal" if after else "admin / admin", changed_badge),
            delta_node("mongodb", "changed", "replica-set;backups" if after else "standalone", 168, 304, "store", "DB", "MongoDB",
                       "replica set" if after else "standalone", changed_badge),
        ]
        if after:
            parts += [
                delta_node("prometheus", "added", "prometheus", 16, 176, "service", "MON", "Prometheus", "alerts on 5xx", "+"),
                delta_node("elasticsearch", "added", "elasticsearch", 320, 176, "service", "ES", "Elasticsearch", "analytics", "+"),
            ]
        if after:
            corners = [(144, 40), (296, 40), (144, 304), (296, 304), (144, 176), (320, 176), (200, 150), (264, 150)]
            parts += [number_marker(x, y, number) for number, (x, y) in enumerate(corners, start=1)]
        origin = "808 72" if after else "24 72"
        return f'<g data-snapshot="{name}" data-grid="448 384 4" transform="translate({origin})">\n' + "\n".join(parts) + "\n</g>"

    ledger = [
        ("CHANGED", "Traefik", "local CA → Let's Encrypt, real DNS name"),
        ("CHANGED", "Gateway", "2 pods on 1 node → autoscaled on 3 nodes"),
        ("CHANGED", "Management API", "admin/admin → SSO, internal only"),
        ("CHANGED", "MongoDB", "standalone → replica set with backups"),
        ("ADDED", "Prometheus", "scrapes :18082, alerts on 5xx ratio"),
        ("ADDED", "Elasticsearch", "stores request analytics"),
        ("ADDED", "scrape path", "Prometheus → gateway"),
        ("ADDED", "report path", "gateway → Elasticsearch"),
    ]
    ledger_svg = [f'<text x="512" y="64" fill="{MUTED}" font-size="9.5" font-family="{SANS}" letter-spacing="0.14em">CHANGES</text>',
                  f'<line x1="512" y1="72" x2="768" y2="72" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>']
    for index, (change, subject, detail) in enumerate(ledger):
        y = 100 + index * 44
        ledger_svg.append(number_marker(519, y - 4, index + 1))
        ledger_svg.append(f'<g data-ledger-entry="{index}"><text x="532" y="{y}" fill="{INK}" font-size="9" font-weight="600" font-family="{SANS}" letter-spacing="0.08em">{change} <tspan fill="{INK}" font-family="{SANS}" font-size="13" letter-spacing="0">{esc(subject)}</tspan></text>'
                          f'<text x="532" y="{y + 18}" fill="{MUTED}" font-size="12" font-family="{SANS}">{esc(detail)}</text></g>')
    headings = [
        f'<text x="40" y="64" fill="{MUTED}" font-size="9.5" font-family="{SANS}" letter-spacing="0.14em">TODAY · THIS REPOSITORY</text>',
        f'<text x="824" y="64" fill="{MUTED}" font-size="9.5" font-family="{SANS}" letter-spacing="0.14em">BEFORE PRODUCTION</text>',
        f'<rect x="24" y="72" width="448" height="384" rx="8" fill="transparent" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>',
        f'<rect x="808" y="72" width="448" height="384" rx="8" fill="transparent" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>',
    ]
    body = headings + [snapshot("before", False), "\n".join(ledger_svg), snapshot("after", True),
            f'<text x="640" y="484" fill="{SOFT}" font-size="10.5" font-family="{SANS}" text-anchor="middle" letter-spacing="0.04em">ALSO MISSING, NOT DRAWN: VAULT FOR SECRETS · REDIS FOR RATE LIMITS · GITOPS · CI CHECKS · READ-ONLY GRAVITEE CONTAINERS · API KEYS · CENTRAL LOGS · IN-CLUSTER TLS</text>',
            legend(520, 1280, [("backend", "Δ changed"), ("service", "+ added"), ("focal", "Fix this first"),
                               (("link", True, f"{slug}-arrow-link"), "Added connection")])]
    return svg(slug, 1280, 548, "Today versus production",
               "Before and after comparison with numbered changes: today's single-node demo against the production target with Let's Encrypt, autoscaled gateways, SSO on the Management API, a MongoDB replica set, Prometheus and Elasticsearch.",
               "\n".join(body), extra=' data-diagram="architecture-delta"')

if __name__ == "__main__":
    import json
    print(json.dumps({"architecture": architecture(), "request": request(), "config": config(),
                      "make-up": make_up(), "security": security(), "production": production()}))
