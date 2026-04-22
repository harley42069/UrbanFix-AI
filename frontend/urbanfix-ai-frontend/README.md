# UrbanFix AI Frontend

## Overview
UrbanFix AI is a web application designed to facilitate the reporting and processing of municipal issues through user-generated signalements. This frontend is built using Next.js with TypeScript, Tailwind CSS, and shadcn/ui components, providing a modern and professional interface.

## Features
- **Bilingual Support**: The application supports both Arabic and French, with French as the primary language.
- **User Authentication**: Secure login using JWT tokens.
- **Signalement Management**: Users can create, view, and manage signalements with detailed processing information.
- **Real-time Updates**: The application polls for updates on signalement processing status.
- **Media Generation**: Options to generate audio and PDF reports from signalements.

## Project Structure
```
urbanfix-ai-frontend
├── src
│   ├── app
│   │   ├── login
│   │   │   └── page.tsx
│   │   ├── dashboard
│   │   │   └── page.tsx
│   │   ├── signalements
│   │   │   ├── page.tsx
│   │   │   ├── new
│   │   │   │   └── page.tsx
│   │   │   └── [id]
│   │   │       └── page.tsx
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components
│   │   ├── ui
│   │   ├── StatusBadge.tsx
│   │   ├── ProgressPipeline.tsx
│   │   ├── ScenarioCard.tsx
│   │   ├── ImageUploader.tsx
│   │   └── AudioPlayer.tsx
│   ├── lib
│   │   └── api.ts
│   └── types
│       └── index.ts
├── public
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── next.config.js
└── README.md
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd urbanfix-ai-frontend
   ```
2. Install dependencies:
   ```
   npm install
   ```
3. Start the development server:
   ```
   npm run dev
   ```

## Usage
- Navigate to `/login` to authenticate.
- After logging in, you will be redirected to the `/dashboard` where you can view statistics and recent signalements.
- Use the `/signalements/new` page to create a new signalement.
- View details of each signalement at `/signalements/[id]`.

## API Integration
The frontend communicates with the UrbanFix AI backend running at `http://localhost:8000/api/v1`. Ensure the backend is running before using the frontend.

## Styling
The application uses Tailwind CSS for styling. Custom styles can be added in `src/app/globals.css`.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.