import os
import json
import pandas as pd

BASE_DIR = r"C:\Users\DELL\Desktop\assignment webvory\ai_agent_workflows"
os.makedirs(os.path.join(BASE_DIR, "core"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "tools"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "tests"), exist_ok=True)

print("1. Creating directory structure... Done.")

# --- 1. Generate Excel File with Workflows & Test_Questions ---
workflows_data = [
    {"Workflow_ID": "WF001", "Workflow_Name": "Inventory Restock Check", "Trigger": "User asks which products need restocking", "Inputs": "Product inventory CSV; minimum stock threshold", "Steps": "Load inventory → compare current stock with minimum threshold → identify low-stock products → calculate reorder quantity → generate restock list", "Decision_Logic": "If current_stock < minimum_stock, mark product for restock", "Tools_Required": "CSV reader; calculator", "Expected_Output": "List of products requiring restock with current stock, threshold, and suggested reorder quantity"},
    {"Workflow_ID": "WF002", "Workflow_Name": "Product Price Validation", "Trigger": "User asks to validate product prices", "Inputs": "Product CSV; vendor price list", "Steps": "Load product prices → match products by SKU → compare internal and vendor prices → calculate percentage difference → flag exceptions", "Decision_Logic": "Flag when price difference exceeds 10%", "Tools_Required": "CSV reader; calculator", "Expected_Output": "Validation report showing matched products, price differences, and exceptions"},
    {"Workflow_ID": "WF003", "Workflow_Name": "Vendor File Processing", "Trigger": "User provides a vendor file for processing", "Inputs": "CSV/XLSX file containing vendor product data", "Steps": "Read file → detect columns → normalize column names → validate required fields → identify invalid rows → produce cleaned dataset", "Decision_Logic": "Rows missing SKU or product name are invalid", "Tools_Required": "Excel/CSV parser; data validation", "Expected_Output": "Cleaned file plus validation summary and invalid-row report"},
    {"Workflow_ID": "WF004", "Workflow_Name": "Product Description Generator", "Trigger": "User asks to generate product content", "Inputs": "Product name; category; attributes; material; color; target audience", "Steps": "Validate required attributes → create product description → generate short description → generate SEO title → generate meta description", "Decision_Logic": "Do not invent missing product attributes; explicitly mark missing information", "Tools_Required": "LLM; text validation", "Expected_Output": "Product description, short description, SEO title, and meta description"},
    {"Workflow_ID": "WF005", "Workflow_Name": "Customer Order Status", "Trigger": "User asks for an order status", "Inputs": "Order ID or customer email", "Steps": "Validate identifier → search order data → retrieve order status → retrieve shipment information → summarize current status", "Decision_Logic": "If no order is found, ask for another identifier", "Tools_Required": "Order database/API; shipment lookup", "Expected_Output": "Order status, items, shipment status, and tracking information when available"},
    {"Workflow_ID": "WF006", "Workflow_Name": "Duplicate Product Detection", "Trigger": "User asks to find duplicate products", "Inputs": "Product catalog", "Steps": "Load products → normalize names/SKUs → compare identifiers → compare product attributes → group likely duplicates → assign confidence", "Decision_Logic": "Exact SKU match is a definite duplicate; high attribute similarity is a possible duplicate", "Tools_Required": "CSV/database reader; text similarity", "Expected_Output": "Duplicate groups with matching fields and confidence level"},
    {"Workflow_ID": "WF007", "Workflow_Name": "Marketing Campaign Brief", "Trigger": "User asks to create a campaign brief", "Inputs": "Campaign goal; product list; target audience; promotion; dates", "Steps": "Validate inputs → identify campaign objective → summarize products → create messaging → create channel recommendations → create campaign checklist", "Decision_Logic": "If campaign goal or dates are missing, request them before generating the brief", "Tools_Required": "LLM; product data reader", "Expected_Output": "Structured campaign brief with objective, audience, messaging, channels, timeline, and checklist"},
    {"Workflow_ID": "WF008", "Workflow_Name": "SEO Keyword Classification", "Trigger": "User uploads or provides a keyword list", "Inputs": "Keyword CSV; product/category information", "Steps": "Read keywords → remove duplicates → classify search intent → map keywords to categories → identify high-priority keywords → export results", "Decision_Logic": "Classify each keyword as informational, commercial, transactional, or navigational", "Tools_Required": "CSV reader; LLM/classifier", "Expected_Output": "Keyword report with intent, category, priority, and recommended target page"},
    {"Workflow_ID": "WF009", "Workflow_Name": "Employee Task Assignment", "Trigger": "Manager asks the agent to assign a task", "Inputs": "Task description; employee list; skills; workload; priority; deadline", "Steps": "Understand task requirements → compare employee skills → check current workload → rank candidates → select employee → generate assignment summary", "Decision_Logic": "Prefer employees with required skills and available capacity; escalate if no suitable employee exists", "Tools_Required": "Employee/task database; ranking logic", "Expected_Output": "Recommended employee, reasoning, priority, deadline, and task summary"},
    {"Workflow_ID": "WF010", "Workflow_Name": "Workflow Performance Report", "Trigger": "User asks for a performance report", "Inputs": "Workflow execution logs", "Steps": "Load execution logs → calculate success/failure rate → calculate average execution time → identify frequent errors → identify slow steps → generate recommendations", "Decision_Logic": "Flag workflows with failure rate above 10% or average execution time above defined threshold", "Tools_Required": "CSV/database reader; calculator; reporting", "Expected_Output": "Performance summary with metrics, problem areas, and improvement recommendations"}
]

