import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { getSignalementDetails, getProcessStatus } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import ProgressPipeline from '@/components/ProgressPipeline';
import AudioPlayer from '@/components/AudioPlayer';
import ScenarioCard from '@/components/ScenarioCard';

const SignalementDetailPage = () => {
  const router = useRouter();
  const { id } = router.query;

  const [signalement, setSignalement] = useState(null);
  const [processStatus, setProcessStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (id) {
      fetchSignalementDetails(id);
      const interval = setInterval(() => {
        fetchProcessStatus(id);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [id]);

  const fetchSignalementDetails = async (id) => {
    try {
      const data = await getSignalementDetails(id);
      setSignalement(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchProcessStatus = async (id) => {
    try {
      const status = await getProcessStatus(id);
      setProcessStatus(status);
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Signalement Details</h1>
      {signalement && (
        <div>
          <img src={`http://localhost:8000/static/outputs/${signalement.image}`} alt="Original" />
          <ProgressPipeline currentStage={processStatus?.currentStage} />
          <div className="grid grid-cols-3 gap-4">
            {signalement.generatedImages.map((image, index) => (
              <ScenarioCard key={index} image={image} title={`Scenario ${index + 1}`} cost={signalement.costs[index]} />
            ))}
          </div>
          {processStatus && (
            <div>
              <h2 className="text-lg">Process Status</h2>
              <StatusBadge status={processStatus.status} />
            </div>
          )}
          {signalement.audio_url && <AudioPlayer src={signalement.audio_url} />}
          {signalement.pdf_url && (
            <a href={`http://localhost:8000/static/outputs/${signalement.pdf_url}`} className="text-blue-600">
              Download PDF
            </a>
          )}
        </div>
      )}
    </div>
  );
};

export default SignalementDetailPage;