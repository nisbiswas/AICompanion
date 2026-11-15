const BRIDGE_URL = "http://127.0.0.1:8766/context";
let captureVersion = 0;

async function readPage(tabId) {
    const results = await chrome.scripting.executeScript({
        target: {tabId, allFrames: true}, world: "MAIN",
        func: () => {
            const visible = node => !!(node && node.getBoundingClientRect().width && node.getBoundingClientRect().height);
            const main = document.querySelector("main, [role=main], article") || document.body;
            const code = [];
            // Text editors often store the complete document outside rendered DOM lines.
            if (document.querySelector(".monaco-editor") && window.monaco?.editor) {
                for (const model of window.monaco.editor.getModels()) {
                    code.push(`[${model.getLanguageId()}]\n${model.getValue()}`);
                }
            }
            for (const node of document.querySelectorAll(".CodeMirror")) {
                if (visible(node) && node.CodeMirror) code.push(node.CodeMirror.getValue());
            }
            for (const node of document.querySelectorAll(".cm-content")) {
                if (visible(node)) code.push(node.cmView?.view?.state?.doc?.toString() || node.innerText);
            }
            for (const node of document.querySelectorAll(".ace_editor")) {
                if (visible(node) && node.env?.editor) code.push(node.env.editor.getValue());
            }
            for (const node of document.querySelectorAll("textarea, pre")) {
                if (visible(node)) code.push(node.value || node.innerText || "");
            }
            const raw = main?.innerText || "";
            const fullCode = [...new Set(code.filter(Boolean))].join("\n\n");
            return {page_text: raw.slice(0, 24000), code_text: fullCode.slice(0, 16000),
                selected_text: window.getSelection()?.toString().slice(0, 4000) || "",
                text_length: raw.length, code_length: fullCode.length,
                truncated: raw.length > 24000 || fullCode.length > 16000};
        }
    });
    const frames = results.filter(r => r.result).sort((a,b) => a.frameId - b.frameId).map(r => r.result);
    const text = frames.map(r => r.page_text).join("\n\n");
    const code = frames.map(r => r.code_text).filter(Boolean).join("\n\n");
    return {page_text: text.slice(0, 24000), code_text: code.slice(0, 16000),
        selected_text: frames.map(r => r.selected_text).filter(Boolean).join("\n").slice(0,4000),
        text_length: frames.reduce((n,r) => n + r.text_length, 0),
        code_length: frames.reduce((n,r) => n + r.code_length, 0),
        truncated: frames.some(r => r.truncated) || text.length > 24000 || code.length > 16000};
}

async function sendContext(tab) {
    if (!tab?.url) return;
    const version = ++captureVersion;
    let active = await chrome.tabs.query({active: true, lastFocusedWindow: true});
    if (!active.length || active[0].id !== tab.id) return;
    let page = {page_text:"", code_text:"", selected_text:"", truncated:false};
    if (/^https?:/.test(tab.url)) {
        try { page = await readPage(tab.id); } catch (_) { page.capture_error = "Page text could not be read"; }
    }
    active = await chrome.tabs.query({active:true,lastFocusedWindow:true});
    if (version !== captureVersion || !active.length || active[0].id !== tab.id || active[0].url !== tab.url) return;
    try {
        await fetch(BRIDGE_URL, {method:"POST", headers:{"Content-Type":"application/json"},
            body:JSON.stringify({browser:"Chrome", title:tab.title||"", url:tab.url,
                tab_id:tab.id, captured_at:new Date().toISOString(), ...page})});
    } catch (_) { /* Companion may not be running. */ }
}

async function refreshActiveContext() {
    try {
        const tabs = await chrome.tabs.query({active:true,lastFocusedWindow:true});
        if (tabs.length) await sendContext(tabs[0]);
    } catch (_) { /* A tab/window can close while capturing. */ }
}
chrome.tabs.onActivated.addListener(refreshActiveContext);
chrome.tabs.onUpdated.addListener((id, change, tab) => {
    if (tab.active && (change.status === "complete" || change.title || change.url)) refreshActiveContext();
});
chrome.webNavigation.onHistoryStateUpdated.addListener(details => {
    if (details.frameId === 0) refreshActiveContext();
});
chrome.windows.onFocusChanged.addListener(refreshActiveContext);
chrome.runtime.onMessage.addListener((message, sender) => {
    if (message.type === "hornet-page-changed" && sender.tab?.active) refreshActiveContext();
});
chrome.alarms.create("hornet-context", {periodInMinutes:0.5});
chrome.alarms.onAlarm.addListener(alarm => { if (alarm.name === "hornet-context") refreshActiveContext(); });
refreshActiveContext();
