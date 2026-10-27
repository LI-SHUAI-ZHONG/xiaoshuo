import process from "node:process";

const target = process.argv[2] ?? "unknown";
process.stdout.write(
  `${target} runtime is intentionally deferred to its numbered execution stage.\n`,
);
