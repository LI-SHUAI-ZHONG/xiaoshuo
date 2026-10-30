/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-circular-workspace-dependencies",
      severity: "error",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    exclude: "(^|/)(node_modules|coverage|dist|执行|\\.next)(/|$)",
    tsConfig: { fileName: "tsconfig.json" },
  },
};
