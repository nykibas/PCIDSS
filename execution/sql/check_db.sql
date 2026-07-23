-- Check Oracle Database health, tablespace usage, and active wait events
SET PAGESIZE 100
SET LINESIZE 200
COLUMN tablespace_name FORMAT A25
COLUMN "Size (MB)" FORMAT 999,999,999
COLUMN "Used (MB)" FORMAT 999,999,999
COLUMN "Free (MB)" FORMAT 999,999,999
COLUMN "% Used" FORMAT 990.99

PROMPT =========================================================================
PROMPT 1. TABLESPACE USAGE CHECK
PROMPT =========================================================================

SELECT 
    d.tablespace_name,
    NVL(a.bytes / 1024 / 1024, 0) "Size (MB)",
    NVL((a.bytes - NVL(f.bytes, 0)) / 1024 / 1024, 0) "Used (MB)",
    NVL(f.bytes / 1024 / 1024, 0) "Free (MB)",
    NVL(((a.bytes - NVL(f.bytes, 0)) / a.bytes) * 100, 0) "% Used"
FROM 
    sys.dba_tablespaces d,
    (SELECT tablespace_name, SUM(bytes) bytes FROM dba_data_files GROUP BY tablespace_name) a,
    (SELECT tablespace_name, SUM(bytes) bytes FROM dba_free_space GROUP BY tablespace_name) f
WHERE 
    d.tablespace_name = a.tablespace_name(+)
    AND d.tablespace_name = f.tablespace_name(+)
ORDER BY 
    "% Used" DESC;

PROMPT
PROMPT =========================================================================
PROMPT 2. TOP ACTIVE WAIT EVENTS (ASH-like current waits)
PROMPT =========================================================================

COLUMN event FORMAT A40
SELECT 
    event,
    COUNT(*) "Session Count",
    ROUND(ratio_to_report(COUNT(*)) OVER () * 100, 2) "% Activity"
FROM 
    v$active_session_history
WHERE 
    sample_time > SYSDATE - 1/24 -- Last 1 hour
    AND session_state = 'WAITING'
GROUP BY 
    event
ORDER BY 
    COUNT(*) DESC
FETCH FIRST 10 ROWS ONLY;

PROMPT
PROMPT =========================================================================
PROMPT 3. SYSTEM STATS & INSTANCE DETAILS
PROMPT =========================================================================

SELECT instance_name, host_name, version, status, database_status FROM v$instance;

EXIT;
