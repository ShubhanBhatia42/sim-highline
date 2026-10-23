(function(root){
/* Observer layer: what a survey does to a simulated catalogue that the simulation does not do itself.
   Written for comparisons in this project; not a calibrated model of any survey. Docs: docs/OBSERVER-LAYER.md.
   The Python mirror is in sim_highline.py (same names in snake_case); scripts/test-observer.mjs and scripts/test_observer.py keep the two equal on one fixture.

   A "points" array is the project's record format: [{x, y, yLow?, yHigh?, count?}] with x = log10(stellar mass / Msun) and y = log10 of a number density per dex
   (a stellar mass function, SMF). Every function returns new points and never changes its input. Nothing here fits, calibrates or interpolates a record:
   the operations are applied to the points you pass, at the x of those points. */
const LN10=Math.LN10,SQRT2PI=Math.sqrt(2*Math.PI);
const DEFAULTS={step:0.005,nsig:8,edgeFit:3,edgeFlag:0.05,maxGap:1,sigmaMin:0.001,sigmaProbe:0.05,sigmaMargin:3};

function clean(points,maxGap){
  const p=points.filter(q=>Number.isFinite(q.x)&&Number.isFinite(q.y)).slice().sort((a,b)=>a.x-b.x);
  if(p.length<2)throw new Error("need at least two points with finite x and y");
  for(let i=1;i<p.length;i++){
    if(p[i].x===p[i-1].x)throw new Error(`duplicate x = ${p[i].x}`);
    if(p[i].x-p[i-1].x>maxGap)throw new Error(`gap of ${(p[i].x-p[i-1].x).toFixed(3)} dex between x = ${p[i-1].x} and ${p[i].x} is larger than maxGap = ${maxGap}; split the curve at the gap`);
  }
  return p;
}
function interp1(xs,ys,x){ /* linear, held constant outside the table (the same rule as numpy.interp) */
  if(x<=xs[0])return ys[0];
  const n=xs.length;if(x>=xs[n-1])return ys[n-1];
  let lo=0,hi=n-1;while(hi-lo>1){const m=(lo+hi)>>1;if(xs[m]<=x)lo=m;else hi=m}
  return ys[lo]+(ys[hi]-ys[lo])*(x-xs[lo])/(xs[hi]-xs[lo]);
}
/* A scatter or a floor may be a number, a function of log10 mass, or a table {x:[...], sigma:[...]} (or {x, floor}) read by linear interpolation and held constant outside. */
function asFunction(spec,field,what){
  if(typeof spec==="number"){if(!Number.isFinite(spec))throw new Error(`${what} must be finite`);return()=>spec}
  if(typeof spec==="function")return spec;
  if(spec&&Array.isArray(spec.x)&&Array.isArray(spec[field])&&spec.x.length===spec[field].length&&spec.x.length>0)return m=>interp1(spec.x,spec[field],m);
  throw new Error(`${what} must be a number, a function of log10 mass or a table {x:[...], ${field}:[...]}`);
}
function lsSlope(xs,ys){
  const n=xs.length,mx=xs.reduce((a,b)=>a+b,0)/n,my=ys.reduce((a,b)=>a+b,0)/n;
  let sxy=0,sxx=0;for(let i=0;i<n;i++){sxy+=(xs[i]-mx)*(ys[i]-my);sxx+=(xs[i]-mx)**2}
  return sxy/sxx;
}

/* Poisson bands for points that carry a count and no band: for N counts the 1-sigma interval of the density is n(1 +- 1/sqrt(N)), written in log10;
   the lower bound is left out (NaN) when N <= 1 because the logarithm is then undefined. Points that already have a band are left alone. */
function poissonBands(points){
  return points.map(p=>{
    if(Number.isFinite(p.yLow)||Number.isFinite(p.yHigh)||!(p.count>0))return{...p};
    const e=1/Math.sqrt(p.count);
    return{...p,yHigh:p.y+Math.log10(1+e),yLow:e<1?p.y+Math.log10(1-e):NaN};
  });
}

/* (a) Gaussian scatter in log10 stellar mass.
   Model: each galaxy of true log mass m is observed at m + e, e ~ Normal(0, sigma(m)^2), with sigma a function of the TRUE mass (a number gives a constant scatter).
   The observed density per dex at x is then   n_obs(x) = integral n(m) N(x - m; sigma(m)) dm.   Number is conserved: the kernel integrates to one for every m.
   Grid and interpolation (the documented discretisation): log10 n is interpolated linearly in x between the points; beyond the first and last point it is continued as a
   straight line whose slope is a least-squares fit to the nearest edgeFit points (the slope above the last point is never allowed to be positive). The integral is a sum over a
   uniform grid of spacing h = min(step, sigmaMin_found/2) centred on each output x and reaching nsig sigma to each side (defaults: step 0.005 dex, 8 sigma, so the kernel sums to 1
   to better than 1e-12), where sigmaMin_found is the smallest sigma met when sigma is read every sigmaProbe dex over the data range +- sigmaMargin dex. Values of sigma below sigmaMin (0.001 dex) are raised to it.
   sigma = 0 (a number) returns the input unchanged. Output x are the input x.
   Assumptions: the density is smooth between points (a coarse point spacing is an interpolation error, not an observation); the scatter is Gaussian in log mass and independent of everything else;
   the continuation beyond the data is a guess, so each output carries edgeShare, the fraction of the scattered density that came from the continuation, and edge = edgeShare > edgeFlag (0.05).
   Uncertainty: the output log density at x is a weighted average of the input log densities, y_out = sum_j a_j y_j, where a_j is the share of the scattered density at x that comes from the
   interval around input point j (shares from the continuation go to the end point; they sum to one). Independent input errors then give  s_out = sqrt(sum_j a_j^2 s_j^2),  computed separately for the upper
   (yHigh - y) and lower (y - yLow) error. Points with only a count get Poisson bands first (poissonBands). What is NOT propagated: the uncertainty of sigma itself, of the continuation slope, of the
   interpolation, and the correlation between output points (errors of neighbouring outputs are correlated after scatter; they are reported as if independent). count_out = count * n_out / n_in (the expected count in the same bin).
   This is a statement about a density, not a catalogue: it does not add noise to individual galaxies. */
function scatterPoints(points,sigma,opts){
  const o={...DEFAULTS,...(opts||{})};
  if(typeof sigma==="number"&&sigma<0)throw new Error("sigma must be >= 0");
  const base=clean(points,o.maxGap);
  if(typeof sigma==="number"&&sigma===0)return base.map(p=>({...p,edgeShare:0,edge:false}));
  const sig=asFunction(sigma,"sigma","sigma");
  const src=o.poisson===false?base:poissonBands(base);
  const xs=src.map(p=>p.x),ys=src.map(p=>p.y),N=xs.length;
  const kfit=Math.max(2,Math.min(o.edgeFit,N));
  const sLo=lsSlope(xs.slice(0,kfit),ys.slice(0,kfit)),sHi=Math.min(0,lsSlope(xs.slice(N-kfit),ys.slice(N-kfit)));
  /* sigma range, to size the grid */
  let smin=Infinity,smax=0;
  for(let m=xs[0]-o.sigmaMargin;m<=xs[N-1]+o.sigmaMargin+1e-9;m+=o.sigmaProbe){const s=Math.max(sig(m),o.sigmaMin);if(!Number.isFinite(s))throw new Error("sigma returned a non-finite value");smin=Math.min(smin,s);smax=Math.max(smax,s)}
  const h=Math.min(o.step,smin/2),K=Math.ceil(o.nsig*smax/h);
  const bandOf=(key,sign)=>{ /* error in log10 units per point, gaps filled by interpolation between the points that have one */
    const e=src.map(p=>Number.isFinite(p[key])?sign*(p[key]-p.y):NaN),ok=e.map((v,i)=>Number.isFinite(v)?i:-1).filter(i=>i>=0);
    if(!ok.length)return null;
    const gx=ok.map(i=>xs[i]),gv=ok.map(i=>e[i]);
    return e.map((v,i)=>Number.isFinite(v)?v:interp1(gx,gv,xs[i]));
  };
  const up=bandOf("yHigh",1),dn=bandOf("yLow",-1);
  const out=[];
  for(const p of src){
    let num=0,ext=0;const A=new Array(N).fill(0);let j=0;
    for(let k=-K;k<=K;k++){
      const d=k*h,m=p.x+d,s=Math.max(sig(m),o.sigmaMin);
      if(Math.abs(d)>o.nsig*s)continue;
      const w=h*Math.exp(-0.5*(d/s)**2)/(s*SQRT2PI);
      let y,wj,wj1=0,jj;
      if(m<xs[0]){y=ys[0]+sLo*(m-xs[0]);jj=0;wj=1}
      else if(m>xs[N-1]){y=ys[N-1]+sHi*(m-xs[N-1]);jj=N-1;wj=1}
      else{
        while(j<N-2&&xs[j+1]<=m)j++; while(j>0&&xs[j]>m)j--; /* k runs upward, so j only moves forward except when sigma is read at a different m */
        const t=(m-xs[j])/(xs[j+1]-xs[j]);y=ys[j]+t*(ys[j+1]-ys[j]);jj=j;wj=1-t;wj1=t;
      }
      const f=w*Math.pow(10,y);num+=f;
      if(m<xs[0]||m>xs[N-1])ext+=f;
      A[jj]+=f*wj;if(wj1)A[jj+1]+=f*wj1;
    }
    const q={x:p.x,y:Math.log10(num)};
    const err=(e)=>{let v=0;for(let i=0;i<N;i++){const a=A[i]/num;v+=a*a*e[i]*e[i]}return Math.sqrt(v)};
    if(up)q.yHigh=q.y+err(up);
    if(dn)q.yLow=q.y-err(dn);
    if(Number.isFinite(p.count))q.count=p.count*num/Math.pow(10,p.y);
    q.edgeShare=ext/num;q.edge=q.edgeShare>o.edgeFlag;
    out.push(q);
  }
  return out;
}

/* (b) A systematic offset in the measured mass: observed log mass = true log mass + offset (dex). A density per dex does not change when the mass axis is translated,
   so x moves and y, the bands and the counts stay. Assumes the offset is the same at every mass (no mass-dependent offset, no change of slope). Applied after scatter, where the two commute for a constant offset. */
function shiftPoints(points,offset){
  if(!Number.isFinite(offset))throw new Error("offset must be a finite number of dex");
  return points.map(p=>({...p,x:p.x+offset}));
}

/* (c) Completeness. Two separate operations.
   completenessCut: a hard limiting mass; points with x < mLim are removed (a survey that corrects for completeness above its limit and publishes nothing below it).
   completenessWeight: a smooth completeness C(x) = 1/(1 + exp(-(x - m50)/width)), a logistic in observed log mass with half-completeness m50 and scale width (dex; the 10 to 90 per cent span is 4.4 width);
   the density an UNCORRECTED catalogue would show is C times the true density, so y gets + log10 C, and so do the bands (their relative size is kept; no new Poisson noise is derived) and count is multiplied by C.
   The logistic is a convenient shape, not a measured completeness curve. Both act on the observed mass, so apply them after scatter and offset. */
function completenessCut(points,mLim){
  if(!Number.isFinite(mLim))throw new Error("mLim must be a finite log10 mass");
  return points.filter(p=>p.x>=mLim).map(p=>({...p}));
}
function completenessFraction(x,m50,width){
  if(!(width>0))throw new Error("width must be > 0");
  return 1/(1+Math.exp(-(x-m50)/width));
}
function completenessWeight(points,m50,width){
  return points.map(p=>{
    const c=completenessFraction(p.x,m50,width),l=Math.log10(c),q={...p,y:p.y+l,completeness:c};
    if(Number.isFinite(p.yLow))q.yLow=p.yLow+l;
    if(Number.isFinite(p.yHigh))q.yHigh=p.yHigh+l;
    if(Number.isFinite(p.count))q.count=p.count*c;
    return q;
  });
}

/* All three, in the order a survey applies them: scatter (true mass to measured mass), then the systematic offset, then completeness on the measured mass.
   opts: {sigma, offset, mLim, completeness: {m50, width}, ...scatter options}. Returns {points, steps} with a line per step applied. */
function observePoints(points,opts){
  const o=opts||{},steps=[];let p=points.map(q=>({...q}));
  if(o.sigma!==undefined&&!(o.sigma===0)){p=scatterPoints(p,o.sigma,o);steps.push(typeof o.sigma==="number"?`Gaussian scatter ${o.sigma} dex in log mass`:"Gaussian scatter, mass-dependent")}
  if(o.offset){p=shiftPoints(p,o.offset);steps.push(`mass offset ${o.offset>0?"+":""}${o.offset} dex`)}
  if(o.completeness){p=completenessWeight(p,o.completeness.m50,o.completeness.width);steps.push(`smooth completeness, half at log M = ${o.completeness.m50}, scale ${o.completeness.width} dex`)}
  if(o.mLim!==undefined){p=completenessCut(p,o.mLim);steps.push(`limiting mass log M = ${o.mLim}`)}
  return{points:p,steps};
}

/* (d) Detection floor for a specific star formation rate (sSFR) relation. y is log10 sSFR (per year); a galaxy with sSFR below the floor is not measured (it is an upper limit in a survey).
   ssfrFloorPoints: for a curve of medians with a 16 to 84 per cent band (yLow, yHigh): a point whose MEDIAN is below the floor(x) is removed (the typical galaxy there is undetected, so no median
   can be measured); for the others the lower band is raised to the floor and the point is marked clipped = true. This is the only thing that can be done to a published median curve; it does not
   recompute the median of the detected galaxies, which is higher than the median of all of them. floor is a number, a function of x or a table {x, floor}, in log10 per year.
   ssfrFloorRow: the proper version when the per-galaxy counts are known (a record's representation.distribution): for one row of counts over the sSFR edges yEdges, drop the counts below the floor
   (the bin that holds the floor keeps its upper share, galaxies being spread evenly within a bin, as in compare.js), and return the detected fraction and the quantiles of the detected galaxies
   (linear within a bin, the same rule as compare.js distQuantile). sfrFloorToSsfr: a floor in SFR (log10 Msun/yr) is an sSFR floor of sfrMin - log10 M at mass log10 M. */
function ssfrFloorPoints(points,floor){
  const f=asFunction(floor,"floor","floor"),out=[];
  for(const p of points){
    const fl=f(p.x);if(!Number.isFinite(fl))throw new Error("floor returned a non-finite value");
    if(p.y<fl)continue;
    const q={...p};
    if(Number.isFinite(p.yLow)&&p.yLow<fl){q.yLow=fl;q.clipped=true}
    out.push(q);
  }
  return out;
}
function rowQuantile(row,edges,total,q){
  const target=q*total;let cum=0;
  for(let j=0;j<row.length;j++){const c=row[j];if(c>0&&cum+c>=target){const t=(target-cum)/c;return edges[j]+Math.min(1,Math.max(0,t))*(edges[j+1]-edges[j])}cum+=c}
  return edges[edges.length-1];
}
function ssfrFloorRow(row,yEdges,floorLog,levels){
  const lv=levels||[.16,.5,.84];
  if(row.length+1!==yEdges.length)throw new Error("yEdges must have one more entry than row");
  const kept=row.map((c,j)=>{
    const lo=yEdges[j],hi=yEdges[j+1];
    if(hi<=floorLog)return 0;
    if(lo>=floorLog)return c;
    return c*(hi-floorLog)/(hi-lo);
  });
  const total=row.reduce((a,b)=>a+b,0),det=kept.reduce((a,b)=>a+b,0);
  return{total,detected:det,fractionDetected:total>0?det/total:NaN,levels:lv,quantiles:lv.map(q=>det>0?rowQuantile(kept,yEdges,det,q):NaN)};
}
function sfrFloorToSsfr(sfrMinLog,logM){return sfrMinLog-logM}

root.SimHighlineObserver={DEFAULTS,poissonBands,scatterPoints,shiftPoints,completenessCut,completenessFraction,completenessWeight,observePoints,ssfrFloorPoints,ssfrFloorRow,sfrFloorToSsfr,interp1};
})(typeof globalThis!=="undefined"?globalThis:window);
