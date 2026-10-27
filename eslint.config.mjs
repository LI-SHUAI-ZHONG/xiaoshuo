import eslint from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      ".import_linter_cache/**",
      ".mypy_cache/**",
      "**/.next/**",
      ".pytest_cache/**",
      ".ruff_cache/**",
      ".tmp-*/**",
      ".tmp-node*/**",
      ".tmp-pytest/**",
      ".tmp-python/**",
      ".tmp-uv-cache/**",
      ".venv/**",
      "coverage/**",
      "dist/**",
      "infra/.data/**",
      "node_modules/**",
      "packages/api-client/src/generated/**",
      "执行/**",
    ],
  },
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      globals: globals.node,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: [
      "apps/studio/**/*.ts",
      "apps/studio/**/*.tsx",
      "packages/ui/**/*.ts",
      "packages/ui/**/*.tsx",
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    files: ["**/*.js", "**/*.mjs", "**/*.cjs"],
    ...tseslint.configs.disableTypeChecked,
    languageOptions: {
      globals: globals.node,
    },
  },
);
