# Accessibility walkthrough: the pages read as a screen-reader user meets them

Written 25 October 2026 by hand from the output of the checks named below. **This is an internal software check. No person has used these pages with a screen reader, and no outside expert has reviewed them.** It finds structure problems that a program can find. It does not show that the pages are pleasant or even workable with NVDA, JAWS, VoiceOver or TalkBack. Section 6 lists what a person still has to do.

## 1. What was checked

Chromium 1194 (the build installed here) driven by Playwright 1.63, desktop width 1280 px unless stated. Two views of each page were read:

- the accessibility tree, as Playwright prints it (`locator.ariaSnapshot()`), for the roles, names, states and order;
- Chrome's own accessibility tree through the DevTools protocol (`Accessibility.getPartialAXTree`), where the name or value of one control mattered (slider values, button names, the live-region properties of `<output>`).

Flows read, each from a fresh page load: the front page; a study page (the joint-reachability study and the others in the list below); the data page; the methods and sources pages; the dials page on load, after moving a dial with the arrow keys, after pressing "Make SIMBA look like TNG", after pressing a redshift button and during the tour; the Explorer on first load (`highline.html`), after choosing a relation (by keyboard), after toggling a legend entry (by keyboard), with the evidence panel open (a curve clicked), the Notes, Customise and Get data panels, the "Your run" panel before and after "Try an example", the Vs observations, What exists, Disagreement, Distribution and Over time views, the About dialog and the search dialog. Tab order of the Explorer was walked for 210 stops.

Every one of the 19 site pages and the 404 page was also read as a tree by `scripts/test-a11y-tree.mjs`, which now fails when a control loses its name, a heading level is skipped, the landmarks are wrong, two links with the same name go to different places, a table lacks header cells, row headers or a name, a link that opens a new tab does not say so, or the dials page stops announcing its results. The checker was tried on a copy of `dist/` with seven deliberate breaks (a row header turned back into a cell, a removed new-tab note, a skipped heading level, an unhidden section sign, an unnamed button, two links with one name, a redshift button without a name); it reported each of them.

## 2. Reading the pages in order

**Site pages (all of them share this shape).** Skip link, then the banner (home link, the Main navigation, the version link, the theme button, and a strip of counts), then `main`, then the footer. Inside `main`: a navigation called "On this page" with the section list, the kicker line, one `h1`, the lead paragraph, then `h2` sections that are landmarks (`region`) named by their heading. The order is the visual order; headings never skip a level on any page (the test checks it). The skip link goes to `main`. There is one `h1`, one banner, one `main` and one footer landmark per page.

**Dials page.** After the sections' text comes the instrument: a guide (`details`), the tour button, one sentence ("At these dials the two universes agree on 2 of 11 things"), a group of five redshift buttons, two groups of four dials (a fieldset for each universe), the selects and buttons that search the dials, the fit form (a `details`), three download buttons, a summary line, the eleven chart panels (each a `figure` with a chart that has a text alternative) and the distance table. Reading it in this order is sensible.

**Explorer.** Skip link ("Skip to the chart"), banner (view buttons, site links, tool buttons, theme, About), the relation rail (a navigation with seven `h2` groups of buttons), then `main` with the `h1`, the sub-title, the first-visit note, the chart, the legend, then the details panel (an `aside` with five tabs), then the footer with the play button and the epoch slider. The relation rail comes before `main`, so the headings read h2, h2, ..., h1. The chart's description is a live region that is rewritten on every change; that is how a change of relation or epoch is announced.

## 3. What was found and fixed on the site

