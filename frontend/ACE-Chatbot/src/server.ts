// server.ts
import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';

import express from 'express';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Resolve paths to dist folders
const serverDistFolder = dirname(fileURLToPath(import.meta.url));
const browserDistFolder = resolve(serverDistFolder, '../browser');

// Create Express app and Angular engine
const app = express();
const angularApp = new AngularNodeAppEngine();

// ✅ STEP 1: Fix CSP headers to allow loading favicon, images, scripts, etc.
app.use((req, res, next) => {
  res.setHeader(
  'Content-Security-Policy',
  "default-src 'self'; connect-src 'self' http://localhost:8000; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self';"
);

  next();
});

// ✅ STEP 2: Serve static assets from browser dist
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  })
);

// ✅ STEP 3: SSR fallback for all other routes
app.use('/**', (req, res, next) => {
  angularApp
    .handle(req)
    .then((response) => {
      if (response) {
        writeResponseToNodeResponse(response, res);
      } else {
        next();
      }
    })
    .catch(next);
});

// ✅ STEP 4: Start server in local dev / prod
if (isMainModule(import.meta.url)) {
  const port = process.env['PORT'] || 4000;
  app.listen(port, () => {
    console.log(`✅ Angular SSR server listening at http://localhost:${port}`);
  });
}

// ✅ STEP 5: Export handler for Angular CLI/Vite SSR usage
export const reqHandler = createNodeRequestHandler(app);
