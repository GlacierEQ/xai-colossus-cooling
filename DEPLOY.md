# 🚀 Vercel Dashboard Deploy

## One-Click (recommended)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/GlacierEQ/xai-colossus-cooling&root=dashboard)

## Manual Steps

1. **Make repo public** (GitHub Settings > Danger Zone > Change visibility)

2. **Import to Vercel**
   - Go to https://vercel.com/new
   - Import `GlacierEQ/xai-colossus-cooling`
   - Root directory: `dashboard`
   - Framework: **Next.js** (auto-detected)

3. **Set Environment Variables** (Vercel Dashboard > Settings > Environment Variables)
   ```
   COLOSSUS_API_URL   = https://your-colossus-api.com
   COLOSSUS_API_KEY   = your-key
   MASTERMIND_URL     = https://your-mastermind-api.com
   ```

4. **Deploy** — Dashboard will be live at `https://xai-colossus-cooling.vercel.app`

## Features
- 🔥 Live thermal zone grid (3s refresh)
- ⚡ Piston flow rate bars (real-time)
- 🧠 MORPHEUS RL decision log (5s refresh)
- 🟢 Online/offline status indicator
- 🎙️ Graceful mock data fallback if Colossus API unreachable
- 🎨 Full dark-mode APEX design system

## Local Dev
```bash
cd dashboard
npm install
npm run dev
# http://localhost:3000
```
