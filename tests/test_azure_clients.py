import unittest
from unittest.mock import patch, MagicMock
from src.azure.aks_client import AKSClient
from src.azure.network_client import NetworkClient

class TestAzureClients(unittest.TestCase):

    @patch.object(AKSClient, 'get_node_pools')
    def test_get_node_pools_success(self, mock_get_node_pools):
        mock_get_node_pools.return_value = [
            {'name': 'nodepool1', 'count': 3},
            {'name': 'nodepool2', 'count': 5}
        ]
        client = AKSClient()
        node_pools = client.get_node_pools()
        self.assertEqual(len(node_pools), 2)
        self.assertEqual(node_pools[0]['name'], 'nodepool1')
        self.assertEqual(node_pools[0]['count'], 3)

    @patch.object(NetworkClient, 'get_subnet_info')
    def test_get_subnet_info_success(self, mock_get_subnet_info):
        mock_get_subnet_info.return_value = {
            'name': 'subnet1',
            'address_prefix': '10.0.0.0/24',
            'ip_count': 256
        }
        client = NetworkClient()
        subnet_info = client.get_subnet_info('subnet1')
        self.assertEqual(subnet_info['name'], 'subnet1')
        self.assertEqual(subnet_info['ip_count'], 256)

    @patch.object(AKSClient, 'get_node_pools')
    def test_get_node_pools_failure(self, mock_get_node_pools):
        mock_get_node_pools.side_effect = Exception("Failed to retrieve node pools")
        client = AKSClient()
        with self.assertRaises(Exception) as context:
            client.get_node_pools()
        self.assertTrue('Failed to retrieve node pools' in str(context.exception))

    @patch.object(NetworkClient, 'get_subnet_info')
    def test_get_subnet_info_failure(self, mock_get_subnet_info):
        mock_get_subnet_info.side_effect = Exception("Failed to retrieve subnet info")
        client = NetworkClient()
        with self.assertRaises(Exception) as context:
            client.get_subnet_info('subnet1')
        self.assertTrue('Failed to retrieve subnet info' in str(context.exception))

if __name__ == '__main__':
    unittest.main()