# app.py
# Main launcher for GTO ATL Jira Operations Center

from flask import Flask, render_template, jsonify, request, redirect, url_for
import sys
import os
import importlib.util

from config_manager import list_instances, inject_config_to_framework, validate_instance_config

app = Flask(__name__)
# Set secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-' + os.urandom(24).hex())

# Store for framework initialization
_framework_modules = {}

# Framework definitions (must be before registration)
FRAMEWORKS = {
    "health-dashboard": {
        "name": "Health Dashboard",
        "description": "Comprehensive health monitoring for Jira clusters",
        "icon": "📊",
        "module": "health_dashboard",
        "port_offset": 0  # Will use main port
    },
    "response-tracker": {
        "name": "Response Time Tracker",
        "description": "Monitor slow requests from Jira access logs",
        "icon": "⏱️",
        "module": "response_tracker",
        "port_offset": 0
    },
    "preflight-validator": {
        "name": "Preflight Validator",
        "description": "Pre-deployment validation for Jira Data Center nodes",
        "icon": "✅",
        "module": "preflight_validator",
        "port_offset": 0
    },
    "script-executor": {
        "name": "Script Executor",
        "description": "Execute scripts on multiple servers via SSH",
        "icon": "🔧",
        "module": "script_executor",
        "port_offset": 0
    }
}

# Pre-register all framework blueprints at startup (Flask requirement)
# They'll be initialized with config when an instance is selected
def register_framework_blueprints():
    """Register all framework blueprints at startup."""
    frameworks_dir = os.path.join(os.path.dirname(__file__), 'frameworks')
    
    for framework_id, framework_info in FRAMEWORKS.items():
        framework_module_name = framework_info["module"]
        framework_path = os.path.join(frameworks_dir, framework_module_name, 'app.py')
        
        if os.path.exists(framework_path):
            try:
                # Use unique module name to avoid conflicts
                module_name = f"frameworks_{framework_module_name}_app"
                
                # Load the module
                spec = importlib.util.spec_from_file_location(
                    module_name, 
                    framework_path
                )
                framework_module = importlib.util.module_from_spec(spec)
                
                # Add paths for config imports
                framework_dir_path = os.path.dirname(framework_path)
                if framework_dir_path not in sys.path:
                    sys.path.insert(0, framework_dir_path)
                parent_dir = os.path.dirname(os.path.dirname(framework_path))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                
                # Execute the module
                spec.loader.exec_module(framework_module)
                
                # Get the blueprint
                if not hasattr(framework_module, 'app'):
                    raise AttributeError(f"Framework {framework_id} module does not have 'app' attribute")
                
                framework_blueprint = framework_module.app
                
                # Store module for later config injection
                _framework_modules[framework_id] = framework_module
                
                # Register blueprint (will be initialized later with config)
                app.register_blueprint(framework_blueprint, url_prefix=f'/{framework_id}')
                print(f"✓ Registered framework: {framework_id}")
            except Exception as e:
                # Log but don't fail - framework might not be ready yet
                import traceback
                print(f"✗ Warning: Could not pre-register {framework_id}: {e}")
                print(traceback.format_exc())
                # Store None so we know it failed
                _framework_modules[framework_id] = None

# Register all blueprints at startup
register_framework_blueprints()

@app.route('/')
def index():
    """Main selection page - choose framework and instance."""
    instances = list_instances()
    return render_template('main.html', frameworks=FRAMEWORKS, instances=instances)

@app.route('/api/instances')
def api_instances():
    """API endpoint to list all instances."""
    instances = list_instances()
    return jsonify(instances)

@app.route('/api/frameworks')
def api_frameworks():
    """API endpoint to list all frameworks."""
    return jsonify(FRAMEWORKS)

@app.route('/launch/<framework_id>')
def launch_framework(framework_id):
    """Launch a framework with instance selection."""
    if framework_id not in FRAMEWORKS:
        return jsonify({"error": "Framework not found"}), 404
    
    instance_id = request.args.get('instance_id')
    if not instance_id:
        # Show instance selection page
        instances = list_instances()
        framework = FRAMEWORKS[framework_id]
        return render_template('select_instance.html', 
                             framework=framework, 
                             framework_id=framework_id,
                             instances=instances)
    
    # Validate instance
    is_valid, errors = validate_instance_config(instance_id)
    if not is_valid:
        return jsonify({"error": "Invalid instance configuration", "details": errors}), 400
    
    # Inject configuration
    try:
        instance_config = inject_config_to_framework(framework_id, instance_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # Blueprint is already registered at startup
    # Initialize it with the instance config
    try:
        # Store instance config in config_manager for framework to access
        import config_manager
        config_manager._injected_configs[framework_id] = instance_config
        
        # Get the already-loaded framework module
        if framework_id in _framework_modules and _framework_modules[framework_id] is not None:
            framework_module = _framework_modules[framework_id]
            
            # Initialize with config if method exists
            if hasattr(framework_module, 'initialize_with_config'):
                framework_module.initialize_with_config(instance_config)
            
            # Also try to reload config in the framework
            # The framework's config should read from config_manager
            framework_module_name = FRAMEWORKS[framework_id]["module"]
            framework_dir = os.path.join(os.path.dirname(__file__), 'frameworks', framework_module_name)
            config_path = os.path.join(framework_dir, 'config.py')
            
            if os.path.exists(config_path):
                # Reload config module with injected config
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"{framework_module_name}_config", 
                    config_path
                )
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                
                # Inject config
                if hasattr(config_module, 'inject_config'):
                    config_module.inject_config(instance_config)
                
                # Update sys.modules so framework can import it
                sys.modules['config'] = config_module
        else:
            return jsonify({"error": f"Framework {framework_id} not loaded"}), 500
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": f"Failed to initialize framework: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500
    
    # Redirect to framework's main page
    redirect_url = f'/{framework_id}/'
    print(f"DEBUG: Redirecting to {redirect_url} for framework {framework_id}")
    return redirect(redirect_url)

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "gto-ATL-Jira-ops-center"})

if __name__ == '__main__':
    # Default port (using 8000 to avoid Chrome's ERR_UNSAFE_PORT for port 6000)
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)
