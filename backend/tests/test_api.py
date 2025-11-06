import pytest
import json

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'service' in data
    assert 'connected_users' in data

# Add your own API tests here following the same pattern
def test_example_placeholder(client):
    """Example test - replace with your own tests"""
    # TODO: Add your custom test here
    assert True
