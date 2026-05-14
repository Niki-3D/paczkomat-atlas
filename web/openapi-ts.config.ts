import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: 'http://localhost:8080/openapi.json',
  output: {
    path: 'lib/api',
    format: 'prettier',
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/typescript',
    '@hey-api/sdk',
    '@hey-api/schemas',
  ],
})
