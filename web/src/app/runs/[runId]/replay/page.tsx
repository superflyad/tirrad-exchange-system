import { ReplayViewer } from "@/components/ReplayViewer";

export const dynamic = "force-dynamic";

export default async function ReplayRunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <ReplayViewer runId={runId} />;
}
