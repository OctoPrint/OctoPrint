const {defineConfig} = require("eslint/config");
const globals = require("globals");

module.exports = defineConfig([
    {
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.jquery
            }
        }
    }
]);
