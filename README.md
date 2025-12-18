# NVIDIA SMI Server

A lightweight HTTP server that exposes NVIDIA GPU metrics as JSON via a REST API. Built using Python's built-in HTTP server and the `nvidia-smi` command-line tool.

## Features

- 🚀 **Simple & Lightweight** - No external dependencies, uses only Python standard library
- 📊 **Comprehensive Metrics** - GPU temperature, memory usage, power draw, utilization, clock speeds, and more
- 🔄 **Real-time Data** - Fresh metrics on every request
- 🛡️ **Robust** - Graceful fallback for unsupported GPU features
- 🐧 **Linux Service** - Easy systemd service installation on Ubuntu
- 📡 **Process Monitoring** - Track running GPU processes

## Metrics Collected

### Core Metrics (Supported on most GPUs)
- GPU index, name, UUID, driver version
- PCI bus ID and link information
- GPU temperature
- GPU and memory utilization
- Memory usage (total, used, free)
- Power draw and limits
- Graphics and memory clock speeds
- Compute mode and display status
- PCIe link generation and width

### Optional Metrics (GPU-dependent)
- Fan speed
- Encoder/decoder utilization
- SM and video clocks
- Maximum clock speeds
- Extended power limits
- Memory temperature
- Detailed PCI information
- Persistence mode
- ECC mode and errors

### Process Information
- GPU bus ID
- Process ID (PID)
- Process name
- GPU memory usage per process

## Requirements

- Python 3.6+
- NVIDIA GPU with drivers installed
- `nvidia-smi` command-line tool

## Installation

### Quick Start (Development)

```bash
# Clone or download the repository
cd nvidia-smi-server

# Run the server
python3 main.py
```

The server will start on `http://localhost:8000`

### Production Installation (Ubuntu/Debian)

For running as a system service:

```bash
# Make the setup script executable
chmod +x setup.sh

# Run the setup (requires sudo)
sudo ./setup.sh
```

The setup script will:
1. Validate the installation files
2. Check for Ubuntu-based OS
3. Install files to `/opt/nvidia-smi-server/`
4. Create and enable a systemd service
5. Start the service
6. Run a health check

## Usage

### API Endpoint

**GET /**

Returns JSON with GPU metrics and running processes.

#### Example Request

```bash
curl http://localhost:8000/
```

#### Example Response

```json
{
  "timestamp": "2025-12-18T17:57:55.801636",
  "gpus": [
    {
      "index": "0",
      "name": "NVIDIA GeForce RTX 3050",
      "uuid": "GPU-...",
      "driver_version": "581.15",
      "pci.bus_id": "00000000:0A:00.0",
      "temperature.gpu": 63,
      "utilization.gpu": 98.0,
      "utilization.memory": 20.0,
      "memory.total": 8192.0,
      "memory.used": 2714.0,
      "memory.free": 5478.0,
      "power.draw": 179.0,
      "power.limit": 180.0,
      "clocks.current.graphics": 1350,
      "clocks.current.memory": 4266,
      "compute_mode": "Default",
      "display_active": "Enabled",
      "pcie.link.gen.current": "4",
      "pcie.link.gen.max": "4",
      "pcie.link.width.current": "16",
      "pcie.link.width.max": "16"
    }
  ],
  "processes": [
    {
      "gpu_bus_id": "00000000:0A:00.0",
      "pid": "1234",
      "process_name": "python",
      "used_memory": "2048"
    }
  ]
}
```

### Service Management (Ubuntu)

After running the setup script:

```bash
# Check service status
sudo systemctl status nvidia-smi-server

# View logs
sudo journalctl -u nvidia-smi-server -f

# Restart service
sudo systemctl restart nvidia-smi-server

# Stop service
sudo systemctl stop nvidia-smi-server

# Start service
sudo systemctl start nvidia-smi-server

# Disable service (prevent auto-start on boot)
sudo systemctl disable nvidia-smi-server
```

## Configuration

### Change Port

Edit `main.py` and modify the `port` parameter in the `run()` function:

```python
if __name__ == '__main__':
    run(port=8080)  # Change to your desired port
```

For systemd service, also update the service file and reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart nvidia-smi-server
```

### Run on All Network Interfaces

By default, the server binds to all interfaces (`0.0.0.0`). To restrict to localhost only, modify the `server_address` in `main.py`:

```python
def run(server_class=HTTPServer, handler_class=NvidiaSmiHandler, port=8000):
    server_address = ('127.0.0.1', port)  # Localhost only
    # ...
```

## Use Cases

- 🖥️ **Monitoring dashboards** - Integrate GPU metrics into Grafana, Prometheus, or custom dashboards
- 🤖 **ML infrastructure** - Monitor GPU usage across training clusters
- 📈 **Resource management** - Track GPU utilization for workload optimization
- 🔔 **Alerting** - Set up alerts based on temperature, power, or utilization thresholds
- 🌐 **Remote monitoring** - Check GPU status from anywhere

## Security Considerations

⚠️ **Warning**: This server has no authentication or authorization. Do not expose it directly to the internet.

Recommended security measures:
- Run behind a reverse proxy (nginx, Apache)
- Use a firewall to restrict access
- Implement authentication at the reverse proxy level
- Use VPN or SSH tunneling for remote access
- Consider rate limiting

## Troubleshooting

### Service won't start

```bash
# Check the logs
sudo journalctl -u nvidia-smi-server -n 50

# Verify nvidia-smi works
nvidia-smi

# Check if port 8000 is already in use
sudo lsof -i :8000
```

### No GPU data returned

- Ensure NVIDIA drivers are installed: `nvidia-smi`
- Check if the GPU is detected: `lspci | grep -i nvidia`
- Verify Python has permissions to execute nvidia-smi

### Empty or partial metrics

Some metrics may not be supported on all GPUs. The server gracefully handles unsupported fields and returns `null` for those values.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Acknowledgments

Built using:
- Python standard library
- NVIDIA System Management Interface (`nvidia-smi`)
