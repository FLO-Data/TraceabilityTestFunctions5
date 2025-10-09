import azure.functions as func
import logging
import json

# Import all blueprints with real database functionality
from InfoStatus import bp as info_status_bp
from GetInfoGitter import bp as get_info_gitter_bp
from ReadStatus import bp as read_status_bp
from ChangeStatus import bp as change_status_bp
from KovaciLinkaCheck import bp as kovaci_linka_check_bp
from KovaciLinkaScan import bp as kovaci_linka_scan_bp
from ProtocolPartInsert import bp as protocol_part_insert_bp
from CheckInsert import bp as check_insert_bp

app = func.FunctionApp()

# Register all blueprints
app.register_functions(info_status_bp)          # GET /api/InfoStatus
app.register_functions(get_info_gitter_bp)      # GET /api/GetInfoGitter
app.register_functions(read_status_bp)          # GET /api/readstatus
app.register_functions(change_status_bp)        # POST /api/ChangeStatus
app.register_functions(kovaci_linka_check_bp)   # POST /api/KovaciLinkaCheck
app.register_functions(kovaci_linka_scan_bp)    # POST /api/KovaciLinkaScan
app.register_functions(protocol_part_insert_bp) # POST /api/ProtocolPartInsert
app.register_functions(check_insert_bp)         # Queue trigger

# Simple test function
@app.function_name(name="TestFunction")
@app.route(route="test", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Test function called")
    return func.HttpResponse("Test function works with Python 3.11!", status_code=200)
