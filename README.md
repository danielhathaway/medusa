# Medusa

**Medusa is a lightweight web UI for running and managing Python scripts on a headless Linux server.**

It provides a simple browser-based interface for viewing scripts, running them, creating new scripts, editing existing scripts, deleting scripts, and viewing command output.

Medusa is built with Flask and is designed to be useful on servers where you don't have a desktop environment or don't want to manage scripts exclusively from an SSH session.

## Features

* Web-based interface for managing scripts
* Run Python scripts directly from the browser
* Create and edit scripts through a web editor
* Delete scripts from the UI
* View script output after execution
* Configurable script directory
* CSRF protection using Flask-WTF
* Designed for Linux/headless servers
* Built with Python and Flask

## How It Works

Medusa maintains a configurable directory containing the Python scripts you want to manage.

When you open the application, Medusa scans this directory and presents the available files in the web interface. Selecting a script allows you to execute or modify it.

When a script is executed, Medusa runs it through the project's `chempy.pysub` helper and displays the resulting output and exit status in the browser.

The default script directory is:

```text
./modules
```

This can be changed through `medusa.conf`.

## Requirements

Medusa currently requires:

* Python 3
* Flask
* Flask-WTF
* WTForms
* MarkupSafe
* `chemlibrary_chempy`

The exact dependency requirements are maintained in `requirements.txt`.

For production deployments, Medusa should be run using a WSGI server such as Gunicorn rather than Flask's development server.

## Installation

Clone the repository:

```bash
git clone https://github.com/danielhathaway/medusa.git
cd medusa
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Alternatively, the repository includes a `setup.sh` script that installs Python and the project's requirements on a Debian/Ubuntu-style system.

> **Note:** `setup.sh` uses `apt` and therefore is intended for Debian-based Linux systems.

## Configuration

Medusa uses `medusa.conf` for configuration.

The default configuration is:

```ini
# This is an example config file for medusa.py
base_dir = ./modules
```

### Changing the Script Directory

To manage scripts stored somewhere else, change `base_dir`:

```ini
base_dir = /opt/my-scripts
```

The configured directory becomes the root directory from which Medusa lists, executes, creates, edits, and deletes scripts.

If `base_dir` is not present in the configuration, Medusa falls back to a `modules` directory relative to the application.

## Running Medusa

For development and testing, Medusa can be started with Flask:

```bash
flask --app "medusa" run
```

By default, Flask will make the application available at:

```text
http://127.0.0.1:5000
```

The included `setup.sh` script also launches Medusa using this command after installing its dependencies.

### Running on a Remote Server

If Medusa is running on a remote headless server, you may want to make it accessible beyond localhost:

```bash
flask --app "medusa" run --host=0.0.0.0
```

You can also specify a different port:

```bash
flask --app "medusa" run --host=0.0.0.0 --port=8080
```

> **Security note:** The Flask development server is not intended for production use. For production deployments, use a WSGI server such as Gunicorn and, preferably, place it behind a reverse proxy.

## Production Deployment

A recommended production setup is:

```text
Internet / LAN
      |
      v
   Nginx
      |
      v
   Gunicorn
      |
      v
   Medusa
      |
      v
 Python scripts
```

This separates the public-facing web server from the Python application and allows `systemd` to manage the application process.

The following example assumes:

```text
Application: /opt/medusa
User:        medusa
Script dir:  /opt/medusa/modules
Port:        127.0.0.1:8000
```

Adjust these paths and values to match your environment.

### Create a Dedicated User

Medusa should not normally run as `root`.

Create a dedicated system user:

```bash
sudo useradd \
    --system \
    --home /opt/medusa \
    --shell /usr/sbin/nologin \
    medusa
