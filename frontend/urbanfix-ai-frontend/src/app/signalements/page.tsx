"use client";

import { useEffect, useState } from 'react';
import { fetchSignalements } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import type { Signalement } from '@/types';

const SignalementsPage = () => {
  const [signalements, setSignalements] = useState<Signalement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('all'); // For filtering by status

  useEffect(() => {
    const loadSignalements = async () => {
      try {
        const data = await fetchSignalements(filter);
        setSignalements(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load reports');
      } finally {
        setLoading(false);
      }
    };

    loadSignalements();
  }, [filter]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Reports</h1>
      <div className="mb-4">
        <label htmlFor="filter" className="mr-2">Filter by status:</label>
        <select
          id="filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border rounded p-2"
        >
          <option value="all">All</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      <table className="min-w-full border-collapse border border-gray-300">
        <thead>
          <tr>
            <th className="border border-gray-300 p-2">Title</th>
            <th className="border border-gray-300 p-2">City</th>
            <th className="border border-gray-300 p-2">Status</th>
            <th className="border border-gray-300 p-2">Date</th>
            <th className="border border-gray-300 p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {signalements.map((signalement) => (
            <tr key={signalement.id}>
              <td className="border border-gray-300 p-2">{signalement.title}</td>
              <td className="border border-gray-300 p-2">{signalement.city}</td>
              <td className="border border-gray-300 p-2">
                <StatusBadge status={signalement.status} />
              </td>
              <td className="border border-gray-300 p-2">{new Date(signalement.createdAt).toLocaleDateString()}</td>
              <td className="border border-gray-300 p-2">
                <a href={`/signalements/${signalement.id}`} className="text-blue-600">View</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default SignalementsPage;
