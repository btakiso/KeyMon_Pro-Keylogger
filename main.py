import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Setup the environment and required paths"""
    try:
        # Get the absolute path of the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        # Add project root and src directory to Python path
        src_dir = os.path.join(project_root, 'src')
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            
        return True
    except Exception as e:
        logger.error(f"Error setting up environment: {e}")
        return False

def main():
    """Main entry point for the application"""
    try:
        # Setup environment
        if not setup_environment():
            logger.error("Failed to setup environment")
            return
        
        # Import GUI after environment setup
        try:
            from src.gui import MonitoringGUI
        except ImportError as e:
            logger.error(f"Error importing GUI module: {e}")
            return
        
        # Create and run GUI
        app = MonitoringGUI()
        app.run()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
