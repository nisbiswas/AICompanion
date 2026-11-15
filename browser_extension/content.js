// Debounce visible document and editor changes instead of waiting 30 seconds.
let timer;
function changed() {
    if (document.visibilityState !== "visible") return;
    clearTimeout(timer);
    timer = setTimeout(() => {
        try { chrome.runtime.sendMessage({type:"hornet-page-changed"}).catch(() => {}); } catch (_) {}
    }, 700);
}
new MutationObserver(changed).observe(document.documentElement, {subtree:true,childList:true,characterData:true});
document.addEventListener("input", changed, true);
document.addEventListener("selectionchange", changed);
document.addEventListener("visibilitychange", changed);
changed();
