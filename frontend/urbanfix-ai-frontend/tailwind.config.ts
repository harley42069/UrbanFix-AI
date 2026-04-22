import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx}', 
    './public/index.html'
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1a5490',
        secondary: '#2c7bb6',
        accent: '#f0f4f8',
      },
    },
  },
  plugins: [],
};

export default config;