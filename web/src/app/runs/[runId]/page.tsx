import { notFound } from "next/navigation";

import { RunDetailClient } from "@/components/RunDetailClient";
import { tesApi } from "@/lib/api/client";

export const dynamic = "force-dynamic";

export default async function RunDetailPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  try {
    const run = await tesApi.getRun(runId);
    return <RunDetailClient run={run} />;
  } catch {
    notFound();
  }
}
