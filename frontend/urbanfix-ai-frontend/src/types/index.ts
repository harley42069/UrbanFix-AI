export interface Signalement {
  id: number;
  title: string;
  description: string;
  city: string;
  region: string;
  latitude: number;
  longitude: number;
  imageUrl: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
}

export interface ProcessStatus {
  id: number;
  currentStage: 'detection' | 'images' | 'cost' | 'audio' | 'pdf';
  isComplete: boolean;
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
  imageUrl: string;
  title: string;
  cost: number;
}