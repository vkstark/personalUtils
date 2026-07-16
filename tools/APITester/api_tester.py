#!/usr/bin/env python3
"""
APITester - HTTP API Testing Tool
Quick and friendly HTTP API testing with history and response formatting.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import contextlib
import ipaddress
import json
import socket
import time
from urllib import request, error, parse
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path


class SSRFError(Exception):
    """Raised when a request target resolves to a disallowed (internal) address."""


def _ip_is_blocked(ip_str: str) -> bool:
    """True if the IP is loopback/link-local/private/reserved (SSRF targets).

    169.254.169.254 (cloud metadata) is link-local and therefore blocked here.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_loopback or ip.is_link_local or ip.is_private
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


class _ValidatingRedirectHandler(request.HTTPRedirectHandler):
    """Follows redirects but refuses to jump to a non-http(s) scheme.

    IP-level validation of the redirect target is handled uniformly by the
    _ssrf_guarded_dns() socket guard, which checks every host resolution
    (initial and each hop) at connect time.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        scheme = parse.urlparse(newurl).scheme
        if scheme not in ("http", "https"):
            raise SSRFError(f"Refusing redirect to non-http(s) URL: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@contextlib.contextmanager
def _ssrf_guarded_dns():
    """Validate every DNS resolution against the private-IP block-list.

    By checking inside getaddrinfo, the address that is validated is the exact
    address the socket then connects to — closing the TOCTOU / DNS-rebinding gap
    a separate pre-flight check would leave open. Also covers each redirect hop.
    """
    real_getaddrinfo = socket.getaddrinfo

    def guarded(host, *args, **kwargs):
        infos = real_getaddrinfo(host, *args, **kwargs)
        for info in infos:
            ip = info[4][0]
            if _ip_is_blocked(ip):
                raise SSRFError(
                    f"Refusing to connect to '{host}': resolves to blocked "
                    f"internal/private address {ip}"
                )
        return infos

    socket.getaddrinfo = guarded
    try:
        yield
    finally:
        socket.getaddrinfo = real_getaddrinfo

# Color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'

    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_CYAN = '\033[96m'

class APITester:
    """HTTP API tester"""

    def __init__(self, colors: bool = True, verbose: bool = False):
        self.colors = colors and self._supports_color()
        self.verbose = verbose
        self.history_file = Path.home() / '.api_tester_history.json'

    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb')

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def request(self, url: str, method: str = 'GET',
                headers: Optional[Dict[str, str]] = None,
                data: Optional[str] = None,
                timeout: int = 30) -> Dict[str, Any]:
        """Make HTTP request"""

        # Prepare headers
        req_headers = headers or {}
        if data and 'Content-Type' not in req_headers:
            req_headers['Content-Type'] = 'application/json'

        # Prepare data
        req_data = None
        if data:
            if isinstance(data, str):
                req_data = data.encode('utf-8')
            else:
                req_data = json.dumps(data).encode('utf-8')

        # SSRF: only http(s), and reject before we do any work
        scheme = parse.urlparse(url).scheme.lower()
        if scheme not in ("http", "https"):
            return {
                "success": False,
                "error": f"Only http/https URLs are allowed (got scheme '{scheme or 'none'}')",
                "time": 0.0,
            }

        # Create request
        req = request.Request(url, data=req_data, headers=req_headers, method=method)

        # Install a validating opener so redirects are re-checked at each hop.
        # Calling request.urlopen (not opener.open) keeps this interceptable by
        # the standard urllib.request.urlopen mock in tests.
        request.install_opener(request.build_opener(_ValidatingRedirectHandler()))

        # Make request
        start_time = time.time()

        try:
            with _ssrf_guarded_dns(), request.urlopen(req, timeout=timeout) as response:
                response_time = time.time() - start_time
                body = response.read().decode('utf-8')

                # Try to parse as JSON
                try:
                    body_json = json.loads(body)
                except json.JSONDecodeError:
                    body_json = None

                result = {
                    'status': response.status,
                    'headers': dict(response.headers),
                    'body': body,
                    'body_json': body_json,
                    'time': response_time,
                    'success': True
                }

        except SSRFError as e:
            return {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time,
            }

        except error.HTTPError as e:
            response_time = time.time() - start_time
            body = e.read().decode('utf-8') if e.fp else ''

            try:
                body_json = json.loads(body) if body else None
            except (json.JSONDecodeError, ValueError):
                body_json = None

            result = {
                'status': e.code,
                'headers': dict(e.headers) if hasattr(e, 'headers') else {},
                'body': body,
                'body_json': body_json,
                'time': response_time,
                'success': False,
                'error': str(e)
            }

        except error.URLError as e:
            result = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }

        except Exception as e:
            result = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }

        return result

    def format_response(self, response: Dict[str, Any], show_headers: bool = False) -> str:
        """Format response for display"""
        output = []

        # Status
        if 'status' in response:
            status = response['status']
            if 200 <= status < 300:
                status_color = Colors.GREEN
            elif 300 <= status < 400:
                status_color = Colors.YELLOW
            else:
                status_color = Colors.RED

            status_text = self._colorize(f"Status: {status}", status_color + Colors.BOLD)
            time_text = self._colorize(f"Time: {response['time']:.3f}s", Colors.DIM)
            output.append(f"{status_text} | {time_text}\n")

        # Headers
        if show_headers and 'headers' in response:
            output.append(self._colorize("Headers:", Colors.CYAN + Colors.BOLD))
            for key, value in response['headers'].items():
                output.append(f"  {key}: {value}")
            output.append("")

        # Body
        if 'body_json' in response and response['body_json'] is not None:
            output.append(self._colorize("Response (JSON):", Colors.BRIGHT_CYAN + Colors.BOLD))
            output.append(json.dumps(response['body_json'], indent=2, ensure_ascii=False))
        elif 'body' in response and response['body']:
            output.append(self._colorize("Response:", Colors.BRIGHT_CYAN + Colors.BOLD))
            output.append(response['body'][:1000])
            if len(response['body']) > 1000:
                output.append(self._colorize("... (truncated)", Colors.DIM))

        # Error
        if not response.get('success'):
            output.append(self._colorize(f"\nError: {response.get('error', 'Unknown error')}", Colors.RED))

        return '\n'.join(output)

    def save_to_history(self, url: str, method: str, response: Dict[str, Any]):
        """Save request to history"""
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)

            history.append({
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'method': method,
                'status': response.get('status'),
                'time': response.get('time')
            })

            # Keep last 100
            history = history[-100:]

            # Create 0600 (history can contain URLs/tokens); match the
            # conversation-history at-rest model rather than the umask default.
            # The chmod also tightens a pre-existing file left loose by an
            # older version (O_CREAT's mode only applies on creation).
            fd = os.open(self.history_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.chmod(self.history_file, 0o600)
            except OSError:
                pass
            with os.fdopen(fd, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            if self.verbose:
                print(f"Could not save history: {e}", file=sys.stderr)

    def show_history(self, limit: int = 10):
        """Show request history"""
        if not self.history_file.exists():
            print("No history found")
            return

        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)

            history = history[-limit:]

            print(f"\n{self._colorize('Recent Requests:', Colors.BRIGHT_CYAN + Colors.BOLD)}\n")

            for i, entry in enumerate(reversed(history), 1):
                timestamp = entry.get('timestamp', 'Unknown')
                method = entry.get('method', 'GET')
                url = entry.get('url', '')
                status = entry.get('status', 'N/A')
                req_time = entry.get('time', 0)

                status_str = str(status) if status else 'N/A'
                time_str = f"{req_time:.3f}s" if req_time else 'N/A'

                print(f"{i}. [{timestamp[:19]}] {method} {url}")
                print(f"   Status: {status_str} | Time: {time_str}\n")

        except Exception as e:
            print(f"Error reading history: {e}", file=sys.stderr)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="APITester - HTTP API Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # GET request
  %(prog)s GET https://api.example.com/users

  # POST with JSON data
  %(prog)s POST https://api.example.com/users -d '{"name":"John"}'

  # With custom headers
  %(prog)s GET https://api.example.com/users -H "Authorization: Bearer TOKEN"

  # Show response headers
  %(prog)s GET https://api.example.com/users --show-headers

  # View history
  %(prog)s --history
        """)

    parser.add_argument('method', nargs='?', help='HTTP method (GET, POST, PUT, DELETE, etc.)')
    parser.add_argument('url', nargs='?', help='URL to request')

    # Request options
    parser.add_argument('-d', '--data', help='Request body (JSON string)')
    parser.add_argument('-H', '--header', action='append', help='Custom headers (can be used multiple times)')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='Timeout in seconds (default: 30)')

    # Display options
    parser.add_argument('--show-headers', action='store_true', help='Show response headers')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    # History
    parser.add_argument('--history', action='store_true', help='Show request history')
    parser.add_argument('--limit', type=int, default=10, help='History limit (default: 10)')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    tester = APITester(colors=not args.no_color, verbose=args.verbose)

    # Show history
    if args.history:
        tester.show_history(args.limit)
        sys.exit(0)

    # Validate required arguments
    if not args.method or not args.url:
        parser.print_help()
        sys.exit(1)

    try:
        # Parse headers
        headers = {}
        if args.header:
            for header in args.header:
                if ':' in header:
                    key, value = header.split(':', 1)
                    headers[key.strip()] = value.strip()

        # Make request
        print(f"{tester._colorize('Requesting:', Colors.CYAN)} {args.method} {args.url}\n")

        response = tester.request(
            args.url,
            method=args.method.upper(),
            headers=headers,
            data=args.data,
            timeout=args.timeout
        )

        # Save to history
        tester.save_to_history(args.url, args.method.upper(), response)

        # Display response
        print(tester.format_response(response, args.show_headers))

        # Exit with error code if request failed
        sys.exit(0 if response.get('success') else 1)

    except KeyboardInterrupt:
        print("\n\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
