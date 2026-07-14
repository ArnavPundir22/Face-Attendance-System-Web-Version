# 🌍 Production Deployment

Because this application relies on Supabase `pgvector` for its data storage, it is entirely **stateless**. This means you do not have to worry about managing complex Docker volumes or persistent storage drives just to save student photos! 

You can host this application practically anywhere that supports Python.

## 1. Hardware Requirements
Machine learning inference requires memory. Regardless of where you deploy this application, ensure your environment has at least:
- **2GB of RAM** (1GB will crash with Out Of Memory errors when InsightFace attempts to load the model).
- **1 vCPU** (2+ recommended for faster photo processing).

## 2. Virtual Private Server (VPS)
Hosting on a standard VPS (like DigitalOcean, AWS EC2, Linode, or Hetzner) is the most traditional approach.

1. Provision an Ubuntu 22.04+ server.
2. Clone your repository onto the server.
3. Set up your Python virtual environment and `.env` file just like in the [Local Setup Guide](./SETUP.md).
4. Run the application using **Gunicorn**:

```bash
# -w 1 ensures only one worker is created to conserve RAM
# -t 120 gives the model plenty of time to process large group photos
# -b binds it to a local port
gunicorn -w 1 -t 120 -b 127.0.0.1:5000 app:app
```

5. Set up **Nginx** as a reverse proxy to route port 80/443 traffic securely to `127.0.0.1:5000`. An example Nginx configuration is provided in the `nginx/` folder of this repository.

## 3. Platform as a Service (PaaS)
Because the app is stateless, deploying to modern platforms like **Render.com** or **Railway** is incredibly straightforward.

### Render.com Instructions
1. Connect your GitHub repository to Render.
2. Create a new **Web Service**.
3. Set the Environment to **Python**.
4. **Build Command**: 
   ```bash
   pip install -r requirements.txt
   ```
5. **Start Command**:
   ```bash
   gunicorn -w 1 -t 120 -b 0.0.0.0:$PORT app:app
   ```
6. Add your Supabase credentials to Render's **Environment Variables** settings.
7. Deploy!

> [!WARNING]  
> If you deploy to Vercel (using serverless functions), ensure the function timeout is set high enough (e.g., 60 seconds) to allow the InsightFace model to download and load into memory on a cold start. However, a dedicated container (Render/Railway) is highly recommended over Serverless.
