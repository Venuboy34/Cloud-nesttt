# CloudNest VPS Deployment Guide 🚀

This guide will walk you through deploying CloudNest on a VPS (Ubuntu/Debian).

## Prerequisites

- VPS with Ubuntu 20.04+ or Debian 11+
- Root or sudo access
- Domain name pointing to your VPS (e.g., cloudnest.app)
- At least 2GB RAM and 20GB storage

## Step 1: Initial VPS Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx docker.io mongodb

# Enable and start services
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl enable mongodb
sudo systemctl start mongodb
sudo systemctl enable nginx
sudo systemctl start nginx

# Add current user to docker group
sudo usermod -aG docker $USER
```

Log out and log back in for group changes to take effect.

## Step 2: Clone CloudNest

```bash
# Create directory
sudo mkdir -p /var/www/cloudnest
sudo chown -R $USER:$USER /var/www/cloudnest

# Clone repository
cd /var/www/cloudnest
git clone <your-repo-url> .

# Or upload files manually
```

## Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

Configure these important variables:
```bash
SECRET_KEY=your-very-secret-random-key-here
MONGODB_URL=mongodb://localhost:27017
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
DOMAIN=cloudnest.app
FRONTEND_URL=https://cloudnest.app
BASE_DEPLOY_PATH=/var/cloudnest/apps
```

## Step 4: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 5: Test the Application

```bash
# Run the app
python app.py

# Test in another terminal
curl http://localhost:8000/health
```

If it works, proceed to production setup.

## Step 6: Setup Systemd Service

```bash
# Copy service file
sudo cp cloudnest.service /etc/systemd/system/

# Edit service file if needed
sudo nano /etc/systemd/system/cloudnest.service

# Update paths if you used virtualenv:
# ExecStart=/var/www/cloudnest/venv/bin/python /var/www/cloudnest/app.py

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable cloudnest
sudo systemctl start cloudnest

# Check status
sudo systemctl status cloudnest

# View logs
sudo journalctl -u cloudnest -f
```

## Step 7: Configure Nginx

```bash
# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/cloudnest

# Create symbolic link
sudo ln -s /etc/nginx/sites-available/cloudnest /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 8: Setup SSL with Let's Encrypt

```bash
# Obtain SSL certificate
sudo certbot --nginx -d api.cloudnest.app -d cloudnest.app -d *.cloudnest.app

# Certbot will automatically configure SSL in nginx

# Test auto-renewal
sudo certbot renew --dry-run
```

Note: For wildcard certificates (*.cloudnest.app), you'll need DNS validation:
```bash
sudo certbot certonly --manual --preferred-challenges dns -d "*.cloudnest.app" -d cloudnest.app
```

## Step 9: Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Check status
sudo ufw status
```

## Step 10: Setup MongoDB (Optional: Authentication)

```bash
# Connect to MongoDB
mongosh

# Create admin user
use admin
db.createUser({
  user: "cloudnest_admin",
  pwd: "strong_password_here",
  roles: ["userAdminAnyDatabase", "readWriteAnyDatabase"]
})

# Exit mongosh
exit

# Enable authentication
sudo nano /etc/mongod.conf

# Add these lines:
# security:
#   authorization: enabled

# Restart MongoDB
sudo systemctl restart mongodb

# Update MONGODB_URL in .env:
# MONGODB_URL=mongodb://cloudnest_admin:strong_password_here@localhost:27017/cloudnest?authSource=admin
```

## Step 11: Setup Email (Gmail Example)

1. Enable 2-Factor Authentication on your Google account
2. Generate App Password:
   - Google Account → Security → 2-Step Verification → App passwords
   - Create password for "Mail"
3. Use in `.env`:
   ```bash
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=generated-app-password
   ```

## Step 12: Test Deployment

```bash
# Check API
curl https://api.cloudnest.app/health

# Test registration
curl -X POST https://api.cloudnest.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "username": "testuser"
  }'
```

## Monitoring & Maintenance

### View Logs
```bash
# Application logs
sudo journalctl -u cloudnest -f

# Nginx access logs
sudo tail -f /var/log/nginx/cloudnest-api-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/cloudnest-api-error.log
```

### Restart Services
```bash
# Restart CloudNest
sudo systemctl restart cloudnest

# Restart Nginx
sudo systemctl restart nginx

# Restart MongoDB
sudo systemctl restart mongodb
```

### Update Application
```bash
cd /var/www/cloudnest
git pull
sudo systemctl restart cloudnest
```

### Backup MongoDB
```bash
# Create backup
mongodump --out=/var/backups/mongodb/$(date +%Y%m%d)

# Restore backup
mongorestore /var/backups/mongodb/20240101
```

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u cloudnest -n 50

# Check if port is in use
sudo lsof -i :8000

# Check environment variables
sudo systemctl show cloudnest --property=Environment
```

### MongoDB connection issues
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# Check connection
mongosh --eval "db.adminCommand('ping')"

# Check logs
sudo tail -f /var/log/mongodb/mongod.log
```

### Docker issues
```bash
# Check Docker service
sudo systemctl status docker

# Check Docker logs
sudo journalctl -u docker -n 50

# Test Docker
docker run hello-world
```

### Nginx issues
```bash
# Test configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log

# Check if nginx is running
sudo systemctl status nginx
```

## Security Checklist

- ✅ Change SECRET_KEY to a random string
- ✅ Use strong passwords for MongoDB
- ✅ Enable firewall (UFW)
- ✅ Setup SSL certificates
- ✅ Configure SMTP with app passwords (not main password)
- ✅ Regular updates: `sudo apt update && sudo apt upgrade`
- ✅ Monitor logs regularly
- ✅ Backup MongoDB regularly
- ✅ Limit MongoDB access to localhost only

## Performance Optimization

### Add Swap Space (if needed)
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Optimize MongoDB
```bash
# Edit mongod.conf
sudo nano /etc/mongod.conf

# Add:
# storage:
#   wiredTiger:
#     engineConfig:
#       cacheSizeGB: 1
```

## Support

If you encounter issues:
1. Check logs: `sudo journalctl -u cloudnest -n 100`
2. Verify all services are running
3. Check firewall rules
4. Ensure domain DNS is properly configured

---

**Congratulations! Your CloudNest backend is now deployed! 🎉**
