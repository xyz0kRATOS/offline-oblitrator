#!/usr/bin/env python3
# certificate_backend_integration.py
# Module to send JSON certificates to the backend for PDF generation
# This is a standalone module that doesn't modify the main GUI

import json
import requests
import os
import time
from typing import Dict, Optional, Tuple
from datetime import datetime

class CertificateBackendClient:
    """Client for interacting with the certificate PDF generation backend"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", auth_token: Optional[str] = None):
        """
        Initialize the backend client
        
        Args:
            backend_url: Base URL of the backend server
            auth_token: Optional authentication token if backend requires auth
        """
        self.backend_url = backend_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            'Content-Type': 'application/json'
        }
        if auth_token:
            self.headers['Authorization'] = f'Bearer {auth_token}'
    
    def test_connection(self) -> bool:
        """Test connection to the backend server"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Backend connection test failed: {e}")
            return False
    
    def convert_obliterator_to_sanitization_format(self, obliterator_json: Dict) -> Dict:
        """
        Convert Obliterator JSON format to the backend's expected format
        
        Args:
            obliterator_json: JSON certificate from generate_certificate.sh
            
        Returns:
            Dictionary in the format expected by the backend
        """
        # Extract the certificate payload if it's wrapped
        if 'certificate_payload' in obliterator_json:
            cert_data = obliterator_json['certificate_payload']
        else:
            cert_data = obliterator_json
        
        # Extract media info
        media_info = cert_data.get('media_information', {})
        tool_info = cert_data.get('tool_information', {})
        sanitization_event = cert_data.get('sanitization_event', {})
        compliance_info = cert_data.get('compliance_information', {})
        
        # Map to backend format
        sanitization_data = {
            'manufacturer': media_info.get('manufacturer', 'Unknown'),
            'model': media_info.get('model', 'Unknown'),
            'serial_number': media_info.get('serial_number', 'UNKNOWN'),
            'property_number': None,  # Not in Obliterator format
            'media_type': media_info.get('media_type', 'Block Device'),
            'media_source': sanitization_event.get('operator', {}).get('hostname', 'Unknown'),
            'pre_sanitization_confidentiality': media_info.get('pre_sanitization_classification', 'Unknown'),
            'sanitization_method': tool_info.get('method', 'Clear'),
            'sanitization_technique': tool_info.get('technique', '5-Pass Overwrite'),
            'tool_used': f"{tool_info.get('name', 'OBLITERATOR')} v{tool_info.get('version', 'Unknown')}",
            'verification_method': tool_info.get('verification_method', 'Zero-byte verification'),
            'post_sanitization_confidentiality': media_info.get('post_sanitization_classification', 'Unclassified'),
            'post_sanitization_destination': 'Storage/Disposal'  # Default value
        }
        
        return sanitization_data
    
    def generate_pdf_from_json(self, json_file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Send JSON certificate to backend for PDF generation
        
        Args:
            json_file_path: Path to the JSON certificate file
            
        Returns:
            Tuple of (success, pdf_url, error_message)
        """
        try:
            # Read the JSON file
            with open(json_file_path, 'r') as f:
                obliterator_json = json.load(f)
            
            # Convert to backend format
            sanitization_data = self.convert_obliterator_to_sanitization_format(obliterator_json)
            
            # Send to backend
            response = requests.post(
                f"{self.backend_url}/generate-certificate",
                json=sanitization_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                pdf_url = result.get('pdf_url')
                print(f"✅ PDF generated successfully: {pdf_url}")
                return True, pdf_url, None
            else:
                error_msg = f"Backend returned {response.status_code}: {response.text}"
                print(f"❌ PDF generation failed: {error_msg}")
                return False, None, error_msg
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error generating PDF: {error_msg}")
            return False, None, error_msg
    
    def download_pdf(self, pdf_url: str, output_path: str) -> bool:
        """
        Download PDF from URL to local file
        
        Args:
            pdf_url: URL of the PDF to download
            output_path: Local path to save the PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(pdf_url, timeout=30)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ PDF downloaded to: {output_path}")
                return True
            else:
                print(f"❌ Failed to download PDF: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error downloading PDF: {e}")
            return False
    
    def batch_process_certificates(self, cert_dir: str, output_dir: str = None) -> Dict:
        """
        Process all JSON certificates in a directory
        
        Args:
            cert_dir: Directory containing JSON certificates
            output_dir: Directory to save PDFs (optional)
            
        Returns:
            Dictionary with processing results
        """
        if not os.path.exists(cert_dir):
            return {'error': f'Certificate directory not found: {cert_dir}'}
        
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'certificates': []
        }
        
        # Find all JSON certificate files
        json_files = [f for f in os.listdir(cert_dir) if f.endswith('.json')]
        
        for json_file in json_files:
            json_path = os.path.join(cert_dir, json_file)
            print(f"\n📄 Processing: {json_file}")
            
            success, pdf_url, error = self.generate_pdf_from_json(json_path)
            
            cert_result = {
                'json_file': json_file,
                'success': success,
                'pdf_url': pdf_url,
                'error': error
            }
            
            if success and pdf_url and output_dir:
                # Download the PDF locally
                pdf_filename = json_file.replace('.json', '.pdf')
                pdf_path = os.path.join(output_dir, pdf_filename)
                if self.download_pdf(pdf_url, pdf_path):
                    cert_result['local_pdf_path'] = pdf_path
            
            results['certificates'].append(cert_result)
            results['processed'] += 1
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)
        
        return results


# Standalone script functionality
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PDF certificates from JSON')
    parser.add_argument('--backend-url', default='http://localhost:8000',
                       help='Backend server URL')
    parser.add_argument('--auth-token', help='Authentication token if required')
    parser.add_argument('--cert-dir', default='./certificates',
                       help='Directory containing JSON certificates')
    parser.add_argument('--output-dir', help='Directory to save PDF files')
    parser.add_argument('--single-file', help='Process a single JSON file')
    
    args = parser.parse_args()
    
    # Initialize client
    client = CertificateBackendClient(args.backend_url, args.auth_token)
    
    # Test connection
    print(f"🔌 Connecting to backend at {args.backend_url}...")
    if not client.test_connection():
        print("❌ Cannot connect to backend server. Is it running?")
        exit(1)
    print("✅ Backend connection successful!")
    
    if args.single_file:
        # Process single file
        success, pdf_url, error = client.generate_pdf_from_json(args.single_file)
        if success:
            print(f"✅ PDF URL: {pdf_url}")
            if args.output_dir:
                pdf_filename = os.path.basename(args.single_file).replace('.json', '.pdf')
                pdf_path = os.path.join(args.output_dir, pdf_filename)
                client.download_pdf(pdf_url, pdf_path)
        else:
            print(f"❌ Failed: {error}")
    else:
        # Batch process directory
        print(f"\n📁 Processing certificates in: {args.cert_dir}")
        results = client.batch_process_certificates(args.cert_dir, args.output_dir)
        
        print(f"\n{'='*50}")
        print(f"📊 Processing Complete!")
        print(f"{'='*50}")
        print(f"Total Processed: {results['processed']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        if results['failed'] > 0:
            print(f"\n❌ Failed certificates:")
            for cert in results['certificates']:
                if not cert['success']:
                    print(f"  - {cert['json_file']}: {cert['error']}")
