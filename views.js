const EXTRA_VIEWS=new Set(["fingerprint","atlas","evolution","library"]);
const PIVOT={sfms:10,ssfr:10,gsmf:10,quenched:10.5,size:10.5,mzr:10,shmr:11.5,gas:10,jstar:10.5,btfr:2.2,bh:11,bhsigma:2.3};
const Z_TOL=.27;
const MIN_OVERLAP=window.SimHighlineCompare.MIN_BINS;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const simUnits=()=>[...new Set(RECORDS.filter(r=>r.kind==="simulation").map(r=>r.source))].sort();
const rowsOf=recs=>Object.keys(RELATIONS).flatMap(rel=>{const runs=[...new Set(recs.filter(r=>r.relation===rel).map(r=>r.run))];return runs.map(run=>({rel,run,label:RELATIONS[rel].code+(runs.length>1&&run?` · ${run}`:"")}))});

function pick(recs,z){
  const analytic=recs.find(r=>r.epoch.mode==="analytic-evolution"&&z>=r.epoch.zMin&&z<=r.epoch.zMax);if(analytic)return analytic;
  const containing=recs.find(r=>r.epoch.mode!=="analytic-evolution"&&z>=r.epoch.zMin&&z<=r.epoch.zMax);if(containing)return containing;
  const nearest=recs.filter(r=>r.epoch.mode!=="analytic-evolution").sort((a,b)=>Math.abs(a.epoch.zRepresentative-z)-Math.abs(b.epoch.zRepresentative-z))[0];
  return nearest&&Math.abs(nearest.epoch.zRepresentative-z)<=Z_TOL?nearest:null;
}
function sample(record,z){
  if(record.representation.type==="points")return record.representation.points.map(p=>({...p,sigmaKind:record.representation.intervalKind}));
  const f=evaluator(record);if(!f)return[];const lo=record.domain.xMin,hi=record.domain.xMax,out=[];
  for(let i=0;i<80;i++){const x=lo+i/79*(hi-lo),y=f(x,z);if(Number.isFinite(y))out.push({x,y,sigmaKind:"scatter"})}return out;
}
function compareAt(sim,z){
  const obsUnits=[...new Set(RECORDS.filter(r=>r.kind!=="simulation"&&r.relation===sim.relation).map(unit))];
  const rows=obsUnits.map(u=>pick(RECORDS.filter(r=>unit(r)===u&&r.relation===sim.relation),z)).filter(Boolean).map(ref=>{
    const check=compatible(sim,ref),stats=check.verdict==="not-comparable"?null:summarize(residuals(sample(sim,z),sample(ref,z)));
    return{ref,check,stats};
  });
  const rank=r=>r.stats?(r.check.verdict==="comparable"?0:1):2;
  return rows.sort((a,b)=>rank(a)-rank(b)||Math.abs(a.ref.epoch.zRepresentative-z)-Math.abs(b.ref.epoch.zRepresentative-z));
}

