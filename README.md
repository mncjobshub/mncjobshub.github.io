# MNC JobsHub - Setup Guide

A pure HTML + CSS + vanilla JavaScript job portal. No build step and no backend, so it runs free and fast on GitHub Pages.

## Folder structure

```
jobportal/
├── index.html            Home: search, category filter, job cards
├── job-details.html      Dynamic page  ->  job-details.html?id=<job-id>
├── about.html
├── contact.html
├── privacy-policy.html   Privacy Policy + Disclaimer
├── 404.html
├── jobs.json             All jobs live here
├── robots.txt
├── sitemap.xml
└── assets/
    ├── style.css
    ├── app.js            CONFIG at the top: Telegram, Instagram, YouTube, email, domain, resources
    ├── logo-mark.svg     Logo icon used in header/footer
    ├── favicon.svg, favicon-48.png, apple-touch-icon.png, logo-512.png
    └── og-image.png      Share preview image (1200x630)
```

## 1. Replace these placeholders

| What | Where | Replace with |
|---|---|---|
| Domain `https://mncjobshub.github.io` | All `.html` files, `robots.txt`, `sitemap.xml` | Your domain (Find & Replace All) |
| `siteUrl` | `CONFIG` in `assets/app.js` | Your domain |
| `YOUR_FORM_ID` | `contact.html` | Your Formspree form ID (free) |

Telegram, Instagram and YouTube links are set in `CONFIG`. The HTML files carry the same links as a fallback, and `app.js` overrides them at runtime.

## 2. How to add a new job

Open `jobs.json` and paste a new object into the `jobs` array (copy any existing job and edit it).

| Field | Notes |
|---|---|
| `id` | Unique slug, lowercase with hyphens (for example `tcs-ninja-2026`). It becomes the URL: `job-details.html?id=tcs-ninja-2026` |
| `company`, `role`, `location`, `salary`, `batch`, `experience`, `eligibility`, `workMode`, `jobId` | Shown on the job page. Leave out any field you do not have |
| `tags` | Filter chips on the home page are created automatically from these (for example "Data Analyst", "Internship") |
| `postedOn`, `lastDate` | `YYYY-MM-DD`. After `lastDate` the job shows an "Expired" badge. `lastDate` is optional |
| `employmentType` | `FULL_TIME`, `INTERN`, `PART_TIME` or `CONTRACTOR` (used for Google for Jobs data) |
| `applyLink` | The official apply link. The company logo is picked up from it automatically |
| `description`, `responsibilities`, `requirements`, `skills`, `selectionProcess`, `aboutCompany` | Write in your own words. Aim for 300-400 words in total so every page has unique content |
| `website` (optional) | Company website, used only to find the logo (see below) |
| `logo` (optional) | Direct image URL or a file such as `assets/logos/tcs.png`. Overrides the automatic logo |

You can link a category directly from Instagram or Telegram: `index.html?cat=Internship`

## 3. Automatic company logo

When you add a job, the logo appears automatically:

1. If the job has a `logo`, that image is used.
2. Otherwise the company's domain is taken from `website` (if present) or from `applyLink`. For example `careers.americanexpress.com` becomes `americanexpress.com`.
3. The logo is loaded from Google's favicon service, then from DuckDuckGo's icon service.
4. If no logo is found, or only a tiny default icon, the company's first letter is shown instead.

Important: if the apply link points to a job board or application system (Workday, Greenhouse, Lever, LinkedIn, Naukri and similar), the logo is not guessed, because that would show the wrong logo. Add the company site to the job so the right logo is used:

```json
"website": "americanexpress.com"
```

These services return the company's favicon, which can look small or soft for some companies. For the sharpest result, save the real logo in `assets/logos/` and set `"logo": "assets/logos/company.png"`.

## 4. Resources box (ATS checker, YouTube, affiliate links)

The "Recommended Resources" box on job pages is controlled by `CONFIG.resources` in `assets/app.js`. To add an affiliate link, add one entry with `sponsored: true`. The `rel="sponsored"` attribute and the affiliate disclosure line are added automatically.

## 5. Local testing

`jobs.json` is loaded with `fetch`, so opening `index.html` by double-click will not show jobs. Start a local server:

```
cd jobportal
python3 -m http.server 8000
# then open http://localhost:8000
```

(or use the "Live Server" extension in VS Code)

## 6. Deploy on GitHub Pages

1. Create a new GitHub repository and upload or push all files.
2. Go to Settings -> Pages -> Source: `Deploy from a branch` -> `main` / `(root)` -> Save.
3. Your site goes live at `https://USERNAME.github.io/REPO/`.

All internal links are relative (`assets/...`, `job-details.html`), so they work on a project site (`/REPO/`) and on a custom domain. Only `404.html` uses absolute `/` paths; on a project site, edit it to use `/REPO/`.

## 7. Custom domain (.in / .com)

1. In your registrar's DNS, add `A` records for `185.199.108.153`, `185.199.109.153`, `185.199.110.153` and `185.199.111.153`, plus a `CNAME` for `www` pointing to `USERNAME.github.io`.
2. Add a file named `CNAME` in the repo root containing only your domain (for example `www.yourdomain.in`), or set it under Settings -> Pages -> Custom domain.
3. Turn on "Enforce HTTPS".
4. Find & Replace `yourdomain.in` placeholders and update `CONFIG.siteUrl`.

