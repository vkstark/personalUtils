"""
Tests for APITester utility
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).parent.parent))

from APITester.api_tester import APITester


class TestAPITester:
    """Test cases for APITester"""

    @pytest.fixture
    def tester(self, temp_dir):
        """Create APITester instance with temp history file"""
        tester = APITester(colors=False)
        # Override history file to temp location
        tester.history_file = temp_dir / '.api_tester_history.json'
        return tester

    @patch('urllib.request.urlopen')
    def test_successful_get_request(self, mock_urlopen, tester):
        """Test successful GET request"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = tester.request('https://api.example.com/test')

        assert result['success'] is True
        assert result['status'] == 200
        assert result['body_json'] == {'status': 'ok'}
        assert 'time' in result

    @patch('urllib.request.urlopen')
    def test_post_request_with_data(self, mock_urlopen, tester):
        """Test POST request with JSON data"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"id": 123}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = '{"name": "Test"}'
        result = tester.request('https://api.example.com/users', method='POST', data=data)

        assert result['success'] is True
        assert result['status'] == 201
        assert result['body_json'] == {'id': 123}

    @patch('urllib.request.urlopen')
    def test_http_error_handling(self, mock_urlopen, tester):
        """Test handling HTTP error responses"""
        # Mock HTTP 404 error
        mock_error = HTTPError(
            url='https://api.example.com/notfound',
            code=404,
            msg='Not Found',
            hdrs={},
            fp=None
        )
        mock_urlopen.side_effect = mock_error

        result = tester.request('https://api.example.com/notfound')

        assert result['success'] is False
        assert result['status'] == 404

    @patch('urllib.request.urlopen')
    def test_network_error_handling(self, mock_urlopen, tester):
        """Test handling network errors"""
        mock_urlopen.side_effect = URLError('Network error')

        result = tester.request('https://api.example.com/test')

        assert result['success'] is False
        assert 'error' in result
        assert 'Network error' in result['error']

    @patch('urllib.request.urlopen')
    def test_custom_headers(self, mock_urlopen, tester):
        """Test request with custom headers"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'OK'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        headers = {'Authorization': 'Bearer TOKEN'}
        result = tester.request('https://api.example.com/test', headers=headers)

        # Verify request was called
        assert mock_urlopen.called


class TestResponseFormatting:
    """Test response formatting"""

    @pytest.fixture
    def tester(self):
        return APITester(colors=False)

    def test_format_successful_response(self, tester):
        """Test formatting successful response"""
        response = {
            'status': 200,
            'time': 0.5,
            'body_json': {'message': 'Success'},
            'success': True
        }

        formatted = tester.format_response(response)

        assert 'Status: 200' in formatted
        assert 'Time: 0.500s' in formatted
        assert 'Success' in formatted

    def test_format_error_response(self, tester):
        """Test formatting error response"""
        response = {
            'status': 500,
            'time': 0.3,
            'success': False,
            'error': 'Internal Server Error'
        }

        formatted = tester.format_response(response)

        assert 'Status: 500' in formatted
        assert 'Error: Internal Server Error' in formatted

    def test_format_with_headers(self, tester):
        """Test formatting response with headers"""
        response = {
            'status': 200,
            'time': 0.5,
            'headers': {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            'body_json': {'data': 'test'},
            'success': True
        }

        formatted = tester.format_response(response, show_headers=True)

        assert 'Headers:' in formatted
        assert 'Content-Type' in formatted
        assert 'Cache-Control' in formatted

    def test_format_non_json_response(self, tester):
        """Test formatting non-JSON response"""
        response = {
            'status': 200,
            'time': 0.5,
            'body': 'Plain text response',
            'body_json': None,
            'success': True
        }

        formatted = tester.format_response(response)

        assert 'Plain text response' in formatted


class TestHistory:
    """Test history functionality"""

    @pytest.fixture
    def tester(self, temp_dir):
        """Create APITester instance with temp history file"""
        tester = APITester(colors=False)
        tester.history_file = temp_dir / '.api_tester_history.json'
        return tester

    def test_save_to_history(self, tester):
        """Test saving request to history"""
        response = {
            'status': 200,
            'time': 0.5,
            'success': True
        }

        tester.save_to_history('https://api.example.com/test', 'GET', response)

        # History file should exist
        assert tester.history_file.exists()

        # Load and verify
        with open(tester.history_file) as f:
            history = json.load(f)

        assert len(history) == 1
        assert history[0]['url'] == 'https://api.example.com/test'
        assert history[0]['method'] == 'GET'
        assert history[0]['status'] == 200

    def test_history_limit(self, tester):
        """Test history keeps only last 100 entries"""
        response = {'status': 200, 'time': 0.5, 'success': True}

        # Add 105 entries
        for i in range(105):
            tester.save_to_history(f'https://api.example.com/test{i}', 'GET', response)

        # Load history
        with open(tester.history_file) as f:
            history = json.load(f)

        # Should only keep last 100
        assert len(history) == 100

    def test_show_history_empty(self, tester, capsys):
        """Test showing history when none exists"""
        tester.show_history()

        captured = capsys.readouterr()
        assert 'No history found' in captured.out

    def test_show_history_with_entries(self, tester, capsys):
        """Test showing history with entries"""
        response = {'status': 200, 'time': 0.5, 'success': True}
        tester.save_to_history('https://api.example.com/test', 'GET', response)

        tester.show_history()

        captured = capsys.readouterr()
        assert 'Recent Requests:' in captured.out
        assert 'https://api.example.com/test' in captured.out
        assert 'GET' in captured.out


class TestRequestMethods:
    """Test different HTTP methods"""

    @pytest.fixture
    def tester(self):
        return APITester(colors=False)

    @patch('urllib.request.urlopen')
    def test_put_request(self, mock_urlopen, tester):
        """Test PUT request"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'{}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = tester.request('https://api.example.com/test', method='PUT', data='{"key": "value"}')

        assert result['success'] is True

    @patch('urllib.request.urlopen')
    def test_delete_request(self, mock_urlopen, tester):
        """Test DELETE request"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.headers = {}
        mock_response.read.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = tester.request('https://api.example.com/test', method='DELETE')

        assert result['success'] is True
        assert result['status'] == 204
