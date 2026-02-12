# CloudNest Backend 🚀

**Deploy Anything. Instantly.**

CloudNest is a universal application hosting platform backend, similar to Koyeb, that allows users to deploy any type of application from Git repositories.

## Features

### ✨ Core Features
- **Universal App Deployment**: Deploy Telegram bots, Flask/FastAPI APIs, Node.js apps, static sites, and Docker containers
- **Automatic Detection**: Intelligently detects app type from repository contents
- **Dynamic Subdomains**: Each app gets a unique subdomain: `{app-name}-{username}.cloudnest.app`
- **Email Verification**: Secure user registration with email verification
- **Password Reset**: Complete forgot password functionality with email notifications

### 🔐 Authentication
- Email + Password authentication
- JWT token-based sessions
- Secure password hashing (bcrypt)
- Email verification required before login
- Password reset with time-limited tokens
- Email notifications for all account activities

### 🐳 Deployment System
- **Docker Support**: Build and run Dockerfile-based apps
- **Buildpack Detection**: Automatic detection for Node.js and Python apps
- **App Type Detection**:
  - `Dockerfile` → Docker build
  - `package.json` → Node.js app
  - `requirements.txt` / `app.py` → Python app
  - `bot.py` → Telegram bot
  - `index.html` → Static site

### 📡 API Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `GET /auth/verify/{token}` - Verify email address
- `POST /auth/login` - Login user
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token
- `GET /auth/me` - Get current user info

#### Applications
- `POST /apps/create` - Create and deploy new app
- `POST /apps/deploy` - Deploy/redeploy app
- `POST /apps/start` - Start stopped app
- `POST /apps/stop` - Stop running app
- `GET /apps/list` - List all user apps
- `GET /apps/{id}/status` - Get app status
- `GET /apps/{id}/logs` - View app logs
- `DELETE /apps/{id}` - Delete app

#### Health
- `GET /health` - System health check
- `GET /` - API information

## Installation

### Prerequisites
- Python 3.9+
- MongoDB
- Docker (for Docker-based deployments)
- SMTP server credentials (for emails)

### Quick Start

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd cloudnest-backend
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start MongoDB** (if not already running)
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or use your existing MongoDB instance
```

5. **Run the application**
```bash
python app.py
```

The API will be available at `http://localhost:8000`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key (CHANGE IN PRODUCTION) | `cloudnest-secret-key-change-in-production` |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `SMTP_HOST` | SMTP server host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username/email | `` |
| `SMTP_PASSWORD` | SMTP password/app password | `` |
| `DOMAIN` | Your domain name | `cloudnest.app` |
| `FRONTEND_URL` | Frontend URL for links | `http://localhost:3000` |
| `BASE_DEPLOY_PATH` | Path for app deployments | `/var/cloudnest/apps` |

### SMTP Setup (Gmail Example)

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Create a new app password for "Mail"
3. Use the generated password in `SMTP_PASSWORD`

## API Usage Examples

### Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "username": "johndoe"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

### Forgot Password
```bash
curl -X POST http://localhost:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### Reset Password
```bash
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset-token-from-email",
    "new_password": "newsecurepass123"
  }'
```

### Create App (requires authentication)
```bash
curl -X POST http://localhost:8000/apps/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "my-app",
    "git_url": "https://github.com/username/repo.git",
    "branch": "main",
    "env_vars": {
      "NODE_ENV": "production"
    }
  }'
```

### List Apps
```bash
curl -X GET http://localhost:8000/apps/list \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Database Models

### Users Collection
```javascript
{
  "_id": ObjectId,
  "email": String,
  "username": String,
  "password": String (hashed),
  "verified": Boolean,
  "verification_token": String (optional),
  "reset_token": String (optional),
  "reset_token_expires": DateTime (optional),
  "created_at": DateTime,
  "updated_at": DateTime
}
```

### Apps Collection
```javascript
{
  "_id": String,
  "name": String,
  "user_id": String,
  "git_url": String,
  "branch": String,
  "env_vars": Object,
  "subdomain": String,
  "status": String, // pending, building, running, stopped, failed
  "app_type": String, // docker, nodejs, python, telegram-bot, static
  "container": Object,
  "created_at": DateTime,
  "updated_at": DateTime,
  "deployed_at": DateTime
}
```

## Email Templates

CloudNest sends professional HTML emails for:
- ✅ Email verification
- 🔐 Password reset requests
- ✓ Password change confirmations

All emails are responsive and branded with CloudNest styling.

## Security Features

- **Password Hashing**: bcrypt with salt
- **JWT Tokens**: Secure token-based authentication
- **Email Verification**: Required before login
- **Password Reset**: Time-limited tokens (1 hour)
- **Rate Limiting**: Built into FastAPI
- **CORS**: Configured for cross-origin requests
- **Container Isolation**: Docker containers for app sandboxing

## Deployment

### VPS Deployment

1. **Install system dependencies**
```bash
sudo apt update
sudo apt install python3-pip docker.io mongodb
```

2. **Clone and setup**
```bash
git clone <your-repo>
cd cloudnest-backend
pip3 install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
nano .env  # Edit with production values
```

4. **Run with systemd** (production)
Create `/etc/systemd/system/cloudnest.service`:
```ini
[Unit]
Description=CloudNest Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/cloudnest
Environment="PATH=/usr/bin"
ExecStart=/usr/bin/python3 /var/www/cloudnest/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl enable cloudnest
sudo systemctl start cloudnest
```

### Docker Deployment
```bash
# Build image
docker build -t cloudnest-backend .

# Run container
docker run -d \
  -p 8000:8000 \
  -v /var/cloudnest/apps:/var/cloudnest/apps \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file .env \
  cloudnest-backend
```

## Nginx Reverse Proxy

Setup Nginx for production:

```nginx
server {
    listen 80;
    server_name api.cloudnest.app;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Wildcard subdomain for apps
server {
    listen 80;
    server_name *.cloudnest.app;

    location / {
        # Proxy to app containers based on subdomain
        # This requires additional configuration
        proxy_pass http://localhost:$app_port;
    }
}
```

## Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# Check connection
mongosh --eval "db.adminCommand('ping')"
```

### Docker Issues
```bash
# Check Docker service
sudo systemctl status docker

# Check Docker permissions
sudo usermod -aG docker $USER
```

### Email Not Sending
- Verify SMTP credentials
- Check SMTP_HOST and SMTP_PORT
- For Gmail, ensure App Password is used (not regular password)
- Check firewall rules for outbound SMTP connections

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Architecture

```
┌─────────────────┐
│   Frontend      │
│   (React/Vue)   │
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────┐
│   FastAPI       │
│   Backend       │
└────┬──────┬─────┘
     │      │
     │      └──────┐
     │             │
┌────▼─────┐  ┌───▼──────┐
│ MongoDB  │  │  Docker  │
│          │  │ Engine   │
└──────────┘  └──────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - feel free to use this for your projects!

## Support

For issues and questions:
- Create an issue on GitHub
- Email: support@cloudnest.app

---

**CloudNest** - Deploy Anything. Instantly. 🚀
