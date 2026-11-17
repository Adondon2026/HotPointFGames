/* ZMZ v0.24.1: isolate Android WebView touch gestures in the open buff list.
   Browser users keep native CSS scrolling. This source is loaded after lite.js. */
(function(){
  'use strict';
  const modal=document.getElementById('settingsModal');
  const details=document.getElementById('siegeAllowedConfig');
  const list=document.getElementById('siegeBuffChoices');
  const back=document.getElementById('siegeBuffBack');
  if(!modal||!details||!list||!back)return;
  const nativeWebView=()=>document.documentElement.classList.contains('zmz-webview');
  let lastY=null,firstY=null,firstX=null,dragging=false;
  const reset=()=>{lastY=firstY=firstX=null;dragging=false};
  list.addEventListener('touchstart',e=>{
    reset();
    if(!nativeWebView()||!details.open||e.touches.length!==1)return;
    firstX=e.touches[0].clientX;firstY=lastY=e.touches[0].clientY;
  },{passive:true});
  list.addEventListener('touchmove',e=>{
    if(!nativeWebView()||!details.open||e.touches.length!==1||lastY===null)return;
    const x=e.touches[0].clientX,y=e.touches[0].clientY;
    if(!dragging){
      if(Math.abs(y-firstY)<4||Math.abs(y-firstY)<Math.abs(x-firstX)*1.15)return;
      dragging=true;
    }
    // The gesture ALWAYS belongs to this list, even at its top/bottom.
    // Otherwise Android System WebView transfers it to the outer settings sheet.
    if(list.scrollHeight>list.clientHeight+1){
      list.scrollTop+=lastY-y;
      if(e.cancelable)e.preventDefault();
      e.stopPropagation();
    }
    lastY=y;
  },{passive:false});
  list.addEventListener('touchend',reset,{passive:true});
  list.addEventListener('touchcancel',reset,{passive:true});
  back.addEventListener('click',()=>{
    details.open=false;reset();
    const sheet=modal.querySelector('.sheet');
    if(sheet){
      const delta=details.getBoundingClientRect().top-sheet.getBoundingClientRect().top;
      sheet.scrollTop=Math.max(0,sheet.scrollTop+delta-60);
    }
  });
  modal.addEventListener('touchmove',e=>{
    if(!nativeWebView()||modal.classList.contains('hidden'))return;
    if(!e.target.closest('.sheet')&&e.cancelable)e.preventDefault();
  },{passive:false});
})();
