import threading
import time
import psutil
from datetime import datetime

class ProcessMonitor:
    def __init__(self, stop_event=None, interval=5):
        self.stop_event = stop_event or threading.Event()
        self.interval = interval
        self.previous_processes = set()
        
    def start(self):
        """Start monitoring processes"""
        try:
            while not self.stop_event.is_set():
                try:
                    self.check_processes()
                    time.sleep(self.interval)
                except Exception as e:
                    print(f"Error monitoring processes: {e}")
                    time.sleep(1)
        except Exception as e:
            print(f"Process monitor thread error: {e}")

    def check_processes(self):
        """Check for new and terminated processes"""
        try:
            # Get current running processes
            current_processes = set()
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    process_info = proc.info
                    current_processes.add(process_info['pid'])
                    
                    # Log process info
                    self.log_process(
                        pid=process_info['pid'],
                        name=process_info['name'],
                        cpu_percent=process_info['cpu_percent']
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Check for terminated processes
            terminated = self.previous_processes - current_processes
            if terminated:
                for pid in terminated:
                    self.log_process_termination(pid)
            
            self.previous_processes = current_processes
            
        except Exception as e:
            print(f"Error in check_processes: {e}")

    def log_process(self, pid, name, cpu_percent):
        """Log process information"""
        try:
            from src.central_logger import central_logger
            central_logger.log_event("process", {
                "pid": pid,
                "name": name,
                "cpu_percent": cpu_percent,
                "status": "running",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error logging process: {e}")

    def log_process_termination(self, pid):
        """Log when a process terminates"""
        try:
            from src.central_logger import central_logger
            central_logger.log_event("process", {
                "pid": pid,
                "status": "terminated",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error logging process termination: {e}")

    def stop(self):
        """Stop the process monitor"""
        if self.stop_event:
            self.stop_event.set()

if __name__ == "__main__":
    from threading import Event
    stop_event = Event()
    monitor = ProcessMonitor(stop_event)
    monitor.start()
