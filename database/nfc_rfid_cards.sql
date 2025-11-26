-- NFC/RFID Cards Table for User Authentication
-- Tabuľka pre NFC/RFID karty na autentifikáciu používateľov
-- Database: Traceability_TEST (TEST ENVIRONMENT)
-- Poznámka: Pre produkciu zmeňte na USE [Traceability]

USE [Traceability_TEST]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Create table for NFC/RFID cards
-- Vytvorenie tabuľky pre NFC/RFID karty
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[nfc_rfid_cards]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[nfc_rfid_cards](
        [card_id] [varchar](50) NOT NULL,
        [employee_name] [varchar](100) NOT NULL,
        [employee_id] [varchar](100) NULL,
        [is_active] [bit] NOT NULL DEFAULT 1,
        [created_at] [datetime] NOT NULL DEFAULT GETDATE(),
        [last_used] [datetime] NULL,
        [created_by] [varchar](100) NULL,
        [notes] [varchar](500) NULL,
        PRIMARY KEY CLUSTERED ([card_id] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
    ) ON [PRIMARY]
    
    -- Create index on employee_name for faster lookups
    CREATE NONCLUSTERED INDEX [IX_nfc_rfid_cards_employee_name] 
    ON [dbo].[nfc_rfid_cards] ([employee_name] ASC)
    
    -- Create index on is_active for filtering active cards
    CREATE NONCLUSTERED INDEX [IX_nfc_rfid_cards_is_active] 
    ON [dbo].[nfc_rfid_cards] ([is_active] ASC)
    
    PRINT 'Table [dbo].[nfc_rfid_cards] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[nfc_rfid_cards] already exists.'
END
GO

-- Create stored procedure to authenticate user by card ID
-- Vytvorenie stored procedure na autentifikáciu používateľa podľa ID karty
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sp_authenticate_card]') AND type in (N'P', N'PC'))
    DROP PROCEDURE [dbo].[sp_authenticate_card]
GO

CREATE PROCEDURE [dbo].[sp_authenticate_card]
    @card_id VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @employee_name VARCHAR(100);
    DECLARE @employee_id VARCHAR(100);
    DECLARE @is_active BIT;
    
    -- Get card information
    SELECT 
        @employee_name = employee_name,
        @employee_id = employee_id,
        @is_active = is_active
    FROM [dbo].[nfc_rfid_cards]
    WHERE card_id = @card_id;
    
    -- Check if card exists
    IF @employee_name IS NULL
    BEGIN
        SELECT 
            'error' AS status,
            'Card not found' AS message,
            NULL AS employee_name,
            NULL AS employee_id;
        RETURN;
    END
    
    -- Check if card is active
    IF @is_active = 0
    BEGIN
        SELECT 
            'error' AS status,
            'Card is deactivated' AS message,
            NULL AS employee_name,
            NULL AS employee_id;
        RETURN;
    END
    
    -- Update last_used timestamp
    UPDATE [dbo].[nfc_rfid_cards]
    SET last_used = GETDATE()
    WHERE card_id = @card_id;
    
    -- Return success with user information
    SELECT 
        'success' AS status,
        'Authentication successful' AS message,
        @employee_name AS employee_name,
        @employee_id AS employee_id;
END
GO

-- Create stored procedure to get all active cards
-- Vytvorenie stored procedure na získanie všetkých aktívnych kariet
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sp_get_all_cards]') AND type in (N'P', N'PC'))
    DROP PROCEDURE [dbo].[sp_get_all_cards]
GO

CREATE PROCEDURE [dbo].[sp_get_all_cards]
    @include_inactive BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @include_inactive = 1
    BEGIN
        SELECT 
            card_id,
            employee_name,
            employee_id,
            is_active,
            created_at,
            last_used,
            created_by,
            notes
        FROM [dbo].[nfc_rfid_cards]
        ORDER BY employee_name, created_at DESC;
    END
    ELSE
    BEGIN
        SELECT 
            card_id,
            employee_name,
            employee_id,
            is_active,
            created_at,
            last_used,
            created_by,
            notes
        FROM [dbo].[nfc_rfid_cards]
        WHERE is_active = 1
        ORDER BY employee_name, created_at DESC;
    END
END
GO

PRINT 'NFC/RFID cards table and stored procedures created successfully.'
GO

