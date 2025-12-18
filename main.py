#nvidia-smi-server/main.py
# Simple HTTP server to run nvidia-smi and return formatted JSON
import subprocess
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
from datetime import datetime

def get_nvidia_smi_data():
	"""
	Get comprehensive GPU data using nvidia-smi --query-gpu
	"""
	result = {
		"timestamp": datetime.now().isoformat(),
		"gpus": [],
		"processes": []
	}
	
	# Define field groups to query separately (some may not be supported on all GPUs)
	field_groups = {
		'basic': [
			'index',
			'name',
			'uuid',
			'driver_version',
			'pci.bus_id',
		],
		'temperature': [
			'temperature.gpu',
		],
		'utilization': [
			'utilization.gpu',
			'utilization.memory',
		],
		'memory': [
			'memory.total',
			'memory.used',
			'memory.free',
		],
		'power': [
			'power.draw',
			'power.limit',
		],
		'clocks': [
			'clocks.current.graphics',
			'clocks.current.memory',
		],
		'modes': [
			'compute_mode',
			'display_active',
		],
		'pcie': [
			'pcie.link.gen.current',
			'pcie.link.gen.max',
			'pcie.link.width.current',
			'pcie.link.width.max',
		],
	}
	
	# Optional fields that may not be supported
	optional_fields = {
		'fan': ['fan.speed'],
		'encoder': ['utilization.encoder', 'utilization.decoder'],
		'advanced_clocks': ['clocks.current.sm', 'clocks.current.video'],
		'max_clocks': ['clocks.max.graphics', 'clocks.max.memory'],
		'power_limits': ['power.default_limit', 'power.min_limit', 'power.max_limit'],
		'temperature_memory': ['temperature.memory'],
		'pci_details': ['pci.domain', 'pci.bus', 'pci.device', 'pci.device_id', 'pci.sub_device_id'],
		'persistence': ['persistence_mode'],
		'ecc': ['ecc.mode.current'],
	}
	
	try:
		# Start with basic fields
		all_fields = []
		for group_name, fields in field_groups.items():
			all_fields.extend(fields)
		
		# Try to add optional fields
		for group_name, fields in optional_fields.items():
			all_fields.extend(fields)
		
		# Try querying all fields first
		query_string = ','.join(all_fields)
		try:
			gpu_output = subprocess.check_output(
				['nvidia-smi', f'--query-gpu={query_string}', '--format=csv,noheader,nounits'],
				encoding='utf-8',
				errors='replace',
				stderr=subprocess.PIPE
			)
			successful_fields = all_fields
		except subprocess.CalledProcessError:
			# If that fails, fall back to just basic + core fields
			core_fields = []
			for group_name in ['basic', 'temperature', 'utilization', 'memory', 'power', 'clocks', 'modes', 'pcie']:
				core_fields.extend(field_groups[group_name])
			
			query_string = ','.join(core_fields)
			gpu_output = subprocess.check_output(
				['nvidia-smi', f'--query-gpu={query_string}', '--format=csv,noheader,nounits'],
				encoding='utf-8',
				errors='replace'
			)
			successful_fields = core_fields
		
		# Parse GPU data
		for line in gpu_output.strip().split('\n'):
			if not line.strip():
				continue
			values = [v.strip() for v in line.split(',')]
			gpu_data = {}
			for i, field in enumerate(successful_fields):
				if i < len(values):
					value = values[i]
					# Convert to appropriate type
					if value == '[Not Supported]' or value == '[N/A]' or value == 'N/A' or value == '':
						gpu_data[field] = None
					elif field.startswith('utilization.') or field.startswith('fan.'):
						try:
							gpu_data[field] = float(value) if value else None
						except ValueError:
							gpu_data[field] = value
					elif field.startswith('temperature.'):
						try:
							gpu_data[field] = int(value) if value else None
						except ValueError:
							gpu_data[field] = value
					elif field.startswith('memory.') or field.startswith('power.'):
						try:
							gpu_data[field] = float(value) if value else None
						except ValueError:
							gpu_data[field] = value
					elif field.startswith('clocks.'):
						try:
							gpu_data[field] = int(value) if value else None
						except ValueError:
							gpu_data[field] = value
					else:
						gpu_data[field] = value
			result["gpus"].append(gpu_data)
		
		# Get running processes
		try:
			process_output = subprocess.check_output(
				['nvidia-smi', '--query-compute-apps=gpu_bus_id,pid,process_name,used_memory', '--format=csv,noheader,nounits'],
				encoding='utf-8',
				errors='replace',
				stderr=subprocess.PIPE
			)
			
			for line in process_output.strip().split('\n'):
				if not line.strip():
					continue
				values = [v.strip() for v in line.split(',')]
				if len(values) >= 4:
					result["processes"].append({
						"gpu_bus_id": values[0],
						"pid": values[1],
						"process_name": values[2],
						"used_memory": values[3]
					})
		except subprocess.CalledProcessError:
			# No processes running or error - that's okay
			pass
			
	except Exception as e:
		result["error"] = str(e)
	
	return result

