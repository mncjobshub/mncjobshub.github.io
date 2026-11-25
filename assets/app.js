/* ==========================================================
   MNC JobsHub - app.js (Vanilla JS, no dependencies)
   >>> Edit only the CONFIG below: the whole site updates <<<
   ========================================================== */
(function () {
  "use strict";

  var CONFIG = {
    siteName: "MNC JobsHub",
    siteUrl: "https://mncjobshub.github.io",              // set this after connecting your custom domain (no trailing slash)
    telegramUrl: "https://t.me/datajobsArbaz",
    instagramUrl: "https://www.instagram.com/sqlwitharbaz",
    youtubeUrl: "https://www.youtube.com/channel/UCoLkZOFxtKFdpJcBpXyAyhg",
    email: "mncjobshub.official@gmail.com",
    jobsFile: "jobs.json",                              // relative path (GitHub Pages friendly)
    jobsPerPage: 12,
    // Links for the "Recommended Resources" box on job pages. To add an affiliate link, add an entry with sponsored: true
    resources: [
      { title: "Free ATS Resume Score Checker", desc: "Check your resume score before you apply", url: "https://roastcv.in", sponsored: false },
      { title: "YouTube: SQL & Data Analytics", desc: "Free tutorials and interview preparation", url: "https://www.youtube.com/channel/UCoLkZOFxtKFdpJcBpXyAyhg", sponsored: false }
      // , { title: "Course name", desc: "Short line", url: "https://affiliate-link", sponsored: true }
    ],
    newBadgeDays: 3                                     // number of days the "New" badge is shown
  };

  /* ---------- Helpers ---------- */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safeUrl(u) {
    try {
      var x = new URL(u, location.href);
      return (x.protocol === "http:" || x.protocol === "https:") ? x.href : "#";
    } catch (e) { return "#"; }
  }
  function parseDate(s) {
    var p = String(s || "").split("-");
    if (p.length !== 3) return null;
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return isNaN(d) ? null : d;
  }
  function fmtDate(s) {
    var d = parseDate(s);
    return d ? d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "";
  }
  function isExpired(job) {
    var d = parseDate(job.lastDate);
    if (!d) return false;
    return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59) < new Date();
  }
  function isNew(job) {
    var d = parseDate(job.postedOn);
    if (!d) return false;
    return (Date.now() - d.getTime()) / 86400000 <= CONFIG.newBadgeDays;
  }
  function jobLink(job) { return "job-details.html?id=" + encodeURIComponent(job.id); }
  function absUrl(path) { return CONFIG.siteUrl.replace(/\/$/, "") + "/" + path.replace(/^\//, ""); }


  /* ---------- Company logo (automatic) ---------- */
  // Hosts of job boards, application systems and link shorteners. Their favicon is NOT the
  // company logo, so the logo is not guessed from these links (add a "website" field instead).
  var LOGO_BLOCKED_HOSTS = [
    "myworkdayjobs.com", "workday.com", "greenhouse.io", "lever.co", "smartrecruiters.com", "icims.com",
    "taleo.net", "oraclecloud.com", "successfactors.com", "successfactors.eu", "ashbyhq.com", "bamboohr.com",
    "jobvite.com", "breezy.hr", "recruitee.com", "workable.com", "linkedin.com", "naukri.com", "indeed.com",
    "glassdoor.com", "instahyre.com", "wellfound.com", "unstop.com", "internshala.com", "foundit.in",
    "shine.com", "t.me", "bit.ly", "tinyurl.com", "linktr.ee", "forms.gle", "docs.google.com", "airtable.com", "typeform.com"
  ];
  var SECOND_LEVEL = ["co", "com", "org", "net", "gov", "edu", "ac"];

  function rootDomain(host) {
    var parts = host.replace(/^www\./, "").toLowerCase().split(".");
    if (parts.length <= 2) return parts.join(".");
    var last = parts[parts.length - 1], prev = parts[parts.length - 2];
    if (last.length === 2 && SECOND_LEVEL.indexOf(prev) !== -1) return parts.slice(-3).join("."); // e.g. company.co.in
    return parts.slice(-2).join(".");                                                              // careers.company.com -> company.com
  }
  function companyDomain(job) {
    var explicit = job.website || job.domain;
    var src = explicit || job.applyLink;
    if (!src) return "";
    try {
      var u = new URL(/^https?:\/\//i.test(src) ? src : "https://" + src);
      var host = u.hostname.toLowerCase();
      if (!explicit && LOGO_BLOCKED_HOSTS.some(function (b) { return host === b || host.slice(-b.length - 1) === "." + b; })) return "";
      return rootDomain(host);
    } catch (e) { return ""; }
  }
  function logoSources(domain) {
    return [
      "https://www.google.com/s2/favicons?sz=128&domain=" + encodeURIComponent(domain),
      "https://icons.duckduckgo.com/ip3/" + encodeURIComponent(domain) + ".ico"
    ];
  }
  function logoHTML(job) {
    var initial = esc(String(job.company).charAt(0).toUpperCase());
    var custom = job.logo ? safeUrl(job.logo) : "";
    var domain = custom && custom !== "#" ? "" : companyDomain(job);
    var src = custom && custom !== "#" ? custom : (domain ? logoSources(domain)[0] : "");
    var img = src
      ? '<img class="logo-img" src="' + esc(src) + '" alt="" width="46" height="46" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-domain="' + esc(domain) + '" data-step="0">'
      : initial;
    return '<span class="logo-chip" data-initial="' + initial + '" aria-hidden="true">' + img + "</span>";
  }
  // If a logo fails to load (or is only a tiny default icon), try the next source, then show the company's first letter.
  function logoFail(img) {
    var domain = img.getAttribute("data-domain"), step = +img.getAttribute("data-step") || 0, chip = img.parentNode;
    if (domain) {
      var list = logoSources(domain);
      if (step + 1 < list.length) { img.setAttribute("data-step", String(step + 1)); img.src = list[step + 1]; return; }
    }
    if (chip) chip.textContent = chip.getAttribute("data-initial");
  }
  document.addEventListener("error", function (e) {
    var t = e.target;
    if (t && t.classList && t.classList.contains("logo-img")) logoFail(t);
  }, true);
  document.addEventListener("load", function (e) {
    var t = e.target;
    if (t && t.classList && t.classList.contains("logo-img") && t.naturalWidth && t.naturalWidth < 24) logoFail(t);
  }, true);

  function loadJobs() {
    return fetch(CONFIG.jobsFile, { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (data) {
        var list = Array.isArray(data) ? data : (data.jobs || []);
        return list
          .filter(function (j) { return j && j.id && j.role && j.company; })
          .sort(function (a, b) { return String(b.postedOn || "").localeCompare(String(a.postedOn || "")); });
      });
  }
  function loadError(el) {
    el.innerHTML = '<div class="notice">Jobs could not be loaded. If you opened this file directly (file://), please use a local server (see the README). It will work normally once the site is online.</div>';
  }

  /* ---------- Common: nav, config links, year ---------- */
  function initCommon() {
    var toggle = $(".nav-toggle"), nav = $("#site-nav");
    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        var open = nav.classList.toggle("open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
    var page = (location.pathname.split("/").pop() || "index.html") || "index.html";
    $all(".site-nav a:not(.btn)").forEach(function (a) {
      if (a.getAttribute("href") === page) a.classList.add("active");
    });
    $all("[data-telegram]").forEach(function (a) { a.href = CONFIG.telegramUrl; });
    $all("[data-instagram]").forEach(function (a) { a.href = CONFIG.instagramUrl; });
    $all("[data-youtube]").forEach(function (a) { a.href = CONFIG.youtubeUrl; });
    $all("[data-email]").forEach(function (a) { a.href = "mailto:" + CONFIG.email; a.textContent = CONFIG.email; });
    $all("[data-year]").forEach(function (n) { n.textContent = new Date().getFullYear(); });
    $all("[data-site]").forEach(function (n) { n.textContent = CONFIG.siteName; });
  }

  /* ---------- Home page ---------- */
  function cardHTML(job) {
    var tags = (job.tags || []).map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("");
    var badge = isExpired(job) ? '<span class="tag expired">Expired</span>' : (isNew(job) ? '<span class="tag new">New</span>' : "");
    return '<article class="job-card">' +
      '<div class="job-card-top">' + logoHTML(job) +
      '<div><h3><a href="' + jobLink(job) + '">' + esc(job.role) + "</a></h3>" +
      '<p class="company">' + esc(job.company) + "</p></div></div>" +
      '<ul class="meta">' +
      (job.batch ? '<li data-icon="🎓">Batch: ' + esc(job.batch) + "</li>" : "") +
      (job.location ? '<li data-icon="📍">' + esc(job.location) + "</li>" : "") +
      (job.salary ? '<li data-icon="💰">' + esc(job.salary) + "</li>" : "") +
      "</ul>" +
      '<div class="tags">' + badge + tags + "</div>" +
      '<div class="job-card-foot"><span class="posted">Posted ' + esc(fmtDate(job.postedOn)) + "</span>" +
      '<a class="btn btn-primary btn-sm" href="' + jobLink(job) + '">View Details</a></div>' +
      "</article>";
  }

  function initHome() {
    var grid = $("#jobs-grid");
    if (!grid) return;
    var chipsEl = $("#filters"), countEl = $("#job-count"), moreWrap = $("#load-more"), moreBtn = $("#load-more-btn");
    var input = $("#search-input"), form = $("#search-form");
    var params = new URLSearchParams(location.search);
    var state = { q: params.get("q") || "", tag: params.get("cat") || "All", limit: CONFIG.jobsPerPage, jobs: [] };
    input.value = state.q;

    function matches(job) {
      if (state.tag !== "All" && (job.tags || []).indexOf(state.tag) === -1) return false;
      if (!state.q) return true;
      var hay = [job.company, job.role, job.location, job.batch, job.salary, (job.tags || []).join(" "), (job.skills || []).join(" ")].join(" ").toLowerCase();
      return state.q.toLowerCase().split(/\s+/).every(function (w) { return hay.indexOf(w) !== -1; });
    }

    function render() {
      var list = state.jobs.filter(matches);
      var shown = list.slice(0, state.limit);
      countEl.textContent = list.length + (list.length === 1 ? " job found" : " jobs found");
      if (!list.length) {
        grid.innerHTML = '<div class="empty" style="grid-column:1/-1"><h3>No jobs found</h3><p>Try a different keyword or category, or join our Telegram channel to get alerts for new jobs.</p></div>';
      } else {
        grid.innerHTML = shown.map(function (j, i) {
          var html = cardHTML(j);
          // One in-feed ad placeholder after the 6th card
          if (i === 5 && shown.length > 6) {
            html += '<!-- AD SLOT: in-feed (paste your AdSense code here) --><div class="ad-slot ad-infeed" aria-label="Advertisement"><span>Advertisement</span></div>';
          }
          return html;
        }).join("");
      }
      moreWrap.hidden = shown.length >= list.length;
    }

    function buildChips() {
      var counts = {};
      state.jobs.forEach(function (j) { (j.tags || []).forEach(function (t) { counts[t] = (counts[t] || 0) + 1; }); });
      var tags = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
      if (state.tag !== "All" && tags.indexOf(state.tag) === -1) state.tag = "All";
      chipsEl.innerHTML = ["All"].concat(tags).map(function (t) {
        return '<button type="button" class="chip' + (t === state.tag ? " active" : "") + '" data-tag="' + esc(t) + '">' + esc(t) + "</button>";
      }).join("");
    }

    chipsEl.addEventListener("click", function (e) {
      var b = e.target.closest(".chip");
      if (!b) return;
      state.tag = b.getAttribute("data-tag");
      state.limit = CONFIG.jobsPerPage;
      $all(".chip", chipsEl).forEach(function (c) { c.classList.toggle("active", c === b); });
      render();
    });
    form.addEventListener("submit", function (e) { e.preventDefault(); state.q = input.value.trim(); state.limit = CONFIG.jobsPerPage; render(); });
    input.addEventListener("input", function () { state.q = input.value.trim(); state.limit = CONFIG.jobsPerPage; render(); });
    moreBtn.addEventListener("click", function () { state.limit += CONFIG.jobsPerPage; render(); });

    loadJobs().then(function (jobs) { state.jobs = jobs; buildChips(); render(); }).catch(function () { loadError(grid); });
  }

  /* ---------- Job details page ---------- */
  function setMeta(sel, attr, val) {
    var el = $(sel);
    if (el) el.setAttribute(attr, val);
  }
  function listHTML(items, cls) {
    if (!items || !items.length) return "";
    return '<ul' + (cls ? ' class="' + cls + '"' : "") + ">" + items.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ul>";
  }

  function updateSEO(job) {
    var city = String(job.location || "India").split(",")[0];
    var title = job.company + " " + job.role + " Job in " + city;
    if ((title + " | " + CONFIG.siteName).length <= 65) title += " | " + CONFIG.siteName; // keep titles short enough for search results
    var desc = job.summary || (job.role + " job at " + job.company + " in " + (job.location || "India") + ". Check eligibility, salary and apply link.");
    var url = absUrl("job-details.html?id=" + encodeURIComponent(job.id));
    document.title = title;
    setMeta('meta[name="description"]', "content", desc);
    setMeta('link[rel="canonical"]', "href", url);
    setMeta('meta[property="og:title"]', "content", title);
    setMeta('meta[property="og:description"]', "content", desc);
    setMeta('meta[property="og:url"]', "content", url);
    setMeta('meta[name="twitter:title"]', "content", title);
    setMeta('meta[name="twitter:description"]', "content", desc);

    // Structured data for Google for Jobs
    var ld = {
      "@context": "https://schema.org",
      "@type": "JobPosting",
      "title": job.role,
      "description": (job.description || []).join(" ") || desc,
      "datePosted": job.postedOn,
      "validThrough": job.lastDate ? job.lastDate + "T23:59:59+05:30" : undefined,
      "employmentType": job.employmentType || "FULL_TIME",
      "hiringOrganization": { "@type": "Organization", "name": job.company, "sameAs": companyDomain(job) ? "https://" + companyDomain(job) : undefined, "logo": job.logo ? safeUrl(job.logo) : undefined },
      "jobLocation": { "@type": "Place", "address": { "@type": "PostalAddress", "addressLocality": job.location || "India", "addressCountry": "IN" } },
      "directApply": false,
      "identifier": job.jobId ? { "@type": "PropertyValue", "name": job.company, "value": job.jobId } : undefined
    };
    var s = document.createElement("script");
    s.type = "application/ld+json";
    s.textContent = JSON.stringify(ld);
    document.head.appendChild(s);

    var crumbs = document.createElement("script");
    crumbs.type = "application/ld+json";
    crumbs.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "position": 1, "name": "Home", "item": absUrl("") },
        { "@type": "ListItem", "position": 2, "name": job.company + " " + job.role, "item": url }
      ]
    });
    document.head.appendChild(crumbs);
  }

  function resourcesHTML() {
    var hasAff = CONFIG.resources.some(function (r) { return r.sponsored; });
    return '<div class="panel"><h3>Recommended Resources</h3><div class="resource-list">' +
      CONFIG.resources.map(function (r) {
        return '<a class="resource" href="' + esc(safeUrl(r.url)) + '" target="_blank" rel="' + (r.sponsored ? "sponsored " : "") + 'noopener"><strong>' + esc(r.title) + "</strong><small>" + esc(r.desc) + "</small></a>";
      }).join("") + "</div>" +
      (hasAff ? '<p class="disclosure">Disclosure: Some links are affiliate links. We may earn a commission at no extra cost to you.</p>' : "") + "</div>";
  }

  function initDetails() {
    var root = $("#job-root");
    if (!root) return;
    var id = new URLSearchParams(location.search).get("id");

    loadJobs().then(function (jobs) {
      var job = jobs.filter(function (j) { return j.id === id; })[0];
      if (!job) {
        document.title = "Job not found | " + CONFIG.siteName;
        root.innerHTML = '<div class="panel empty"><h1>Job not found</h1><p>This job has been removed or the link is incorrect.</p><a class="btn btn-primary" href="index.html">View all jobs</a></div>';
        return;
      }
      updateSEO(job);
      var expired = isExpired(job);
      var link = safeUrl(job.applyLink);
      var pageUrl = absUrl("job-details.html?id=" + encodeURIComponent(job.id));
      var shareText = job.role + " at " + job.company + " - " + (job.batch ? job.batch + " batch. " : "") + "Apply here: ";

      var info = [
        ["Company", job.company], ["Role", job.role], ["Batch / Eligibility", job.batch],
        ["Location", job.location], ["Work Mode", job.workMode], ["Salary / CTC", job.salary],
        ["Experience", job.experience], ["Last Date", job.lastDate ? fmtDate(job.lastDate) : ""], ["Job ID", job.jobId]
      ].filter(function (r) { return r[1]; }).map(function (r) {
        return '<div class="info"><span>' + esc(r[0]) + "</span><strong>" + esc(r[1]) + "</strong></div>";
      }).join("");

      var html =
        '<div class="breadcrumb"><a href="index.html">Home</a> &rsaquo; Jobs &rsaquo; ' + esc(job.company) + "</div>" +
        '<div class="job-layout"><article class="panel job-body">' +
        '<div class="job-head">' + logoHTML(job) +
        "<div><h1>" + esc(job.role) + '</h1><p class="company">' + esc(job.company) + "</p></div></div>" +
        '<div class="tags">' + (expired ? '<span class="tag expired">Application closed</span>' : "") +
        (job.tags || []).map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div>" +
        '<div class="info-grid">' + info + "</div>" +
        '<!-- AD SLOT: job-details TOP --><div class="ad-slot" aria-label="Advertisement"><span>Advertisement</span></div>' +
        "<h2>Job Description</h2>" +
        (job.description || []).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("") +
        (job.responsibilities && job.responsibilities.length ? "<h2>Key Responsibilities</h2>" + listHTML(job.responsibilities) : "") +
        (job.requirements && job.requirements.length ? "<h2>Eligibility &amp; Requirements</h2>" + (job.eligibility ? "<p><strong>Eligibility:</strong> " + esc(job.eligibility) + "</p>" : "") + listHTML(job.requirements) : "") +
        (job.skills && job.skills.length ? '<h2>Skills Required</h2><div class="skill-list">' + job.skills.map(function (s) { return "<span>" + esc(s) + "</span>"; }).join("") + "</div>" : "") +
        (job.selectionProcess && job.selectionProcess.length ? "<h2>Selection Process</h2>" + listHTML(job.selectionProcess, "steps") : "") +
        (job.aboutCompany ? "<h2>About " + esc(job.company) + "</h2><p>" + esc(job.aboutCompany) + "</p>" : "") +
        '<!-- AD SLOT: job-details MIDDLE --><div class="ad-slot" aria-label="Advertisement"><span>Advertisement</span></div>' +
        '<div class="apply-box"><h2>' + (expired ? "Applications are closed" : "Ready to apply?") + "</h2>" +
        "<p>" + (expired ? "The last date for this job has passed. Join our Telegram channel for new jobs." : "Always apply on the company's official website. We never charge any fee.") + "</p>" +
        (expired ? "" : '<a class="btn btn-primary btn-lg" href="' + esc(link) + '" target="_blank" rel="noopener noreferrer nofollow">Apply Now &rarr;</a>') +
        '<div class="social-cta"><a class="btn btn-tg" data-telegram href="' + esc(CONFIG.telegramUrl) + '" target="_blank" rel="noopener">Join Telegram</a>' +
        '<a class="btn btn-ig" data-instagram href="' + esc(CONFIG.instagramUrl) + '" target="_blank" rel="noopener">Follow on Instagram</a>' +
        '<a class="btn btn-yt" data-youtube href="' + esc(CONFIG.youtubeUrl) + '" target="_blank" rel="noopener">Subscribe on YouTube</a></div></div>' +
        '<div class="warn"><strong>Safety tip:</strong> Genuine companies never ask for money during recruitment. Do not make any payment, and always verify the official careers page before applying.</div>' +
        '</article><aside class="side">' +
        '<div class="panel"><h3>Share this job</h3><div class="share">' +
        '<a class="btn btn-outline btn-sm" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent(shareText + pageUrl) + '">WhatsApp</a>' +
        '<a class="btn btn-outline btn-sm" target="_blank" rel="noopener" href="https://t.me/share/url?url=' + encodeURIComponent(pageUrl) + "&text=" + encodeURIComponent(shareText) + '">Telegram</a>' +
        '<button class="btn btn-outline btn-sm" type="button" id="copy-link">Copy link</button></div></div>' +
        resourcesHTML() +
        '<!-- AD SLOT: job-details SIDEBAR --><div class="ad-slot" aria-label="Advertisement" style="min-height:250px"><span>Advertisement</span></div>' +
        "</aside></div>" +
        '<section class="related" id="related"></section>';

      root.innerHTML = html;
      initCommon(); // apply the config to the newly injected social links

      var copy = $("#copy-link");
      if (copy) copy.addEventListener("click", function () {
        var done = function () { copy.textContent = "Copied!"; setTimeout(function () { copy.textContent = "Copy link"; }, 1800); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(location.href).then(done);
        else { var t = document.createElement("textarea"); t.value = location.href; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); done(); } catch (e) {} document.body.removeChild(t); }
      });

      // Related jobs (internal linking)
      var rel = jobs.filter(function (j) {
        return j.id !== job.id && (j.tags || []).some(function (t) { return (job.tags || []).indexOf(t) !== -1; });
      });
      if (rel.length < 3) rel = rel.concat(jobs.filter(function (j) { return j.id !== job.id && rel.indexOf(j) === -1; }));
      rel = rel.slice(0, 3);
      if (rel.length) $("#related").innerHTML = '<div class="section-head"><h2>More jobs you may like</h2></div><div class="jobs-grid">' + rel.map(cardHTML).join("") + "</div>";
    }).catch(function () { loadError(root); });
  }

  /* ---------- Contact form (Formspree / mailto fallback) ---------- */
  function initContact() {
    var form = $("#contact-form");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      var action = form.getAttribute("action") || "";
      if (action.indexOf("YOUR_FORM_ID") !== -1) {
        // Formspree is not set up -> open the mail app instead
        e.preventDefault();
        var n = form.elements["name"].value, em = form.elements["email"].value, sub = form.elements["subject"].value, msg = form.elements["message"].value;
        location.href = "mailto:" + CONFIG.email + "?subject=" + encodeURIComponent(sub || "Website enquiry") +
          "&body=" + encodeURIComponent("Name: " + n + "\nEmail: " + em + "\n\n" + msg);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCommon();
    initHome();
    initDetails();
    initContact();
  });
})();