function miniPlot(series,{w=300,h=190,xLabel="",yLabel="",zero=false}={}){
  const m={l:38,r:8,t:8,b:26},xs=series.flatMap(s=>s.points.flatMap(p=>[p.x,p.xLow,p.xHigh])).filter(Number.isFinite),ys=series.flatMap(s=>s.points.flatMap(p=>[p.y,p.yLow,p.yHigh])).filter(Number.isFinite);
  if(!xs.length)return`<svg viewBox="0 0 ${w} ${h}"><text x="${w/2}" y="${h/2}" text-anchor="middle" fill="#66716b" font-size="10">no data</text></svg>`;
  let [x0,x1]=[Math.min(...xs),Math.max(...xs)],[y0,y1]=[Math.min(...ys),Math.max(...ys)];if(x0===x1){x0-=.5;x1+=.5}if(y0===y1){y0-=.5;y1+=.5}const py=(y1-y0)*.08;y0-=py;y1+=py;
  const X=x=>m.l+(x-x0)/(x1-x0)*(w-m.l-m.r),Y=y=>m.t+(y1-y)/(y1-y0)*(h-m.t-m.b);
  let out=`<svg viewBox="0 0 ${w} ${h}" class="mini">`;
  for(let i=0;i<=3;i++){const yv=y0+i/3*(y1-y0),xv=x0+i/3*(x1-x0);out+=`<line x1="${m.l}" x2="${w-m.r}" y1="${Y(yv)}" y2="${Y(yv)}" stroke="#1d2521"/><text x="${m.l-4}" y="${Y(yv)+3}" text-anchor="end" font-size="8" fill="#8f9b94">${yv.toFixed(1)}</text><text x="${X(xv)}" y="${h-m.b+11}" text-anchor="middle" font-size="8" fill="#8f9b94">${xv.toFixed(1)}</text>`}
  if(zero&&y0<0&&y1>0)out+=`<line x1="${m.l}" x2="${w-m.r}" y1="${Y(0)}" y2="${Y(0)}" class="residual-zero"/>`;
  out+=`<text x="${(m.l+w-m.r)/2}" y="${h-3}" text-anchor="middle" font-size="8" fill="#c6cec9">${esc(xLabel)}</text><text x="4" y="${m.t+6}" font-size="8" fill="#c6cec9">${esc(yLabel)}</text>`;
  for(const s of series){
    const pts=s.points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));if(!pts.length)continue;
    if(s.band){const up=pts.filter(p=>Number.isFinite(p.yHigh)),dn=pts.filter(p=>Number.isFinite(p.yLow)).reverse();if(up.length>1&&dn.length>1)out+=`<path d="${up.map((p,i)=>`${i?"L":"M"}${X(p.x)},${Y(p.yHigh)}`).join("")}${dn.map(p=>`L${X(p.x)},${Y(p.yLow)}`).join("")}Z" fill="${s.color}" opacity=".13"/>`}
    if(s.line)out+=`<path d="${pts.map((p,i)=>`${i?"L":"M"}${X(p.x)},${Y(p.y)}`).join("")}" fill="none" stroke="${s.color}" stroke-width="1.6" ${s.dashed?'stroke-dasharray="5 3"':""}/>`;
    if(s.markers)for(const p of pts){
      if(Number.isFinite(p.yLow)&&Number.isFinite(p.yHigh))out+=`<line x1="${X(p.x)}" x2="${X(p.x)}" y1="${Y(p.yLow)}" y2="${Y(p.yHigh)}" stroke="${s.color}"/>`;
      if(Number.isFinite(p.xLow)&&Number.isFinite(p.xHigh))out+=`<line x1="${X(p.xLow)}" x2="${X(p.xHigh)}" y1="${Y(p.y)}" y2="${Y(p.y)}" stroke="${s.color}"/>`;
      out+=`<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="2.6" fill="${s.open?"#0c100f":s.color}" stroke="${s.color}"><title>${esc(s.label)} · x ${p.x.toFixed(2)} · y ${p.y.toFixed(2)}</title></circle>`;
    }
  }
  return out+"</svg>";
}
const seriesFor=(record,z,key)=>({label:short(key),color:colorOf(key),points:sample(record,z),line:record.kind==="simulation"||record.representation.type==="parametric"||record.representation.connect,markers:record.representation.type==="points",open:record.kind==="observation",dashed:!record.rankable,band:record.kind==="simulation"});
const signed=v=>`${v>=0?"+":""}${v.toFixed(2)}`;
function spread(comps){const meds=comps.filter(c=>c.stats).map(c=>c.stats.median).sort((a,b)=>a-b),n=meds.length;if(!n)return null;return{n,mid:n%2?meds[(n-1)/2]:(meds[n/2-1]+meds[n/2])/2,lo:meds[0],hi:meds[n-1]}}

