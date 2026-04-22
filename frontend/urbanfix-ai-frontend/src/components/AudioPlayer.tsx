import React, { useEffect, useRef } from 'react';

interface AudioPlayerProps {
  audioUrl: string;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl }) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.load();
    }
  }, [audioUrl]);

  return (
    <div className="flex flex-col items-center">
      <audio ref={audioRef} controls className="w-full">
        <source src={audioUrl} type="audio/wav" />
        Your browser does not support the audio element.
      </audio>
      <p className="mt-2 text-sm text-gray-600">Audio playback</p>
    </div>
  );
};

export default AudioPlayer;