```

Create the application directory:

```bash
sudo mkdir -p /opt/medusa
```

Clone or copy the application into `/opt/medusa`:

```bash
sudo git clone https://github.com/danielhathaway/medusa.git /opt/medusa
```

Set ownership:

```bash
sudo chown -R medusa:medusa /opt/medusa
```

### Create a Python Virtual Environment

Using a virtual environment keeps Medusa's dependencies isolated from the system Python installation.

Install the required packages if necessary:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

Create the virtual environment:

```bash
sudo -u medusa python3 -m venv /opt/medusa/venv
```

Install the dependencies:

```bash
sudo -u medusa /opt/medusa/venv/bin/pip install --upgrade pip
sudo -u medusa /opt/medusa/venv/bin/pip install -r /opt/medusa/requirements.txt
```

Install Gunicorn:

```bash
sudo -u medusa /opt/medusa/venv/bin/pip install gunicorn
```

### Configure `medusa.conf`

For a production installation, an absolute path is recommended:

```ini
base_dir = /opt/medusa/modules
```

Make sure the directory exists:

```bash
sudo mkdir -p /opt/medusa/modules
sudo chown -R medusa:medusa /opt/medusa/modules
```

### Test Gunicorn

Before creating the systemd service, verify that Gunicorn can start the application:

```bash
sudo -u medusa \
    /opt/medusa/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    medusa:app
```

You should see Gunicorn start and listen on port `8000`.

Press `Ctrl+C` to stop it.

You can test the application locally with:

```bash
curl http://127.0.0.1:8000
```

## systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/medusa.service
```

Add:

```ini
[Unit]
Description=Medusa Python Script Manager
After=network.target

[Service]
Type=simple

User=medusa
Group=medusa

WorkingDirectory=/opt/medusa

ExecStart=/opt/medusa/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    medusa:app

Restart=on-failure
RestartSec=5

# Basic process isolation
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
```

Reload `systemd`:

```bash
sudo systemctl daemon-reload
```

Enable Medusa to start automatically at boot:

```bash
sudo systemctl enable medusa
```

Start the service:

```bash
sudo systemctl start medusa
```

Check its status:

```bash
sudo systemctl status medusa
```

A successful deployment should show something similar to:

```text
● medusa.service - Medusa Python Script Manager
     Loaded: loaded
     Active: active (running)
```

### Managing the Service

Stop Medusa:

```bash
sudo systemctl stop medusa
```

Restart Medusa:

```bash
sudo systemctl restart medusa
```

View the logs:

```bash
sudo journalctl -u medusa
```

Follow the logs in real time:

```bash
sudo journalctl -u medusa -f
```

View logs from the current boot:

```bash
sudo journalctl -u medusa -b
```

## Nginx Reverse Proxy

For a production installation, Nginx can be used as a reverse proxy in front of Gunicorn.

Install Nginx:

```bash
sudo apt update
sudo apt install nginx
```

Create a site configuration:

```bash
sudo nano /etc/nginx/sites-available/medusa
```

Example configuration:

```nginx
server {
    listen 80;
    server_name medusa.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/medusa \
    /etc/nginx/sites-enabled/medusa
```

Test the Nginx configuration:

```bash
sudo nginx -t
```

If the configuration is valid, reload Nginx:

```bash
sudo systemctl reload nginx
```

Medusa should now be accessible through the configured hostname.

### HTTPS

If Medusa is accessible over an untrusted network, HTTPS should be enabled.

For a publicly accessible server, Let's Encrypt and Certbot can be used:

```bash
sudo apt install certbot python3-certbot-nginx
```

Then:

```bash
sudo certbot --nginx -d medusa.example.com
```

Certbot can configure the TLS certificate and Nginx configuration automatically.

For private networks, consider using an internal certificate authority or a VPN instead of exposing Medusa directly to the public internet.

## Production Security

Medusa can execute arbitrary Python code through its web interface. Access to the application should therefore be treated as access to the server.

### Do Not Run as Root

Run Medusa as a dedicated, unprivileged user:

```ini
User=medusa
Group=medusa
```

Avoid running the application as `root`.

### Restrict Network Access

Gunicorn should normally listen only on localhost:

```text
127.0.0.1:8000
```

This prevents clients from bypassing Nginx and connecting directly to the application.

If Medusa is intended for use only on a private network, firewall access accordingly.

### Protect the Script Directory

The Medusa service account needs appropriate permissions to the configured `base_dir`.

For example:

```bash
sudo chown -R medusa:medusa /opt/medusa/modules
sudo chmod -R u=rwX,go-rwx /opt/medusa/modules
```

The exact permissions should be adjusted based on how the scripts need to interact with other files on the system.

### Authentication