| # | What a screen-reader user met | Element | Fix (in this repository) |
|---|---|---|---|
| S1 | Every section heading was read as "§1Start here": the section sign and number were part of the heading's name, and the contents links read the same way. 80 headings and 80 contents links. | `<span class="sn">§1</span>` in `site/src/*.html`; `<span>§1</span>` in the "On this page" navigation | `aria-hidden="true"` on both spans. The test fails if a heading name starts with "§". |
| S2 | No table had a row header (46 tables, 0 row headers): in a 46-row table a cell was read without the row it belongs to. | first `<td>` of each body row | `scripts/build-site.mjs`, `rowHeaders()`: the first cell of each body row becomes `<th scope="row">` (638 cells), except numeric first cells and cells that span columns. The studies tables and the dials page's tables build the cell directly. `site/src/site.css` has one block that sets `th[scope=row]` like the cells beside it. |
| S3 | 19 tables had no name, so the list of tables in a screen reader showed "table" 19 times. | `<table>` | `nameTables()` in `scripts/build-site.mjs` names a table after the heading above it (unless a caption or a labelled wrapper exists). |
| S4 | 284 links open a new tab (83 on Methods, 190 on Sources, 3 on the seeding page, others) without saying so. | `<a target="_blank">` | `newTabNote()` adds `title="Opens in a new tab"`, which is read as the link's description; the visible text is unchanged. |
| S5 | Links with the same name went to different places: three "Explorer" links in the Methods figures (three relations), six "open" links on Sources (one per simulation), "Methods" and "Data" used as the text of section links while the menu has links of the same name to the top of those pages. | `site/src/methods.html`, `scripts/build-site.mjs` (simulation cards), `site/src/index.html`, `data.html` | The links now say what they open ("Open the star-forming main sequence in the Explorer", "open IllustrisTNG in the Explorer", "Methods, limits", "Methods, how values enter", "Data, evidence tiers"). The test compares names and targets on every page; in-page contents links are left out of the comparison. |
| S6 | The footer's 17 links were a paragraph, not a navigation; the strip of counts in the banner was bare text. | footer `<p class="links">`, `.status` | `<nav aria-label="More pages and project files">` around the footer links; `role="group"` with a label on the strip. |
| S7 | Dials page: each of the eight value read-outs (`<output>`) is a live region, and every redraw rewrote all eight, so moving one dial could speak eight values. | `<output>` | `aria-live="off"` on the outputs, and only the text that changed is written. The dial's spoken value is its `aria-valuetext` ("×1.07"), which was already set. |
| S8 | Dials page: pressing "Make SIMBA look like TNG" (or any search) spoke only the one-sentence summary; the paragraph that says what moved, what came into line and what was given up appeared silently. | `#rt-live` | The live region now says the new story once (it contains the summary), and afterwards the summary only when it changes. |
| S9 | Dials page: the redshift buttons were named "z = 0.00 1/11"; pressing one rebuilt the strip, so keyboard focus fell to the page. | `.rt-z` | `aria-label="z = 0.95: 2 of 11 properties agree"`, and the rebuilt button takes focus back. |
| S10 | Dials page: the three selects had names ("Property to match", "Keep this property as it is") that do not contain the words on screen ("Match on", "While keeping"); the eight dials were named identically in the two universes. | `#rt-match`, `#rt-hold`, `#rt-obs`, the dial labels | Names now start with the visible label ("Match on (the property to match)"); each dial label has a hidden prefix ("IllustrisTNG: Supernova wind strength"). |
| S11 | Dials page: the charts' text alternative said what the panel is ("Stellar mass function at z = 0.00: IllustrisTNG and SIMBA emulated curves"), not what it shows. | chart `svg role="img"` | The alternative now gives the curves' values at the ends of the range (or for each category) and the average difference between the codes. The numbers are computed in the page from the emulators. |
| S12 | Dials page: the tour dialog's text was not tied to the dialog and the whole dialog (with its buttons) was a live region; a pinned copy of one chart (used on narrow screens) was read twice; the sensitivity bar beside each dial carried its message only in a tooltip; a duplicate id (`rtc-gsmf-090`). | `.rt-tour`, `.rt-mini`, `.rt-sens` | `aria-describedby` on the dialog and the live region on its text only; the pinned copy is `aria-hidden` and its ids are unique; the bar is an image with a label. |

Not changed on purpose: the dials page's `<fieldset>` for each universe (a screen reader announces the group name when entering it, which is the right behaviour), the `details` guide, and the Contents navigation (its links now share a name with the menu entries "Data", "Methods"; they are in a landmark called "On this page", and the test does not count them).

## 4. Explorer: patches for the coordinator

`highline/index.html` is being changed by someone else, so none of this is applied. Each patch below is an exact before/after on the current file (commit 8ccbff6). They were applied together to a copy of the built `dist/highline.html`, with the content-security hash recomputed. `node scripts/test-a11y-tree.mjs --explorer` reports 22 problems on the current Explorer and none on the patched copy. The existing suites `test-keyboard`, `test-ui` and `test-yourrun` were run on the patched copy; the results are in section 5. To check after applying: build, then `node scripts/test-a11y-tree.mjs --explorer`. When the patches are merged, add `--explorer` to the `test:a11y` script in `package.json` and to the `test-a11y-tree` line in the workflows so the Explorer is covered by the test every time.

Each "Before" text occurs exactly once in the file unless said otherwise (the script that tries the patches checks that).

### E1. A closed details panel is still in the tab order and the tree

**What a screen-reader or keyboard user meets.** The panel is moved off screen with a transform only. With it closed, Tab lands on its five tabs and the Close button (stops 134 to 139 of the first page load, after the whole legend), invisible, and a screen reader lists them as controls. The existing keyboard test stops after 90 stops and never gets there.

**Edit E1.1**

Before:

```
transform:translateX(100%);transition:transform .3s ease;z-index:5}
.panel.open{transform:none}
```

After:

