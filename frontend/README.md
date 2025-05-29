# 3D Photogrammetry Frontend

A modern Next.js application for uploading images and generating 3D models using photogrammetry. This frontend interfaces with a Flask backend that uses COLMAP for 3D reconstruction.

## Features

- **Drag & Drop File Upload**: Intuitive file upload with drag and drop support
- **Real-time Progress Tracking**: Live status updates during processing
- **Responsive Design**: Works on desktop and mobile devices
- **File Validation**: Client-side validation for image files and sizes
- **Download Management**: Easy download of generated 3D models
- **Error Handling**: Comprehensive error handling with user feedback
- **TypeScript**: Full type safety throughout the application

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety and better development experience
- **Tailwind CSS** - Utility-first CSS framework
- **React Hooks** - Custom hooks for state management
- **Fetch API** - HTTP client for backend communication

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Running Flask backend on `http://localhost:5000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

### Environment Variables

Create a `.env.local` file in the frontend directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_NAME=3D Photogrammetry
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_MAX_FILE_SIZE=16777216
NEXT_PUBLIC_MAX_FILES=50
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/          # React components
│   │   ├── FileUpload.tsx   # File upload component
│   │   ├── ProcessingStatus.tsx
│   │   ├── ResultsDisplay.tsx
│   │   └── Notification.tsx
│   ├── hooks/               # Custom React hooks
│   │   ├── usePhotogrammetry.ts
│   │   └── useNotification.ts
│   ├── lib/                 # Utility libraries
│   │   └── api.ts           # API client
│   └── types/               # TypeScript type definitions
│       └── index.ts
├── public/                  # Static assets
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── next.config.js
```

## API Integration

The frontend communicates with the Flask backend through a REST API:

### Key Endpoints

- `POST /upload` - Upload image files
- `POST /process` - Start 3D reconstruction
- `GET /status/{session_id}` - Get processing status
- `GET /download/{session_id}` - Download results
- `GET /health` - Health check

### API Client

The `ApiClient` class in `src/lib/api.ts` provides typed methods for all backend endpoints:

```typescript
import { apiClient } from '@/lib/api'

// Upload files
const response = await apiClient.uploadFiles(files)

// Start processing
await apiClient.startProcessing(sessionId, options)

// Get status
const status = await apiClient.getProcessingStatus(sessionId)
```

## Components

### FileUpload
- Drag and drop file upload
- File validation (type, size, count)
- Progress indicators
- Error handling

### ProcessingStatus
- Real-time status updates
- Progress visualization
- Processing time tracking
- Error display

### ResultsDisplay
- Download management
- File type icons
- Processing statistics
- Usage instructions

### Notification
- Toast notifications
- Multiple types (success, error, warning, info)
- Auto-dismiss functionality

## Custom Hooks

### usePhotogrammetry
Manages the entire photogrammetry workflow:
- File upload
- Processing status polling
- Result retrieval
- Error handling

### useNotification
Handles notification state and display:
- Show/hide notifications
- Auto-dismiss timers
- Multiple notification types

## Styling

The application uses Tailwind CSS with custom components defined in `globals.css`:

- `.btn-primary`, `.btn-secondary` - Button styles
- `.card` - Card container
- `.upload-area` - File upload area
- `.status-badge` - Status indicators
- `.notification` - Toast notifications

## File Upload Features

- **Drag & Drop**: Drag files directly onto the upload area
- **File Validation**: Only JPG, PNG images allowed
- **Size Limits**: 16MB per file, 50 files maximum
- **Progress Tracking**: Real-time upload progress
- **Error Handling**: Clear error messages for invalid files

## Processing Workflow

1. **Upload**: User uploads images via drag & drop or file selection
2. **Validation**: Client-side validation of file types and sizes
3. **Processing**: Backend processes images using COLMAP
4. **Monitoring**: Real-time status updates with polling
5. **Results**: Download generated 3D models and related files

## Development

### Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Type Safety

The application is fully typed with TypeScript:
- API response types in `src/types/index.ts`
- Component prop types
- Hook return types
- API client methods

## Deployment

### Build for Production

```bash
npm run build
npm start
```

### Environment Configuration

Update `.env.local` for your production environment:
- Set `NEXT_PUBLIC_API_URL` to your backend URL
- Adjust file size limits if needed

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow TypeScript best practices
2. Use Tailwind CSS for styling
3. Add proper error handling
4. Include type definitions
5. Test with the Flask backend

## Troubleshooting

### Common Issues

1. **Backend Connection**: Ensure Flask backend is running on port 5000
2. **CORS Errors**: Backend should have CORS enabled for localhost:3000
3. **File Upload Limits**: Check both frontend and backend size limits
4. **TypeScript Errors**: Run `npm run lint` to check for issues

### Debug Mode

Set environment variable for debugging:
```env
NODE_ENV=development
```

## License

MIT License - see LICENSE file for details