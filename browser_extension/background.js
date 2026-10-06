const BRIDGE_URL = "http://127.0.0.1:8766/context";


async function sendContext(tab) {

    if (!tab) {
        return;
    }

    if (!tab.url) {
        return;
    }

    const payload = {
        browser: "Chrome",
        title: tab.title || "",
        url: tab.url || ""
    };

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
        // Ignore connection failures.

    }
}


chrome.tabs.onActivated.addListener(
    async (activeInfo) => {

        try {

            const tab = await chrome.tabs.get(
                activeInfo.tabId
            );

            await sendContext(tab);

        } catch (error) {

            console.error(error);

        }
    }
);


chrome.tabs.onUpdated.addListener(
    async (tabId, changeInfo, tab) => {

        if (
            changeInfo.status === "complete" ||
            changeInfo.title ||
            changeInfo.url
        ) {

            await sendContext(tab);

        }
    }
);