function simControls(){
  const sims=simUnits();if(!sims.includes(state.sim))state.sim=sims[0];
  return`<div class="view-controls"><label>Simulation<select id="simSelect">${sims.map(s=>`<option value="${esc(s)}" ${s===state.sim?"selected":""}>${esc(short(s))}</option>`).join("")}</select></label></div>`;
}
const REGISTRY_ALIAS={"IllustrisTNG":["tng100","tng50"],"Magneticum Pathfinder":["magneticum"],"THESAN-1":["thesan"],"NIHAO zoom suite":["nihao"],"THESAN-zoom":["thesan-zoom"],"FIRE-2":["fire2"],"FLARES":["flares"],"BlueTides":["bluetides"],"SPHINX20":["sphinx20"]};
function simProfile(source){
  const reg=window.SIMHIGHLINE_REGISTRY||{simulations:[],families:[]},ids=REGISTRY_ALIAS[source]||[source.toLowerCase().replace(/[^a-z0-9]/g,"")];
  const sims=reg.simulations.filter(s=>ids.includes(s.id)),fam=sims.length?reg.families.find(f=>f.id===sims[0].family):null;
  const recs=RECORDS.filter(r=>r.source===source),rels=Object.keys(RELATIONS).filter(k=>recs.some(r=>r.relation===k));
  const cov=rels.map(k=>{const zs=[...new Set(recs.filter(r=>r.relation===k).map(r=>+r.epoch.zRepresentative.toFixed(1)))].sort((a,b)=>a-b);return`<tr><th>${RELATIONS[k].code}</th><td>${zs.length} epoch${zs.length>1?"s":""}</td><td>${zs.length?`z ${zs[0]}–${zs.at(-1)}`:""}</td><td>${[...new Set(recs.filter(r=>r.relation===k).map(r=>r.provenance.tier))].join(", ")}</td></tr>`}).join("");
  const facts=sims.map(s=>`<p><b>${esc(s.id)}</b> · ${esc(s.regime)}${s.boxMpc?.length?` · box ${s.boxMpc.join("/")} cMpc`:""}${s.baryonMassMsun?.length?` · m<sub>b</sub> ${s.baryonMassMsun.map(m=>m.toExponential(1)).join("/")} M☉`:""} · access: ${esc(s.access)}</p>${s.calibration?.length?`<p>Calibrated on: ${esc(s.calibration.join(", "))}</p>`:""}${s.notes?`<p>${esc(s.notes)}</p>`:""}`).join("");
  return`<section class="sim-profile"><div>${facts||"<p>No registry entry for this source yet.</p>"}${fam?`<p class="family">${esc(fam.label)}: ${esc(fam.dependence)}</p>`:""}</div><table class="atlas coverage"><thead><tr><th>Relation</th><th>Coverage</th><th>Range</th><th>Evidence tier</th></tr></thead><tbody>${cov}</tbody></table></section>`;
}
function renderFingerprint(){
  const recs=RECORDS.filter(r=>r.source===state.sim);
  const panels=rowsOf(recs).map(({rel,run,label})=>{
    const sim=pick(recs.filter(r=>r.relation===rel&&r.run===run),state.z);
    if(!sim)return`<article class="fp-panel empty-panel"><header><b>${esc(label)}</b><span>no output near z=${fmt(state.z)}</span></header></article>`;
    const comps=compareAt(sim,sim.epoch.zRepresentative),best=comps[0];
    const series=[seriesFor(sim,sim.epoch.zRepresentative,unit(sim)),...comps.map(c=>seriesFor(c.ref,sim.epoch.zRepresentative,unit(c.ref)))];
    const sp=spread(comps);
    const badge=!comps.length?`<span class="tag">no reference</span>`:sp?`<span class="tag ${sp.lo<0&&sp.hi>0?"bad":"warn"}" title="${esc(comps.filter(c=>c.stats).map(c=>`${short(unit(c.ref))}: ${signed(c.stats.median)} dex`).join("\n"))}">${signed(sp.mid)} dex${sp.n>1?` (${signed(sp.lo)}…${signed(sp.hi)}, ${sp.n} refs)`:` vs ${esc(short(unit(best.ref)))}`}</span>`:best.check.verdict!=="not-comparable"?`<span class="tag">overlap &lt; ${MIN_OVERLAP} bins</span>`:`<span class="tag bad" title="${esc(best.check.blockers.join("; "))}">not comparable</span>`;
    const role=sim.calibration==="target"?`<span class="tag target">calibration target</span>`:`<span class="tag">${esc(sim.calibration)}</span>`;
    return`<article class="fp-panel" data-goto="${rel}" data-z="${sim.epoch.zRepresentative}"><header><b>${esc(label)}</b><span>z=${fmt(sim.epoch.zRepresentative)}</span>${role}${badge}</header>${miniPlot(series,{xLabel:RELATIONS[rel].code==="SHMR"?"log Mhalo":"log x",yLabel:""})}<footer>${series.map(s=>`<i style="color:${s.color}">${esc(s.label)}</i>`).join(" · ")}</footer></article>`;
  }).join("");
  return`${simControls()}${simProfile(state.sim)}<p class="view-note">Every relation this model has near z = ${fmt(state.z)}, against every observational reference at a matching epoch. Badges give the median offset over all definition-compatible references and their range (red when references disagree on the sign); click a panel to open it in the relation view.</p><div class="fp-grid">${panels}</div>`;
}
function renderAtlas(){
  const byRelation=state.atlasMode==="relation";
  const recs=byRelation?RECORDS.filter(r=>r.kind==="simulation"&&r.relation===state.relation):RECORDS.filter(r=>r.source===state.sim);
  const rows=byRelation?[...new Set(recs.map(unit))].sort().map(u=>({key:u,label:short(u),match:r=>unit(r)===u})):rowsOf(recs).map(({rel,run,label})=>({key:`${rel}|${run}`,label,match:r=>r.relation===rel&&r.run===run}));
  const zs=[...new Set(recs.map(r=>+r.epoch.zRepresentative.toFixed(2)))].sort((a,b)=>a-b);
  const cell=(row,z)=>{
    const sim=recs.find(r=>row.match(r)&&Math.abs(r.epoch.zRepresentative-z)<.006);if(!sim)return`<td class="atlas-none">—</td>`;
    const rel=sim.relation;z=sim.epoch.zRepresentative;
    const comps=compareAt(sim,z),best=comps[0];
    if(!best)return`<td class="atlas-noref" title="No observational reference within dz=${Z_TOL}">no ref</td>`;
    if(!best.stats&&best.check.verdict!=="not-comparable")return`<td class="atlas-noref" title="Definitions compatible but fewer than ${MIN_OVERLAP} overlapping bins">n&lt;${MIN_OVERLAP}</td>`;
    if(!best.stats)return`<td class="atlas-blocked" data-goto="${rel}" data-z="${z}" title="${esc(best.check.blockers.join("; "))}">×</td>`;
    const scored=comps.filter(c=>c.stats),{n,mid:d,lo,hi}=spread(comps),split=lo<0&&hi>0,a=Math.min(Math.abs(d)/.5,1);
    const bg=split?"repeating-linear-gradient(45deg,#1e2622 0 4px,#2a332e 4px 8px)":d>=0?`rgba(223,118,105,${.15+.6*a})`:`rgba(103,193,207,${.15+.6*a})`;
    const detail=scored.map(c=>`${short(unit(c.ref))}: ${c.stats.median>=0?"+":""}${c.stats.median.toFixed(2)} dex (n=${c.stats.n}${c.check.verdict==="comparable"?"":", caveats"})`).join("\n");
    const fmtd=signed;
    return`<td style="background:${bg}" data-goto="${rel}" data-z="${z}" title="${esc(detail)}"><b>${fmtd(d)}</b>${n>1?`<small>${fmtd(lo)}…${fmtd(hi)} · ${n} refs</small>`:`<small>1 ref</small>`}</td>`;
  };
  const toggle=`<div class="view-controls"><label>Rows<select id="atlasMode"><option value="model" ${byRelation?"":"selected"}>Relations of one simulation</option><option value="relation" ${byRelation?"selected":""}>Simulations for ${esc(RELATIONS[state.relation].code)}</option></select></label></div>`;
  return`${toggle}${byRelation?"":simControls()}<p class="view-note">Offset of the model (dex, model minus data) for each relation and output epoch, as the median over every definition-compatible reference, with the range across references underneath. Red: model above the data; blue: below; hatched: references disagree on the sign, so the data do not decide. Hover for each reference; × definitions incompatible; "no ref" means no observational record at that epoch; n&lt;${MIN_OVERLAP} means too little overlap in x to summarise. Click a cell to open it.</p><div class="atlas-wrap"><table class="atlas"><thead><tr><th></th>${zs.map(z=>`<th>z ${fmt(z)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr><th>${esc(row.label)}</th>${zs.map(z=>cell(row,z)).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function evolutionSeries(key,x0){
  const recs=RECORDS.filter(r=>unit(r)===key&&r.relation===state.relation),out=[];if(!recs.length)return null;
  const s={label:short(key),color:colorOf(key),points:[],markers:true,open:recs[0].kind==="observation",line:recs[0].kind==="simulation"};
  for(const r of recs){
    if(x0<r.domain.xMin||x0>r.domain.xMax)continue;
    if(r.epoch.mode==="analytic-evolution"){const f=evaluator(r),pts=[];for(let i=0;i<=40;i++){const z=r.epoch.zMin+i/40*(r.epoch.zMax-r.epoch.zMin);pts.push({x:z,y:f(x0,z)})}out.push({...s,points:pts,markers:false,line:true});continue}
    const pts=sample(r,r.epoch.zRepresentative),y=interpolate(pts,x0);if(!Number.isFinite(y))continue;
    const sig=r.representation.type==="points"?interpolate(pts,x0,"sigma"):NaN,p={x:r.epoch.zRepresentative,y};
    if(Number.isFinite(sig)){p.yLow=y-sig;p.yHigh=y+sig}if(r.epoch.zMax>r.epoch.zMin){p.xLow=r.epoch.zMin;p.xHigh=r.epoch.zMax}s.points.push(p);
  }
  s.points.sort((a,b)=>a.x-b.x);if(s.points.length)out.push(s);return out;
}
function renderEvolution(){
  if(!Number.isFinite(state.x0))state.x0=PIVOT[state.relation];
  const keys=[...new Set(RECORDS.filter(r=>r.relation===state.relation).map(unit))],series=keys.flatMap(k=>evolutionSeries(k,state.x0)||[]);
  return`<div class="view-controls"><label>Evaluate at x =<input id="x0Input" type="number" step="0.1" value="${state.x0}"></label></div><p class="view-note">${esc(RELATIONS[state.relation].title)} evaluated at a fixed x = ${state.x0} across every epoch each source provides. Simulations: connected outputs; observations: open markers with their redshift-bin width and reported uncertainty; analytic fits: continuous in z. Definitions are not harmonised here; use the relation view for compatibility checks.</p><div class="evo-plot">${miniPlot(series,{w:860,h:420,xLabel:"redshift",yLabel:RELATIONS[state.relation].code})}</div><div class="legend">${series.filter((s,i,a)=>a.findIndex(t=>t.label===s.label)===i).map(s=>`<span class="legend-item" style="color:${s.color}"><i class="legend-swatch"></i>${esc(s.label)}</span>`).join("")}</div>`;
}
function renderLibrary(){
  const sims=[...new Set(RECORDS.filter(r=>r.kind==="simulation").map(r=>r.source))].sort(),rels=Object.keys(RELATIONS).filter(k=>RECORDS.some(r=>r.relation===k));
  const obsCount=k=>new Set(RECORDS.filter(r=>r.relation===k&&r.kind!=="simulation").map(r=>r.source)).size;
  const cell=(k,s)=>{const recs=RECORDS.filter(r=>r.relation===k&&r.source===s);if(!recs.length)return`<td class="atlas-none">·</td>`;if(RELATIONS[k].x==="z"){const lo=Math.min(...recs.map(r=>r.domain.xMin)),hi=Math.max(...recs.map(r=>r.domain.xMax));return`<td class="lib-cell" data-lib="${k}" data-z="0" data-sim="${esc(s)}" title="${esc(`${s} · ${RELATIONS[k].title}: ${recs.length} redshift curve(s)`)}" style="background:rgba(103,193,207,.4)"><b>${recs.length}</b><small>z ${lo.toFixed(0)}–${hi.toFixed(0)}</small></td>`}
    const zs=[...new Set(recs.map(r=>+r.epoch.zRepresentative.toFixed(1)))].sort((a,b)=>a-b),scored=recs.some(r=>r.rankable),tier=[...new Set(recs.map(r=>r.provenance.tier))];
    return`<td class="lib-cell" data-lib="${k}" data-z="${zs[0]}" data-sim="${esc(s)}" title="${esc(`${s} · ${RELATIONS[k].title}\n${recs.length} records, z = ${zs.join(", ")}\n${tier.join(", ")}`)}" style="background:rgba(103,193,207,${Math.min(.12+.08*zs.length,.75)})"><b>${zs.length}</b><small>${zs[0]}${zs.length>1?`–${zs.at(-1)}`:""}</small></td>`};
  const total=RECORDS.length,nObs=new Set(RECORDS.filter(r=>r.kind!=="simulation").map(r=>r.source)).size;
  return`<p class="view-note"><b>${total}</b> evidence records · <b>${rels.length}</b> relations · <b>${sims.length}</b> simulation suites · <b>${nObs}</b> observational and empirical sources. Each cell gives the number of epochs a suite covers for a relation and the redshift span; darker means more epochs. Click a cell to open that suite's fingerprint at its first epoch; the last column counts independent observational references.</p>
  <div class="atlas-wrap"><table class="atlas library"><thead><tr><th>Relation</th>${sims.map(s=>`<th class="rot"><span>${esc(short(s))}</span></th>`).join("")}<th>Obs.</th></tr></thead><tbody>${rels.map(k=>`<tr><th title="${esc(RELATIONS[k].question)}">${RELATIONS[k].code} <small>${esc(RELATIONS[k].title)}</small></th>${sims.map(s=>cell(k,s)).join("")}<td class="lib-obs">${obsCount(k)||""}</td></tr>`).join("")}</tbody></table></div>`;
}
function renderExtra(){
  const el=$("extraView");el.innerHTML=state.view==="fingerprint"?renderFingerprint():state.view==="atlas"?renderAtlas():state.view==="library"?renderLibrary():renderEvolution();
  el.querySelectorAll("[data-lib]").forEach(n=>n.onclick=()=>{setRelation(n.dataset.lib);state.z=Number(n.dataset.z);state.sim=n.dataset.sim;state.view="fingerprint";syncHash();render()});
  const sel=$("simSelect");if(sel)sel.onchange=e=>{state.sim=e.target.value;syncHash();renderMain()};
  const am=$("atlasMode");if(am)am.onchange=e=>{state.atlasMode=e.target.value;syncHash();renderMain()};
  const x0=$("x0Input");if(x0)x0.onchange=e=>{state.x0=Number(e.target.value);syncHash();renderMain()};
  el.querySelectorAll("[data-goto]").forEach(n=>n.onclick=()=>{setRelation(n.dataset.goto);state.z=Number(n.dataset.z);state.view="relation";syncHash();render()});
}
