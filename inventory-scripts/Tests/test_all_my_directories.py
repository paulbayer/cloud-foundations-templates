import unittest
from unittest.mock import patch, MagicMock
from ..all_my_directories import parse_args, find_all_directories


class TestAllMyDirectories(unittest.TestCase):
	def setUp(self):
		"""Set up any necessary test fixtures"""
		self.sample_credentials = {
			'profile': 'test-profile',
			'region' : 'us-west-2',
			'account': '123456789012'
			}

	def test_parse_args_with_valid_input(self):
		"""Test parse_args with valid command line arguments"""
		test_args = [
			'--profile', 'test-profile',
			'--regions', 'us-west-2',
			'--fragment', 'test-fragment',
			'--timing',
			'--root-only'
			]

		args = parse_args(test_args)

		self.assertEqual(args.profile, ['test-profile'])
		self.assertEqual(args.regions, ['us-west-2'])
		self.assertEqual(args.fragment, 'test-fragment')
		self.assertTrue(args.timing)
		self.assertTrue(args.root_only)

	def test_parse_args_with_multiple_profiles(self):
		"""Test parse_args with multiple profiles"""
		test_args = [
			'--profile', 'profile1', 'profile2',
			'--regions', 'us-west-2'
			]

		args = parse_args(test_args)

		self.assertEqual(args.profile, ['profile1', 'profile2'])

	@patch('all_my_directories.find_directories2')
	def test_find_all_directories(self, mock_find_directories):
		"""Test find_all_directories with mocked dependencies"""
		# Setup mock return value
		mock_find_directories.return_value = ['dir1', 'dir2']

		# Test with sample fragments and exact match
		fragments = ['test']
		exact = False

		result = find_all_directories(self.sample_credentials, fragments, exact)

		# Verify the results
		mock_find_directories.assert_called_once()
		self.assertIsInstance(result, list)

	def test_find_all_directories_with_empty_credentials(self):
		"""Test find_all_directories with empty credentials"""
		with self.assertRaises(ValueError):
			find_all_directories({}, ['test'], False)


if __name__ == '__main__':
	unittest.main()
