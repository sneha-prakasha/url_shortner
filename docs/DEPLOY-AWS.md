# Deploy snip. on AWS EC2 (step by step)

You will run the same `docker compose` setup on one Linux server in the cloud. This guide uses the AWS website (console), no AWS CLI needed.

> **Check before you start:** AWS free-tier rules change, so look at the current free-tier page and the pricing of the instance type you choose. A `t3.small` or `t3.micro` is enough for this project. Set a billing alert first (Step 0) and **stop or terminate the instance when you are not using it**.

## Step 0 – Safety first: billing alert

1. AWS Console -> top-right account menu -> **Billing and Cost Management**.
2. **Budgets** -> **Create budget** -> "Zero spend" or a small monthly budget (e.g. $5) -> add your email.

## Step 1 – Push the code to GitHub

On your laptop, inside the project folder:

```bash
git init
git add .
git commit -m "snip url shortener"
git branch -M main
git remote add origin https://github.com/<your-username>/snip.git
git push -u origin main
```

`.env` is in `.gitignore`, so your passwords are not uploaded. Never commit it.

## Step 2 – Launch the EC2 server

1. Console -> **EC2** -> **Launch instance**.
2. **Name:** `snip-server`
3. **AMI:** *Ubuntu Server 24.04 LTS*.
4. **Instance type:** `t3.small` (2 GB RAM). If you pick a 1 GB type, add swap in Step 4 or the MySQL container may be killed.
5. **Key pair:** *Create new key pair* -> name `snip-key`, type RSA, format `.pem` -> it downloads. **Keep this file safe**, you cannot download it again.
6. **Network settings -> Edit -> Security group** (this is the firewall). Add 3 inbound rules:

   | Type | Port | Source |
   |---|---|---|
   | SSH | 22 | **My IP** (not anywhere) |
   | HTTP | 80 | Anywhere (0.0.0.0/0) |
   | HTTPS | 443 | Anywhere (only needed if you add a domain later) |

   Do **not** open ports 3306 (MySQL) or 6379 (Redis). They are private inside Docker.
7. **Storage:** 20 GB gp3.
8. **Launch instance**.

## Step 3 – Give it a fixed address (Elastic IP)

Without this the public IP changes every time the instance restarts.

1. EC2 -> **Elastic IPs** -> **Allocate Elastic IP address** -> Allocate.
2. Select it -> **Actions -> Associate Elastic IP address** -> choose `snip-server` -> Associate.
3. Write down this IP. Below it is `YOUR_IP`.

> An Elastic IP that is allocated but not attached to a running instance can be charged. Release it when you delete the project.

## Step 4 – Connect and install Docker

On your laptop (Mac/Linux terminal, or PowerShell on Windows):

```bash
chmod 400 snip-key.pem                      # Mac/Linux only
ssh -i snip-key.pem ubuntu@YOUR_IP
```

Then on the server:

```bash
# Install Docker from Docker's official repository
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Let the ubuntu user run docker without sudo, then log out and back in
sudo usermod -aG docker ubuntu
exit
```

Reconnect (`ssh -i snip-key.pem ubuntu@YOUR_IP`) and test:

```bash
docker run --rm hello-world
docker compose version
```

**Only if you chose a 1 GB instance**, add swap:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Step 5 – Get the code and configure it

```bash
git clone https://github.com/<your-username>/snip.git
cd snip
cp .env.example .env
nano .env
```

Change these in `.env`:

```
MYSQL_ROOT_PASSWORD=<a long random password>
MYSQL_PASSWORD=<another long random password>
SECRET_KEY=<paste the output of:  openssl rand -hex 32>
BASE_URL=http://YOUR_IP
WEB_PORT=80
```

Save in nano with `Ctrl+O`, `Enter`, `Ctrl+X`.

`BASE_URL` matters: every short link is built from it. `WEB_PORT=80` makes the site reachable without typing a port.

## Step 6 – Start it

```bash
docker compose up --build -d
docker compose ps
```

The first build takes a few minutes. Wait until all four services show `running` / `healthy`.

Open **http://YOUR_IP** in your browser. You should see the login page. Create an account, make a link, and open the short link in another tab.

## Step 7 – Check it really works

```bash
curl -I http://YOUR_IP/api/health                  # 200 OK
docker compose logs --tail 50 api                  # no errors
docker compose exec redis redis-cli keys '*'       # after opening a short link: link:<code>
```

## Updating the app later

On your laptop: change code, `git commit`, `git push`. On the server:

```bash
cd ~/snip
git pull
docker compose up --build -d
```

Optional next step: a **GitHub Actions** workflow that runs the tests on every push (`pytest` in `backend/`). It is a good extra line for your resume once you understand it.

## Troubleshooting

| Problem | Fix |
|---|---|
| Browser times out | Security group is missing the HTTP (80) rule, or you are using the wrong IP. |
| `permission denied` for docker | You skipped the logout/login after `usermod -aG docker`. |
| `variable is missing a value` | `.env` is missing or incomplete. Check `ls -a` shows `.env`. |
| `api` keeps restarting | `docker compose logs api`. Usually a wrong MySQL password. If you changed passwords after the first start, run `docker compose down -v` once (this deletes the database). |
| `db` killed / out of memory | Use a 2 GB instance or add the swap from Step 4. |
| Short links show `localhost` | `BASE_URL` in `.env` is wrong. Fix it, then `docker compose up -d`. |
| Copy button does nothing | It works over plain http here. If your browser blocks it, use https (see below). |

## Next steps (optional)

- **Own domain + HTTPS:** point a domain's A record to the Elastic IP, put Caddy or nginx with Let's Encrypt in front, and change `BASE_URL` to `https://yourdomain`.
- **Managed services:** replace the `db` container with **RDS MySQL** and `redis` with **ElastiCache**. Set `MYSQL_HOST` to the RDS endpoint and `REDIS_URL` to the ElastiCache endpoint. This is the "production" answer to give in interviews.

## Clean up when done (avoid charges)

1. EC2 -> Instances -> select -> **Instance state -> Terminate**.
2. EC2 -> Elastic IPs -> **Release**.
3. EC2 -> Volumes -> delete any leftover volume.
