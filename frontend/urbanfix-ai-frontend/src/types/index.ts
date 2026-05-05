export interface Signalement {
  id: number;
  title: string;
  description?: string | null;
  city: string;
  region: string;
  latitude: number;
  longitude: number;
  imageUrl?: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
}

export interface ProcessStatus {
  id?: number;
  signalementId?: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  currentStage?: string | null;
  isComplete?: boolean;
  audioUrl?: string;
  pdfUrl?: string;
}

export interface CostEstimation {
  repairs: number;
  improvements: number;
}

export interface Detection {
  type: string;
  count: number;
  priority: number;
}

export interface Scenario {
  imageUrl?: string | null;
  title?: string;
  cost?: number;
}

export interface SignalementDetail extends Signalement {
  generatedImages?: string[];
  costs?: number[];
  scenarios?: Scenario[];
  audioUrl?: string | null;
  pdfUrl?: string | null;
}
