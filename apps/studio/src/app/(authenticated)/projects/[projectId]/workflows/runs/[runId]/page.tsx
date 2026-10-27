import { WorkflowRunDetail } from "../../../../../../../features/workflows/workflow-run-detail";

export default async function WorkflowRunPage(
  props: PageProps<"/projects/[projectId]/workflows/runs/[runId]">,
) {
  const { runId } = await props.params;
  return <WorkflowRunDetail runId={runId} />;
}
