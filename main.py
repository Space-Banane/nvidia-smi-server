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
