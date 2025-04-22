const base = require("@playwright/test");
const {MD5} = require("crypto-js");

const credentials = {
    username: process.env.OCTOPRINT_USERNAME || "admin",
    password: process.env.OCTOPRINT_PASSWORD || "test"
};

const mfaCredentials = {
    username: process.env.OCTOPRINT_MFA_USERNAME || "mfa",
    password: process.env.OCTOPRINT_MFA_PASSWORD || "mfa",
    token: "secret"
};

const expect = base.expect;

exports.test = base.test.extend({
    loginApi: async ({context, baseURL}, use) => {
        const loginApi = {
            login: async (username, password, remember) => {
                return await context.request.post(baseURL + "/api/login", {
                    data: {
                        user: username,
                        pass: password,
                        remember: !!remember
                    }
                });
            },

            logout: async () => {
                return await context.request.post(baseURL + "/api/logout");
            },

            loginDefault: async (remember) => {
                const response = await loginApi.login(
                    credentials.username,
                    credentials.password,
                    remember
                );
                await expect(response.ok()).toBeTruthy();
                return response;
            }
        };

        await use(loginApi);
    },

    connectionApi: async ({context, baseURL}, use) => {
        const connect = async (port, baudrate) => {
            port = port || "AUTO";
            baudrate = baudrate || 0;
            return await context.request.post(baseURL + "/api/connection", {
                data: {
                    command: "connect",
                    port: port,
                    baudrate: baudrate
                }
            });
        };
        const disconnect = async () => {
            return await context.request.post(baseURL + "/api/connection", {
                data: {
                    command: "disconnect"
                }
            });
        };

        const connectionApi = {
            connect: connect,
            disconnect: disconnect,
            ensureConnected: async (port, baudrate) => {
                const response = await context.request.get(baseURL + "/api/connection");
                const data = await response.json();
                if (
                    data.current.state === "Operational" &&
                    (!port || data.current.port === port) &&
                    (!baudrate || data.current.baudrate === baudrate)
                ) {
                    return;
                }
                await disconnect();
                await connect(port, baudrate);
            }
        };
        await use(connectionApi);
    },

    filesApi: async ({context, baseURL}, use) => {
        const filesApi = {
            ensureFileUnknown: async (location, name) => {
                return await context.request.delete(
                    baseURL + `/api/files/${location}/${name}`
                );
            },
            getEntryId: (origin, path) => {
                path = path.replace(/^\/+/, "");
                return MD5(`${origin}:${path}`);
            }
        };
        await use(filesApi);
    },

    credentials: async ({}, use) => {
        await use(credentials);
    },

    mfaCredentials: async ({}, use) => {
        await use(mfaCredentials);
    },

    ui: async ({page, util, loginApi, baseURL}, use) => {
        const ui = {
            gotoLogin: async () => {
                await page.goto(baseURL + "/?l10n=en");
                await ui.loginHasLoaded();
            },

            gotoCore: async () => {
                await page.goto(baseURL + "/?l10n=en");
                await ui.coreHasLoaded();
            },

            gotoLoggedInCore: async () => {
                await loginApi.loginDefault();
                await page.goto(baseURL + "/?l10n=en");
                await ui.coreHasLoaded();
            },

            coreIsLoading: async () => {
                await expect(page).toHaveURL(util.getFullUrlRegExp("/"), {
                    timeout: 15_000
                });
            },

            coreHasLoaded: async () => {
                await ui.coreIsLoading();
                await page.waitForFunction(
                    () =>
                        window.OctoPrint &&
                        window.OctoPrint.coreui &&
                        window.OctoPrint.coreui.startedUp,
                    {timeout: 10_000}
                );
            },

            loggedInCoreHasLoaded: async (username) => {
                username = username || credentials.username;
                await ui.coreHasLoaded();
                await expect(page.getByTestId("login-menu-title")).toContainText(
                    username
                );
            },

            loginIsLoading: async () => {
                await expect(page).toHaveURL(util.getFullUrlRegExp("/login/"), {
                    timeout: 15_000
                });
            },

            loginHasLoaded: async () => {
                await ui.loginIsLoading();
                await page.waitForFunction(
                    () =>
                        window.OctoPrint &&
                        window.OctoPrint.loginui &&
                        window.OctoPrint.loginui.startedUp,
                    {timeout: 10_000}
                );

                const loginForm = await page.getByTestId("login-form");
                await expect(loginForm).toBeVisible();

                const loginTitle = await page.getByTestId("login-title");
                await expect(loginTitle).toBeVisible();
                await expect(loginTitle).toContainText("Please log in");
            },

            mfaHasLoaded: async () => {
                await ui.loginIsLoading();
                await page.waitForFunction(
                    () =>
                        window.OctoPrint &&
                        window.OctoPrint.loginui &&
                        window.OctoPrint.loginui.startedUp,
                    {timeout: 10_000}
                );

                const mfaForm = await page.getByTestId("mfa-form");
                await expect(mfaForm).toBeVisible();
            }
        };
        await use(ui);
    },

    util: async ({context, baseURL}, use) => {
        const getCookieName = (cookie) => {
            const url = new URL(baseURL);
            const port = url.port || (url.protocol === "https:" ? 443 : 80);
            if (url.pathname && url.pathname !== "/") {
                let path = url.pathname;
                if (path.endsWith("/")) {
                    path = path.substring(0, path.length - 1);
                }
                return `${cookie}_P${port}_R${path.replace(/\//, "|")}`;
            } else {
                return `${cookie}_P${port}`;
            }
        };

        const util = {
            loginCookiesWithoutRememberMe: async () => {
                const cookies = await context.cookies();
                const sessionCookie = util.getCookieName("session", baseURL);
                const rememberMeCookie = util.getCookieName("remember_token", baseURL);
                await expect(
                    cookies.find((element) => element.name == sessionCookie)
                ).toBeTruthy();
                await expect(
                    cookies.find((element) => element.name == rememberMeCookie)
                ).toBeFalsy();
            },

            loginCookiesWithRememberMe: async () => {
                const cookies = await context.cookies();
                const sessionCookie = util.getCookieName("session", baseURL);
                const rememberMeCookie = util.getCookieName("remember_token", baseURL);
                await expect(
                    cookies.find((element) => element.name == sessionCookie)
                ).toBeTruthy();
                await expect(
                    cookies.find((element) => element.name == rememberMeCookie)
                ).toBeTruthy();
            },

            getCookieName: getCookieName,

            setCookie: async (name, value) => {
                const cookieName = getCookieName(name);
                await context.addCookies([
                    {name: cookieName, value: value, url: baseURL}
                ]);
            },

            deleteCookie: async (name) => {
                const cookieName = getCookieName(name);
                await context.clearCookies({name: cookieName});
            },

            getFullUrlRegExp: (path) => {
                const fullUrl = baseURL + path;
                const escaped = fullUrl.replace(/[/\-\\^$*+?.()|[\]{}]/g, "\\$&");
                return new RegExp("^" + escaped + "(\\?.*)?(#.*)?$");
            }
        };
        await use(util);
    }
});

exports.expect = expect;
