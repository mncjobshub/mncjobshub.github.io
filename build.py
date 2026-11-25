#!/usr/bin/env python3
"""
MNC JobsHub - static site generator (no dependencies, Python 3.8+).

Run:  python3 build.py

Reads:   jobs.json, src/site.json, src/categories.json, src/guides/*.html
Writes:  jobs/<id>.html          one static page per job
         <category>.html         landing pages (only when at least one job matches)
         guides/*.html           guide articles and guides/index.html
         sitemap.xml             always in sync with the pages above
         index.html (marker blocks) and the footer "Popular searches" list on hand-written pages
"""
import glob
import html
import json
import os
import re
from datetime import date, datetime
from urllib.parse import quote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today()


def P(*parts):
    return os.path.join(ROOT, *parts)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


SITE = read_json(P("src", "site.json"))
BASE = SITE["siteUrl"].rstrip("/")
NAME = SITE["name"]
NEW_DAYS = int(SITE.get("newBadgeDays", 3))

# ------------------------------------------------------------------ dates
def pdate(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
        return None


def fmt(s):
    d = pdate(s)
    return "%d %s" % (d.day, d.strftime("%b %Y")) if d else ""


def is_expired(j):
    d = pdate(j.get("lastDate"))
    return bool(d and d < TODAY)


def is_new(j):
    d = pdate(j.get("postedOn"))
    return bool(d and 0 <= (TODAY - d).days <= NEW_DAYS)


# ------------------------------------------------------------------ company logo (same rules as assets/app.js)
LOGO_BLOCKED = [
    "myworkdayjobs.com", "workday.com", "greenhouse.io", "lever.co", "smartrecruiters.com", "icims.com",
    "taleo.net", "oraclecloud.com", "successfactors.com", "successfactors.eu", "ashbyhq.com", "bamboohr.com",
    "jobvite.com", "breezy.hr", "recruitee.com", "workable.com", "linkedin.com", "naukri.com", "indeed.com",
    "glassdoor.com", "instahyre.com", "wellfound.com", "unstop.com", "internshala.com", "foundit.in",
    "shine.com", "t.me", "bit.ly", "tinyurl.com", "linktr.ee", "forms.gle", "docs.google.com", "airtable.com",
    "typeform.com",
]
SECOND_LEVEL = {"co", "com", "org", "net", "gov", "edu", "ac"}


def root_domain(host):
    parts = host.lower().replace("www.", "", 1).split(".")
    if len(parts) <= 2:
        return ".".join(parts)
    if len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def company_domain(j):
    explicit = j.get("website") or j.get("domain")
    src = explicit or j.get("applyLink")
    if not src:
        return ""
    if not re.match(r"^https?://", src, re.I):
        src = "https://" + src
    try:
        host = (urlparse(src).hostname or "").lower()
    except Exception:
        return ""
    if not host:
        return ""
    if not explicit and any(host == b or host.endswith("." + b) for b in LOGO_BLOCKED):
        return ""
    return root_domain(host)


def logo_html(j, prefix):
    initial = esc(str(j["company"])[:1].upper())
    custom = j.get("logo") or ""
    src, domain = "", ""
    if custom:
        src = custom if re.match(r"^https?://", custom) else prefix + custom.lstrip("/")
    else:
        domain = company_domain(j)
        if domain:
            src = "https://www.google.com/s2/favicons?sz=128&domain=" + quote(domain)
    if src:
        inner = ('<img class="logo-img" src="%s" alt="" width="46" height="46" loading="lazy" decoding="async" '
                 'referrerpolicy="no-referrer" data-domain="%s" data-step="0">' % (esc(src), esc(domain)))
    else:
        inner = initial
    return '<span class="logo-chip" data-initial="%s" aria-hidden="true">%s</span>' % (initial, inner)


# ------------------------------------------------------------------ data
def load_jobs():
    raw = read_json(P("jobs.json"))
    jobs = raw if isinstance(raw, list) else raw.get("jobs", [])
    jobs = [j for j in jobs if j.get("id") and j.get("role") and j.get("company")]
    ids = [j["id"] for j in jobs]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit("Duplicate job ids in jobs.json: %s" % ", ".join(sorted(dup)))
    for j in jobs:
        if not re.match(r"^[a-z0-9][a-z0-9\-]*$", j["id"]):
            raise SystemExit("Job id must be lowercase letters, numbers and hyphens only: %s" % j["id"])
    return sorted(jobs, key=lambda j: str(j.get("postedOn", "")), reverse=True)


JOBS = load_jobs()
CATS = read_json(P("src", "categories.json"))


def cat_matches(cat, j):
    m = cat.get("match", {})
    if any(t in j.get("tags", []) for t in m.get("tags", [])):
        return True
    skills = [s.lower() for s in j.get("skills", [])]
    if any(s.lower() in skills for s in m.get("skills", [])):
        return True
    if m.get("location_regex") and re.search(m["location_regex"], j.get("location", ""), re.I):
        return True
    if m.get("role_regex") and re.search(m["role_regex"], j.get("role", ""), re.I):
        return True
    return False


for c in CATS:
    c["jobs"] = [j for j in JOBS if cat_matches(c, j)]
LIVE_CATS = [c for c in CATS if c["jobs"]]


def cats_for(j):
    return [c for c in LIVE_CATS if j in c["jobs"]]


# ------------------------------------------------------------------ guides
def load_guides():
    guides = []
    for path in sorted(glob.glob(P("src", "guides", "*.html"))):
        text = open(path, encoding="utf-8").read()
        head, sep, body = text.partition("\n---\n")
        if not sep:
            raise SystemExit("Guide missing '---' separator: %s" % path)
        meta = {}
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        meta["slug"] = os.path.splitext(os.path.basename(path))[0]
        meta["body"] = body.strip()
        guides.append(meta)
    return sorted(guides, key=lambda g: g.get("date", ""), reverse=True)


GUIDES = load_guides()

# ------------------------------------------------------------------ shared page pieces
def ld(obj):
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def short_title(base):
    full = "%s | %s" % (base, NAME)
    return full if len(full) <= 65 else base


def head(prefix, title, desc, path, og_type="website", extra="", robots="index, follow, max-image-preview:large"):
    url = BASE + "/" + path.lstrip("/")
    img = BASE + "/assets/og-image.png"
    return """<!DOCTYPE html>
<html lang="en-IN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{name}">
  <meta property="og:locale" content="en_IN">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{img}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{img}">
  <meta name="theme-color" content="#1d4ed8">
  <link rel="icon" href="{p}assets/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="{p}assets/favicon-48.png" sizes="48x48" type="image/png">
  <link rel="apple-touch-icon" href="{p}assets/apple-touch-icon.png">
  <link rel="stylesheet" href="{p}assets/style.css">
  <!-- GOOGLE ADSENSE: after approval, uncomment and add your publisher ID
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script>
  -->
  {extra}
</head>
""".format(title=esc(title), desc=esc(desc), robots=robots, url=esc(url), og_type=og_type, name=esc(NAME),
           img=esc(img), p=prefix, extra=extra)


def header(prefix, active=""):
    def a(href, label, key):
        cls = ' class="active"' if active == key else ""
        return '<a href="%s%s"%s>%s</a>' % (prefix, href, cls, label)
    return """  <a class="sr-only" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="{p}index.html" aria-label="{name} home"><img class="brand-mark" src="{p}assets/logo-mark.svg" alt="" width="36" height="36"><span>mncjobs<b>hub</b></span></a>
      <button class="nav-toggle" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav">&#9776;</button>
      <nav id="site-nav" class="site-nav" aria-label="Main">
        {home}
        {guides}
        {about}
        {contact}
        {privacy}
        <a class="btn btn-tg btn-sm" data-telegram href="{tg}" target="_blank" rel="noopener">Join Telegram</a>
      </nav>
    </div>
  </header>
""".format(p=prefix, name=esc(NAME), tg=esc(SITE["telegram"]),
           home=a("index.html", "Home", "home"), guides=a("guides/index.html", "Guides", "guides"),
           about=a("about.html", "About", "about"), contact=a("contact.html", "Contact", "contact"),
           privacy=a("privacy-policy.html", "Privacy", "privacy"))


def popular_links(prefix):
    top = sorted(LIVE_CATS, key=lambda c: -len(c["jobs"]))[:6]
    return "".join('<li><a href="%s%s.html">%s</a></li>' % (prefix, c["slug"], esc(c["h1"])) for c in top)


def footer(prefix):
    return """  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div>
          <a class="brand" href="{p}index.html"><img class="brand-mark" src="{p}assets/logo-mark.svg" alt="" width="36" height="36"><span>mncjobs<b>hub</b></span></a>
          <p style="margin-top:10px">A free job update portal for freshers and off-campus candidates. We share information only; we are not a recruitment agency.</p>
        </div>
        <div>
          <h4>Quick Links</h4>
          <ul>
            <li><a href="{p}index.html">Home</a></li>
            <li><a href="{p}guides/index.html">Guides</a></li>
            <li><a href="{p}about.html">About Us</a></li>
            <li><a href="{p}contact.html">Contact Us</a></li>
            <li><a href="{p}privacy-policy.html">Privacy Policy &amp; Disclaimer</a></li>
          </ul>
        </div>
        <div>
          <h4>Popular Searches</h4>
          <ul>
            <!-- POPULAR:START -->{pop}<!-- POPULAR:END -->
          </ul>
        </div>
        <div>
          <h4>Follow Us</h4>
          <ul>
            <li><a data-telegram href="{tg}" target="_blank" rel="noopener">Telegram Channel</a></li>
            <li><a data-instagram href="{ig}" target="_blank" rel="noopener">Instagram</a></li>
            <li><a data-youtube href="{yt}" target="_blank" rel="noopener">YouTube</a></li>
            <li><a data-email href="mailto:{em}">{em}</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">&copy; <span data-year>{year}</span> <span data-site>{name}</span>. All rights reserved. Company names and logos belong to their respective owners.</div>
    </div>
  </footer>
  <script src="{p}assets/app.js" defer></script>
</body>
</html>
""".format(p=prefix, pop=popular_links(prefix), tg=esc(SITE["telegram"]), ig=esc(SITE["instagram"]),
           yt=esc(SITE["youtube"]), em=esc(SITE["email"]), year=TODAY.year, name=esc(NAME))


AD = '<!-- AD SLOT: %s - paste your AdSense code here --><div class="ad-slot" aria-label="Advertisement"><span>Advertisement</span></div>'


def card(j, prefix=""):
    tags = "".join('<span class="tag">%s</span>' % esc(t) for t in j.get("tags", []))
    if is_expired(j):
        badge = '<span class="tag expired">Expired</span>'
    elif is_new(j):
        badge = '<span class="tag new">New</span>'
    else:
        badge = ""
    meta = ""
    if j.get("batch"):
        meta += '<li data-icon="🎓">Batch: %s</li>' % esc(j["batch"])
    if j.get("location"):
        meta += '<li data-icon="📍">%s</li>' % esc(j["location"])
    if j.get("salary"):
        meta += '<li data-icon="💰">%s</li>' % esc(j["salary"])
    link = "%sjobs/%s.html" % (prefix, j["id"])
    return ('<article class="job-card"><div class="job-card-top">%s<div><h3><a href="%s">%s</a></h3>'
            '<p class="company">%s</p></div></div><ul class="meta">%s</ul><div class="tags">%s%s</div>'
            '<div class="job-card-foot"><span class="posted">Posted %s</span>'
            '<a class="btn btn-primary btn-sm" href="%s">View Details</a></div></article>') % (
        logo_html(j, prefix), link, esc(j["role"]), esc(j["company"]), meta, badge, tags,
        esc(fmt(j.get("postedOn"))), link)


def ul(items, cls=""):
    if not items:
        return ""
    return "<ul%s>%s</ul>" % (' class="%s"' % cls if cls else "", "".join("<li>%s</li>" % esc(i) for i in items))


# ------------------------------------------------------------------ job pages
def job_ld(j):
    desc = "".join("<p>%s</p>" % esc(p) for p in j.get("description", []))
    if j.get("responsibilities"):
        desc += "<h3>Responsibilities</h3>" + ul(j["responsibilities"])
    if j.get("requirements"):
        desc += "<h3>Requirements</h3>" + ul(j["requirements"])
    org = {"@type": "Organization", "name": j["company"]}
    dom = company_domain(j)
    if dom:
        org["sameAs"] = "https://" + dom
    loc = j.get("location", "India")
    obj = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": j["role"],
        "description": desc or esc(j.get("summary", "")),
        "datePosted": j.get("postedOn"),
        "employmentType": j.get("employmentType", "FULL_TIME"),
        "hiringOrganization": org,
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": loc,
                                                        "addressCountry": "IN"}},
        "directApply": False,
    }
    if j.get("lastDate"):
        obj["validThrough"] = j["lastDate"] + "T23:59:59+05:30"
    if j.get("jobId"):
        obj["identifier"] = {"@type": "PropertyValue", "name": j["company"], "value": j["jobId"]}
    return obj


