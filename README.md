# Comprehensive Documentation: Self-Hosted Cloud Infrastructure with Cloudflare Tunnel & TunnelTray

## 1. Problem Statement

The objective was to securely expose locally hosted web applications (Jellyfin, Immich, Nextcloud) running on a home Windows server to the public internet to facilitate remote access.

**Key Challenges:**

* **Dynamic IP Address:** The Internet Service Provider (ISP) assigns a dynamic IP, making direct DNS records unreliable without constant updates.
* **Security Risks:** Traditional "Port Forwarding" requires opening firewall ports on the home router, exposing the internal network to scanners and attacks.
* **Ephemeral Connectivity:** Initial tests with `cloudflared` Quick Tunnels generated random, temporary URLs (e.g., `https://random-uuid.trycloudflare.com`) that expired or changed upon service restart, rendering them unusable for long-term access.
* **User Experience:** Managing the tunnel required keeping a Command Prompt window open. If closed accidentally, connectivity was lost.

**Solution:**
Implement a persistent **Cloudflare Tunnel** (Zero Trust) connected to a custom domain. To manage this on a personal Windows machine, a custom System Tray application (**"TunnelTray"**) was developed to handle silent startup, connection monitoring, and error logging without user intervention.

---

## 2. Infrastructure Setup & Domain Configuration

### 2.1. Initial Proof of Concept (Quick Tunnels)

We initially validated the `cloudflared` tool using its "Quick Tunnel" feature, which requires no account.

* **Command Used:** `cloudflared tunnel --url http://localhost:8096`
* **Outcome:** Successfully exposed the local service to the internet.
* **Limitation:** The URL was randomized and temporary. This confirmed the technology worked but highlighted the need for a stable domain.

### 2.2. Domain Acquisition & DNS Migration

To establish a permanent identity, we transitioned to a custom domain setup.

1. **Domain Purchase:** The domain `prefect-sys.online` was purchased via **Hostinger**.
2. **Cloudflare Integration:**
* A free account was created on Cloudflare.
* The domain `prefect-sys.online` was added as a "Site" in the Cloudflare dashboard.
* Cloudflare generated two authoritative Nameservers (e.g., `ns1.cloudflare.com`, `ns2.cloudflare.com`).


3. **Nameserver Update:**
* We navigated to the **Hostinger** domain management console.
* The default Hostinger nameservers were replaced with the Cloudflare nameservers.
* **Result:** Cloudflare became the authoritative DNS provider, allowing us to manage subdomains and security settings directly from Cloudflare.



---

## 3. Cloudflare Tunnel Implementation

### 3.1. Installation

The `cloudflared` daemon (Windows amd64 version) was downloaded and extracted to a dedicated directory on the host machine.

### 3.2. Authentication & Tunnel Creation

We established a persistent, authenticated connection between the local host and the Cloudflare Edge network.

1. **Login:**
```powershell
cloudflared tunnel login

```


*Action:* This opened a browser window to authorize the specific Cloudflare account and downloaded a certificate file (`cert.pem`).
2. **Tunnel Creation:**
```powershell
cloudflared tunnel create prefect-home

```


*Result:* This generated a unique **Tunnel ID (UUID)** and a credentials JSON file stored in `C:\Users\morph\.cloudflared\`.

### 3.3. Routing & Configuration

Instead of manually routing traffic via CLI flags, we implemented a persistent configuration file.

**Configuration File (`config.yml`):**
This file maps public subdomains to local ports.

```yaml
tunnel: <UUID>
credentials-file: C:\Users\morph\.cloudflared\<UUID>.json

ingress:
  - hostname: jellyfin.prefect-sys.online
    service: http://localhost:8096
  - hostname: photos.prefect-sys.online
    service: http://localhost:2283
  - hostname: files.prefect-sys.online
    service: http://localhost:8080
  - service: http_status:404

```

**DNS Records (CNAMEs):**
We executed commands to permanently route the subdomains to the tunnel UUID.

```powershell
cloudflared tunnel route dns prefect-home jellyfin.prefect-sys.online
cloudflared tunnel route dns prefect-home photos.prefect-sys.online
cloudflared tunnel route dns prefect-home files.prefect-sys.online

```

---

## 4. Automation: The "TunnelTray" Application

To eliminate the need for a visible terminal window and to ensure reliability, a custom Python application was developed.

### 4.1. Application Logic (`main.pyw`)

A System Tray utility built using **Python**, **pystray**, and **Pillow**.

* **Process Management:** It executes `cloudflared tunnel run prefect-home` as a hidden background subprocess using `creationflags=0x08000000`.
* **Singleton Enforcement:** It binds to local TCP port `64123` on startup. If the port is busy, the app detects an existing instance and exits immediately, preventing duplicate processes.
* **Status Monitoring:**
* **Connecting:** Yellow Blinking Icon.
* **Connected:** Solid Green Icon (Triggered by real-time parsing of `tunnel.log` for the text "Registered tunnel connection").
* **Stopped:** Solid Red Icon.


* **Dynamic Menus:** The context menu regenerates on every click to ensure accurate options (e.g., showing "Stop" only when running).

### 4.2. Dependency Management (`run.bat`)

A robust Batch script acts as the entry point.

* **Environment Check:** Detects if a Python virtual environment (`venv`) exists.
* **Auto-Healing:** Computes a hash of `requirements.txt`. If dependencies change or are missing, it automatically runs `pip install` before launching the app.
* **Execution:** Launches `main.pyw` using `pythonw.exe` (Windowless Python) for silent operation, or `python.exe` if Debug Mode is enabled.

### 4.3. Silent Boot Mechanism (`hideWindowsTerminal.vbs`)

To ensure the Batch file itself does not flash a black window on startup, a VBScript wrapper was implemented.

```vb
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & WScript.Arguments(0) & chr(34), 0
Set WshShell = Nothing

```

### 4.4. Startup Integration (`create_shortcut.bat`)

A utility script generates a specific Windows Shortcut (`.lnk`) placed in the `shell:startup` folder.

* **Target:** `wscript.exe`
* **Arguments:** `"path\to\hideWindowsTerminal.vbs" "path\to\run.bat"`

**Workflow:** Windows Boot -> Shortcut -> WScript -> VBS (Hidden) -> Batch (Hidden) -> Python (Hidden) -> Tray Icon (Visible).

---

## 5. Summary of Files

| File Name | Purpose |
| --- | --- |
| **`config.yml`** | Defines the Ingress Rules mapping public subdomains to localhost ports. |
| **`main.pyw`** | The core Python application handling the System Tray UI and process logic. |
| **`run.bat`** | The launcher script responsible for environment setup and execution. |
| **`requirements.txt`** | Lists Python dependencies (`pystray`, `Pillow`). |
| **`hideWindowsTerminal.vbs`** | Wrapper to suppress the console window of the batch launcher. |
| **`create_shortcut.bat`** | Helper script to create the startup shortcut with correct arguments. |

---

## 6. Final Status

The system is fully operational.

* **Access:** All services are accessible via HTTPS with valid SSL certificates managed by Cloudflare.
* **Security:** Local ports remain closed; traffic enters solely via the encrypted tunnel.
* **Reliability:** The tunnel starts automatically on boot, recovers from crashes, and provides visual feedback via the system tray.