test_questions_data = [
    {"Workflow_ID": "WF001", "Test_Request": "Which products need restocking?", "What_To_Check": "Tests workflow selection and threshold logic"},
    {"Workflow_ID": "WF002", "Test_Request": "Find products where vendor price differs by more than 10%.", "What_To_Check": "Tests comparison and decision logic"},
    {"Workflow_ID": "WF003", "Test_Request": "Process this vendor spreadsheet and show invalid rows.", "What_To_Check": "Tests file ingestion and validation"},
    {"Workflow_ID": "WF004", "Test_Request": "Generate SEO content for this product.", "What_To_Check": "Tests LLM workflow and missing-data handling"},
    {"Workflow_ID": "WF005", "Test_Request": "Where is order ORD-1001?", "What_To_Check": "Tests lookup and missing-order handling"},
    {"Workflow_ID": "WF006", "Test_Request": "Find likely duplicate products in the catalog.", "What_To_Check": "Tests similarity and confidence"},
    {"Workflow_ID": "WF007", "Test_Request": "Create a campaign brief for the new collection.", "What_To_Check": "Tests structured content generation"},
    {"Workflow_ID": "WF008", "Test_Request": "Classify these keywords and map them to pages.", "What_To_Check": "Tests classification and mapping"},
    {"Workflow_ID": "WF009", "Test_Request": "Assign this urgent task to the best available developer.", "What_To_Check": "Tests ranking and decision logic"},
    {"Workflow_ID": "WF010", "Test_Request": "Which workflows are failing most often?", "What_To_Check": "Tests aggregation and reporting"}
]

excel_path = os.path.join(BASE_DIR, "AI_Agent_Workflow_Assessment (1).xlsx")
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    pd.DataFrame(workflows_data).to_excel(writer, sheet_name="Workflows", index=False)
    pd.DataFrame(test_questions_data).to_excel(writer, sheet_name="Test_Questions", index=False)
print("2. Excel Assessment file created at:", excel_path)

# --- 2. Generate Mock Data Files in ai_agent_workflows/data/ ---
data_dir = os.path.join(BASE_DIR, "data")

# WF001 - inventory.csv
pd.DataFrame([
    {"sku": "SKU-101", "product_name": "Ergonomic Chair", "current_stock": 4, "minimum_stock": 10, "reorder_batch_size": 15},
    {"sku": "SKU-102", "product_name": "Mechanical Keyboard", "current_stock": 25, "minimum_stock": 15, "reorder_batch_size": 20},
    {"sku": "SKU-103", "product_name": "USB-C Docking Station", "current_stock": 2, "minimum_stock": 8, "reorder_batch_size": 10},
    {"sku": "SKU-104", "product_name": "Wireless Mouse", "current_stock": 18, "minimum_stock": 12, "reorder_batch_size": 25}
]).to_csv(os.path.join(data_dir, "inventory.csv"), index=False)

