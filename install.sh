#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# DEFAULT VARIABLES
PROJECT_DIR=$(pwd)
DEFAULT_DEST_DIR="/usr/local/bin/docker_npm_listener"
SERVICE_FILE="/etc/systemd/system/docker-npm-listener.service"
MAIN_SCRIPT="main.py"
HELPER_SCRIPTS=("npm_integration.py" "ntfy_integration.py" ".env")

# FUNCTION: print a prompt and read answer with default
prompt_default() {
  local prompt_msg=$1
  local default_val=$2
  read -rp "$prompt_msg [$default_val]: " input
  echo "${input:-$default_val}"
}

# FUNCTION: check dependencies
check_dependencies() {
  command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not installed." >&2; exit 1; }
  command -v systemctl >/dev/null 2>&1 || { echo "Error: systemctl not found." >&2; exit 1; }
}

# FUNCTION: uninstall existing installation
uninstall() {
  echo "Stopping service if running..."
  systemctl stop docker-npm-listener.service || true
  echo "Disabling service..."
  systemctl disable docker-npm-listener.service || true
  echo "Removing systemd service file: $SERVICE_FILE"
  rm -f "$SERVICE_FILE"
  echo "Reloading systemd daemon..."
  systemctl daemon-reload
  if [ -d "$DEST_DIR" ]; then
    echo "Removing installation directory $DEST_DIR"
    rm -rf "$DEST_DIR"
  fi
  echo "Uninstallation complete."
}

# FUNCTION: install or upgrade
install_or_upgrade() {
  echo "Creating installation directory $DEST_DIR..."
  mkdir -p "$DEST_DIR"

  echo "Copying main script $MAIN_SCRIPT..."
  cp "$MAIN_SCRIPT" "$DEST_DIR/"

  for script in "${HELPER_SCRIPTS[@]}"; do
    echo "Copying helper script $script..."
    cp "$script" "$DEST_DIR/"
  done

  echo "Setting executable permissions on $DEST_DIR/$MAIN_SCRIPT..."
  chmod +x "$DEST_DIR/$MAIN_SCRIPT"

  if [ "$USE_VENV" == "yes" ]; then
    if [ ! -d "$DEST_DIR/venv" ]; then
      echo "Creating Python virtual environment in $DEST_DIR/venv..."
      python3 -m venv "$DEST_DIR/venv"
    fi
    echo "Installing dependencies in virtualenv..."
    "$DEST_DIR/venv/bin/pip" install --upgrade pip
    "$DEST_DIR/venv/bin/pip" install -r requirements.txt
    PYTHON_BIN="$DEST_DIR/venv/bin/python"
  else
    PYTHON_BIN=$(which python3)
    echo "Using system Python: $PYTHON_BIN"
  fi

  echo "Creating systemd service file: $SERVICE_FILE"
  cat > "$SERVICE_FILE" <<EOL
[Unit]
Description=Docker NPM Listener Service
After=docker.service
Requires=docker.service

[Service]
ExecStart=$PYTHON_BIN $DEST_DIR/$MAIN_SCRIPT
Restart=always
User=root
Group=root
WorkingDirectory=$DEST_DIR
Nice=10
CPUWeight=512
MemoryMax=256M
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

  echo "Reloading systemd daemon..."
  systemctl daemon-reload

  echo "Starting the Docker NPM Listener service..."
  systemctl restart docker-npm-listener.service

  echo "Enabling the Docker NPM Listener service on boot..."
  systemctl enable docker-npm-listener.service

  echo "Installation / upgrade complete."
  echo "Check service status with: sudo systemctl status docker-npm-listener.service"
}

# MAIN SCRIPT STARTS HERE

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo." >&2
  exit 1
fi

check_dependencies

echo "Welcome to Docker NPM Listener Installer"

# Ask for install directory, default is /usr/local/bin/docker_npm_listener
DEST_DIR=$(prompt_default "Install directory" "$DEFAULT_DEST_DIR")

# Check if already installed
if [ -d "$DEST_DIR" ]; then
  echo "Detected existing installation at $DEST_DIR"
  read -rp "Do you want to (u)ninstall, (r)einstall/upgrade or (c)ancel? [r]: " action
  action=${action:-r}
  case $action in
    u|U)
      uninstall
      exit 0
      ;;
    r|R)
      echo "Proceeding with upgrade/reinstall..."
      ;;
    c|C)
      echo "Cancelling."
      exit 0
      ;;
    *)
      echo "Invalid option. Exiting."
      exit 1
      ;;
  esac
fi

# Ask whether to use virtualenv
USE_VENV=$(prompt_default "Create and use Python virtual environment (very much recommended)" "yes")
USE_VENV=$(echo "$USE_VENV" | tr '[:upper:]' '[:lower:]')

# Start installation or upgrade
install_or_upgrade