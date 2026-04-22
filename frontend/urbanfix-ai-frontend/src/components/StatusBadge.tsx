import React from 'react';

interface StatusBadgeProps {
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

const statusStyles = {
  pending: 'bg-yellow-500 text-white',
  processing: 'bg-blue-500 text-white',
  completed: 'bg-green-500 text-white',
  failed: 'bg-red-500 text-white',
};

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${statusStyles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export default StatusBadge;