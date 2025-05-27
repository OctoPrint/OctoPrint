const {test, expect} = require("../fixtures");

test.describe("CSRF Protection", {tag: "@csrf"}, () => {
    test("Core API is CSRF protected", async ({context, baseURL, credentials}) => {
        const response = await context.request.post(baseURL + "/api/login", {
            data: {
                user: credentials.username,
                pass: credentials.password
            }
        });
        await expect(response.status()).toBe(400);
        const body = await response.json();
        expect(body.error).toContain("CSRF");
    });

    test("SimpleApiPlugin command is CSRF protected", async ({context, baseURL}) => {
        const response = await context.request.post(baseURL + "/api/plugin/csrf_test", {
            data: {}
        });
        await expect(response.status()).toBe(400);
        const body = await response.json();
        expect(body.error).toContain("CSRF");
    });

    test("Active BlueprintPlugin endpoint is CSRF protected", async ({
        context,
        baseURL
    }) => {
        const response = await context.request.post(
            baseURL + "/plugin/csrf_test/active",
            {
                data: {}
            }
        );
        await expect(response.status()).toBe(400);
        const body = await response.json();
        expect(body.error).toContain("CSRF");
    });

    test("Exempt BlueprintPlugin endpoint is not CSRF protected", async ({
        context,
        baseURL
    }) => {
        const response = await context.request.post(
            baseURL + "/plugin/csrf_test/exempt",
            {
                data: {}
            }
        );
        await expect(response.status()).toBe(403);
        const body = await response.json();
        expect(body.error).not.toContain("CSRF");
    });

    test("API key based access is not CSRF protected", async ({
        context,
        baseURL,
        credentials
    }) => {
        const response = await context.request.post(baseURL + "/api/login", {
            data: {
                passive: true
            },
            headers: {
                Authorization: `Bearer ${credentials.apikey}`
            }
        });
        await expect(response.status()).toBe(200);
    });

    test("Login via browser works", async ({page, ui, credentials, util}) => {
        await ui.gotoLogin();

        await page.getByTestId("login-username").fill(credentials.username);
        await page.getByTestId("login-password").fill(credentials.password);
        await page.getByTestId("login-submit").click();

        await ui.coreIsLoading();
        await util.loginCookiesWithoutRememberMe();
    });
});
