const {test, expect} = require("../fixtures");

test.describe.parallel("Page loads", async () => {
    [
        "reverse_proxy_test",
        "reverse_proxy_check",
        "reverse-proxy-test",
        "reverse-proxy-check",
        "proxy_test",
        "proxy_check",
        "proxy-test",
        "proxy-check"
    ].forEach((endpoint) => {
        ["", "/"].forEach((suffix) => {
            test(`endpoint: ${endpoint}${suffix}`, async ({page, baseURL}) => {
                await page.goto(`${baseURL}/${endpoint}${suffix}`);

                await expect(page).toHaveTitle("OctoPrint Reverse Proxy Test");
                await expect(page).toHaveURL(`${baseURL}/reverse_proxy_test/`);
                await expect(page.locator("#reverse_proxy_test")).toBeVisible();
            });
        });
    });
});
