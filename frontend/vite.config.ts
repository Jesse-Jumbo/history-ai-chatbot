import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // 允許從外部訪問
    port: 3000,
    open: false  // 遠端部署時不自動打開瀏覽器
  }
})

