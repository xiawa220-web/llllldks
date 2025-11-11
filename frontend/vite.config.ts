import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages 部署需要设置 base 为仓库名子路径
// 本地开发不受影响（通过环境变量可覆盖）
const repoBase = '/llllldks/'

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || repoBase,
  server: {
    port: 5173,
  }
})