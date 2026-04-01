# Makefile for Mimi Project

# Variables
PYTHON := python
VENV_DIR := .venv
VENV_ACTIVATE := $(VENV_DIR)/Scripts/activate
PIP := $(VENV_DIR)/Scripts/pip
WAIT_PORT := 8765

# Detect OS
ifeq ($(OS),Windows_NT)
    # Windows specific
    SHELL := cmd.exe
    MKDIR := mkdir
    RM := rmdir /s /q
    ACTIVATE_CMD := $(VENV_DIR)\Scripts\activate.bat
else
    # Linux/Unix specific (assumed for generic sh)
    SHELL := /bin/bash
    MKDIR := mkdir -p
    RM := rm -rf
    ACTIVATE_CMD := source $(VENV_DIR)/bin/activate
endif

.PHONY: all setup install run-agent run-web clean help

# Default target
all: run

# Setup virtual environment
setup:
	$(PYTHON) -m venv $(VENV_DIR)

# Install dependencies
install: setup
	$(ACTIVATE_CMD) && $(PIP) install -r requirements.txt
	cd web_avatar && npm install

# Run the entire application (Agent + Web + Backend)
run:
	@echo "Please run components separately locally or use start.bat (deprecated)"
	@echo "Recommended: make run-backend, then make run-agent, then make run-frontend"

# Run the Node.js WebSocket Backend


run-backend:
ifeq ($(OS),Windows_NT)
	@if "$${SHELL}"=="powershell.exe" (\
		start-process powershell -ArgumentList '-NoExit','-Command','cd web_avatar; node server.js'\
	) else (\
		start "Mimi Backend" cmd /k "cd web_avatar && node server.js"\
	)
else
	(cd web_avatar && nohup node server.js &)
endif

# Run the Python Agent (Client)
run-agent:
	$(ACTIVATE_CMD) && $(PYTHON) agent/main.py

# Run the Web Frontend (Frontend)


run-frontend:
ifeq ($(OS),Windows_NT)
	@if "$${SHELL}"=="powershell.exe" (\
		start-process powershell -ArgumentList '-NoExit','-Command','cd web_avatar; npm run dev'\
	) else (\
		start "Mimi Frontend" cmd /k "cd web_avatar && npm run dev"\
	)
else
	(cd web_avatar && nohup npm run dev &)
endif

# Alias for web
run-web: run-frontend

# Clean build artifacts
clean:
	-$(RM) __pycache__
	-$(RM) agent\__pycache__
	-$(RM) agent\core\__pycache__
	-$(RM) agent\llm\__pycache__
	-$(RM) agent\tools\__pycache__
	-$(RM) agent\avatar\__pycache__
	-$(RM) agent\input\__pycache__
	-$(RM) agent\output\__pycache__

# Help
help:
	@echo "Available targets:"
	@echo "  make setup      - Create virtual environment"
	@echo "  make install    - Install Python and Node.js dependencies"
	@echo "  make run        - Run the full system (Agent + Web)"
	@echo "  make run-agent  - Run only the backend agent"
	@echo "  make run-web    - Run only the frontend web app"
	@echo "  make clean      - Remove cache files"
