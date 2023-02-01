// @ts-check
const {devices} = require("@playwright/test");

const config = {
    testDir: "./specs",
    timeout: 60_000,
    expect: {
        timeout: 10_000
    },
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 2 : undefined,
    reportSlowTests: {
        max: 30_000,
        threshold: 50_000
    },
    reporter: "html",
    use: {
        actionTimeout: 0,
        baseURL: process.env.PLAYWRIGHT_BASEURL || "http://localhost:5000",
        testIdAttribute: "data-test-id",
        trace: "on",
        video: "on",
        viewport: {width: 1280, height: 720}
    },

    projects: [
        {
            name: "chromium",
            use: {
                ...devices["Desktop Chrome"]
            }
        },
        {
            name: "firefox",
            use: {
                ...devices["Desktop Firefox"]
            }
        }

        /* Test against mobile viewports. */
        // {
        //   name: 'Mobile Chrome',
        //   use: {
        //     ...devices['Pixel 5'],
        //   },
        // },
        // {
        //   name: 'Mobile Safari',
        //   use: {
        //     ...devices['iPhone 12'],
        //   },
        // },

        /* Test against branded browsers. */
        // {
        //   name: 'Microsoft Edge',
        //   use: {
        //     channel: 'msedge',
        //   },
        // },
        // {
        //   name: 'Google Chrome',
        //   use: {
        //     channel: 'chrome',
        //   },
        // },
    ]
};

if (!process.env.NO_SERVER) {
    const octoprintServerOpts = process.env.OCTOPRINT_SERVER_BASE
        ? `-b ${process.env.OCTOPRINT_SERVER_BASE}`
        : "";

    config.webServer = {
        command: `octoprint ${octoprintServerOpts} serve --host 127.0.0.1 --port 5000`,
        url: "http://127.0.0.1:5000/online.txt",
        reuseExistingServer: !process.env.CI
    };
}

module.exports = config;
