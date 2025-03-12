import psutil
import time
import requests
from datetime import datetime, timezone
import json
import threading
from queue import Queue

class PCCollector:
    def get_process_count(self):
        return len(psutil.pids())
    
    def get_cpu_frequency(self):
        try:
            # Get current CPU frequency in MHz
            freq = psutil.cpu_freq()
            if freq:
                return freq.current
            return None
        except:
            return None

class ThirdPartyCollector:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.last_request_time = 0
        self.min_interval = 5  # Binance allows more frequent requests

    def get_crypto_price(self, symbol='BTCUSDT'):
        current_time = time.time()
        if current_time - self.last_request_time < self.min_interval:
            return None
        
        try:
            response = requests.get(f"{self.base_url}/ticker/price", params={"symbol": symbol})
            if response.status_code == 200:
                self.last_request_time = current_time
                return float(response.json()['price'])
            else:
                print(f"Error fetching crypto price: {response.text}")
                return None
        except Exception as e:
            print(f"Error fetching crypto price: {str(e)}")
            return None

class UploaderQueue:
    def __init__(self, api_url='https://patrickwalsh3333.pythonanywhere.com/api/metrics'):
        self.queue = Queue()
        self.api_url = api_url
        self.running = True
        self.upload_thread = threading.Thread(target=self._upload_worker)
        self.upload_thread.daemon = True
        self.upload_thread.start()

    def add_metric(self, device_name, metric_name, value):
        if value is not None:  # Only queue metrics with valid values
            metric_data = {
                'device_name': device_name,
                'metric_name': metric_name,
                'value': value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.queue.put(metric_data)

    def _upload_worker(self):
        while self.running:
            try:
                if not self.queue.empty():
                    metric_data = self.queue.get()
                    try:
                        # Add error handling for connection issues
                        response = requests.post(
                            self.api_url, 
                            json=metric_data,
                            timeout=10  # Add timeout
                        )
                        if response.status_code != 200:
                            print(f"Failed to upload metric: {response.text}")
                            # Put failed metrics back in queue
                            self.queue.put(metric_data)
                    except requests.exceptions.RequestException as e:
                        print(f"Connection error: {str(e)}")
                        # Put failed metrics back in queue
                        self.queue.put(metric_data)
                        time.sleep(5)  # Wait before retry
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in upload worker: {str(e)}")
                time.sleep(1)

def main():
    print("Starting collectors...")
    pc_collector = PCCollector()
    third_party_collector = ThirdPartyCollector()
    uploader = UploaderQueue()

    print("Collecting metrics. Press Ctrl+C to stop.")
    try:
        while True:
              # Collect PC metrics
            process_count = pc_collector.get_process_count()
            cpu_freq = pc_collector.get_cpu_frequency()

            # Collect third-party metric (BTC price)
            crypto_price = third_party_collector.get_crypto_price()

            # Upload metrics
            uploader.add_metric('Device_1', 'Process_Count', process_count)
            if cpu_freq is not None:
                uploader.add_metric('Device_1', 'CPU_Frequency', cpu_freq)
            if crypto_price:
                uploader.add_metric('Device_2', 'BTC_Price', crypto_price) 
            time.sleep(5)  # Collect metrics every 5 seconds
    except KeyboardInterrupt:
        print("\nStopping collectors...")
        uploader.running = False
        print("Collectors stopped.")

if __name__ == '__main__':
    main() 