# WF002 - internal_prices.csv
pd.DataFrame([
    {"sku": "SKU-201", "product_name": "4K Gaming Monitor", "internal_price": 300.00},
    {"sku": "SKU-202", "product_name": "Laptop Stand Aluminum", "internal_price": 40.00},
    {"sku": "SKU-203", "product_name": "Webcam 1080p", "internal_price": 50.00}
]).to_csv(os.path.join(data_dir, "internal_prices.csv"), index=False)

# WF002 - vendor_prices.csv
pd.DataFrame([
    {"sku": "SKU-201", "vendor_price": 345.00}, # 15% diff (>10%)
    {"sku": "SKU-202", "vendor_price": 42.00},  # 5% diff
    {"sku": "SKU-203", "vendor_price": 42.50}   # -15% diff (>10%)
]).to_csv(os.path.join(data_dir, "vendor_prices.csv"), index=False)

# WF003 - vendor_raw_feed.xlsx (messy headers, missing SKU/name)
pd.DataFrame([
    {"vendor_sku": "VN-301", "item_title": "Bluetooth Speaker", "cost": 35.0},
    {"vendor_sku": None, "item_title": "Power Bank 20000mAh", "cost": 22.0},  # Invalid - missing SKU
    {"vendor_sku": "VN-303", "item_title": None, "cost": 15.0}                # Invalid - missing name
]).to_excel(os.path.join(data_dir, "vendor_raw_feed.xlsx"), index=False)

# WF005 - orders.json
with open(os.path.join(data_dir, "orders.json"), "w") as f:
    json.dump({
        "ORD-1001": {"email": "user@example.com", "items": ["Desk Mat", "Keyboard"], "status": "Shipped", "tracking": "TRK-9901", "carrier": "FedEx"}
    }, f, indent=2)

# WF006 - catalog.csv (with duplicates)
pd.DataFrame([
    {"sku": "CAT-001", "name": "Apple iPhone 15 Pro 128GB Black"},
    {"sku": "CAT-001", "name": "Apple iPhone 15 Pro 128GB Black"}, # Exact SKU match
    {"sku": "CAT-002", "name": "Apple iPhone 15 Pro 128GB Space Black"}, # High similarity
    {"sku": "CAT-003", "name": "Samsung Galaxy S24"}
]).to_csv(os.path.join(data_dir, "catalog.csv"), index=False)

# WF008 - keywords.csv (with duplicates)
pd.DataFrame([
    {"keyword": "buy mechanical keyboard online"},
    {"keyword": "how to clean keycaps"},
    {"keyword": "buy mechanical keyboard online"}, # Duplicate
    {"keyword": "best budget keyboard 2026"}
]).to_csv(os.path.join(data_dir, "keywords.csv"), index=False)

# WF009 - employees.json
with open(os.path.join(data_dir, "employees.json"), "w") as f:
    json.dump([
        {"id": "EMP-01", "name": "Alice Chen", "skills": ["Python", "FastAPI"], "active_tasks": 1, "capacity": 4},
        {"id": "EMP-02", "name": "Bob Miller", "skills": ["React"], "active_tasks": 4, "capacity": 4}
    ], f, indent=2)

# WF010 - execution_logs.csv (WF002 has >10% failure rate)
pd.DataFrame([
    {"workflow_id": "WF001", "time_ms": 110, "status": "SUCCESS"},
    {"workflow_id": "WF002", "time_ms": 280, "status": "FAILED"},
    {"workflow_id": "WF002", "time_ms": 310, "status": "FAILED"},
    {"workflow_id": "WF002", "time_ms": 190, "status": "SUCCESS"}
]).to_csv(os.path.join(data_dir, "execution_logs.csv"), index=False)

print("3. All mock datasets created in:", data_dir)
print("\nInitialization Complete! Ready for Phase 2 implementation.")