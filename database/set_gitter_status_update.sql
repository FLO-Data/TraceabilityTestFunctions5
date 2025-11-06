-- Updated stored procedure set_gitter_status with employee_id parameter
-- Aktualizovaná stored procedure set_gitter_status s parametrem employee_id

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

ALTER PROCEDURE [dbo].[set_gitter_status]
    @station_id VARCHAR(100),
    @status VARCHAR(20),
    @status_timestamp DATETIME,
    @shipping_id VARCHAR(50),
    @current_workspace_id INT,
    @employee_id VARCHAR(100) = NULL  -- New parameter / Nový parametr
AS
BEGIN
    -- If employee_id is provided, append '_virtual' suffix to indicate virtual/automatic action
    -- If employee_id is NULL or empty, use 'virtual'
    -- Pokud employee_id je poskytnut, přidá se suffix '_virtual' pro označení virtuální/automatické akce
    -- Pokud employee_id je NULL nebo prázdný, použije se 'virtual'
    DECLARE @actual_employee_id VARCHAR(100) = 
        CASE 
            WHEN @employee_id IS NOT NULL AND LEN(LTRIM(RTRIM(@employee_id))) > 0 
                THEN @employee_id + '_virtual'
            ELSE 'virtual'
        END;

    INSERT INTO traceability_log (
        part_id,
        employee_id,
        station_id,
        [status],
        status_timestamp,
        shipping_id
    )
    SELECT 
        part_id,
        @actual_employee_id AS employee_id,  -- Use parameter or 'virtual_auto' if not provided
        @current_workspace_id AS station_id,
        @status AS [status],
        @status_timestamp AS status_timestamp,
        @shipping_id AS shipping_id
    FROM dbo.part_status
    WHERE
        station_id = @station_id
        --AND [last_status] = @status
        AND shipping_id = @shipping_id;
END
GO

