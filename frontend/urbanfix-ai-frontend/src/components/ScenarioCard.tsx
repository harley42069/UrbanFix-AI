import React from 'react';

interface ScenarioCardProps {
  imageUrl: string;
  title: string;
  cost: number;
}

const ScenarioCard: React.FC<ScenarioCardProps> = ({ imageUrl, title, cost }) => {
  return (
    <div className="border rounded-lg shadow-md overflow-hidden">
      <img src={imageUrl} alt={title} className="w-full h-48 object-cover" />
      <div className="p-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-gray-700">Cost: ${cost.toFixed(2)}</p>
      </div>
    </div>
  );
};

export default ScenarioCard;