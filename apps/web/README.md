# Property Assessment Web Application

A modern, production-ready Next.js 14 application for property assessment and evaluation.

## Features

- **Next.js 14** with App Router and TypeScript
- **Tailwind CSS** for styling with custom design system
- **MapLibre GL** for interactive maps
- **TanStack Query** for efficient data fetching
- **NextAuth.js** for authentication
- **React Hook Form** with Zod validation
- **Responsive design** with mobile-first approach
- **Dark mode** support
- **SEO optimized** with proper meta tags

## Getting Started

### Prerequisites

- Node.js 18.17.0 or later
- pnpm 8.0.0 or later

### Installation

1. Install dependencies:
```bash
pnpm install
```

2. Set up environment variables:
```bash
cp .env.local.example .env.local
```

Edit `.env.local` with your actual values.

3. Start the development server:
```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint
- `pnpm lint:fix` - Fix ESLint issues
- `pnpm type-check` - Run TypeScript type checking
- `pnpm test` - Run tests
- `pnpm test:watch` - Run tests in watch mode
- `pnpm test:coverage` - Run tests with coverage

## Project Structure

```
apps/web/
├── app/                    # Next.js App Router
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   └── providers.tsx      # React providers
├── src/
│   ├── components/        # Reusable components
│   │   ├── ui/           # UI components
│   │   └── theme-provider.tsx
│   ├── lib/              # Utility functions
│   │   └── utils.ts
│   └── types/            # TypeScript type definitions
│       └── index.ts
├── public/               # Static assets
├── next.config.js        # Next.js configuration
├── tailwind.config.ts    # Tailwind CSS configuration
├── tsconfig.json         # TypeScript configuration
└── package.json          # Dependencies and scripts
```

## Configuration

### Environment Variables

Copy `.env.local.example` to `.env.local` and configure:

- **Database**: PostgreSQL connection string
- **Authentication**: NextAuth configuration and OAuth providers
- **Maps**: Mapbox or Google Maps API keys
- **External Services**: Redis, SMTP, monitoring services

### Tailwind CSS

The application uses a custom design system built with Tailwind CSS:

- Custom color palette with CSS variables
- Dark mode support
- Responsive utilities
- Animation classes
- Component variants with `class-variance-authority`

### TypeScript

Strict TypeScript configuration with:

- Absolute imports using `@/` prefix
- Type checking for all files
- Path mapping for clean imports

## Architecture

### State Management

- **TanStack Query** for server state management
- **React Context** for app-wide state
- **React Hook Form** for form state

### Authentication

- **NextAuth.js** with multiple providers
- JWT tokens for session management
- Role-based access control

### Data Fetching

- **TanStack Query** for caching and synchronization
- Optimistic updates
- Error handling and retry logic
- Background refetching

### Styling

- **Tailwind CSS** utility-first approach
- **CSS Variables** for theming
- **Responsive design** patterns
- **Component composition** with variants

## Development Guidelines

### Code Style

- Use TypeScript for type safety
- Follow ESLint and Prettier configurations
- Use absolute imports with `@/` prefix
- Implement proper error boundaries

### Component Structure

- Keep components small and focused
- Use composition over inheritance
- Implement proper prop types
- Add JSDoc comments for complex components

### Performance

- Use Next.js Image component for optimized images
- Implement proper code splitting
- Use React.memo for expensive components
- Optimize bundle size with dynamic imports

### Testing

- Unit tests with Jest and Testing Library
- Component testing for UI components
- Integration tests for critical flows
- E2E tests for user journeys

## Deployment

### Production Build

```bash
pnpm build
pnpm start
```

### Docker

```bash
docker build -t property-assessment-web .
docker run -p 3000:3000 property-assessment-web
```

### Environment Setup

Ensure all environment variables are properly configured for production:

- Set `NODE_ENV=production`
- Configure database connections
- Set up monitoring and logging
- Configure CDN for static assets

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Run linting and type checking
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.