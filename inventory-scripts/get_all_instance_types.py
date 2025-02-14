import boto3
from tabulate import tabulate
import os
from collections import Counter


def get_instance_type_info():
	# Initialize EC2 client
	ec2 = boto3.client('ec2',
	                   aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
	                   aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
	                   region_name=os.environ.get('AWS_REGION', 'us-east-1')
	                   )

	# Get all instance type information
	paginator = ec2.get_paginator('describe_instance_types')

	instance_data = []

	try:
		for page in paginator.paginate():
			for instance in page['InstanceTypes']:
				# Extract relevant information
				instance_info = {
					'Instance Type'      : instance['InstanceType'],
					'Hypervisor'         : instance.get('Hypervisor', 'N/A'),
					'CPU Manufacturer'   : instance.get('ProcessorInfo', {}).get('SupportedArchitectures', ['N/A'])[0],
					'Current Generation' : instance.get('CurrentGeneration', 'N/A'),
					'Memory (GiB)'       : instance.get('MemoryInfo', {}).get('SizeInMiB', 0) / 1024,
					'Storage'            : get_storage_info(instance),
					'Network Performance': instance.get('NetworkInfo', {}).get('NetworkPerformance', 'N/A')
					}
				instance_data.append(instance_info)

	except Exception as e:
		print(f"Error fetching instance information: {str(e)}")
		return None

	return instance_data


def get_storage_info(instance):
	"""Helper function to format storage information"""
	if 'InstanceStorageInfo' not in instance:
		return 'EBS only'

	storage = instance['InstanceStorageInfo']
	total_size = storage.get('TotalSizeInGB', 0)

	if total_size == 0:
		return 'EBS only'
	else:
		return f"{total_size} GB"


def get_summary_stats(instance_data):
	"""Generate summary statistics for instance types"""
	summary = {
		'total_instances'  : len(instance_data),
		'hypervisors'      : Counter(i['Hypervisor'] for i in instance_data),
		'cpu_manufacturers': Counter(i['CPU Manufacturer'] for i in instance_data),
		'current_gen'      : Counter(i['Current Generation'] for i in instance_data),
		'storage_types'    : Counter(i['Storage'] == 'EBS only' for i in instance_data)
		}
	return summary


def print_summary(summary):
	"""Print formatted summary statistics"""
	print("\n=== Instance Type Summary ===")
	print(f"Total Instance Types: {summary['total_instances']}")

	print("\nHypervisor Distribution:")
	for hypervisor, count in summary['hypervisors'].items():
		print(f"  {hypervisor}: {count}")

	print("\nCPU Architecture Distribution:")
	for cpu, count in summary['cpu_manufacturers'].items():
		print(f"  {cpu}: {count}")

	print("\nGeneration Distribution:")
	current_gen = summary['current_gen'][True]
	previous_gen = summary['current_gen'][False]
	print(f"  Current Generation: {current_gen}")
	print(f"  Previous Generation: {previous_gen}")

	print("\nStorage Type Distribution:")
	ebs_only = summary['storage_types'][True]
	local_storage = summary['storage_types'][False]
	print(f"  EBS-only: {ebs_only}")
	print(f"  With Local Storage: {local_storage}")


def main():
	# Get instance information
	instance_data = get_instance_type_info()

	if instance_data:
		# Sort by instance type name
		instance_data.sort(key=lambda x: x['Instance Type'])

		# Print table
		headers = instance_data[0].keys()
		table = [[row[col] for col in headers] for row in instance_data]
		print(tabulate(table, headers=headers, tablefmt='grid'))

		# Generate and print summary statistics
		summary = get_summary_stats(instance_data)
		print_summary(summary)


if __name__ == "__main__":
	main()