def related_jobs(j, n=3):
    mine = set(j.get("tags", []))
    rel = [o for o in JOBS if o["id"] != j["id"] and mine & set(o.get("tags", []))]
    rel += [o for o in JOBS if o["id"] != j["id"] and o not in rel]
    return rel[:n]


def resources_html():
    items = SITE.get("resources", [])
    if not items:
        return ""
    has_aff = any(r.get("sponsored") for r in items)
    links = "".join('<a class="resource" href="%s" target="_blank" rel="%snoopener"><strong>%s</strong><small>%s</small></a>' % (
        esc(r["url"]), "sponsored " if r.get("sponsored") else "", esc(r["title"]), esc(r.get("desc", ""))) for r in items)
    disc = ('<p class="disclosure">Disclosure: Some links are affiliate links. We may earn a commission at no extra cost to you.</p>'
            if has_aff else "")
    return '<div class="panel"><h3>Recommended Resources</h3><div class="resource-list">%s</div>%s</div>' % (links, disc)


def build_job_page(j):
    prefix = "../"
    city = str(j.get("location", "India")).split(",")[0]
    title = short_title("%s %s Job in %s" % (j["company"], j["role"], city))
    desc = j.get("summary") or "%s job at %s in %s. Check eligibility, salary and apply link." % (j["role"], j["company"], city)
    path = "jobs/%s.html" % j["id"]
    url = BASE + "/" + path
    expired = is_expired(j)
    link = j.get("applyLink", "#")

    mine_cats = cats_for(j)
    first = None
    if mine_cats:
        t0 = (j.get("tags") or [None])[0]
        first = next((c for c in mine_cats if t0 and t0 in c.get("match", {}).get("tags", [])), mine_cats[0])
    crumb_mid = ('<a href="../%s.html">%s</a>' % (first["slug"], esc(first["h1"]))) if first else "Jobs"
    breadcrumb = '<div class="breadcrumb"><a href="../index.html">Home</a> &rsaquo; %s &rsaquo; %s</div>' % (crumb_mid, esc(j["company"]))

    rows = [("Company", j.get("company")), ("Role", j.get("role")), ("Batch / Eligibility", j.get("batch")),
            ("Location", j.get("location")), ("Work Mode", j.get("workMode")), ("Salary / CTC", j.get("salary")),
            ("Experience", j.get("experience")), ("Last Date", fmt(j.get("lastDate"))), ("Job ID", j.get("jobId"))]
    info = "".join('<div class="info"><span>%s</span><strong>%s</strong></div>' % (esc(k), esc(v)) for k, v in rows if v)

    tags = ('<span class="tag expired">Application closed</span>' if expired else "") + "".join(
        '<span class="tag">%s</span>' % esc(t) for t in j.get("tags", []))

    body = ""
    body += "<h2>Job Description</h2>" + "".join("<p>%s</p>" % esc(p) for p in j.get("description", []))
    if j.get("responsibilities"):
        body += "<h2>Key Responsibilities</h2>" + ul(j["responsibilities"])
    if j.get("requirements"):
        body += "<h2>Eligibility &amp; Requirements</h2>"
        if j.get("eligibility"):
            body += "<p><strong>Eligibility:</strong> %s</p>" % esc(j["eligibility"])
        body += ul(j["requirements"])
    if j.get("skills"):
        body += '<h2>Skills Required</h2><div class="skill-list">%s</div>' % "".join("<span>%s</span>" % esc(s) for s in j["skills"])
    if j.get("selectionProcess"):
        body += "<h2>Selection Process</h2>" + ul(j["selectionProcess"], "steps")
    if j.get("aboutCompany"):
        body += "<h2>About %s</h2><p>%s</p>" % (esc(j["company"]), esc(j["aboutCompany"]))

    apply_title = "Applications are closed" if expired else "Ready to apply?"
    apply_text = ("The last date for this job has passed. Join our Telegram channel for new jobs." if expired else
                  "Always apply on the company's official website. We never charge any fee.")
    apply_btn = "" if expired else '<a class="btn btn-primary btn-lg" href="%s" target="_blank" rel="noopener noreferrer nofollow">Apply Now &rarr;</a>' % esc(link)
    apply_box = ('<div class="apply-box"><h2>%s</h2><p>%s</p>%s<div class="social-cta">'
                 '<a class="btn btn-tg" data-telegram href="%s" target="_blank" rel="noopener">Join Telegram</a>'
                 '<a class="btn btn-ig" data-instagram href="%s" target="_blank" rel="noopener">Follow on Instagram</a>'
                 '<a class="btn btn-yt" data-youtube href="%s" target="_blank" rel="noopener">Subscribe on YouTube</a></div></div>') % (
        apply_title, apply_text, apply_btn, esc(SITE["telegram"]), esc(SITE["instagram"]), esc(SITE["youtube"]))
    warn = ('<div class="warn"><strong>Safety tip:</strong> Genuine companies never ask for money during recruitment. '
            'Do not make any payment, and always verify the official careers page before applying. '
            'Read <a href="../guides/how-to-identify-fake-job-offers.html">how to identify fake job offers</a>.</div>')

    share_text = "%s at %s - %sApply here: " % (j["role"], j["company"], (j["batch"] + " batch. ") if j.get("batch") else "")
    side = ('<aside class="side"><div class="panel"><h3>Share this job</h3><div class="share">'
            '<a class="btn btn-outline btn-sm" target="_blank" rel="noopener" href="https://wa.me/?text=%s">WhatsApp</a>'
            '<a class="btn btn-outline btn-sm" target="_blank" rel="noopener" href="https://t.me/share/url?url=%s&amp;text=%s">Telegram</a>'
            '<button class="btn btn-outline btn-sm" type="button" id="copy-link">Copy link</button></div></div>') % (
        quote(share_text + url, safe=""), quote(url, safe=""), quote(share_text, safe=""))
    side += resources_html()
    mine = cats_for(j)
    if mine:
        side += '<div class="panel"><h3>Related searches</h3><div class="resource-list">%s</div></div>' % "".join(
            '<a class="resource" href="../%s.html"><strong>%s</strong><small>%d openings</small></a>' % (
                c["slug"], esc(c["h1"]), len(c["jobs"])) for c in mine[:4])
    side += '<!-- AD SLOT: job sidebar --><div class="ad-slot" aria-label="Advertisement" style="min-height:250px"><span>Advertisement</span></div>'
    side += "</aside>"

    rel = related_jobs(j)
    related = ('<section class="related"><div class="section-head"><h2>More jobs you may like</h2></div><div class="jobs-grid">%s</div></section>' %
               "".join(card(r, prefix) for r in rel)) if rel else ""

    crumbs_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "%s %s" % (j["company"], j["role"]), "item": url}]}

    main = ('<main id="main" class="container">%s<div class="job-layout"><article class="panel job-body">'
            '<div class="job-head">%s<div><h1>%s</h1><p class="company">%s</p></div></div>'
            '<div class="tags">%s</div><div class="info-grid">%s</div>%s%s%s%s%s</article>%s</div>%s</main>') % (
        breadcrumb, logo_html(j, prefix), esc(j["role"]), esc(j["company"]), tags, info, AD % "job top", body,
        AD % "job middle", apply_box, warn, side, related)

    page = head(prefix, title, desc, path, "article", ld(job_ld(j)) + "\n  " + ld(crumbs_ld)) + "<body>\n" + header(prefix) + main + "\n" + footer(prefix)
    write(P(path), page)


