const BRIDGE_URL = "http://127.0.0.1:8766/context";

const MAX_PAGE_TEXT = 12000;

let lastSentUrl = "";
let lastSentTitle = "";


async function readPageText(tabId) {
    try {
        const results = await chrome.scripting.executeScript({
            target: {
                tabId: tabId
            },
            func: () => {
                return document.body
                    ? document.body.innerText
                    : "";
            }
        });

        if (!results || !results.length) {
            return "";
        }

        return results[0].result || "";

    } catch (error) {
        return "";
    }
}


async function sendPayload(payload) {
    try {
        await fetch(
            BRIDGE_URL,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            }
        );
    } catch (error) {
        // Hornet may not be running.
    }
}


async function sendContext(tab, force = false) {
    if (!tab) {
        return;
    }

    if (!tab.url) {
        return;
    }

    const url = tab.url;
    const title = tab.title || "";

    /*
     * Avoid browser internal pages.
     */
    if (
        url.startsWith("chrome://") ||
        url.startsWith("edge://") ||
        url.startsWith("about:")
    ) {
        const payload = {
            browser: "Chrome",
            title: title,
            url: url,
            page_text: ""
        };

        await sendPayload(payload);
        return;
    }

    /*
     * Avoid sending the exact same URL/title repeatedly.
     */
    if (
        !force &&
        url === lastSentUrl &&
        title === lastSentTitle
    ) {
        return;
    }

    const pageText = await readPageText(tab.id);

    let limitedText = pageText;

    if (limitedText.length > MAX_PAGE_TEXT) {
        limitedText =
            limitedText.substring(0, MAX_PAGE_TEXT);
    }

    lastSentUrl = url;
    lastSentTitle = title;

    const payload = {
        browser: "Chrome",
        title: title,
        url: url,
        page_text: limitedText
    };

    console.log(
        "HORN ET PAGE:",
        title,
        "|",
        url
    );

    await sendPayload(payload);
}


/*
 * Normal tab activation.
 */
chrome.tabs.onActivated.addListener(
    async (activeInfo) => {

        try {
            const tab =
                await chrome.tabs.get(
                    activeInfo.tabId
                );

            await sendContext(
                tab,
                true
            );

        } catch (error) {
            console.error(error);
        }
    }
);


/*
 * Normal navigation/title changes.
 */
chrome.tabs.onUpdated.addListener(
    async (tabId, changeInfo, tab) => {

        if (
            changeInfo.status === "complete" ||
            changeInfo.title ||
            changeInfo.url
        ) {

            await sendContext(
                tab,
                true
            );
        }
    }
);


/*
 * Important for YouTube and other
 * single-page applications.
 *
 * YouTube can change videos without
 * performing a normal page navigation.
 */
chrome.webNavigation.onHistoryStateUpdated.addListener(
    async (details) => {

        if (details.frameId !== 0) {
            return;
        }

        try {

            const tab =
                await chrome.tabs.get(
                    details.tabId
                );

            await sendContext(
                tab,
                true
            );

        } catch (error) {
            console.error(error);
        }
    }
);