## 8. Google AdSense

1. Put the site on a custom domain first. AdSense does not approve free `github.io` subdomains.
2. Publish at least 15-20 jobs with original content and get some organic traffic.
3. Add the site in AdSense, then uncomment the `adsbygoogle.js` script in the `<head>` of every HTML file and enter your `ca-pub-...` ID.
4. Create ad units and replace the `<span>` inside each `<div class="ad-slot">` with the AdSense `<ins>` code. Slots: home top, home middle, in-feed (in `app.js`), and job details top, middle and sidebar.
5. Add an `ads.txt` file in the repo root: `google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0`

## 9. About share previews (Open Graph)

Telegram and WhatsApp crawlers do not run JavaScript. When you share a `job-details.html?id=...` link, the preview shows the generic title, description and image, not a different preview for each job. Google Search does run JavaScript, so SEO is not affected. If you want a separate preview for each job, a small script can generate a static page per job from `jobs.json`.

## 10. SEO checklist

Already built in: keyword-focused title, description and H1 on the home page, `en-IN` language and locale tags, canonical URLs, Open Graph tags, WebSite + Organization schema (with your social profiles), JobPosting and Breadcrumb schema on every job page, `sitemap.xml`, `robots.txt` and a text section with FAQs on the home page.

Notes:
- The `keywords` meta tag is ignored by Google, so it is not used. Rankings come from content quality, titles, structure and links.
- Nobody can guarantee the first position. Competition for "MNC jobs" is very high, so also target specific searches such as "<company> off campus 2026", "data analyst fresher jobs" or "python developer fresher Bhubaneswar".

To do after going live:
1. Add the site to Google Search Console (paste the verification tag in `index.html`) and Bing Webmaster Tools, then submit `sitemap.xml`.
2. Add every new job to `sitemap.xml` and use the "Request indexing" button in Search Console for new job URLs.
3. Publish new jobs consistently and write original descriptions. Remove or mark expired jobs.
4. Put your website link in your Instagram bio, Telegram channel description and YouTube channel/video descriptions. These are your first backlinks.

## 11. Branding

The logo is an SVG (`assets/logo-mark.svg`), so it stays sharp at every size. Contact email is `mncjobshub.official@gmail.com`. Colours: navy `#0a2463`, blue `#2563eb`, orange `#f97316`. To change the email later, edit `CONFIG.email` in `assets/app.js` and Find & Replace it in the HTML files.

## 12. Current URL

The site currently uses `https://mncjobshub.github.io`. When you connect a custom domain, Find & Replace `https://mncjobshub.github.io` with your new domain in all `.html` files, `robots.txt`, `sitemap.xml` and `CONFIG.siteUrl` in `assets/app.js`, then add the new domain in Google Search Console and use its "Change of address" tool.

## 13. Auto-build system (job pages, category pages, guides, sitemap)

You only edit `jobs.json`. `build.py` then generates everything else:

| Output | What it is |
|---|---|
| `jobs/<id>.html` | One real HTML page per job (best for Google, WhatsApp and Telegram previews) |
| `fresher-jobs.html`, `data-analyst-jobs.html`, `power-bi-jobs.html`, `sql-jobs.html`, `python-developer-jobs.html`, `jobs-in-bengaluru.html` ... | Search landing pages. A page is created only when at least one job matches, so there are no empty pages |
| `guides/*.html` | Career guides (from `src/guides/`) |
| `sitemap.xml` | Always in sync with all pages |
| `index.html` blocks | Latest jobs, category links and guide links are filled in automatically |

### Option A (recommended): automatic build on GitHub
1. Upload the file `.github/workflows/build.yml` (create it in GitHub with **Add file -> Create new file** and the name `.github/workflows/build.yml`).
2. Edit `jobs.json` on GitHub and commit. In 1-2 minutes the **Actions** tab shows "Build site" running, and the new job pages appear in the repo and on the site.
3. It also rebuilds every day at 06:00 IST so "New" and "Expired" badges stay correct. You can run it manually from **Actions -> Build site -> Run workflow**.

### Option B: build on your computer
Install Python 3, then in this folder run `python3 build.py` and upload the changed files.

### Rules for jobs.json
- `id` is lowercase letters, numbers and hyphens, and must be unique. It becomes the page address.
- Use `tags` such as `Fresher`, `Experienced`, `Data Analyst`, `Software Developer`, `Internship`, `Off-Campus`, `HR`, `QA Testing`, `AI & ML`, `Cloud & Infrastructure`. These decide which category pages the job appears on. Skills and location also match categories (for example `Power BI`, `SQL`, `Python`, `Bengaluru`).
- Add more categories or edit the text in `src/categories.json`. Add or edit guides in `src/guides/` (the first lines are `title:`, `description:`, `date:`, then a line with `---`, then the HTML).
- Links, email and resources for generated pages are in `src/site.json`.
- When you change your domain, update `siteUrl` in `src/site.json` and `assets/app.js`, Find & Replace the old address in `index.html`, `about.html`, `contact.html`, `privacy-policy.html`, `job-details.html` and `robots.txt`, then run the build again.
