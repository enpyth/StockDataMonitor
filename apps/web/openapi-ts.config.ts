import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: './openapi.json',
  output: './src/generated/client',
  plugins: ['@hey-api/client-fetch'],
})
