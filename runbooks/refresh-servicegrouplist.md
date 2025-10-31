# `serviceGroupLabelValues` filter dropdown not refreshed in Kloudfuse UI 

## **Summary**
When the **APM Services list filter dropdown** (`serviceGroupLabelValues`) fails to refresh or shows outdated entries in the Kloudfuse UI, the root cause is typically that the **ApmStore (orchestrator DB)** has not been updated from the **Pinot traces data source**.  
This results in missing or stale service entries in dashboards and filters.

---

## **Impact**
- Affected UI: APM → Services or Traces filter dropdown.  
- Users see incomplete or outdated dropdown values.    
- No data loss — this is a metadata synchronization issue only. You can always see services details in `All` option

---

## **Root Cause**
- The **trace query service** periodically populates the orchestrator database from **Pinot**.  
- In some cases, this refresh process may be **delayed**, **stuck**
- Until refreshed, the `serviceGroupLabelValues` in the UI will remain stale.


## **Resolution Steps**

### Option 1: Wait for Automatic Refresh
The system automatically triggers refresh jobs periodically (default every few hours).  
If the issue is not urgent, you can allow the next scheduled job to run.

### Option 2: Manually Trigger Refresh (Recommended for Immediate Fix)

1. Open the trace query playground:
   ```
   https://<DNS>/debug/trace/playground
   ```

2. Run the following query to force refresh of the services from Pinot:
   ```graphql
   query {
     refreshServicesInApmStore(lookbackDays: 1)
   }
   ```

3. Once executed, the orchestrator DB will be updated.
4. Reload the Kloudfuse UI → APM → Services to verify the updated list.
