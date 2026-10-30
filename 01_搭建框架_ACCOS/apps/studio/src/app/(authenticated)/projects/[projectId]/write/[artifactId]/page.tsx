import { WritingSpace } from "../../../../../../features/writing/writing-space";

export default async function WritingPage({ params }: { params: Promise<{ artifactId: string }> }) {
  const { artifactId } = await params;
  return <WritingSpace artifactId={artifactId} />;
}
