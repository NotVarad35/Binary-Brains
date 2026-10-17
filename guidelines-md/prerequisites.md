# Prerequisites & Environment Setup: Civic Fix Platform

This document outlines the required tools, dependencies, and environment configurations needed before an AI agent or developer begins implementing the **Civic Fix** platform.

---

## 1. System Requirements & Runtime Environment
Ensure the following base software and runtimes are installed on the local system or container environment:

- **Node.js**: `v18.x` or `v20.x` LTS
- **Package Manager**: `npm` (v9+) or `pnpm` (v8+)
- **Database**:
  - **PostgreSQL**: `v14+` with **PostGIS** extension enabled (for spatial geospatial queries like finding nearby issues and duplicate matching within radius $r$).
  - *Alternative (NoSQL)*: **MongoDB** `v6.0+` with 2DSphere indexing.
- **Docker & Docker Compose**: Optional but recommended for running local PostgreSQL/PostGIS services quickly.

---

## 2. API Keys & External Services

Before running or deploying the application, acquire keys for the following services:

1. **Map & Geocoding Provider**:
   - **Mapbox API Key** or **Google Maps Platform API Key** (for map rendering, reverse geocoding, and interactive pin placement).
2. **Object Storage**:
   - **AWS S3 Bucket** or **Cloudinary Account** (for storing citizen issue photos and field team proof-of-work images).
3. **Authentication Provider** *(if using third-party auth)*:
   - Auth0, Supabase Auth, or Firebase Auth credentials.

---

## 3. Environment Variables Template (`.env.example`)

Create a `.env` file in the project root with the following variables configured:

```env
# App Configuration
PORT=5000
NODE_ENV=development
CLIENT_URL=http://localhost:3000

# Database Connection
DATABASE_URL=postgresql://user:password@localhost:5432/civic_fix_db

# Authentication / Security
JWT_SECRET=your_super_secret_jwt_key
JWT_EXPIRES_IN=7d

# Geospatial Settings
MAX_DUPLICATE_RADIUS_METERS=50

# Object Storage (S3 / Cloudinary)
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET_NAME=civic-fix-attachments
AWS_REGION=us-east-1

# Maps & Location Services
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_public_token
```

---

## 4. Required Libraries & Dependencies

### 4.1 Backend Core Dependencies
- **HTTP Framework**: Express.js, Fastify, or NestJS
- **ORM / Database Client**: Prisma, TypeORM, or Drizzle ORM (configured with PostGIS support)
- **Authentication**: `jsonwebtoken`, `bcryptjs`
- **Validation**: `zod` or `joi` (for API request validation)
- **FileUpload**: `multer` + `@aws-sdk/client-s3` (or Cloudinary SDK)

### 4.2 Frontend Core Dependencies
- **Framework**: React / Next.js (TypeScript recommended)
- **UI & Styling**: Tailwind CSS, Lucide React (icons)
- **Map Library**: `react-map-gl`, `leaflet` + `react-leaflet`, or `@react-google-maps/api`
- **State & Data Fetching**: `@tanstack/react-query` (React Query) and `axios`

---

## 5. Pre-Flight Verification Checklist

Before starting task execution, the agent must verify:
- [ ] Database service is active and accessible via `DATABASE_URL`.
- [ ] Spatial extensions (e.g., `CREATE EXTENSION IF NOT EXISTS postgis;`) are initialized in the database.
- [ ] Environment variables are loaded and validated.
- [ ] Storage bucket permissions permit uploading citizen image attachments.