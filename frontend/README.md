# Frontend — S.A.M.V.A. Platform

App Nuxt 4 con Nuxt UI v4 y TailwindCSS 4.

## Comandos

```bash
npm install        # Instalar dependencias
npm run dev        # Servidor dev en http://localhost:3000
npm run build      # Build producción
npm run generate   # Generación estática
npm run preview    # Preview de build
npm run typecheck  # TypeScript type-check
```

## Estructura

```
app/               # Código Vue
├── pages/         # Rutas (/, /login, /dashboard)
├── layouts/       # Layouts (default, login, dashboard)
├── components/    # Componentes Vue
├── composables/   # Composables (useAuth, cms/)
└── middleware/    # Route middleware (auth.ts — stub)
shared/            # Tipos y utilidades compartidas (alias #shared/)
server/            # Rutas Nitro API server
```

## Notas

- El alias `#shared/` mapea a `shared/` (ej: `import type { LandingData } from '#shared/types/cms/landing'`).
- La autenticación es un stub — `app/middleware/auth.ts` redirige siempre a `/login`.
- `npm run typecheck` requiere el directorio `.nuxt/` (generado automáticamente en `postinstall`).
