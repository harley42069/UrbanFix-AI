import React, { useEffect, useState } from 'react';
import { fetchSignalements } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import Link from 'next/link';

const DashboardPage = () => {
  const [signalements, setSignalements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadSignalements = async () => {
      try {
        const data = await fetchSignalements();
        setSignalements(data);
      } catch (err) {
        setError('Failed to load signalements');
      } finally {
        setLoading(false);
      }
    };

    loadSignalements();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <div className="bg-primary text-white p-4 rounded-lg">
          <h2>Total Signalements</h2>
          <p>{signalements.length}</p>
        </div>
        <div className="bg-secondary text-white p-4 rounded-lg">
          <h2>Processing</h2>
          <p>{signalements.filter(s => s.status === 'processing').length}</p>
        </div>
        <div className="bg-accent text-white p-4 rounded-lg">
          <h2>Completed</h2>
          <p>{signalements.filter(s => s.status === 'completed').length}</p>
        </div>
        <div className="bg-red-600 text-white p-4 rounded-lg">
          <h2>Failed</h2>
          <p>{signalements.filter(s => s.status === 'failed').length}</p>
        </div>
      </div>
      <h2 className="text-xl font-bold mb-2">Recent Signalements</h2>
      <table className="min-w-full bg-white border border-gray-300">
        <thead>
          <tr>
            <th className="border-b p-2">Title</th>
            <th className="border-b p-2">City</th>
            <th className="border-b p-2">Status</th>
            <th className="border-b p-2">Date</th>
            <th className="border-b p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {signalements.map(signalement => (
            <tr key={signalement.id}>
              <td className="border-b p-2">{signalement.title}</td>
              <td className="border-b p-2">{signalement.city}</td>
              <td className="border-b p-2">
                <StatusBadge status={signalement.status} />
              </td>
              <td className="border-b p-2">{new Date(signalement.createdAt).toLocaleDateString()}</td>
              <td className="border-b p-2">
                <Link href={`/signalements/${signalement.id}`} className="text-blue-500">View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Link href="/signalements/new" className="mt-4 inline-block bg-primary text-white py-2 px-4 rounded">
        Nouveau Signalement
      </Link>
    </div>
  );
};

export default DashboardPage;