import { LiveMonitor } from "@/components/LiveMonitor";

export const dynamic = "force-dynamic";

export default async function LiveRunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <LiveMonitor runId={runId} />;
}