def get_web_ui_html():
	"""
	Returns the HTML for the web UI
	"""
	return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>NVIDIA SMI Server</title>
	<script src="https://cdn.tailwindcss.com"></script>
	<script>
		tailwind.config = {
			darkMode: 'class'
		}
	</script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
	<div class="container mx-auto px-4 py-8">
		<header class="mb-8">
			<h1 class="text-4xl font-bold text-green-400 mb-2">NVIDIA GPU Monitor</h1>
			<p class="text-gray-400">Real-time GPU metrics and process monitoring</p>
		</header>

		<div class="mb-6 flex items-center justify-between">
			<div class="flex items-center gap-4">
				<div id="status" class="flex items-center gap-2">
					<div class="w-3 h-3 rounded-full bg-gray-500" id="status-dot"></div>
					<span class="text-sm text-gray-400" id="status-text">Connecting...</span>
				</div>
				<button onclick="fetchData()" class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition-colors">
					Refresh
				</button>
			</div>
			<div class="text-sm text-gray-400">
				Auto-refresh: <span id="countdown">5</span>s
			</div>
		</div>

		<div id="error" class="hidden bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6"></div>
		
		<div id="gpus-container" class="space-y-6"></div>
		
		<div id="processes-container" class="mt-8">
			<h2 class="text-2xl font-bold text-green-400 mb-4">Running Processes</h2>
			<div id="processes-table" class="bg-gray-800 rounded-lg overflow-hidden"></div>
		</div>
	</div>

	<script>
		let countdownTimer;
		let autoRefreshInterval;

		function showError(message) {
			const errorDiv = document.getElementById('error');
			errorDiv.textContent = message;
			errorDiv.classList.remove('hidden');
		}

		function hideError() {
			document.getElementById('error').classList.add('hidden');
		}

		function updateStatus(connected) {
			const dot = document.getElementById('status-dot');
			const text = document.getElementById('status-text');
			if (connected) {
				dot.className = 'w-3 h-3 rounded-full bg-green-500 animate-pulse';
				text.textContent = 'Connected';
			} else {
				dot.className = 'w-3 h-3 rounded-full bg-red-500';
				text.textContent = 'Disconnected';
			}
		}

		function formatBytes(bytes) {
			if (bytes === null || bytes === undefined) return 'N/A';
			return (bytes / 1024).toFixed(1) + ' GB';
		}

		function formatPercent(value) {
			if (value === null || value === undefined) return 'N/A';
			return value.toFixed(1) + '%';
		}

		function formatTemp(temp) {
			if (temp === null || temp === undefined) return 'N/A';
			return temp + '°C';
		}

		function formatPower(power) {
			if (power === null || power === undefined) return 'N/A';
			return power.toFixed(1) + 'W';
		}

		function formatClock(clock) {
			if (clock === null || clock === undefined) return 'N/A';
			return clock + ' MHz';
		}

		function getUtilizationColor(value) {
			if (value === null || value === undefined) return 'bg-gray-600';
			if (value < 30) return 'bg-green-600';
			if (value < 70) return 'bg-yellow-600';
			return 'bg-red-600';
		}

		function getTempColor(temp) {
			if (temp === null || temp === undefined) return 'text-gray-400';
			if (temp < 60) return 'text-green-400';
			if (temp < 80) return 'text-yellow-400';
			return 'text-red-400';
		}

		function renderGPU(gpu) {
			const tempColor = getTempColor(gpu['temperature.gpu']);
			const gpuUtilColor = getUtilizationColor(gpu['utilization.gpu']);
			const memUtilColor = getUtilizationColor(gpu['utilization.memory']);
			
			const memUsed = gpu['memory.used'] || 0;
			const memTotal = gpu['memory.total'] || 1;
			const memPercent = (memUsed / memTotal * 100).toFixed(1);

			return `
				<div class="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
					<div class="flex justify-between items-start mb-4">
						<div>
							<h3 class="text-xl font-bold text-green-400">GPU ${gpu.index}</h3>
							<p class="text-gray-300 font-medium">${gpu.name || 'Unknown'}</p>
							<p class="text-xs text-gray-500 mt-1">${gpu.uuid || ''}</p>
						</div>
						<div class="text-right">
							<div class="text-3xl font-bold ${tempColor}">${formatTemp(gpu['temperature.gpu'])}</div>
							<div class="text-xs text-gray-400">Temperature</div>
						</div>
					</div>

					<div class="grid grid-cols-2 gap-4 mb-4">
						<div>
							<div class="text-xs text-gray-400 mb-1">GPU Utilization</div>
							<div class="flex items-center gap-2">
								<div class="flex-1 bg-gray-700 rounded-full h-2">
									<div class="${gpuUtilColor} h-2 rounded-full transition-all" style="width: ${gpu['utilization.gpu'] || 0}%"></div>
								</div>
								<span class="text-sm font-medium">${formatPercent(gpu['utilization.gpu'])}</span>
							</div>
						</div>
						<div>
							<div class="text-xs text-gray-400 mb-1">Memory Utilization</div>
							<div class="flex items-center gap-2">
								<div class="flex-1 bg-gray-700 rounded-full h-2">
									<div class="${memUtilColor} h-2 rounded-full transition-all" style="width: ${memPercent}%"></div>
								</div>
								<span class="text-sm font-medium">${formatPercent(gpu['utilization.memory'])}</span>
							</div>
						</div>
					</div>

					<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
						<div class="bg-gray-700/50 rounded p-3">
							<div class="text-xs text-gray-400 mb-1">Memory</div>
							<div class="font-medium">${formatBytes(gpu['memory.used'])} / ${formatBytes(gpu['memory.total'])}</div>
						</div>
						<div class="bg-gray-700/50 rounded p-3">
							<div class="text-xs text-gray-400 mb-1">Power</div>
							<div class="font-medium">${formatPower(gpu['power.draw'])} / ${formatPower(gpu['power.limit'])}</div>
						</div>
						<div class="bg-gray-700/50 rounded p-3">
							<div class="text-xs text-gray-400 mb-1">Graphics Clock</div>
							<div class="font-medium">${formatClock(gpu['clocks.current.graphics'])}</div>
						</div>
						<div class="bg-gray-700/50 rounded p-3">
							<div class="text-xs text-gray-400 mb-1">Memory Clock</div>
							<div class="font-medium">${formatClock(gpu['clocks.current.memory'])}</div>
						</div>
					</div>

					<div class="mt-4 pt-4 border-t border-gray-700 grid grid-cols-2 gap-2 text-xs">
						<div><span class="text-gray-400">Driver:</span> <span class="text-gray-300">${gpu.driver_version || 'N/A'}</span></div>
						<div><span class="text-gray-400">PCI Bus:</span> <span class="text-gray-300">${gpu['pci.bus_id'] || 'N/A'}</span></div>
						${gpu['fan.speed'] !== null && gpu['fan.speed'] !== undefined ? 
							`<div><span class="text-gray-400">Fan Speed:</span> <span class="text-gray-300">${formatPercent(gpu['fan.speed'])}</span></div>` : ''}
					</div>
				</div>
			`;
		}

		function renderProcesses(processes) {
			if (!processes || processes.length === 0) {
				return '<div class="text-center text-gray-400 py-8">No GPU processes running</div>';
			}

			let html = `
				<table class="w-full">
					<thead class="bg-gray-700 text-left">
						<tr>
							<th class="px-4 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider">GPU</th>
							<th class="px-4 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider">PID</th>
							<th class="px-4 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider">Process Name</th>
							<th class="px-4 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider">Memory Used</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-700">
			`;

			processes.forEach(proc => {
				html += `
					<tr class="hover:bg-gray-700/50">
						<td class="px-4 py-3 text-sm">${proc.gpu_bus_id}</td>
						<td class="px-4 py-3 text-sm font-mono">${proc.pid}</td>
						<td class="px-4 py-3 text-sm">${proc.process_name}</td>
						<td class="px-4 py-3 text-sm">${proc.used_memory} MiB</td>
					</tr>
				`;
			});

			html += '</tbody></table>';
			return html;
		}

		async function fetchData() {
			try {
				const response = await fetch('/');
				if (!response.ok) {
					throw new Error(`HTTP ${response.status}: ${response.statusText}`);
				}
				
				const data = await response.json();
				
				if (data.error) {
					showError('Error: ' + data.error);
					updateStatus(false);
					return;
				}

				hideError();
				updateStatus(true);

				// Render GPUs
				const gpusContainer = document.getElementById('gpus-container');
				gpusContainer.innerHTML = data.gpus.map(gpu => renderGPU(gpu)).join('');

				// Render processes
				const processesTable = document.getElementById('processes-table');
				processesTable.innerHTML = renderProcesses(data.processes);

			} catch (error) {
				showError('Failed to fetch data: ' + error.message);
				updateStatus(false);
			}
		}

		function startCountdown() {
			let seconds = 5;
			const countdownEl = document.getElementById('countdown');
			
			if (countdownTimer) clearInterval(countdownTimer);
			
			countdownTimer = setInterval(() => {
				seconds--;
				countdownEl.textContent = seconds;
				if (seconds <= 0) {
					seconds = 5;
				}
			}, 1000);
		}

		function startAutoRefresh() {
			if (autoRefreshInterval) clearInterval(autoRefreshInterval);
			
			autoRefreshInterval = setInterval(() => {
				fetchData();
			}, 5000);
		}

		// Initial fetch
		fetchData();
		startCountdown();
		startAutoRefresh();
	</script>
</body>
</html>"""

class NvidiaSmiHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		if self.path == '/':
			try:
				data = get_nvidia_smi_data()
				self.send_response(200)
				self.send_header('Content-Type', 'application/json')
				self.end_headers()
				self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
			except Exception as e:
				self.send_response(500)
				self.send_header('Content-Type', 'application/json')
				self.end_headers()
				self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
		elif self.path == '/ui':
			try:
				html = get_web_ui_html()
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write(html.encode('utf-8'))
			except Exception as e:
				self.send_response(500)
				self.send_header('Content-Type', 'text/plain')
				self.end_headers()
				self.wfile.write(str(e).encode('utf-8'))
		else:
			self.send_response(404)
			self.end_headers()

def run(server_class=HTTPServer, handler_class=NvidiaSmiHandler, port=8000):
	server_address = ('', port)
	httpd = server_class(server_address, handler_class)
	print(f'Serving on port {port}...')
	httpd.serve_forever()

if __name__ == '__main__':
	run()
