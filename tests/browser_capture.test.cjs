const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function testBrowser(apiName, expectedName) {
    let active = {id: 1, url: 'https://example.org/problem', title: 'Reverse Integer', active:true};
    let focused = true;
    let loseFocusDuringCapture = false;
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
        [apiName]: {
            tabs: {query:async()=> [active], onActivated:listener, onUpdated:listener},
            scripting:{executeScript:async ({func})=> {
                if (loseFocusDuringCapture) focused = false;
                return [{frameId:0,result:func()}];
            }},
            webNavigation:{onHistoryStateUpdated:listener},
            windows:{onFocusChanged:listener, getLastFocused:async()=>({focused})},
            runtime:{onMessage:listener, ...(apiName === 'browser' ? {getBrowserInfo:async()=>({name:'Firefox'})} : {})},
            alarms:{create(){},onAlarm:listener},
        },
        fetch: async (url, options) => { payloads.push(JSON.parse(options.body)); return {ok:true}; },
    };
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync('browser_extension/background.js','utf8'),sandbox);
    await new Promise(setImmediate); // Let the automatic startup capture settle.
    const page = await sandbox.readPage(1);
    assert.equal(page.code_text, '[java]\n' + editorCode);
    assert.equal(page.selected_text, 'overflow check');
    assert.equal(page.page_text.length, 24000);
    assert.equal(page.truncated, true);
    await sandbox.sendContext(active);
    assert(payloads.some(p => p.code_text.includes('public int reverse')));
    assert(payloads.every(p => p.browser === expectedName));
    focused = false;
    const focusedCount = payloads.length;
    await sandbox.refreshActiveContext();
    assert.equal(payloads.length, focusedCount, 'An unfocused browser must not replace the foreground browser');
    focused = true;
    loseFocusDuringCapture = true;
    await sandbox.sendContext(active);
    assert.equal(payloads.length, focusedCount, 'A capture finishing after switching browsers must be discarded');
    focused = true;
    loseFocusDuringCapture = false;
    await sandbox.refreshActiveContext();
    assert.equal(payloads.length, focusedCount + 1, 'Capture must resume when the browser regains focus');
    const before = payloads.length;
    active = {id:2, url:'https://example.org/new',title:'New page'};
    await sandbox.sendContext({id:1,url:'https://example.org/problem'});
    assert.equal(payloads.length,before, 'Inactive page must not replace active context');
    // Firefox has no chrome global in this sandbox: content notifications must
    // also work through browser.runtime, not just the background script.
    const messages = [];
    const content = {
        [apiName]: {runtime:{sendMessage:async message => messages.push(message)}},
        document:{visibilityState:'visible', documentElement:{}, addEventListener(){}},
        MutationObserver:class {observe(){}},
        setTimeout(callback) {callback();}, clearTimeout(){},
    };
    vm.createContext(content);
    vm.runInContext(fs.readFileSync('browser_extension/content.js','utf8'),content);
    assert.equal(messages[0].type, 'hornet-page-changed');
    console.log(`${expectedName}: editor capture, content notifications, truncation, active tab and browser focus passed`);
}

(async () => {
    const manifest = JSON.parse(fs.readFileSync('browser_extension/manifest.json','utf8'));
    assert.equal(manifest.background.service_worker, 'background.js');
    assert.deepEqual(manifest.background.scripts, ['background.js']);
    assert.equal(manifest.browser_specific_settings.gecko.strict_min_version, '128.0');
    await testBrowser('chrome', 'Chrome');
    await testBrowser('browser', 'Firefox');
})().catch(error => {console.error(error);process.exitCode=1;});
