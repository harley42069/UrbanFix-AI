"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ImageUploader from '@/components/ImageUploader';
import { createSignalement, processSignalement } from '@/lib/api';

const NewSignalementPage = () => {
  const router = useRouter();
  const [image, setImage] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [city, setCity] = useState('');
  const [region, setRegion] = useState('');
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [generateAudio, setGenerateAudio] = useState(false);
  const [generatePDF, setGeneratePDF] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!image || !title || !description || !city || !region) {
      setError('Please fill in all fields and upload an image.');
      return;
    }

    setLoading(true);
    try {
      const signalementId = await createSignalement({
        image,
        title,
        description,
        city,
        region,
        latitude,
        longitude,
      });

      if (generateAudio || generatePDF) {
        await processSignalement(signalementId, { generate_audio: generateAudio, generate_pdf: generatePDF });
      }

      router.push(`/signalements/${signalementId}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error creating report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGeolocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((position) => {
        setLatitude(position.coords.latitude);
        setLongitude(position.coords.longitude);
      });
    } else {
      setError('Geolocation is not supported by this browser.');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">New Report</h1>
      {error && <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <ImageUploader onImageUpload={setImage} />
        <input
          type="text"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="border p-2 w-full"
          required
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="border p-2 w-full"
          required
        />
        <input
          type="text"
          placeholder="City"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="border p-2 w-full"
          required
        />
        <input
          type="text"
          placeholder="Region"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          className="border p-2 w-full"
          required
        />
        <button type="button" onClick={handleGeolocation} className="bg-blue-500 text-white p-2">
          Detect location automatically
        </button>
        <div className="flex items-center">
          <input
            type="checkbox"
            checked={generateAudio}
            onChange={(e) => setGenerateAudio(e.target.checked)}
          />
          <label className="ml-2">Generate Audio</label>
        </div>
        <div className="flex items-center">
          <input
            type="checkbox"
            checked={generatePDF}
            onChange={(e) => setGeneratePDF(e.target.checked)}
          />
          <label className="ml-2">Generate PDF</label>
        </div>
        <button type="submit" className="bg-blue-600 text-white p-2" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit'}
        </button>
      </form>
    </div>
  );
};

export default NewSignalementPage;