# ------------------------------------------------------------------ category pages
def build_category_page(c):
    prefix = ""
    title = short_title(c["title"])
    path = c["slug"] + ".html"
    cards = "".join(card(j, prefix) for j in c["jobs"])
    intro = "".join("<p>%s</p>" % esc(p) for p in c.get("intro", []))
    faq = "".join('<details class="faq"><summary>%s</summary><p>%s</p></details>' % (esc(f["q"]), esc(f["a"])) for f in c.get("faq", []))
    others = [o for o in LIVE_CATS if o is not c][:12]
    chips = "".join('<a class="chip" href="%s.html">%s</a>' % (o["slug"], esc(o["h1"])) for o in others)
    guides = "".join('<li><a href="guides/%s.html">%s</a></li>' % (g["slug"], esc(g["title"])) for g in GUIDES[:4])
    crumbs_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": c["h1"], "item": BASE + "/" + path}]}
    main = """  <main id="main">
    <section class="page-hero"><div class="container"><h1>{h1}</h1><p>{hero}</p></div></section>
    <div class="container section">
      <div class="breadcrumb" style="margin-top:0"><a href="index.html">Home</a> &rsaquo; {h1}</div>
      <div class="section-head"><h2>Latest openings</h2><span class="count">{n} {word}</span></div>
      <div class="jobs-grid">{cards}</div>
      {ad}
      <div class="panel prose" style="max-width:none">
        {intro}
        <h2>Frequently asked questions</h2>
        {faq}
        <h2>Related searches</h2>
        <div class="filters">{chips}</div>
        <h2>Helpful guides</h2>
        <ul>{guides}</ul>
      </div>
    </div>
  </main>
""".format(h1=esc(c["h1"]), hero=esc(c.get("hero", "")), n=len(c["jobs"]), word="job found" if len(c["jobs"]) == 1 else "jobs found",
           cards=cards, ad=AD % "category middle", intro=intro, faq=faq, chips=chips, guides=guides)
    page = head(prefix, title, c["description"], path, "website", ld(crumbs_ld)) + "<body>\n" + header(prefix) + main + footer(prefix)
    write(P(path), page)


