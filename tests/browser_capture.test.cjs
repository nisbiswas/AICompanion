const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

(async () => {
    let active = {id: 1, url: 'https://example.org/problem', title: 'Reverse Integer', active:true};
    const payloads = [];
    const listener = {addListener() {}};
    const editorCode = 'class Solution { public int reverse(int x) { return x; } }';
    const sandbox = {
        console, setTimeout, clearTimeout,
        document: {
            querySelector(selector) { return selector === '.monaco-editor' ? {} : {innerText: 'Problem description '.repeat(1400)}; },
            querySelectorAll() { return []; },
        },
        window: {monaco:{editor:{getModels:() => [{getLanguageId:()=> 'java',getValue:()=>editorCode}]}}, getSelection:()=>({toString:()=> 'overflow check'})},
        chrome: {
            tabs: {query:async()=> [active], onActivated:listener, onUpdated:listener},
            scripting:{executeScript:async ({func})=>[{frameId:0,result:func()}]},
            webNavigation:{onHistoryStateUpdated:listener}, windows:{onFocusChanged:listener},
            runtime:{onMessage:listener}, alarms:{create(){},onAlarm:listener},
        },
        fetch: async (url, options) => { payloads.push(JSON.parse(options.body)); return {ok:true}; },
    };
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync('browser_extension/background.js','utf8'),sandbox);
    const page = await sandbox.readPage(1);
    assert.equal(page.code_text, '[java]\n' + editorCode);
    assert.equal(page.selected_text, 'overflow check');
    assert.equal(page.page_text.length, 24000);
    assert.equal(page.truncated, true);
    await sandbox.sendContext(active);
    assert(payloads.some(p => p.code_text.includes('public int reverse')));
    const before = payloads.length;
    active = {id:2, url:'https://example.org/new',title:'New page'};
    await sandbox.sendContext({id:1,url:'https://example.org/problem'});
    assert.equal(payloads.length,before, 'Inactive page must not replace active context');
    console.log('Browser editor capture, truncation metadata and active-tab filtering passed');
})().catch(error => {console.error(error);process.exitCode=1;});