```
transform:translateX(100%);visibility:hidden;transition:transform .3s ease,visibility 0s linear .3s;z-index:5}
.panel.open{transform:none;visibility:visible;transition:transform .3s ease,visibility 0s}
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (closed panel: visibility hidden).

### E2. The epoch slider says its position, not the redshift

**What a screen-reader or keyboard user meets.** A screen reader says "Redshift, slider, 2" (the index of the epoch) because the slider has no aria-valuetext; the redshift is only in the visible label next to it. In the Over time view the same slider sets x and also says only a number.

**Edit E2.1**

Before:

```
inp.setAttribute("aria-label","Redshift");
```

After:

```
inp.setAttribute("aria-label","Redshift");inp.setAttribute("aria-valuetext","z = "+fmtZ(currentZ()));
```

**Edit E2.2**

Before:

```
inp.setAttribute("aria-label","Evaluate at x");
```

After:

```
inp.setAttribute("aria-label","Evaluate at x");inp.setAttribute("aria-valuetext","x = "+atX());
```

**Edit E2.3**

Before:

```
if(REL[state.rel].xz){inp.min=0;inp.max=0;inp.value=0;inp.disabled=true;
```

After:

```
if(REL[state.rel].xz){inp.min=0;inp.max=0;inp.value=0;inp.disabled=true;inp.removeAttribute("aria-valuetext");
```

Test: `node scripts/test-a11y-tree.mjs --explorer` ().

### E3. The play button does not say whether it is playing

**What a screen-reader or keyboard user meets.** The icon changes between play and pause but the name stays "Play through redshift" and no state is exposed.

**Edit E3.1**

Before:

```
<button class="play" id="play" aria-label="Play through redshift">
```

After:

```
<button class="play" id="play" aria-label="Play through redshift" aria-pressed="false">
```

**Edit E3.2**

Before:

```
state.playing=null;$("playIcon").setAttribute("d","M3 1.5v11l9-5.5z");return}
```

After:

```
state.playing=null;$("playIcon").setAttribute("d","M3 1.5v11l9-5.5z");$("play").setAttribute("aria-pressed","false");return}
```

**Edit E3.3**

Before:

```
$("playIcon").setAttribute("d","M2.5 1.5h3.5v11h-3.5zM8 1.5h3.5v11h-3.5z");
```

After:

```
$("playIcon").setAttribute("d","M2.5 1.5h3.5v11h-3.5zM8 1.5h3.5v11h-3.5z");$("play").setAttribute("aria-pressed","true");
```

Test: `node scripts/test-a11y-tree.mjs --explorer` ().

### E4. Focus is lost whenever a list is rebuilt

**What a screen-reader or keyboard user meets.** Pressing Enter on a legend entry, on a relation in the rail, on "Try an example" or on a Get data option rebuilds that part of the page with innerHTML, so the focused element is removed and focus falls to the page (document.body). A keyboard user starts again from the top; a screen reader says nothing about the new state. Fix: remember which control had focus (by id or data attribute) and focus its replacement.

**Edit E4.1**

Before:

```
function renderLegend(cur){
```

After:

```
/* keep the keyboard where it was when a list is rebuilt */
function focusKey(root){const a=document.activeElement;if(!a||a===document.body||!root.contains(a))return null;if(a.id)return"#"+a.id;if(a.type==="radio"&&a.name)return`[name="${a.name}"][value="${a.value}"]`;for(const n of["data-s","data-only","data-u","data-o","data-ev","data-ref","data-an","data-x","data-r","data-def"])if(a.hasAttribute(n))return`[${n}="${CSS.escape(a.getAttribute(n))}"]`;return null}
function restoreFocus(root,k){if(!k)return;const n=root.querySelector(k);if(n)n.focus({preventScroll:true})}
function renderLegend(cur){
```

**Edit E4.2**

Before:

```
const L=$("legend");L.classList.toggle("closed",!state.legendOpen);L.innerHTML=`<button class="legtog" id="legTog" aria-expanded="${state.legendOpen}">Legend ${state.legendOpen?"▾":"▸"}</button>`+(state.legendOpen?h:"");
```

After:

```
const L=$("legend"),fk=focusKey(L);L.classList.toggle("closed",!state.legendOpen);L.innerHTML=`<button class="legtog" id="legTog" aria-expanded="${state.legendOpen}">Legend <span aria-hidden="true">${state.legendOpen?"▾":"▸"}</span></button>`+(state.legendOpen?h:"");restoreFocus(L,fk);
```

**Edit E4.3**

Before:

```
  $("presets").innerHTML=groups.map(
```

After:

```
  const fk=focusKey($("presets"));$("presets").innerHTML=groups.map(
```

**Edit E4.4**

Before:

```
  $("presets").querySelectorAll("button[data-r]").forEach(b=>b.onclick=()=>selectRelation(b.dataset.r));
```

After:

```
  $("presets").querySelectorAll("button[data-r]").forEach(b=>b.onclick=()=>selectRelation(b.dataset.r));restoreFocus($("presets"),fk);
```

**Edit E4.5**

Before:

```
  if(state.tab==="evidence")body.innerHTML=evidenceHtml();else if(state.tab==="about")body.innerHTML=aboutHtml();else if(state.tab==="tune")body.innerHTML=tuneHtml();else if(state.tab==="mine")body.innerHTML=mineHtml();else body.innerHTML=dataHtml();
```

After:

```
  const fk=focusKey(body);
  if(state.tab==="evidence")body.innerHTML=evidenceHtml();else if(state.tab==="about")body.innerHTML=aboutHtml();else if(state.tab==="tune")body.innerHTML=tuneHtml();else if(state.tab==="mine")body.innerHTML=mineHtml();else body.innerHTML=dataHtml();
```

**Edit E4.6**

Before:

```
  if(state.tab==="evidence")wireEvidence();else if(state.tab==="tune")wireTune();else if(state.tab==="mine")wireMine();else if(state.tab==="data")wireData();
```

After:

```
  if(state.tab==="evidence")wireEvidence();else if(state.tab==="tune")wireTune();else if(state.tab==="mine")wireMine();else if(state.tab==="data")wireData();
  restoreFocus(body,fk);
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (focus kept: legend entry, relation, Try an example).

### E5. Opening a panel does not move focus into it, and the tab panel has no name

**What a screen-reader or keyboard user meets.** Pressing Notes, Customise, Your run or Get data only toggles aria-pressed; the panel is the last thing in the page, so its content is about 130 Tab stops away and nothing is announced. Clicking a curve opens Evidence the same way. The five tabs have no ids and the tab panel has no aria-labelledby, so it is announced as an unnamed panel. The tab strip calls the same thing "My run" that the toolbar calls "Your run".

**Edit E5.1**

Before:

```
<button role="tab" data-t="evidence">Evidence</button><button role="tab" data-t="about">Notes</button><button role="tab" data-t="mine">My run</button><button role="tab" data-t="tune">Customise</button><button role="tab" data-t="data">Get data</button>
```

After:

```
<button role="tab" id="tab-evidence" aria-controls="pbody" data-t="evidence">Evidence</button><button role="tab" id="tab-about" aria-controls="pbody" data-t="about">Notes</button><button role="tab" id="tab-mine" aria-controls="pbody" data-t="mine">Your run</button><button role="tab" id="tab-tune" aria-controls="pbody" data-t="tune">Customise</button><button role="tab" id="tab-data" aria-controls="pbody" data-t="data">Get data</button>
```

**Edit E5.2**

Before:

```
b.tabIndex=b.dataset.t===state.tab?0:-1});
  const body=$("pbody");
```

After:

```
b.tabIndex=b.dataset.t===state.tab?0:-1});
  $("pbody").setAttribute("aria-labelledby","tab-"+state.tab);
  const body=$("pbody");
```

**Edit E5.3**

Before:

```
$("bMine").setAttribute("aria-pressed",tab==="mine")}
```

After:

```
$("bMine").setAttribute("aria-pressed",tab==="mine");const sel=$("panel").querySelector('.tabs [data-t="'+tab+'"]');if(sel&&panelOpener&&panelOpener!==document.body&&!$("panel").contains(document.activeElement))sel.focus({preventScroll:true})}
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (panel takes focus; tab panel named).

### E6. Heading levels in the panel and the distribution cards skip levels

**What a screen-reader or keyboard user meets.** The page has h1 (the title in main) and h2 (the groups in the relation rail, which comes before main in the source). The panel then uses h3 for its title and h4 for its sections, and the Your run tab uses only h4: a screen-reader user who navigates by heading meets h4 with no h2 or h3 before it. aria-level changes what is exposed without changing the look (the styles are on the tag names). Panel titles become level 2, their sections level 3; the three sections of Your run (which has no title) become level 2; the distribution cards, which sit under the view's h1, become level 2.

**Edit (headings, by script).** In `highline/index.html`, between `function evidenceHtml()` and `function wireData()`: every `<h3>` becomes `<h3 aria-level="2">` (6 places), every `<h4>` outside `mineHtml()` becomes `<h4 aria-level="3">` (11 places), and the three `<h4>` in `mineHtml()` (including `<h4 id="mineH">`) get `aria-level="2"` (3 places). Example:

```
before:  return`<h4>YOUR RUN ON ${esc(REL[rel].t.toUpperCase())}</h4>
after:   return`<h4 aria-level="2">YOUR RUN ON ${esc(REL[rel].t.toUpperCase())}</h4>
```

The same script is `E6` in the patch list used to try these edits (see the end of this section); the counts are asserted.

**Edit E6.1**

Before:

```
open the record."><h3>${esc(label(r))}${r.kind==="observation"
```

After:

```
open the record."><h3 aria-level="2">${esc(label(r))}${r.kind==="observation"
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (headings in the panel start at h2).

### E7. Legend buttons have no usable names

**What a screen-reader or keyboard user meets.** The legend has 17 rows of three buttons named "only", "z" and "Show runs" (a screen reader lists the same three names 17 times, with no simulation in them), the Observations row's expander is named "▸", the Legend toggle reads its arrow aloud, and the reference and anchor buttons are "ref" and "anchor". Each button gets a name that says what it acts on; the visible text stays inside the name.

**Edit E7.1**

Before:

```
<button class="mini" data-only="${esc(s)}" title="Show only this simulation">only</button><button class="mini" data-ev="${esc(prim[0])}" aria-pressed="${state.evo===prim[0]}" title="Plot every epoch of this run, coloured by redshift">z</button>${runs.length>1?`<button class="mini" data-x="${esc(s)}" aria-label="Show runs" aria-expanded="${open}">${open?"▾":"▸"}</button>`:""}
```

After:

```
<button class="mini" data-only="${esc(s)}" aria-label="Show only ${esc(SHORT[s]||s)}" title="Show only this simulation">only</button><button class="mini" data-ev="${esc(prim[0])}" aria-pressed="${state.evo===prim[0]}" aria-label="Plot every epoch (z) of ${esc(SHORT[s]||s)}, coloured by redshift" title="Plot every epoch of this run, coloured by redshift">z</button>${runs.length>1?`<button class="mini" data-x="${esc(s)}" aria-label="Runs of ${esc(SHORT[s]||s)}" aria-expanded="${open}"><span aria-hidden="true">${open?"▾":"▸"}</span></button>`:""}
```

**Edit E7.2**

Before:

```
<button class="mini" data-ev="${esc(u)}" aria-pressed="${state.evo===u}" title="Plot every epoch of this run">z</button>
```

After:

```
<button class="mini" data-ev="${esc(u)}" aria-pressed="${state.evo===u}" aria-label="Plot every epoch (z) of ${esc(name)}" title="Plot every epoch of this run">z</button>
```

**Edit E7.3**

Before:

```
<button class="mini" data-x="__obs" aria-expanded="${oopen}">${oopen?"▾":"▸"}</button>
```

After:

```
<button class="mini" data-x="__obs" aria-label="Observation sources" aria-expanded="${oopen}"><span aria-hidden="true">${oopen?"▾":"▸"}</span></button>
```

**Edit E7.4**

Before:

```
aria-pressed="${state.ref===unitOf(oall.find(r=>r.source===s))}" title="Compare everything against this">ref</button>
```

After:

```
aria-pressed="${state.ref===unitOf(oall.find(r=>r.source===s))}" aria-label="Compare everything against ${esc(s)}" title="Compare everything against this">ref</button>
```

**Edit E7.5**

Before:

```
aria-pressed="${!!anc&&anc.source===s}" ${pickObs(rel,z).some(r=>r.source===s)?"":"disabled"} title=
```

After:

```
aria-pressed="${!!anc&&anc.source===s}" aria-label="Use ${esc(s)} as the anchor" ${pickObs(rel,z).some(r=>r.source===s)?"":"disabled"} title=
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (legend buttons named).

### E8. The marks in the legend are letters and symbols with the meaning in a tooltip

**What a screen-reader or keyboard user meets.** Each legend row ends with a source letter (O, C, T, F, D), an offset number and a symbol (check mark, tilde, cross). The meaning is only in a title attribute, which a screen reader does not read, so a row is read as "COLIBRE, D, +0.10, ✕". The letters get a spoken name, the offset says what it is, and the symbols get a spoken word (role img with a label; the symbols and the text on screen are unchanged).

**Edit E8.1**

Before:

```
return`<span class="pv t${g}" title="${esc((TIER_SHORT[p.tier]||p.tier)+": "+citeShort(r))}">${g}</span>`
```

After:

```
return`<span class="pv t${g}" role="img" aria-label="${esc(TIER_SHORT[p.tier]||p.tier)}" title="${esc((TIER_SHORT[p.tier]||p.tier)+": "+citeShort(r))}">${g}</span>`
```

**Edit E8.2**

Before:

```
in y units">${d>=0?"+":"−"}${Math.abs(d).toFixed(2)}</span>`};
```

After:

```
in y units" role="img" aria-label="offset ${d>=0?"+":"−"}${Math.abs(d).toFixed(2)}">${d>=0?"+":"−"}${Math.abs(d).toFixed(2)}</span>`};
```

**Edit E8.3**

Before:

```
(v.blockers.length?": "+v.blockers.join("; "):v.caveats.length?": "+v.caveats.join("; "):""))}">${k==="comparable"?"✓":k==="not-comparable"?"✕":"~"}</span>`};
```

After:

```
(v.blockers.length?": "+v.blockers.join("; "):v.caveats.length?": "+v.caveats.join("; "):""))}" role="img" aria-label="${k==="comparable"?"comparable":k==="not-comparable"?"not comparable":"comparable with caveats"}">${k==="comparable"?"✓":k==="not-comparable"?"✕":"~"}</span>`};
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (legend marks have words).

