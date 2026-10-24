# Sharing Sulvana with Friends on Vercel

This setup allows your friend to use the **Sulvana 2.0 interface on Vercel** (on their phone, tablet, or PC) while the AI model (MiMo-V2.6 9B on RTX 5070) runs on your laptop.

---

## How It Works

```
┌─────────────────────────────────┐         Cloudflare Tunnel
│   Friend's Browser (Vercel)     │ ──────────────────────────────┐
│   https://sulvana.vercel.app    │  (Direct SSE token streaming) │
└─────────────────────────────────┘                               │
                                                                  ▼
                                                      ┌───────────────────────┐
                                                      │  Your Laptop (Local)  │
                                                      │  • RTX 5070 (9B GPU)  │
                                                      │  • Cloudflare Tunnel  │
                                                      │  • Sulvana Web (8766) │
                                                      └───────────────────────┘
```

- **No Public IP or Port Forwarding Needed**: Uses Cloudflare Quick Tunnels (`trycloudflare.com`) from your laptop.
- **No Vercel Timeouts**: The Vercel app acts as a fast client-side frontend that connects directly to your laptop tunnel. Streaming tokens flow without hitting Vercel's 10s–60s serverless function execution limits.
- **Protected Security**:
  - All remote requests require an **Access Key**. Unauthorized visitors cannot use your GPU.
  - Remote users are **forbidden (403)** from executing coding mode, approvals, file edits, or terminal commands on your laptop.

---

## Watching who is using it

Run `./share-logs.sh` in another terminal to see every request live: yours marked `local`, your friends' marked
`friend` with their IP address and country, plus the tunnel's own messages, and for chats the message and the start of the reply. `--all` also
shows the status checks the app makes every few seconds.

## Step 1: Deploy Frontend to Vercel (One-Time Setup)

You only need to deploy the frontend to Vercel once.

### Option A: Via Vercel CLI (Fastest)

Run this in your terminal:

```bash
cd sulvana-ui
vercel
```

- Follow the prompts (press Enter to accept default settings).
- To deploy to production:
```bash
vercel --prod
```
- Copy your deployed URL (e.g., `https://sulvana-ui-yourname.vercel.app`).

### Option B: Via GitHub

1. Push your repository to GitHub.
2. Go to [vercel.com/new](https://vercel.com/new).
3. Import your repository.
4. Set **Root Directory** to `sulvana-ui`.
5. Click **Deploy**.

---

## Step 2: Share with Your Friend

Whenever you want to let your friend use Sulvana from your laptop:

```bash
./share.sh https://your-deployed-app.vercel.app
```

The script will:
1. Start the Sulvana web server on your laptop if it isn't running.
2. Open a secure Cloudflare tunnel.
3. Print a single **Friend Invite Link** like this:
   ```
   https://your-deployed-app.vercel.app/?tunnel=https://random-name.trycloudflare.com&key=sk-sulvana-xxxxx
   ```

### Sending the Link
Send that link to your friend on Telegram, Discord, or WhatsApp.

- When your friend clicks the link, Sulvana automatically configures the tunnel and access key in their browser and cleans the address bar.
- They can start chatting, generating images, searching the web, and thinking with reasoning immediately!
- When you are done, press `Ctrl+C` in your terminal to shut down the tunnel.
