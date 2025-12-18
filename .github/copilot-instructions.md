# NVIDIA SMI Server - AI Coding Agent Instructions

## Project Overview

Single-file HTTP server that exposes NVIDIA GPU metrics via REST API. **Zero external dependencies** - uses only Python stdlib and the `nvidia-smi` CLI tool.

## Architecture

**Single-Entry Point**: [main.py](../main.py)
- `get_nvidia_smi_data()` - Orchestrates nvidia-smi queries with graceful degradation
- `NvidiaSmiHandler` - Minimal HTTP request handler (GET / only)
- `run()` - Server bootstrap on port 8000

**Data Collection Strategy**: Query nvidia-smi in groups (basic, temperature, memory, etc.) with progressive fallback:
1. Try all fields (core + optional)
2. If that fails, retry with only core field groups
3. Parse CSV output into typed JSON (floats for utilization, ints for clocks, etc.)
4. Handle `[Not Supported]` and `N/A` values as `null`

## Critical Conventions

### Field Querying Pattern
When adding new GPU metrics, follow the existing field_groups structure:
- Add to `field_groups` dict for guaranteed-supported fields
- Add to `optional_fields` dict for GPU-dependent fields
- Use dot-notation names matching nvidia-smi (e.g., `temperature.gpu`, `clocks.current.graphics`)

### Type Conversion Rules ([main.py](../main.py#L117-L138))
```python
utilization.* or fan.* → float
temperature.* → int
memory.* or power.* → float
clocks.* → int
```
All conversion failures fall back to string value.

### Error Handling Philosophy
- GPU query failures: Continue with degraded field set
- Process query failures: Return empty processes array
- HTTP errors: Return 500 with JSON error object
- Never crash the server - always return valid JSON

## Development Workflow

**Quick Test**:
```bash
python3 main.py  # Starts on http://localhost:8000
curl http://localhost:8000/  # Test endpoint
```

**Production Deploy** (Ubuntu/Debian only):
```bash
sudo ./setup.sh  # Installs to /opt, creates systemd service
sudo journalctl -u nvidia-smi-server -f  # View logs
```

### Setup Script Validation ([setup.sh](../setup.sh))
**Critical**: [main.py](../main.py#L1) must start with `#nvidia-smi-server/main.py` - setup.sh validates this header before installation.

## Service Configuration

[nvidia-smi-server.service](../nvidia-smi-server.service):
- Runs as root (required for nvidia-smi access)
- Auto-restarts with 10s delay
- Working directory: `/opt/nvidia-smi-server`

## Testing Considerations

No formal test suite. Manual testing requires:
- NVIDIA GPU with drivers installed
- nvidia-smi command available
- Test with GPUs that don't support optional fields to verify fallback logic

## Extending the Server

**Adding new endpoints**: Extend `NvidiaSmiHandler.do_GET()` with path routing
**Adding metrics**: Update field_groups or optional_fields dict - follow existing naming convention
**Changing response format**: Modify `get_nvidia_smi_data()` - preserve timestamp and top-level structure

## Known Constraints

- Single-threaded HTTP server (not for high-traffic use)
- Synchronous nvidia-smi calls (no async)
- No authentication/authorization
- Linux-focused (systemd service)
- Windows development workflow differs from production Linux deployment