# ------------------------------------------------------------------ guides
def unlink_missing_categories(body):
    """Guides may link to category pages. If a category has no jobs yet its page is not generated,
    so turn that link into plain text instead of leaving a broken link."""
    live = {c["slug"] for c in LIVE_CATS}
    all_slugs = {c["slug"] for c in CATS}

    def fix(m):
        slug = m.group(1)
        return m.group(0) if (slug in live or slug not in all_slugs) else m.group(2)

    return re.sub(r'<a href="\.\./([a-z0-9\-]+)\.html">(.*?)</a>', fix, body, flags=re.S)


def build_guides():
    prefix = "../"
    for g in GUIDES:
        g["body"] = unlink_missing_categories(g["body"])
        path = "guides/%s.html" % g["slug"]
        title = short_title(g["title"])
        art = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "description": g["description"],
               "datePublished": g.get("date"), "dateModified": g.get("date"), "inLanguage": "en-IN",
               "author": {"@type": "Organization", "name": NAME},
               "publisher": {"@type": "Organization", "name": NAME, "logo": {"@type": "ImageObject", "url": BASE + "/assets/logo-512.png"}},
               "mainEntityOfPage": BASE + "/" + path}
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Guides", "item": BASE + "/guides/index.html"},
            {"@type": "ListItem", "position": 3, "name": g["title"], "item": BASE + "/" + path}]}
        others = [o for o in GUIDES if o is not g][:3]
        more = "".join('<li><a href="%s.html">%s</a></li>' % (o["slug"], esc(o["title"])) for o in others)
        main = """  <main id="main">
    <section class="page-hero"><div class="container"><h1>{t}</h1><p>Published {d} by {n}</p></div></section>
    <div class="container section">
      <div class="breadcrumb" style="margin-top:0"><a href="../index.html">Home</a> &rsaquo; <a href="index.html">Guides</a></div>
      <article class="prose panel">
        {body}
        {ad}
        <div class="cta-band" style="margin-top:24px"><div><h2>Get new job alerts daily</h2><p>Join our community to hear about new openings first.</p></div>
        <div class="cta-actions"><a class="btn btn-tg" data-telegram href="{tg}" target="_blank" rel="noopener">Join Telegram</a>
        <a class="btn btn-yt" data-youtube href="{yt}" target="_blank" rel="noopener">YouTube</a></div></div>
        <h2>More guides</h2>
        <ul>{more}</ul>
      </article>
    </div>
  </main>
""".format(t=esc(g["title"]), d=esc(fmt(g.get("date"))), n=esc(NAME), body=g["body"], ad=AD % "guide middle",
           tg=esc(SITE["telegram"]), yt=esc(SITE["youtube"]), more=more)
        write(P(path), head(prefix, title, g["description"], path, "article", ld(art) + "\n  " + ld(crumbs)) +
              "<body>\n" + header(prefix, "guides") + main + footer(prefix))

    items = "".join('<article class="feature"><h3><a href="%s.html">%s</a></h3><p>%s</p></article>' % (
        g["slug"], esc(g["title"]), esc(g["description"])) for g in GUIDES)
    idx_title = "Career Guides for Freshers - Interview Prep & Job Search Tips"
    idx_desc = "Free career guides for freshers: SQL and Power BI interview questions, resume ATS tips, off-campus placement strategy and how to avoid fake job offers."
    main = """  <main id="main">
    <section class="page-hero"><div class="container"><h1>Career Guides for Freshers</h1><p>Interview preparation, resume tips and job search advice.</p></div></section>
    <div class="container section"><div class="features">{items}</div></div>
  </main>
""".format(items=items)
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Guides", "item": BASE + "/guides/index.html"}]}
    write(P("guides", "index.html"), head("../", short_title(idx_title), idx_desc, "guides/index.html", "website", ld(crumbs)) +
          "<body>\n" + header("../", "guides") + main + footer("../"))


