# Load notebook - loads processed data into Azure SQL Database

# Accept input_path parameter from ADF
dbutils.widgets.text("input_path", "", "Input file path from Transform")
input_path = dbutils.widgets.get("input_path")

# Fallback to latest file if no parameter provided (manual testing)
if not input_path:
    input_path = dbutils.fs.ls("dbfs:/mnt/pollen/silver/")[-1].path
    print(f"No input_path provided, using latest file: {input_path}")

# TODO: Implement SQL loading logic
print(f"Load notebook - will load data from: {input_path}")

# Note: load.py doesn't need to return a value since it's the final step
# If it did need to return something, we'd use the same pattern as transform.py:
# if dbutils.widgets.get("input_path"):
#     dbutils.notebook.exit(result)


