import React from 'react';
import './globals.css';

export const metadata = {
  title: 'UrbanFix AI',
  description: 'A platform for managing signalements',
};

const RootLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <html lang="fr">
      <body className="bg-accent text-gray-800">
        {children}
      </body>
    </html>
  );
};

export default RootLayout;