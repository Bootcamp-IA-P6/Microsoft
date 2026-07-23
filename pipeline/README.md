# EMT Madrid Spark pipeline (Phase 2)

Upload this folder to Fabric Lakehouse:

```text
Files/python/pipeline/   ← contents of this package
```

Notebooks add `/lakehouse/default/Files/python` to `sys.path`, then:

```python
from pipeline.orchestrator.run_arrives import run_arrives
```

No Fabric Environment / whl required (Starter Pool friendly).

Contract tables unchanged: `bronze_emt_raw`, `silver_arrives`, `silver_alerts`, `gold_emt_stop_line`.
