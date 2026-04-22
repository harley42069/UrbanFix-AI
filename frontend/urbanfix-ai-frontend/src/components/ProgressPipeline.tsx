import React from 'react';

const stages = [
  { name: 'Detection', completed: false },
  { name: 'Images', completed: false },
  { name: 'Cost', completed: false },
  { name: 'Audio', completed: false },
  { name: 'PDF', completed: false },
];

interface ProgressPipelineProps {
  currentStage: number;
}

const ProgressPipeline: React.FC<ProgressPipelineProps> = ({ currentStage }) => {
  return (
    <div className="flex flex-col space-y-2">
      {stages.map((stage, index) => (
        <div key={stage.name} className="flex items-center">
          <div
            className={`w-4 h-4 rounded-full ${
              index <= currentStage ? 'bg-primary' : 'bg-gray-300'
            }`}
          />
          <span className={`ml-2 ${index <= currentStage ? 'text-primary' : 'text-gray-500'}`}>
            {stage.name}
          </span>
        </div>
      ))}
    </div>
  );
};

export default ProgressPipeline;