Medusa's ability to edit, create, delete, and execute Python scripts makes authentication an important consideration for deployments where untrusted users may have network access.

If authentication is not provided by the application itself, consider placing Medusa behind an authenticated reverse proxy, VPN, or another access-control mechanism.

### Flask Secret Key

Production deployments should use a persistent, unpredictable Flask secret key rather than relying on development defaults.

The secret key is used by Flask and Flask-WTF for security-related functionality such as session and CSRF protection.

If the application is modified to read the secret key from an environment variable, a systemd service can provide it using an `EnvironmentFile`:

```ini
[Service]
EnvironmentFile=/etc/medusa/medusa.env
```

For example:

```text
FLASK_SECRET_KEY=<random-secret-value>
```

The environment file should be readable only by the appropriate system account.

## Updating Medusa

When installing a new version from Git:

```bash
cd /opt/medusa
sudo -u medusa git pull
```

Update the Python dependencies:

```bash
sudo -u medusa \
    /opt/medusa/venv/bin/pip install -r requirements.txt
```

Restart the service:

```bash
sudo systemctl restart medusa
```

Verify that it started successfully:

```bash
sudo systemctl status medusa
```

Check the logs if necessary:

```bash
sudo journalctl -u medusa -n 100
```

## Troubleshooting

### Check Service Status

```bash
sudo systemctl status medusa
```

### View Recent Logs

```bash
sudo journalctl -u medusa -n 100
```

### Follow Logs

```bash
sudo journalctl -u medusa -f
```

### Verify Gunicorn Is Listening

```bash
sudo ss -lntp | grep 8000
```

Expected output should show Gunicorn listening on:

```text
127.0.0.1:8000
```

### Test Gunicorn Directly

```bash
sudo -u medusa \
    /opt/medusa/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    medusa:app
```

### Test Nginx

```bash
sudo nginx -t
```

If Nginx is returning an error, check:

```bash
sudo journalctl -u nginx
```

and:

```bash
sudo tail -f /var/log/nginx/error.log
```

## Project Structure

```text
medusa/
├── medusa.py
├── medusa.conf
├── requirements.txt
├── setup.sh
├── modules/
├── static/
├── templates/
│   └── medusa/
└── LICENSE
```

### `medusa.py`

The main Flask application.

It defines the web routes and handles:

* Script listing
* Script execution
* Script creation
* Script editing
* Script deletion
* Navigation
* Execution result reporting

The application also initializes CSRF protection and loads the `base_dir` configuration.

### `medusa.conf`

Application configuration.

Currently, the primary configuration option is `base_dir`, which determines where Medusa looks for scripts.

### `modules/`

The default location for scripts managed by Medusa.

You can change this location using `base_dir`.

### `templates/`

Contains the Jinja templates used to render the web interface.

### `static/`

Contains static assets used by the web interface.

### `requirements.txt`

Python dependencies required by the application.

### `setup.sh`

A convenience setup script for Debian-based Linux systems. It installs Python, installs the Python requirements, and starts the Flask application.

## Development

The application can be run directly from the repository:

```bash
flask --app "medusa" run --debug
```

The project is intentionally small, making it relatively straightforward to modify the Flask routes, templates, or script-management behavior.

## Dependencies

Medusa currently builds on the following Python packages:

| Package            | Purpose                                 |
| ------------------ | --------------------------------------- |
| Flask              | Web application framework               |
| Flask-WTF          | Forms and CSRF protection               |
| WTForms            | Form handling                           |
| MarkupSafe         | Template/string safety support          |
| chemlibrary_chempy | Script execution and filesystem helpers |

These dependencies are declared in `requirements.txt`.

## License

Medusa is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See [`LICENSE`](LICENSE) for the complete license text.

## Contributing

Contributions, bug fixes, documentation improvements, and feature ideas are welcome.

Before submitting a change:

1. Test the application locally.
2. Verify that existing script-management functionality still works.
3. Keep changes focused and documented where appropriate.
4. Open an issue first for larger architectural changes.

## Disclaimer

Medusa executes Python code on the host system. Use it only in environments where the users and scripts being managed are trusted.

The authors provide the software without warranty. See the included GPL-3.0 license for the applicable terms.
