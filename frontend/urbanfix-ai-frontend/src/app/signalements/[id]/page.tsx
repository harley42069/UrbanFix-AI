"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getSignalementDetails, getProcessStatus } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import ProgressPipeline from '@/components/ProgressPipeline';
import AudioPlayer from '@/components/AudioPlayer';
import ScenarioCard from '@/components/ScenarioCard';
import type { ProcessStatus, SignalementDetail } from '@/types';

const SignalementDetailPage = () => {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [signalement, setSignalement] = useState<SignalementDetail | null>(null);
  const [processStatus, setProcessStatus] = useState<ProcessStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchSignalementDetails(id);
      const interval = setInterval(() => {
        fetchProcessStatus(id);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [id]);

  const fetchSignalementDetails = async (signalementId: string) => {
    try {
      const data = await getSignalementDetails(signalementId);
      setSignalement(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const fetchProcessStatus = async (signalementId: string) => {
    try {
      const status = await getProcessStatus(signalementId);
      setProcessStatus(status);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load process status');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!signalement) return <div>Report not found</div>;

  const stageNames = ['queued', 'detection', 'images', 'cost', 'audio', 'video', 'pdf', 'completed'];
  const currentStageIndex = Math.max(0, stageNames.indexOf(processStatus?.currentStage || 'queued'));
  const scenarios = signalement?.scenarios?.length
    ? signalement.scenarios
    : (signalement?.generatedImages || []).map((imageUrl, index) => ({
        imageUrl,
        title: `Scenario ${index + 1}`,
        cost: signalement.costs?.[index] || 0,
      }));

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Report Details</h1>
      <div>
        {signalement.imageUrl && <img src={signalement.imageUrl} alt="Original" />}
        <ProgressPipeline currentStage={currentStageIndex} />
        <div className="grid grid-cols-3 gap-4">
          {scenarios.map((scenario, index) => (
            <ScenarioCard
              key={index}
              imageUrl={scenario.imageUrl || ''}
              title={scenario.title || `Scenario ${index + 1}`}
              cost={scenario.cost || 0}
            />
          ))}
        </div>
        {processStatus && (
          <div>
            <h2 className="text-lg">Process Status</h2>
            <StatusBadge status={processStatus.status} />
          </div>
        )}
        {signalement.audioUrl && <AudioPlayer audioUrl={signalement.audioUrl} />}
        {signalement.pdfUrl && (
          <a href={signalement.pdfUrl} className="text-blue-600">
            Download PDF
          </a>
        )}
      </div>
    </div>
  );
};

export default SignalementDetailPage;