### E9. Messages (toasts) and view changes are silent

**What a screen-reader or keyboard user meets.** toast() writes into a div that is shown for 1.8 s and has no live-region role, so "Link copied", "Python snippet copied" and the error messages are never announced. Switching view (Over time, What exists, Vs observations, Disagreement, Distribution) announces nothing either: the pressed state of the button changes and the new content appears elsewhere. One always-present status region carries both.

**Edit E9.1**

Before:

```
<div class="toast" id="toast"></div>
```

After:

```
<div class="toast" id="toast" aria-hidden="true"></div><div class="sr" id="toastLive" role="status" aria-live="polite"></div>
```

**Edit E9.2**

Before:

```
function toast(m){const t=$("toast");t.textContent=m;
```

After:

```
function say(m){const l=$("toastLive");l.textContent="";setTimeout(()=>{l.textContent=m},30)}
function toast(m){const t=$("toast");say(m);t.textContent=m;
```

**Edit E9.3**

Before:

```
if(m==="dist")renderDist();renderAll(false)}
```

After:

```
if(m==="dist")renderDist();renderAll(false);say((isTable()?document.querySelector("#"+m+" h1"):$("shTitle")).textContent)}
```

**Edit E9.4**

Before:

```
$("shTitle").textContent=t;$("shSub").textContent=sub;
```

