import boto3
from concurrent.futures import ThreadPoolExecutor


def get_all_azs():
	# Create EC2 client for listing regions
	ec2 = boto3.client('ec2')

	# Get all regions, including those that require opt-in
	regions = [{'RegionName':region['RegionName'], 'OptInStatus':region['OptInStatus']} for region in ec2.describe_regions(AllRegions=True)['Regions']]
	all_azs = []

	def get_region_azs(region):
		try:
			# Create EC2 client for specific region
			regional_ec2 = boto3.client('ec2', region_name=region['RegionName'])

			# Get AZs for the region, including those that might not be enabled
			azs = regional_ec2.describe_availability_zones(
				AllAvailabilityZones=True,
				Filters=[{'Name': 'state', 'Values': ['available', 'information', 'opted-out']}]
				)['AvailabilityZones']

			# Filter to include only standard AZs (exclude Local Zones and Wavelength Zones)
			return [(az['ZoneName'], region['OptInStatus'], az['State'])
			        for az in azs if az['ZoneType'] == 'availability-zone']
		except Exception as e:
			print(f"Error getting AZs for region {region['RegionName']}: {str(e)}")
			return []

	# Use ThreadPoolExecutor to fetch AZs from all regions concurrently
	with ThreadPoolExecutor(max_workers=10) as executor:
		results = executor.map(get_region_azs, regions)

		# Combine all results
		for azs in results:
			all_azs.extend(azs)

	return sorted(all_azs)


if __name__ == '__main__':
	azs = get_all_azs()
	print("All Availability Zones (including opt-in required regions):")
	print("Format: (AZ Name, Opt-in Status, State)")
	for az in azs:
		print(az)
