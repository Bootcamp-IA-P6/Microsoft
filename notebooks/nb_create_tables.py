# Fabric notebook — contract v4.3.1 · Phase 2 thin orchestrator
# Prereq: upload repo `pipeline/` → Lakehouse Files/python/pipeline/
# Guide: docs/manual-lakehouse-ingestion.md

# COMMAND ----------

# MAGIC %md
# MAGIC # Create / migrate tables (contract v4.3.1 · Phase 2)
# MAGIC Modules under `Files/python/pipeline/`.

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_create_tables import run_create_tables

run_create_tables(spark)
