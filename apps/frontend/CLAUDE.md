# Claude Code Memory - Infrastructor Frontend

Essential instructions for working on the Infrastructor frontend application.

## 🎨 Frontend Stack

- **Framework**: React 19.1.1 + TypeScript 5.9.2
- **Build**: Vite 7.1.0 (dev server on port 5173)
- **Styling**: Tailwind CSS v4.1.11 with @tailwindcss/vite plugin
- **Components**: shadcn/ui with Radix UI
- **State**: Zustand 5.0.2
- **Routing**: React Router v7.1.1
- **API**: Axios 1.7.9 + WebSocket hooks
- **Forms**: React Hook Form + Zod
- **Charts**: Recharts 2.15.0
- **Types**: @infrastructor/shared-types package

## 📁 Project Structure

```
apps/frontend/
├── src/
│   ├── components/
│   │   ├── ui/          # shadcn/ui components
│   │   ├── dashboard/   # Dashboard components
│   │   └── [feature]/   # Feature-specific components
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utilities (api.ts, cn.ts)
│   ├── pages/           # Route pages
│   ├── stores/          # Zustand stores
│   ├── styles/          # Global styles
│   └── types/           # Local TypeScript types
├── public/              # Static assets
└── [config files]       # vite.config.ts, tailwind.config.ts, etc.
```

## 💻 Essential Commands

```bash
npm run dev              # Start dev server (port 5173)
npm run build           # Build for production
npm run preview         # Preview production build
npm run lint            # Run ESLint
npm run type-check      # TypeScript check

npx shadcn@latest add [component]  # Add shadcn/ui component
```

## 🔌 API Integration

### Axios Setup (`lib/api.ts`)
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Error interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### WebSocket Hook (`hooks/useWebSocket.ts`)
```typescript
export function useWebSocket(url: string) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  
  useEffect(() => {
    const ws = new WebSocket(url);
    ws.onopen = () => setStatus('connected');
    ws.onmessage = (event) => setData(JSON.parse(event.data));
    ws.onclose = () => setStatus('disconnected');
    return () => ws.close();
  }, [url]);
  
  return { data, status };
}
```

## 🗂️ State Management (Zustand)

```typescript
// stores/deviceStore.ts
import { create } from 'zustand';
import type { DeviceResponse } from '@infrastructor/shared-types';

interface DeviceStore {
  devices: DeviceResponse[];
  loading: boolean;
  error: string | null;
  fetchDevices: () => Promise<void>;
  selectDevice: (device: DeviceResponse) => void;
}

export const useDeviceStore = create<DeviceStore>()((set) => ({
  devices: [],
  loading: false,
  error: null,
  
  fetchDevices: async () => {
    set({ loading: true });
    try {
      const { data } = await api.get('/devices');
      set({ devices: data.items, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  selectDevice: (device) => set({ selectedDevice: device }),
}));
```

## 🎨 Component Patterns

### shadcn/ui Usage
```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { DeviceResponse } from '@infrastructor/shared-types';

interface DeviceCardProps {
  device: DeviceResponse;
  className?: string;
}

export function DeviceCard({ device, className }: DeviceCardProps) {
  return (
    <Card className={cn("hover:shadow-lg transition-shadow", className)}>
      <CardHeader>
        <CardTitle>{device.hostname}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>Status: {device.status}</p>
      </CardContent>
    </Card>
  );
}
```

### Form with React Hook Form + Zod
```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const schema = z.object({
  hostname: z.string().min(1, 'Required'),
  ip_address: z.string().ip('Invalid IP'),
});

export function DeviceForm() {
  const form = useForm({
    resolver: zodResolver(schema),
  });
  
  const onSubmit = async (data) => {
    await api.post('/devices', data);
  };
  
  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <Input {...form.register('hostname')} />
      <Button type="submit">Add Device</Button>
    </form>
  );
}
```

## 📦 Shared Types

**ALWAYS** import types from the shared package:
```typescript
// ✅ Correct
import type { 
  DeviceResponse, 
  ContainerResponse,
  SystemMetricResponse 
} from '@infrastructor/shared-types';

// ❌ Wrong - Don't redefine existing types
interface Device { 
  id: string;
  hostname: string;
}
```

## 🎯 Key Guidelines

### Styling
- Use Tailwind CSS classes with `cn()` utility for conditionals
- Mobile-first responsive design (`sm:`, `md:`, `lg:`, `xl:`)
- Follow shadcn/ui component patterns

### Performance
- Use `memo` for expensive components
- Use `useMemo` for expensive computations
- Use `useCallback` for stable function references
- Implement code splitting with `lazy()` for routes

### Error Handling
- Wrap critical sections in ErrorBoundary components
- Handle API errors with try/catch
- Show user-friendly error messages
- Log errors to console in development only

### Security
- Never use `dangerouslySetInnerHTML` unless necessary
- Store auth tokens securely
- Always validate user input
- Use HTTPS in production

## 🚀 Development Workflow

1. **Start the backend first**:
   ```bash
   cd /home/jmagar/code/infrastructor
   ./dev.sh start
   ```

2. **Start frontend dev server**:
   ```bash
   cd apps/frontend
   npm run dev
   ```

3. **API Proxy**: Vite proxies `/api` → `http://localhost:9101`

4. **WebSocket**: Connect to `ws://localhost:9101/ws/stream`

## 📝 Before Committing

- [ ] TypeScript compiles: `npm run type-check`
- [ ] Linting passes: `npm run lint`
- [ ] No console.log in production code
- [ ] Types imported from @infrastructor/shared-types
- [ ] Responsive design tested
- [ ] WebSocket connections cleaned up
- [ ] Error boundaries in place

## 🎯 Current Priorities

1. Complete dashboard with real-time metrics
2. Device management CRUD interface
3. Container management UI
4. Proxy configuration editor
5. ZFS management interface
6. Real-time notifications
7. Authentication flow
8. Settings page

*Keep this file updated as the frontend evolves.*