After:

```
$("shTitle").textContent=t;$("shSub").textContent=sub;document.title=t+" · sim-highline";
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (toast and view change announced; page title follows the view).

### E10. The About and search dialogs do not hold focus or give it back

**What a screen-reader or keyboard user meets.** Both are marked aria-modal, but Tab leaves them for the page behind (the 13th Tab stop in About is the play button), Escape closes About without returning focus to the (i) button (focus stays wherever it had wandered), and when focus is outside the search box Escape does nothing, so the search dialog stays open. The Escape handler also closes About and the panel in one press. Fix: wrap Tab inside the open dialog, close the topmost layer first, and restore focus to what opened it.

**Edit E10.1**

Before:

```
function palOpen(){$("pal").classList.add("on");$("palQ").value="";pal.sel=0;palRender();$("palQ").focus()}
function palClose(){$("pal").classList.remove("on")}
```

After:

```
let palFrom=null;
function palOpen(){palFrom=document.activeElement;$("pal").classList.add("on");$("palQ").value="";pal.sel=0;palRender();$("palQ").focus()}
function palClose(){$("pal").classList.remove("on");if(palFrom&&document.contains(palFrom))palFrom.focus();palFrom=null}
/* keep Tab inside whichever dialog is open */
document.addEventListener("keydown",e=>{if(e.key!=="Tab")return;const d=$("pal").classList.contains("on")?$("pal"):$("about").classList.contains("on")?$("about"):null;if(!d)return;const f=[...d.querySelectorAll('a[href],button,input,select,textarea,[tabindex="0"]')].filter(x=>!x.disabled&&x.getClientRects().length);if(!f.length)return;const first=f[0],last=f[f.length-1],a=document.activeElement;if(!d.contains(a)){e.preventDefault();first.focus()}else if(e.shiftKey&&(a===first||a===d.firstElementChild)){e.preventDefault();last.focus()}else if(!e.shiftKey&&a===last){e.preventDefault();first.focus()}});
```

**Edit E10.2**

Before:

```
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("about").classList.remove("on");if(state.panel)closePanel();else closeRecord()}
```

After:

```
document.addEventListener("keydown",e=>{if(e.key==="Escape"){if($("pal").classList.contains("on")){palClose();return}if($("about").classList.contains("on")){$("about").classList.remove("on");$("infoBtn").focus();return}if(state.panel)closePanel();else closeRecord()}
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (About and search dialogs hold and return focus).

### E11. Your run: unnamed fields, long names, results not announced, table without a name

**What a screen-reader or keyboard user meets.** The two text fields are named only by their placeholder ("label", "x,y per line"). Each definition list's accessible name is its label plus its whole help sentence ("Volume for densities Whether number densities are per comoving or per physical volume."): the help belongs in aria-describedby. After "Plot" or "Try an example" the sentence "68 points read, ..." sits in a live region that is created by the same re-render, so it is not announced. The results table has no name, its header cells are "defs", "Δ" and "n", and the verdict is a symbol.

**Edit E11.1**

Before:

```
<input type="text" id="uName" placeholder="label"
```

After:

```
<input type="text" id="uName" aria-label="Name for your run" placeholder="label"
```

**Edit E11.2**

Before:

```
<textarea id="uText" placeholder="x,y per line">
```

After:

```
<textarea id="uText" aria-label="Your curve, one x,y pair per line" placeholder="x,y per line">
```

**Edit E11.3**

Before:

```
return`<label>${esc(keyLabel(k))}<small>${esc(MINE_HELP[k]||"")}</small><select data-def="${esc(k)}">
```

After:

```
return`<label>${esc(keyLabel(k))}<small id="dh-${esc(k)}">${esc(MINE_HELP[k]||"")}</small><select data-def="${esc(k)}" aria-label="${esc(keyLabel(k))}" aria-describedby="dh-${esc(k)}">
```

**Edit E11.4**

Before:

```
i.innerHTML=state.user?mineInfo(state.user):esc(window.SimHighlineLogic.inspectUserCurve(txt,{linear:lin},mineExpect()).warnings.concat(window.SimHighlineLogic.inspectUserCurve(txt,{linear:lin}).summary).join(" "))}};
```

After:

```
i.innerHTML=state.user?mineInfo(state.user):esc(window.SimHighlineLogic.inspectUserCurve(txt,{linear:lin},mineExpect()).warnings.concat(window.SimHighlineLogic.inspectUserCurve(txt,{linear:lin}).summary).join(" "));const rs=state.user?mineRows():[],fair=rs.filter(x=>x.v&&x.v.verdict!=="not-comparable").length;say(i.textContent+(state.user?` Compared with ${rs.length} published curve${rs.length===1?"":"s"} at this epoch; ${fair} fair to compare.`:""))}};
```

**Edit E11.5**

Before:

```
<table class="mt"><thead><tr><th>Published curve</th><th title="definition compatibility with your declared definitions">defs</th><th title="median of (your run − curve) over the shared x range, in y units">Δ</th><th title="shared x bins">n</th></tr></thead>
```

After:

```
<table class="mt" aria-label="Your run against each published curve"><thead><tr><th>Published curve</th><th aria-label="Definitions: do they agree with yours" title="definition compatibility with your declared definitions">defs</th><th aria-label="Offset: median of your run minus the curve" title="median of (your run − curve) over the shared x range, in y units">Δ</th><th aria-label="Shared x bins" title="shared x bins">n</th></tr></thead>
```

**Edit E11.6**

Before:

```
<td><span class="v ${c}">${v?g:""}</span></td>
```

After:

```
<td><span class="v ${c}"${v?` role="img" aria-label="${k==="comparable"?"comparable":k==="not-comparable"?"not comparable":"comparable with caveats"}"`:""}>${v?g:""}</span></td>
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (Your run: named fields, announced result).

### E12. Table views: empty corner cells, abbreviations, details only in tooltips

**What a screen-reader or keyboard user meets.** What exists, Vs observations and Disagreement are real tables with row headers, which is good. Their top-left header cell is empty; their column headers are abbreviations (GSMF, SFMS, M●–M★) whose full names are in a title attribute; and the cells carry their meaning ("Illustris · TNG100-1 vs Speagle: above by 0.10 in y units (not comparable)", "spread 0.14 across ...") only in title, so a cell is read as "+0.10 ✕" or "0.14 5". A small observer copies each title to aria-label (cells and headers), and the three corners get a hidden word.

**Edit E12.1**

Before:

```
</p></div><table><tr><th></th>${rels.map(k=>`<th title="${esc(REL[k].t)}">${esc(REL[k].c)}</th>`).join("")}
```

After:

```
</p></div><table><tr><th><span class="sr">Simulation</span></th>${rels.map(k=>`<th title="${esc(REL[k].t)}">${esc(REL[k].c)}</th>`).join("")}
```

**Edit E12.2**

Before:

```
</div><table><tr><th></th>${rels.map(k=>`<th title="${esc(REL[k].t)} against 
```

After:

```
</div><table><tr><th><span class="sr">Simulation</span></th>${rels.map(k=>`<th title="${esc(REL[k].t)} against 
```

**Edit E12.3**

Before:

```
<table class="sp"><tr><th></th>${TZ.map(
```

After:

```
<table class="sp"><tr><th><span class="sr">Relation</span></th>${TZ.map(
```

**Edit E12.4**

Before:

```
function renderAtlas(){
```

After:

```
/* the details of a table cell are in its title, which screen readers do not read: copy them to aria-label */
for(const id of["atlas","tension","spread"])new MutationObserver(()=>$(id).querySelectorAll("td[title]:not([aria-label]),th[title]:not([aria-label])").forEach(c=>c.setAttribute("aria-label",c.title))).observe($(id),{childList:true,subtree:true});
function renderAtlas(){
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (table views: corner words and cell labels).

### E13. Notes and Get data: link and button names

**What a screen-reader or keyboard user meets.** The reference list has "doi" and "arXiv" links repeated once per paper with no paper in the name. In Get data the two range fields ("z from [ ] to [ ]") have no name of their own, three buttons are named only "JSON", "SVG" and "PNG", and two different buttons are both named "Copy BibTeX" (the plotted curves, and the dataset). In Customise, the IMF check box's accessible name is a 190-character sentence.

**Edit E13.1**

Before:

```
<a href="https://doi.org/${esc(r.doi)}" target="_blank" rel="noopener">doi</a> · <a href="https://arxiv.org/abs/${esc(r.arxiv)}" target="_blank" rel="noopener">arXiv</a>
```

After:

```
<a href="https://doi.org/${esc(r.doi)}" target="_blank" rel="noopener" aria-label="doi: ${esc(r.cite)} (opens in a new tab)">doi</a> · <a href="https://arxiv.org/abs/${esc(r.arxiv)}" target="_blank" rel="noopener" aria-label="arXiv: ${esc(r.cite)} (opens in a new tab)">arXiv</a>
```

**Edit E13.2**

Before:

```
<input type="number" step="any" id="dz0" value="${dl.z0}" style="width:70px">
```

After:

```
<input type="number" step="any" id="dz0" aria-label="z from (lowest redshift)" value="${dl.z0}" style="width:70px">
```

**Edit E13.3**

Before:

```
<input type="number" step="any" id="dz1" value="${dl.z1}" style="width:70px">
```

After:

```
<input type="number" step="any" id="dz1" aria-label="to (highest redshift)" value="${dl.z1}" style="width:70px">
```

**Edit E13.4**

Before:

```
<button class="btn" id="dJson" ${recs.length?"":"disabled"}>JSON</button>
```

After:

```
<button class="btn" id="dJson" aria-label="Download JSON" ${recs.length?"":"disabled"}>JSON</button>
```

**Edit E13.5**

Before:

```
<button class="btn" id="dBib" ${recs.length?"":"disabled"}>Copy BibTeX</button>
```

After:

```
<button class="btn" id="dBib" aria-label="Copy BibTeX of these curves" ${recs.length?"":"disabled"}>Copy BibTeX</button>
```

**Edit E13.6**

Before:

```
<button class="btn" id="fSvg">SVG</button><button class="btn" id="fPng">PNG</button>
```

After:

```
<button class="btn" id="fSvg" aria-label="Download figure as SVG">SVG</button><button class="btn" id="fPng" aria-label="Download figure as PNG">PNG</button>
```

**Edit E13.7**

Before:

```
<button class="btn" id="cBibD">Copy BibTeX</button>
```

After:

```
<button class="btn" id="cBibD" aria-label="Copy BibTeX of the dataset">Copy BibTeX</button>
```

**Edit E13.8**

Before:

```
id="tImf" ${state.imfc?"checked":""}> convert stellar masses and SFRs to a Chabrier IMF (offsets:
```

After:

```
id="tImf" aria-label="convert stellar masses and SFRs to a Chabrier IMF" aria-describedby="tImfH" ${state.imfc?"checked":""}> convert stellar masses and SFRs to a Chabrier IMF <span id="tImfH">(offsets:
```

**Edit E13.9**

Before:

```
downloads always keep the published values)</label>
```

After:

```
downloads always keep the published values)</span></label>
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (named controls in Notes, Get data, Customise).

### E14. A keyboard or screen-reader user cannot open a single curve's evidence, and does not know how

**What a screen-reader or keyboard user meets.** Evidence opens when a curve is clicked. The curves are not focusable and the chart (focusable, role img) does nothing on Enter. The only keyboard route to a curve is the search box (/ or Ctrl+K), which has no button and is not mentioned near the chart; the chart's description ends "Use Get data for the numbers." The description now says how, and the chart declares the shortcut.

**Edit E14.1**

Before:

```
observational curves. Use Get data for the numbers.`;
```

After:

```
observational curves. Use Get data for the numbers, or press / to search for a curve and open its evidence.`;
```

**Edit E14.2**

Before:

```
<svg id="stage" role="img" tabindex="0" aria-describedby="stageDesc">
```

After:

```
<svg id="stage" role="img" tabindex="0" aria-keyshortcuts="/ Control+K" aria-describedby="stageDesc">
```

Test: `node scripts/test-a11y-tree.mjs --explorer` (chart description names the search shortcut).


Not patched, because they need a design decision:

- **The rail comes before `main`.** Headings read h2 (seven groups) and then the h1. Moving the rail after the title in the source would change the layout CSS; marking the group titles as `<p>` would lose the groups. Left as it is.
- **The chart cannot be read as data.** The text description lists the sources and counts, and Get data downloads the numbers, which is the text alternative; there is no in-page table of the plotted values. A table view would be a feature.
- **Evidence-tier chips in the evidence panel** ("digitized figure", "target", "context only") are three adjacent spans and are read run together.
- **Row click targets in the Your run table** are `tr` elements with `tabindex="0"` and a key handler; a screen reader says "row", not "link". A real link inside the first cell would be better.

## 5. Checks run

Run on 25 October 2026 in this worktree, Chromium only (Firefox and WebKit are not installed here):

- `node scripts/test-a11y-tree.mjs`: passes for the 19 site pages, the 404 page and the dials page; the checker's own test and the seven deliberate breaks above are caught.
- `node scripts/test-a11y-tree.mjs --explorer` on the Explorer as it is: **23 problems** (listed by the script, one line each). The same command on a copy of `dist/` with patches E1 to E14 applied: **no problems**.
- On that patched copy the existing suites pass: `test-ui` 101 checks, `test-journeys` 14 of 14, `test-yourrun` 10 checks, `test-resilience` 14 checks, `test-keyboard` 852 focus stops. (A first version of E8 and E11 added hidden words next to the symbols; `test-ui` reads the symbols' text and failed one check, so the symbols now carry `role="img"` with a label and their text is unchanged.)
- On the site as built from this branch: `node scripts/test-site.mjs`, `node scripts/lint.mjs`, `node scripts/test-keyboard.mjs` (852 stops), `node scripts/test-dials.mjs` (15 checks) and `node scripts/test-layouts.mjs` (177 page views) pass.

What this does not show: the checker uses Chromium's tree and Playwright's names. A person with a screen reader may find things it cannot (section 6).

## 6. What a person still has to check

1. Use the Explorer, the dials page, a study page and the data page with NVDA on Windows (Chrome and Firefox), JAWS if available, VoiceOver on macOS and iOS, and TalkBack on Android. Everything above comes from one browser engine's tree; other browsers build different trees (in Safari, tables whose cells are set to `display:block`, which the studies tables do below 760 px, can lose their table role).
2. Listen to the live regions: how long the sentences are, whether the result of a search on the dials page is too long to be useful spoken at once, whether the legend and chart description announce too often when stepping through epochs with the arrow keys.
3. Judge the names. The names above are literal ("Show only SIMBA", "Plot every epoch (z) of SIMBA, coloured by redshift"); whether they are the words a user wants needs a user.
4. Check zoom to 200% and 400%, reduced motion, forced colours and a mobile screen reader on the Explorer; the layout test covers overflow, not reading.
5. Voice control: a visible label should be speakable. The legend's "only", "z" and the arrows are short on purpose; their new names start with the visible text, but this was not tried with a voice tool.
6. The Explorer's chart has no keyboard path to a single curve other than the search box (E14 only tells the user about it).
7. The long definition sentences, the comparability reasons and the quoted passages are only in tooltips in some places (the Vs observations cells, table headers); E12 copies them to labels, but nobody has judged whether the text reads well aloud.
8. The truncated checksums on the data page (`4fffe7f511…`) keep the full value in a tooltip only; a screen-reader user gets ten characters. The full values are in the manifest file linked from the same page.
9. Colour contrast and focus visibility are covered by the existing axe and keyboard tests, which this document does not repeat.
