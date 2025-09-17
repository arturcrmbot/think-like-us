#!/usr/bin/env python3
"""
Simple HTTP server to serve the Telco Retention Dashboard frontend
Serves the dashboard on port 8050 as requested
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Configuration
PORT = 8050
DIRECTORY = Path(__file__).parent

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with better CORS and error handling"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    """Start the HTTP server"""
    print("Starting Telco Retention Dashboard Frontend Server")
    print(f"Serving from: {DIRECTORY}")
    print(f"Server will run on: http://localhost:{PORT}")
    print("Dashboard URL: http://localhost:8050/index.html")
    print("Backend API should be running on: http://localhost:8000")
    print("\n" + "="*60)
    
    # Check if required files exist
    required_files = ['index.html', 'app.js', 'styles.css']
    missing_files = []
    
    for file in required_files:
        file_path = DIRECTORY / file
        if not file_path.exists():
            missing_files.append(file)
        else:
            print(f"Found: {file}")
    
    if missing_files:
        print(f"ERROR: Missing files: {missing_files}")
        print("Please ensure all dashboard files are in the same directory as this script.")
        sys.exit(1)
    
    print("="*60 + "\n")
    
    try:
        # Create and start the server
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"Server started successfully on port {PORT}")
            print("Auto-refresh: The dashboard will automatically reload when you save changes")
            print("Press Ctrl+C to stop the server\n")
            
            # Start serving
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"ERROR: Port {PORT} is already in use!")
            print(f"Please check if another server is running on port {PORT}")
            print("You can try changing the PORT variable in this script to use a different port.")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
        print("👋 Thanks for using the Telco Retention Dashboard!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()