# ------------------------------------------------------------------ hand-written pages: marker blocks
def replace_block(text, name, content):
    pat = re.compile(r"(<!-- %s:START -->).*?(<!-- %s:END -->)" % (name, name), re.S)
    return pat.sub(lambda m: m.group(1) + content + m.group(2), text)


def update_root_pages():
    for name in ["index.html", "about.html", "contact.html", "privacy-policy.html", "job-details.html"]:
        path = P(name)
        if not os.path.exists(path):
            continue
        s = open(path, encoding="utf-8").read()
        s = replace_block(s, "POPULAR", popular_links(""))
        if name == "index.html":
            s = replace_block(s, "JOBS", "".join(card(j, "") for j in JOBS[:12]))
            cat_links = "".join('<a class="chip" href="%s.html">%s <span class="muted">(%d)</span></a>' % (
                c["slug"], esc(c["h1"]), len(c["jobs"])) for c in LIVE_CATS)
            s = replace_block(s, "CATS", cat_links)
            g_links = "".join('<article class="feature"><h3><a href="guides/%s.html">%s</a></h3><p>%s</p></article>' % (
                g["slug"], esc(g["title"]), esc(g["description"])) for g in GUIDES[:3])
            s = replace_block(s, "GUIDES", g_links)
        write(path, s)


