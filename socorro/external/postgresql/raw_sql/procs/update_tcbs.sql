CREATE OR REPLACE FUNCTION update_tcbs(
    updateday date,
    checkdata boolean DEFAULT true,
    check_period interval DEFAULT '01:00:00'::interval
) RETURNS boolean
    LANGUAGE plpgsql
    SET client_min_messages TO 'ERROR'
AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
    PERFORM 1 FROM tcbs
    WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'TCBS has already been run for the day %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE NOTICE 'Reports_clean has not been updated to the end of %',updateday;
        RETURN FALSE;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- populate the matview for regular releases

INSERT INTO tcbs (
    signature_id,
    report_date,
    product_version_id,
    process_type,
    release_channel,
    report_count,
    win_count,
    mac_count,
    lin_count,
    hang_count,
    startup_count,
    is_gc_count,
    build_type
)
WITH raw_crash_filtered AS (
    SELECT
          uuid
        , json_object_field_text(r.raw_crash, 'IsGarbageCollecting') as is_garbage_collecting
    FROM
        raw_crashes r
    WHERE
        date_processed BETWEEN updateday::timestamptz
            AND updateday::timestamptz + '1 day'::interval
)
SELECT signature_id
    , updateday
    , product_version_id
    , process_type
    , coalesce(reports_clean.build_type::text, lower(reports_clean.release_channel)) as release_channel
    , count(*)
    , sum(case when os_name = 'Windows' THEN 1 else 0 END)
    , sum(case when os_name = 'Mac OS X' THEN 1 else 0 END)
    , sum(case when os_name = 'Linux' THEN 1 else 0 END)
    , count(hang_id)
    , sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
    , sum(CASE WHEN r.is_garbage_collecting = '1' THEN 1 ELSE 0 END) as gc_count
    , coalesce(reports_clean.build_type, lower(reports_clean.release_channel)::build_type) as build_type
FROM reports_clean
    JOIN product_versions USING (product_version_id)
    JOIN signatures USING (signature_id)
    LEFT JOIN raw_crash_filtered r ON r.uuid::text = reports_clean.uuid
WHERE utc_day_is(date_processed, updateday)
        AND tstz_between(date_processed, build_date, sunset_date)
GROUP BY signature_id, updateday, product_version_id,
    process_type, coalesce(reports_clean.build_type::text, lower(reports_clean.release_channel)),
    coalesce(reports_clean.build_type, lower(reports_clean.release_channel)::build_type);

-- populate summary statistics for rapid beta parent records

INSERT INTO tcbs (
    signature_id,
    report_date,
    product_version_id,
    process_type,
    release_channel,
    report_count,
    win_count,
    mac_count,
    lin_count,
    hang_count,
    startup_count,
    is_gc_count,
    build_type
)
SELECT signature_id
    , updateday
    , rapid_beta_id
    , process_type
    , tcbs.build_type
    , sum(report_count)
    , sum(win_count)
    , sum(mac_count)
    , sum(lin_count)
    , sum(hang_count)
    , sum(startup_count)
    , sum(is_gc_count)
    , tcbs.build_type
FROM tcbs
    JOIN product_versions USING (product_version_id)
WHERE report_date = updateday
    AND product_versions.build_type_enum = 'beta'
    AND rapid_beta_id is not null
GROUP BY
    signature_id,
    updateday,
    rapid_beta_id,
    process_type,
    release_channel,
    tcbs.build_type;

-- tcbs_ranking removed until it's being used

RETURN TRUE;
END;
$$;
