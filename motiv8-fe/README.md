# Motiv8 Frontend

React + TypeScript frontend built with Vite.

## Tech Stack

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool with HMR
- **Axios** - HTTP client
- **ESLint** - Code linting

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```
   App will be available at http://localhost:5173

## Available Scripts

- `npm run dev` - Start development server with HMR
- `npm run build` - Type check and build for production
- `npm run lint` - Lint TypeScript files with ESLint
- `npm run preview` - Preview production build locally

## Project Structure

```
src/
├── main.tsx          # Application entry point
├── App.tsx           # Main App component
├── App.css           # App component styles
├── index.css         # Global styles
├── vite-env.d.ts     # Vite type definitions
├── components/       # Reusable components
└── assets/           # Static assets
```

## Development

The app currently shows a simple TODO placeholder page. Ready for further development!

## Building for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.