# ------------------------------------------------------------------ sitemap
def build_sitemap():
    today = TODAY.isoformat()
    rows = [("/", today, "daily", "1.0"), ("/about.html", None, None, "0.5"), ("/contact.html", None, None, "0.5"),
            ("/privacy-policy.html", None, None, "0.3"), ("/guides/index.html", today, "weekly", "0.7")]
    rows += [("/%s.html" % c["slug"], today, "daily", "0.8") for c in LIVE_CATS]
    rows += [("/guides/%s.html" % g["slug"], g.get("date"), "monthly", "0.6") for g in GUIDES]
    rows += [("/jobs/%s.html" % j["id"], j.get("postedOn"), None, "0.7") for j in JOBS]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           "<!-- Generated by build.py. Do not edit by hand. -->",
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, last, freq, pri in rows:
        parts = ["<loc>%s</loc>" % esc(BASE + loc)]
        if last:
            parts.append("<lastmod>%s</lastmod>" % last)
        if freq:
            parts.append("<changefreq>%s</changefreq>" % freq)
        parts.append("<priority>%s</priority>" % pri)
        out.append("  <url>%s</url>" % "".join(parts))
    out.append("</urlset>")
    write(P("sitemap.xml"), "\n".join(out) + "\n")
    return len(rows)


# ------------------------------------------------------------------ main
def clean():
    keep = {j["id"] + ".html" for j in JOBS}
    for f in glob.glob(P("jobs", "*.html")):
        if os.path.basename(f) not in keep:
            os.remove(f)
    for c in CATS:
        f = P(c["slug"] + ".html")
        if not c["jobs"] and os.path.exists(f):
            os.remove(f)
    keep_g = {g["slug"] + ".html" for g in GUIDES} | {"index.html"}
    for f in glob.glob(P("guides", "*.html")):
        if os.path.basename(f) not in keep_g:
            os.remove(f)


def main():
    clean()
    for j in JOBS:
        build_job_page(j)
    for c in LIVE_CATS:
        build_category_page(c)
    build_guides()
    update_root_pages()
    n = build_sitemap()
    print("Built %d job pages, %d category pages, %d guides, sitemap with %d URLs." % (len(JOBS), len(LIVE_CATS), len(GUIDES), n))
    print("Category pages skipped (no matching jobs): %s" % ", ".join(c["slug"] for c in CATS if not c["jobs"]))


if __name__ == "__main__":
    main()
