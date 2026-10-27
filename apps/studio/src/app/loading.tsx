import { Skeleton } from "@accos/ui";

export default function Loading() {
  return (
    <main className="studio-state-wrap" id="main-content">
      <Skeleton lines={5} />
    </main>
  );
}
