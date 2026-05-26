"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const js_1 = __importDefault(require("@eslint/js"));
const globals_1 = __importDefault(require("globals"));
const typescript_eslint_1 = __importDefault(require("typescript-eslint"));
const config_1 = require("eslint/config");
exports.default = (0, config_1.defineConfig)([
    {
        ignores: ["out/**"],
    },
    {
        files: ["**/*.{js,mjs,cjs,ts,mts,cts}"],
        plugins: { js: js_1.default },
        extends: ["js/recommended"],
        languageOptions: {
            globals: globals_1.default.browser,
        },
    },
    typescript_eslint_1.default.configs.recommended,
]);
