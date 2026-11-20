/* Ported from ZMZ v0.24.2: paginated buff configuration, zero list scrolling.
   All checkboxes always stay in the DOM so the upstream room/save/preset
   functions see selections from EVERY page, not just the visible page. */
(function(){
  'use strict';
  const byId=id=>document.getElementById(id);
  const modal=byId('settingsModal'),details=byId('siegeAllowedConfig');
  const list=byId('siegeBuffChoices'),back=byId('siegeBuffBack');
  const pager=byId('zmzBuffPager'),numbers=byId('zmzBuffPageNumbers');
  const prev=byId('zmzBuffPrev'),next=byId('zmzBuffNext');
  const presets=byId('zmzBuffPresets'),summary=byId('zmzBuffPageSummary');
  if(!modal||!details||!list||!back||!pager||!numbers||!prev||!next||!presets||!summary)return;
  const sheet=modal.querySelector('.sheet');
  let rows=[],page=0,pageSize=9,startingScroll=0,queued=false;
  let wasOpen=false;
  const active=()=>details.open&&!modal.classList.contains('hidden');
  const pageCount=()=>Math.max(1,Math.ceil(rows.length/pageSize));

  function collect(){
    rows=[];let group=null;
    for(const el of Array.from(list.children)){
      if(el.classList.contains('siege-buff-group'))group=el;
      // Zombie mode hides negative gains. Never allocate pages to hidden rows.
      if(el.classList.contains('siege-buff-row')&&!el.classList.contains('hidden'))rows.push({el,group});
    }
  }
  function showRows(p){
    const first=p*pageSize,last=first+pageSize;
    const visible=new Set();
    const pageRows=new Set(rows.slice(first,last).map(r=>r.el));
    // Include non-selectable (mode-hidden) rows so switching modes cannot
    // leave stale pagination visibility classes on the same DOM nodes.
    for(const el of list.querySelectorAll('.siege-buff-row'))
      el.classList.toggle('zmz-page-off',!pageRows.has(el));
    rows.slice(first,last).forEach(({group})=>{if(group)visible.add(group)});
    for(const group of list.querySelectorAll('.siege-buff-group'))
      group.classList.toggle('zmz-page-off',!visible.has(group));
  }
  function drawPage(p){
    page=Math.max(0,Math.min(pageCount()-1,p));
    showRows(page);
    prev.disabled=page===0;next.disabled=page>=pageCount()-1;
    // Always show at most three numbered buttons, even on short screens.
    const start=Math.max(0,Math.min(page-1,pageCount()-3));
    const buttons=[];
    for(let i=start;i<Math.min(pageCount(),start+3);i++){
      const button=document.createElement('button');button.type='button';
      button.textContent=String(i+1);button.title='第 '+(i+1)+' 页';
      button.setAttribute('aria-label','第 '+(i+1)+' 页');
      if(i===page)button.setAttribute('aria-current','page');
      button.addEventListener('click',()=>drawPage(i));
      buttons.push(button);
    }
    numbers.replaceChildren(...buttons);
    summary.textContent='第 '+(page+1)+' / '+pageCount()+' 页 · 本页 '+Math.min(pageSize,Math.max(0,rows.length-page*pageSize))+' 项，共 '+rows.length+' 项';
  }
  function fitPages(){
    if(!active()||modal.classList.contains('zmz-buff-presets'))return;
    collect();
    pageSize=Math.min(9,Math.max(1,rows.length));
    // Measure EVERY page (including extra category headings), not just page 1.
    // The viewport-height bounded flex layout determines available list height.
    while(pageSize>1){
      let fits=true;
      const count=pageCount();
      for(let k=0;k<count;k++){
        showRows(k);
        // A flex child can grow to fit its rows while forcing the footer
        // BELOW the clipped modal: verify the whole panel, not only the list.
        const footerBottom=back.getBoundingClientRect().bottom;
        const sheetBottom=sheet.getBoundingClientRect().bottom;
        if(list.scrollHeight>list.clientHeight+2||
           details.scrollHeight>details.clientHeight+2||
           footerBottom>sheetBottom-5){fits=false;break;}
      }
      if(fits)break;
      pageSize--;
    }
    drawPage(page);
  }
  function sync(){
    const open=active();
    const was=wasOpen;
    if(open&&!was){
      startingScroll=sheet?sheet.scrollTop:0;
      page=0;
    }
    wasOpen=open;
    modal.classList.toggle('zmz-buff-mode',open);
    if(!open){
      modal.classList.remove('zmz-buff-presets');
      presets.textContent='预设';presets.setAttribute('aria-pressed','false');
      if(was&&sheet)sheet.scrollTop=startingScroll;
      return;
    }
    if(sheet)sheet.scrollTop=0;
    fitPages();
  }
  function schedule(){
    if(queued)return;
    queued=true;
    const run=()=>{queued=false;sync()};
    if(typeof requestAnimationFrame==='function')requestAnimationFrame(run);else run();
  }
  prev.addEventListener('click',()=>drawPage(page-1));
  next.addEventListener('click',()=>drawPage(page+1));
  presets.addEventListener('click',()=>{
    if(!active())return;
    const showing=modal.classList.toggle('zmz-buff-presets');
    presets.textContent=showing?'返回增益':'预设';
    presets.setAttribute('aria-pressed',String(showing));
    if(!showing)fitPages();
  });
  back.addEventListener('click',()=>{
    details.open=false;
    sync();
  });
  details.addEventListener('toggle',schedule);
  // Closing, reopening or re-rendering room settings must reset the page
  // without recreating or losing checkboxes / other-page selection state.
  if(typeof MutationObserver!=='undefined'){
    new MutationObserver(schedule).observe(modal,{attributes:true,attributeFilter:['class']});
    new MutationObserver(schedule).observe(list,{childList:true});
  }
  window.addEventListener('resize',schedule);
  if(window.visualViewport)window.visualViewport.addEventListener('resize',schedule);
  // No swiping in this selector. Neither the inner list nor the underlying
  // settings should move on Android System WebView or ordinary Chrome.
  list.addEventListener('touchmove',e=>{
    if(!active()||modal.classList.contains('zmz-buff-presets'))return;
    if(e.cancelable)e.preventDefault();
    e.stopPropagation();
  },{passive:false});
  schedule();
})();
