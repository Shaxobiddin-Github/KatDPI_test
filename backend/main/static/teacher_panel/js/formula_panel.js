// Global formula panel (kengaytirilgan) – favorites, recent, wrap, shortcutlar, global qidiruv, mini badge, alias, snippet, yengil LaTeX tekshiruv
(function(){
  if(window.__GFP_LOADED__) return; window.__GFP_LOADED__=true;
  const baseGroups=[
    { name:'Asosiy', items:['+','-','\\times','\\div','=','\\neq','<','>','\\leq','\\geq','x^2','x_1','x_{n}','\\frac{a}{b}','\\sqrt{x}','\\sqrt[3]{x}']},
    { name:'Funksiya', items:['\\sin','\\cos','\\tan','\\log','\\ln','\\exp','\\arcsin','\\arccos','\\arctan']},
    { name:'Yig`indi', items:['\\sum_{i=1}^{n}','\\prod_{k=1}^{m}','\\int_{a}^{b}','\\iint','\\iiint','\\lim_{x \\to 0}']},
    { name:'Belgilar', items:['\\infty','\\pm','\\mp','\\approx','\\rightarrow','\\leftarrow','\\Rightarrow','\\Leftarrow','\\Leftrightarrow']},
    { name:'Greka', items:['\\alpha','\\beta','\\gamma','\\theta','\\lambda','\\mu','\\pi','\\phi','\\omega','\\sigma']},
    { name:'Mantiq', items:['\\forall','\\exists','\\in','\\notin','\\subset','\\supset','\\subseteq','\\supseteq','\\cup','\\cap']},
    { name:'Qavslar', items:['\\left( x \\right)','\\left[ x \\right]','\\left\\{ x \\right\\}','\\langle x \\rangle']},
    { name:'Vektor', items:['\\vec{v}','\\overrightarrow{AB}','\\mathbf{v}','\\hat{n}']},
    { name:'Matritsa', items:['\\begin{matrix} a & b \\ c & d \\end{matrix}','\\begin{pmatrix} a & b \\ c & d \\end{pmatrix}','\\begin{bmatrix} a & b \\ c & d \\end{bmatrix}']},
    { name:'Tenglama', items:['x_{1,2}=\\frac{-b\\pm\\sqrt{b^2-4ac}}{2a}','a^2+b^2=c^2','E=mc^2','\\frac{d}{dx}f(x)','\\int_{0}^{\\infty} e^{-x} \\mathrm{d}x']},
    { name:'To\'plam', items:['\\{1,2,\\dots ,n\\}','\\mathbb{R}','\\mathbb{N}','\\mathbb{Z}']},
    { name:'Statistik', items:['\\bar{x}','\\sigma','\\mu','\\mathrm{Var}(X)','\\mathrm{E}[X]','\\binom{n}{k}']},
    { name:'Operator', items:['\\nabla','\\partial','\\frac{\\partial f}{\\partial x}','\\sum_{k=0}^{\\infty}','\\lim_{n \\to \\infty}']},
  ];
  const LS_USAGE='gfp_usage_counts';
  const LS_RECENT='gfp_recent_formulas';
  const LS_SNIPPETS='gfp_user_snippets';
  const defaultAliases={ intab:'\\int_{a}^{b}', sumij:'\\sum_{i=1}^{n}', prodkm:'\\prod_{k=1}^{m}', lim0:'\\lim_{x \\to 0}', sqrt3:'\\sqrt[3]{x}', sq:'\\sqrt{x}', frac:'\\frac{a}{b}' };
  function loadUsage(){try{return JSON.parse(localStorage.getItem(LS_USAGE)||'{}');}catch{return {}}}
  function saveUsage(o){localStorage.setItem(LS_USAGE,JSON.stringify(o));}
  function loadRecents(){try{return JSON.parse(localStorage.getItem(LS_RECENT)||'[]');}catch{return []}}
  function saveRecents(a){localStorage.setItem(LS_RECENT,JSON.stringify(a));}
  function loadSnippets(){try{return JSON.parse(localStorage.getItem(LS_SNIPPETS)||'{}');}catch{return {}}}
  function saveSnippets(o){localStorage.setItem(LS_SNIPPETS,JSON.stringify(o));}
  let usage=loadUsage(); let recents=loadRecents(); let userSnippets=loadSnippets();
  const specialWrappers={ '\\frac{a}{b}':sel=>`\\frac{${sel||'a'}}{b}`, '\\sqrt{x}':sel=>`\\sqrt{${sel||'x'}}`, '\\sqrt[3]{x}':sel=>`\\sqrt[3]{${sel||'x'}}` };
  const functionWrappers=['\\sin','\\cos','\\tan','\\log','\\ln','\\exp','\\arcsin','\\arccos','\\arctan'];
  const toggleBtn=document.getElementById('global-formula-toggle');
  const panel=document.getElementById('global-formula-panel');
  if(!toggleBtn||!panel) return;
  const body=document.getElementById('gfp-body');
  const search=document.getElementById('gfp-search');
  const cats=document.getElementById('gfp-cats');
  const closeBtn=document.getElementById('gfp-close');
  // snippet modal refs
  const addSnippetBtn=document.getElementById('gfp-add-snippet');
  const snippetModal=document.getElementById('gfp-snippet-modal');
  const snippetName=document.getElementById('gfp-snippet-name');
  const snippetCode=document.getElementById('gfp-snippet-code');
  const snippetSave=document.getElementById('gfp-save-snippet');
  const snippetCancel=document.getElementById('gfp-cancel-snippet');
  const snippetClose=document.getElementById('gfp-close-snippet');
  const snippetError=document.getElementById('gfp-snippet-error');
  let activeInput=null, activeGroupIndex=0, dynamicGroups=[], allGroups=[], aliasMap=buildAliasMap();
  function buildAliasMap(){ return { ...defaultAliases, ...userSnippets }; }

  function rebuildGroups(){
    dynamicGroups=[];
    const fav=Object.entries(usage).filter(([k,v])=>v>1).sort((a,b)=>b[1]-a[1]).slice(0,12).map(e=>e[0]);
    if(recents.length) dynamicGroups.push({name:'Oxirgi', dynamic:true, items:recents.slice(0,12)});
    if(fav.length) dynamicGroups.push({name:"Ko'p ishlatilgan", dynamic:true, items:fav});
    const snippetEntries=Object.entries(userSnippets);
    if(snippetEntries.length){
      const items=snippetEntries.map(([alias,code])=>({code, alias, user:true}));
      dynamicGroups.unshift({name:'Snippetlar', dynamic:true, items});
    }
    allGroups=[...dynamicGroups,...baseGroups];
    if(activeGroupIndex>=allGroups.length) activeGroupIndex=0;
  }
  function buildCats(){ rebuildGroups(); cats.innerHTML=''; allGroups.forEach((g,i)=>{ const b=document.createElement('button'); b.type='button'; b.className='gfp-cat'+(i===activeGroupIndex?' active':'')+(g.dynamic?' gfp-cat-dyn':''); b.textContent=g.name; b.addEventListener('click',()=>{activeGroupIndex=i; buildCats(); renderButtons();}); cats.appendChild(b); }); }
  function collectAllItems(){ const arr=[]; baseGroups.forEach(g=>g.items.forEach(i=>arr.push({code:i}))); Object.entries(userSnippets).forEach(([alias,code])=>arr.push({code, alias, user:true})); return arr; }
  function renderButtons(){ body.innerHTML=''; const term=search.value.trim().toLowerCase(); let list=[]; if(term){ list=collectAllItems().filter(obj=>obj.code.toLowerCase().includes(term)||(obj.alias&&obj.alias.toLowerCase().includes(term))); } else { const g=allGroups[activeGroupIndex]; if(!g) return; list=g.items.map(it=> typeof it==='string'? {code:it}: it); } list.forEach(obj=>{ const lx=obj.code; const btn=document.createElement('button'); btn.type='button'; btn.className='gfp-btn'; btn.dataset.lx=lx; btn.innerHTML='\\('+lx+'\\)'; if(obj.alias){ const pill=document.createElement('span'); pill.className='gfp-alias-pill'; pill.textContent=obj.alias; btn.appendChild(pill);} body.appendChild(btn); }); if(window.MathJax&&MathJax.typesetPromise){MathJax.typesetPromise([body]);} }
  function openPanel(){panel.classList.add('open'); panel.setAttribute('aria-hidden','false'); search.focus();}
  function closePanel(){panel.classList.remove('open'); panel.setAttribute('aria-hidden','true');}
  toggleBtn.addEventListener('click',()=> panel.classList.contains('open')?closePanel():openPanel());
  closeBtn.addEventListener('click',closePanel);
  search.addEventListener('input',()=>renderButtons());
  const shortcutMap={ 'f':'\\frac{a}{b}','r':'\\sqrt{x}','l':'\\lambda' };
  document.addEventListener('keydown',e=>{ if(e.ctrlKey && e.key.toLowerCase()==='m'){ e.preventDefault(); panel.classList.contains('open')?closePanel():openPanel(); return; } if(e.ctrlKey && e.altKey){ const k=e.key.toLowerCase(); if(shortcutMap[k]){ e.preventDefault(); if(!activeInput){ activeInput=document.querySelector('.math-enabled:focus')||document.getElementById('question-text'); } insertLatex(shortcutMap[k]); } } });
  document.addEventListener('focusin',e=>{ if(e.target.classList && e.target.classList.contains('math-enabled')){ activeInput=e.target; positionMiniBadge(e.target); showMiniBadge(); } });
  document.addEventListener('focusout',e=>{ if(e.target.classList && e.target.classList.contains('math-enabled')){ setTimeout(()=>{ if(!panel.contains(document.activeElement)) hideMiniBadge(); },160); } });
  body.addEventListener('click',e=>{ const b=e.target.closest('.gfp-btn'); if(!b||!activeInput) return; insertLatex(b.dataset.lx); });
  function bumpUsage(lx){ usage[lx]=(usage[lx]||0)+1; saveUsage(usage); }
  function pushRecent(lx){ recents=[lx,...recents.filter(x=>x!==lx)].slice(0,10); saveRecents(recents); }
  function insertLatex(lx){ const el=activeInput; if(!el) return; const st=el.selectionStart||0, en=el.selectionEnd||0; const sel=el.value.substring(st,en); let ins=lx; if(specialWrappers[lx]) ins=specialWrappers[lx](sel); else if(functionWrappers.includes(lx)&&sel) ins=lx+'{'+sel+'}'; else if(lx==='x^2'&&sel) ins=sel+'^2'; else if((lx==='x_1'||lx==='x_{n}')&&sel){ ins=sel+(lx==='x_{n}'?'_{n}':'_1'); } el.value=el.value.slice(0,st)+ins+el.value.slice(en); const np=st+ins.length; el.focus(); el.setSelectionRange(np,np); bumpUsage(lx); pushRecent(lx); buildCats(); renderButtons(); if(typeof updatePreview==='function'){ if(el.id==='question-text'){ (window.debouncedPreview?debouncedPreview():updatePreview()); } else if(el.classList.contains('variant-input')){ updateVariantPreview&&updateVariantPreview(el); } } }
  function enableMath(){ const q=document.getElementById('question-text'); if(q) q.classList.add('math-enabled'); document.querySelectorAll('input[type="text"]').forEach(i=>i.classList.add('math-enabled')); }
  // mini badge
  let miniBadge=null; function ensureMini(){ if(!miniBadge){ miniBadge=document.createElement('button'); miniBadge.type='button'; miniBadge.className='mini-formula-badge'; miniBadge.textContent='∑'; miniBadge.title='Formula panel (Ctrl+M)'; miniBadge.addEventListener('click',()=>{ if(!panel.classList.contains('open')) openPanel(); if(activeInput) activeInput.focus(); }); document.body.appendChild(miniBadge); } }
  function positionMiniBadge(input){ ensureMini(); const r=input.getBoundingClientRect(); miniBadge.style.top=(window.scrollY+r.top+4)+'px'; miniBadge.style.left=(window.scrollX+r.right+6)+'px'; }
  function showMiniBadge(){ ensureMini(); miniBadge.style.display='flex'; }
  function hideMiniBadge(){ if(miniBadge) miniBadge.style.display='none'; }
  window.addEventListener('scroll',()=>{ if(document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('math-enabled')) positionMiniBadge(document.activeElement); },{passive:true});
  window.addEventListener('resize',()=>{ if(document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('math-enabled')) positionMiniBadge(document.activeElement); });
  document.addEventListener('mousedown',e=>{ if(panel.classList.contains('open') && !panel.contains(e.target) && e.target!==toggleBtn){ if(window.innerWidth<720) closePanel(); } });

  // ---------- Alias Expansion & Validation ----------
  function getTokenBeforeCaret(el){ const pos=el.selectionStart||0; const val=el.value.slice(0,pos); const m=val.match(/([A-Za-z0-9_]{2,30})$/); return m?m[1]:null; }
  function expandAliasIfNeeded(el, trigger){ const token=getTokenBeforeCaret(el); if(!token) return false; const lx=aliasMap[token]; if(!lx) return false; const start=el.selectionStart-token.length; const end=el.selectionStart; el.value=el.value.slice(0,start)+lx+(trigger==='space'?' ':'')+el.value.slice(end); const np=start+lx.length+(trigger==='space'?1:0); el.focus(); el.setSelectionRange(np,np); bumpUsage(lx); pushRecent(lx); buildCats(); renderButtons(); validateLatex(el); return true; }
  function scheduleValidation(el){ if(!el._gfpValTimer){ el._gfpValTimer=setTimeout(()=>{validateLatex(el); el._gfpValTimer=null;},500);} else { clearTimeout(el._gfpValTimer); el._gfpValTimer=setTimeout(()=>{validateLatex(el); el._gfpValTimer=null;},500);} }
  function basicBraceCheck(str){ let b=0; for(const ch of str){ if(ch==='{' ) b++; else if(ch==='}') b--; if(b<0) return false;} return b===0; }
  function flashBad(el){ el.classList.add('gfp-bad-latex'); setTimeout(()=>el.classList.remove('gfp-bad-latex'),800); }
  function validateLatex(el){ const txt=el.value; if(!/[\\]/.test(txt)) return; if(!basicBraceCheck(txt)){ flashBad(el); return; } if(window.MathJax && MathJax.tex2chtml){ try{ MathJax.tex2chtml(txt); } catch{ flashBad(el); } } }
  document.addEventListener('keydown',e=>{ const el=document.activeElement; if(!el||!el.classList||!el.classList.contains('math-enabled')) return; if(e.key==='Tab'){ const ex=expandAliasIfNeeded(el,'tab'); if(ex){ e.preventDefault(); } } else if(e.key===' '){ const ex=expandAliasIfNeeded(el,'space'); if(ex){ e.preventDefault(); } } });
  document.addEventListener('input',e=>{ const el=e.target; if(!el.classList||!el.classList.contains('math-enabled')) return; scheduleValidation(el); });

  // ---------- Snippet Modal Logic ----------
  function openSnippetModal(){ if(!snippetModal) return; snippetModal.style.display='flex'; snippetModal.setAttribute('aria-hidden','false'); snippetName.value=''; snippetCode.value=''; snippetError.style.display='none'; snippetName.focus(); }
  function closeSnippetModal(){ if(!snippetModal) return; snippetModal.style.display='none'; snippetModal.setAttribute('aria-hidden','true'); }
  function validateSnippetFields(){ const name=snippetName.value.trim(); const code=snippetCode.value.trim(); if(!/^[A-Za-z0-9_]{2,20}$/.test(name)) return "Noto'g'ri nom"; if(!code) return 'Kod bo\'sh'; if(code.length>120) return 'Kod juda uzun'; if(code.split('\\').length>40) return 'Ko\'p belgi'; if(!basicBraceCheck(code)) return 'Qavs mos emas'; try{ if(window.MathJax && MathJax.tex2chtml){ MathJax.tex2chtml(code); } } catch{ return 'MathJax xato'; } return null; }
  function saveSnippet(){ const err=validateSnippetFields(); if(err){ snippetError.textContent=err; snippetError.style.display='block'; flashBad(snippetCode); return; } const alias=snippetName.value.trim(); const code=snippetCode.value.trim(); userSnippets[alias]=code; saveSnippets(userSnippets); aliasMap=buildAliasMap(); closeSnippetModal(); buildCats(); renderButtons(); }
  if(addSnippetBtn){ addSnippetBtn.addEventListener('click',openSnippetModal); }
  [snippetCancel,snippetClose].forEach(btn=> btn && btn.addEventListener('click',closeSnippetModal));
  if(snippetSave){ snippetSave.addEventListener('click',saveSnippet); }
  snippetCode && snippetCode.addEventListener('input',()=>{ const err=validateSnippetFields(); if(err){ snippetError.textContent=err; snippetError.style.display='block'; } else { snippetError.style.display='none'; }});
  document.addEventListener('keydown',e=>{ if(e.key==='Escape' && snippetModal && snippetModal.style.display==='flex'){ closeSnippetModal(); } });

  rebuildGroups(); buildCats(); renderButtons(); enableMath();
})();
